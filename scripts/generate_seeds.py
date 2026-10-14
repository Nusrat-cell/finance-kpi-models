"""Writes the ERP-style seed CSVs in seeds/.

The data is invented but shaped like an export from an ERP system of a
company selling scientific lasers worldwide: invoices in EUR, USD and JPY,
payments that arrive late, credit notes, and a monthly budget per product line.
Two problems found in real exports are included on purpose:
  * one invoice line exported twice
  * one customer paying in two instalments
Run: python scripts/generate_seeds.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEEDS = Path(__file__).resolve().parent.parent / "seeds"
rng = random.Random(42)

customers = [
    # id, name, country, segment, payment terms (days)
    ("C001", "Nordic Quantum Lab", "DK", "Research", 30),
    ("C002", "Uppsala Photonics Institute", "SE", "Research", 30),
    ("C003", "Rhein Microscopy GmbH", "DE", "Industrial", 45),
    ("C004", "Boston BioImaging Inc", "US", "Medical", 60),
    ("C005", "Kyoto Precision Optics", "JP", "Industrial", 60),
    ("C006", "Lyon Semiconductor SA", "FR", "Industrial", 45),
    ("C007", "Delft Space Systems", "NL", "Research", 30),
    ("C008", "California Ophthalmics", "US", "Medical", 60),
]
currency_by_country = {"US": "USD", "JP": "JPY"}

products = [
    # id, name, product line, standard cost EUR, list price EUR
    ("P10", "Supercontinuum Compact", "Supercontinuum", 21000, 42000),
    ("P11", "Supercontinuum High Power", "Supercontinuum", 48000, 89000),
    ("P20", "Femtosecond Oscillator", "Ultrafast", 36000, 65000),
    ("P21", "Femtosecond Amplifier", "Ultrafast", 52000, 98000),
    ("P30", "Photonic Crystal Fiber, 10 m", "Fiber", 900, 2400),
    ("P40", "Service contract, 12 months", "Service", 2500, 9000),
]

# Monthly average rates, units of DKK per 1 unit of currency.
months = [date(2026, m, 1) for m in range(1, 10)]
fx = {}
for i, m in enumerate(months):
    fx[(m, "DKK")] = 1.0
    fx[(m, "EUR")] = round(7.458 + rng.uniform(-0.004, 0.004), 4)
    fx[(m, "USD")] = round(6.85 - i * 0.03 + rng.uniform(-0.05, 0.05), 4)
    fx[(m, "JPY")] = round(0.0462 - i * 0.0003 + rng.uniform(-0.0006, 0.0006), 5)

invoice_lines, payments = [], []
inv_no, pay_no = 1000, 5000
for m in months:
    for _ in range(rng.randint(9, 14)):
        cust = rng.choice(customers)
        currency = currency_by_country.get(cust[2], "DKK" if cust[2] == "DK" else "EUR")
        inv_date = m + timedelta(days=rng.randint(0, 27))
        inv_no += 1
        n_lines = rng.choice([1, 1, 2, 3])
        total_dkk = 0.0
        for line in range(1, n_lines + 1):
            prod = rng.choice(products)
            qty = rng.choice([1, 1, 1, 2]) if prod[2] != "Fiber" else rng.randint(2, 12)
            discount = rng.choice([0, 0, 0.05, 0.1])
            price_eur = prod[4] * (1 - discount)
            price = round(price_eur * fx[(m, "EUR")] / fx[(m, currency)], 2 if currency != "JPY" else 0)
            invoice_lines.append({
                "invoice_id": f"INV{inv_no}", "line_no": line, "invoice_date": inv_date.isoformat(),
                "customer_id": cust[0], "product_id": prod[0], "quantity": qty,
                "unit_price": price, "currency": currency,
                "due_date": (inv_date + timedelta(days=cust[4])).isoformat(),
            })
            total_dkk += qty * price * fx[(m, currency)]
        # Payment behaviour: most pay a bit late, some very late, recent ones still open.
        delay = rng.choice([-5, 0, 3, 8, 15, 25, 40])
        pay_date = inv_date + timedelta(days=cust[4] + delay)
        if pay_date <= date(2026, 9, 30):
            total = sum(l["quantity"] * l["unit_price"] for l in invoice_lines if l["invoice_id"] == f"INV{inv_no}")
            pay_no += 1
            payments.append({"payment_id": f"PAY{pay_no}", "invoice_id": f"INV{inv_no}",
                             "payment_date": pay_date.isoformat(), "amount": round(total, 2), "currency": currency})

# A credit note: part of an earlier invoice returned.
first = invoice_lines[3]
invoice_lines.append({**first, "invoice_id": "CRN0001", "line_no": 1, "quantity": -1,
                      "invoice_date": (date.fromisoformat(first["invoice_date"]) + timedelta(days=20)).isoformat()})
# One instalment payment split in two.
split = payments[10]
payments[10] = {**split, "amount": round(split["amount"] * 0.6, 2)}
payments.append({**split, "payment_id": "PAY9999", "amount": round(split["amount"] - round(split["amount"] * 0.6, 2), 2),
                 "payment_date": (date.fromisoformat(split["payment_date"]) + timedelta(days=14)).isoformat()})
# The same invoice line exported twice.
invoice_lines.append(dict(invoice_lines[25]))

budget = []
base = {"Supercontinuum": 3600000, "Ultrafast": 4700000, "Fiber": 420000, "Service": 380000}
for i, m in enumerate(months):
    for line, b in base.items():
        budget.append({"month": m.isoformat(), "product_line": line,
                       "budget_revenue_dkk": round(b * (1 + 0.015 * i), 0)})


def write(name, rows, fields=None):
    fields = fields or list(rows[0].keys())
    with open(SEEDS / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


SEEDS.mkdir(exist_ok=True)
write("erp_customers.csv", [dict(zip(["customer_id", "customer_name", "country", "segment", "payment_terms_days"], c)) for c in customers])
write("erp_products.csv", [dict(zip(["product_id", "product_name", "product_line", "standard_cost_eur", "list_price_eur"], p)) for p in products])
write("erp_invoice_lines.csv", invoice_lines)
write("erp_payments.csv", payments)
write("fx_monthly_rates.csv", [{"month": m.isoformat(), "currency": c, "dkk_per_unit": r} for (m, c), r in sorted(fx.items())])
write("budget_monthly.csv", budget)
print(f"{len(invoice_lines)} invoice lines, {len(payments)} payments written to {SEEDS}")
