import uuid
import time
import math
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Sabit referans verisi — gerçek SAP master data yapısını taklit eder
COMPANY_CODES   = ["TR01", "DE02", "US03"]
COST_CENTERS    = ["CC-FIN-001", "CC-OPS-002", "CC-PROC-003", "CC-IT-004"]
CURRENCIES      = ["USD", "EUR", "TRY"]
DOCUMENT_TYPES  = ["KR", "ZP", "RE", "AB"]   # SAP FI belge tipleri
PAYMENT_TERMS   = ["NET30", "NET60", "IMMED"]
VENDOR_POOL     = [f"VENDOR-{str(i).zfill(4)}" for i in range(1, 21)]
CUSTOMER_POOL   = [f"CUST-{str(i).zfill(4)}" for i in range(1, 16)]

# Anomali ağırlıkları
ANOMALY_WEIGHTS = {
    "normal":           0.70,
    "large_amount":     0.12,
    "duplicate":        0.08,
    "overdue":          0.07,
    "invalid_currency": 0.03,
}


def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _date_offset(days: int) -> str:
    return (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d")


def _pick_scenario() -> str:
    return random.choices(
        list(ANOMALY_WEIGHTS.keys()),
        weights=list(ANOMALY_WEIGHTS.values()),
        k=1
    )[0]


def _anomaly_score(scenario: str, amount: float) -> float:
    base = {
        "normal":           0.05 + amount / 2_000_000,
        "large_amount":     0.72 + amount / 1_000_000,
        "duplicate":        0.88,
        "overdue":          0.65,
        "invalid_currency": 0.91,
    }[scenario]
    return round(min(base + random.uniform(0.0, 0.05), 0.99), 4)


# ------------------------------------------------------------------ #
#  FI DOCUMENT                                                         #
# ------------------------------------------------------------------ #
def generate_fi_document(seed: int = None) -> Dict[str, Any]:
    if seed is not None:
        random.seed(seed)

    scenario = _pick_scenario()
    currency = "XYZ" if scenario == "invalid_currency" else random.choice(CURRENCIES)

    if scenario == "large_amount":
        amount = round(random.uniform(80_000, 200_000), 2)
    elif scenario == "duplicate":
        amount = 12_500.00   # sabit tutar — duplicate tespiti için
    else:
        amount = round(random.uniform(500, 18_000), 2)

    doc_date   = _date_offset(0)
    base_line  = _date_offset(-random.randint(0, 90))
    due_date   = _date_offset(random.randint(-30, 60) if scenario != "overdue" else -random.randint(31, 120))

    doc: Dict[str, Any] = {
        "DocumentNumber":    f"19{random.randint(10_000_000, 99_999_999)}",
        "CompanyCode":       random.choice(COMPANY_CODES),
        "FiscalYear":        str(datetime.utcnow().year),
        "DocumentType":      random.choice(DOCUMENT_TYPES),
        "PostingDate":       doc_date,
        "DocumentDate":      doc_date,
        "NetDueDate":        due_date,
        "BaselineDate":      base_line,
        "Vendor":            random.choice(VENDOR_POOL),
        "Customer":          random.choice(CUSTOMER_POOL),
        "CostCenter":        random.choice(COST_CENTERS),
        "AmountInDocCurr":   amount,
        "DocumentCurrency":  currency,
        "PaymentTerms":      random.choice(PAYMENT_TERMS),
        "ClearingStatus":    "O" if scenario in ("overdue", "duplicate") else random.choice(["C", "O"]),
        # VoidERP meta alanları
        "_meta": {
            "tx_id":         f"TXN-{uuid.uuid4().hex[:8].upper()}",
            "scenario":      scenario,
            "anomaly_score": _anomaly_score(scenario, amount),
            "atr_value":     round(amount * random.uniform(0.003, 0.012), 2),
            "source":        "SAP_S4HANA_MOCK",
            "generated_at":  _now_iso(),
        }
    }
    return doc


# ------------------------------------------------------------------ #
#  AGING TABLE                                                         #
# ------------------------------------------------------------------ #
def generate_aging_table(customer_count: int = 8) -> List[Dict[str, Any]]:
    rows = []
    for cust in random.sample(CUSTOMER_POOL, min(customer_count, len(CUSTOMER_POOL))):
        current      = round(random.uniform(0, 50_000), 2)
        days_1_30    = round(random.uniform(0, 30_000), 2)
        days_31_60   = round(random.uniform(0, 20_000), 2)
        days_61_90   = round(random.uniform(0, 10_000), 2)
        days_over_90 = round(random.uniform(0, 8_000), 2)
        total        = round(current + days_1_30 + days_31_60 + days_61_90 + days_over_90, 2)

        rows.append({
            "Customer":       cust,
            "CompanyCode":    random.choice(COMPANY_CODES),
            "Currency":       "USD",
            "Current":        current,
            "Days1to30":      days_1_30,
            "Days31to60":     days_31_60,
            "Days61to90":     days_61_90,
            "DaysOver90":     days_over_90,
            "TotalOpen":      total,
            "RiskCategory":   "HIGH" if days_over_90 > 5_000 else ("MEDIUM" if days_61_90 > 3_000 else "LOW"),
        })
    return rows


# ------------------------------------------------------------------ #
#  CASH POSITION                                                       #
# ------------------------------------------------------------------ #
def generate_cash_position() -> Dict[str, Any]:
    accounts = []
    total_balance = 0.0

    for cc in COMPANY_CODES:
        for currency in ["USD", "EUR", "TRY"]:
            balance = round(random.uniform(10_000, 500_000), 2)
            total_balance += balance if currency == "USD" else balance * (0.92 if currency == "EUR" else 0.031)

            accounts.append({
                "CompanyCode":    cc,
                "HouseBank":      f"BANK-{cc}",
                "AccountID":      f"ACC-{cc}-{currency}",
                "Currency":       currency,
                "ClosingBalance": balance,
                "ValueDate":      _date_offset(0),
                "PlanningLevel":  "F1",
            })

    return {
        "Accounts":           accounts,
        "TotalUSDEquivalent": round(total_balance, 2),
        "AsOf":               _now_iso(),
        "LiquidityRatio":     round(random.uniform(1.1, 3.5), 3),
    }