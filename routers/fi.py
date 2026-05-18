from fastapi import APIRouter, Query
from typing import Optional
import random

from core.engine import generate_fi_document

router = APIRouter(prefix="/odata/sap/fi", tags=["FI"])

ODATA_CONTEXT = "$metadata#A_AccountingDocument"


@router.get("/documents")
def get_fi_documents(
    top:    int            = Query(10, alias="$top",    ge=1, le=100),
    skip:   int            = Query(0,  alias="$skip",   ge=0),
    filter: Optional[str]  = Query(None, alias="$filter"),
):
    """
    SAP OData /A_AccountingDocument endpoint'ini taklit eder.
    Gerçek S/4HANA response yapısı: @odata.context + value[].
    $filter: CompanyCode eq 'TR01' | DocumentType eq 'KR' | scenario eq 'large_amount'
    """
    docs = [generate_fi_document(seed=None) for _ in range(top)]

    # Basit $filter desteği
    if filter:
        if "CompanyCode eq" in filter:
            cc = filter.split("'")[1]
            docs = [d for d in docs if d["CompanyCode"] == cc]
        if "DocumentType eq" in filter:
            dt = filter.split("'")[1]
            docs = [d for d in docs if d["DocumentType"] == dt]
        if "scenario eq" in filter:
            sc = filter.split("'")[1]
            docs = [d for d in docs if d["_meta"]["scenario"] == sc]

    return {
        "@odata.context": ODATA_CONTEXT,
        "@odata.count":   len(docs),
        "value":          docs[skip: skip + top],
    }


@router.get("/documents/{document_number}")
def get_fi_document_by_id(document_number: str):
    """Tek belge getir — SAP entity by key."""
    doc = generate_fi_document(seed=int(document_number[-6:], 10) if document_number[-6:].isdigit() else None)
    doc["DocumentNumber"] = document_number
    return {
        "@odata.context": f"{ODATA_CONTEXT}/$entity",
        "value":          doc,
    }