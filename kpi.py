"""A small dbt-style runner for the models in this repo, on SQLite.

    python kpi.py build     seed + run + test (what CI does)
    python kpi.py run       load seeds and build every model in dependency order
    python kpi.py test      run the schema tests and the SQL tests in tests/
    python kpi.py export    write the marts to exports/*.csv for Power BI
    python kpi.py dag       print the model dependency graph

Models are plain SELECT statements in models/. They point at each other with
{{ ref('name') }}, exactly like dbt, and that is how the run order is worked
out. Tests are declared in models/schema.yml in dbt's format (unique,
not_null, accepted_values, relationships), and any .sql file in tests/ is a
test that passes when it returns no rows. The SQL is kept close to standard
so the project can move to dbt on Snowflake or DuckDB with few changes.
"""

from __future__ import annotations

import csv
import re
import sqlite3
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
MODELS, SEEDS, TESTS, EXPORTS = (ROOT / d for d in ("models", "seeds", "tests", "exports"))
DB = ROOT / "warehouse.db"
REF = re.compile(r"\{\{\s*ref\(\s*['\"](\w+)['\"]\s*\)\s*\}\}")
BARE_REF = re.compile(r"ref\(\s*['\"](\w+)['\"]\s*\)")  # schema.yml writes ref('x') without braces


def discover_models() -> dict[str, Path]:
    models = {}
    for path in sorted(MODELS.rglob("*.sql")):
        if path.stem in models:
            raise SystemExit(f"Two models named {path.stem}")
        models[path.stem] = path
    return models


def seed_names() -> set[str]:
    return {p.stem for p in SEEDS.glob("*.csv")}


def dependencies(models: dict[str, Path]) -> dict[str, set[str]]:
    seeds = seed_names()
    deps = {}
    for name, path in models.items():
        refs = set(REF.findall(path.read_text()))
        unknown = refs - set(models) - seeds
        if unknown:
            raise SystemExit(f"{name} refers to unknown model(s): {', '.join(sorted(unknown))}")
        deps[name] = refs & set(models)
    return deps


def build_order(deps: dict[str, set[str]]) -> list[str]:
    order, done, visiting = [], set(), set()

    def visit(n, path):
        if n in done:
            return
        if n in visiting:
            raise SystemExit("Cycle in models: " + " -> ".join(path + [n]))
        visiting.add(n)
        for d in sorted(deps[n]):
            visit(d, path + [n])
        visiting.discard(n)
        done.add(n)
        order.append(n)

    for n in sorted(deps):
        visit(n, [])
    return order


def compile_sql(path: Path) -> str:
    # Every ref resolves to a table of the same name in the one database.
    return REF.sub(lambda m: f'"{m.group(1)}"', path.read_text())


def load_seeds(conn: sqlite3.Connection) -> None:
    for path in sorted(SEEDS.glob("*.csv")):
        with open(path, newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
        conn.execute(f'DROP TABLE IF EXISTS "{path.stem}"')
        conn.execute(f'CREATE TABLE "{path.stem}" ({", ".join(f"{c!r}" for c in header)})')
        conn.executemany(f'INSERT INTO "{path.stem}" VALUES ({", ".join("?" * len(header))})', rows)
        print(f"  seed   {path.stem:<28} {len(rows):>5} rows")


def run_models(conn: sqlite3.Connection) -> None:
    models = discover_models()
    for name in build_order(dependencies(models)):
        start = time.perf_counter()
        sql = compile_sql(models[name])
        conn.execute(f'DROP TABLE IF EXISTS "{name}"')
        try:
            conn.execute(f'CREATE TABLE "{name}" AS {sql}')
        except sqlite3.Error as err:
            raise SystemExit(f"  ERROR  {name}: {err}\n  in {models[name].relative_to(ROOT)}")
        rows = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        print(f"  model  {name:<28} {rows:>5} rows  {1000 * (time.perf_counter() - start):6.1f} ms")
    conn.commit()


# ------------------------------------------------------------------ tests

def schema_tests() -> list[tuple[str, str]]:
    """Turns models/schema.yml into (test name, SQL that returns failing rows)."""
    spec = yaml.safe_load((MODELS / "schema.yml").read_text())
    tests = []
    for model in spec["models"]:
        m = model["name"]
        for col in model.get("columns", []):
            c = col["name"]
            for t in col.get("tests", []):
                if t == "unique":
                    tests.append((f"unique_{m}_{c}",
                                  f'SELECT "{c}" FROM "{m}" GROUP BY "{c}" HAVING COUNT(*) > 1'))
                elif t == "not_null":
                    tests.append((f"not_null_{m}_{c}", f'SELECT * FROM "{m}" WHERE "{c}" IS NULL'))
                elif isinstance(t, dict) and "accepted_values" in t:
                    values = ", ".join(repr(v) for v in t["accepted_values"]["values"])
                    tests.append((f"accepted_values_{m}_{c}",
                                  f'SELECT * FROM "{m}" WHERE "{c}" NOT IN ({values})'))
                elif isinstance(t, dict) and "relationships" in t:
                    rel = t["relationships"]
                    to = BARE_REF.search(rel["to"]).group(1)
                    tests.append((f"relationships_{m}_{c}__{to}",
                                  f'SELECT * FROM "{m}" WHERE "{c}" IS NOT NULL AND "{c}" NOT IN '
                                  f'(SELECT "{rel["field"]}" FROM "{to}")'))
                else:
                    raise SystemExit(f"Unknown test {t!r} on {m}.{c}")
    return tests


def run_tests(conn: sqlite3.Connection) -> int:
    tests = schema_tests() + [(p.stem, compile_sql(p)) for p in sorted(TESTS.glob("*.sql"))]
    failures = 0
    for name, sql in tests:
        bad = conn.execute(f"SELECT COUNT(*) FROM ({sql})").fetchone()[0]
        if bad:
            failures += 1
            print(f"  FAIL   {name} ({bad} rows)")
        else:
            print(f"  pass   {name}")
    print(f"\n{len(tests) - failures} passed, {failures} failed")
    return failures


def export(conn: sqlite3.Connection) -> None:
    EXPORTS.mkdir(exist_ok=True)
    for name in [m for m in discover_models() if m.startswith(("dim_", "fct_", "kpi_"))]:
        cur = conn.execute(f'SELECT * FROM "{name}"')
        with open(EXPORTS / f"{name}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow([d[0] for d in cur.description])
            w.writerows(cur.fetchall())
        print(f"  export exports/{name}.csv")


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "build"
    if command == "dag":
        deps = dependencies(discover_models())
        for name in build_order(deps):
            print(f"{name:<28} <- {', '.join(sorted(deps[name])) or '(seeds only)'}")
        return 0
    conn = sqlite3.connect(DB)
    try:
        if command in ("run", "build"):
            load_seeds(conn)
            run_models(conn)
        if command in ("test", "build"):
            if run_tests(conn):
                return 1
        if command == "export":
            export(conn)
        if command not in ("run", "test", "build", "export"):
            print(__doc__)
            return 2
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
