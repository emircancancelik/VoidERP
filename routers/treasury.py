from fastapi import APIRouter, Query
from core.engine import generate_aging_table, generate_cash_position

aging_router = APIRouter(prefix="/odata/sap/fi", tags=["Aging"])


@aging_router.get("/aging")
def get_aging_table(
    top: int = Query(8, alias="$top", ge=1, le=20),
):
    rows = generate_aging_table(customer_count=top)
    return {
        "@odata.context": "$metadata#AgingReport",
        "@odata.count":   len(rows),
        "value":          rows,
    }

treasury_router = APIRouter(prefix="/odata/sap/treasury", tags=["Treasury"])


@treasury_router.get("/cash-position")
def get_cash_position():
    """
    SAP Cash Management nakit pozisyonu.
    FF7A / TRM Cash Position raporu yapısını taklit eder.
    """
    position = generate_cash_position()
    return {
        "@odata.context": "$metadata#CashPosition",
        "value":          position,
    }