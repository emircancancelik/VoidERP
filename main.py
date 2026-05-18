from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time

from routers.fi       import router        as fi_router
from routers.treasury import aging_router, treasury_router

app = FastAPI(
    title="VoidERP SAP S/4HANA Mock",
    description="SAP FI / Treasury OData v4 mock service for VoidERP hackathon pipeline.",
    version="1.0.0",
    docs_url="/sap/api-docs",
    redoc_url="/sap/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(fi_router)
app.include_router(aging_router)
app.include_router(treasury_router)


@app.get("/sap/health")
def health():
    return {
        "status":    "UP",
        "service":   "SAP_S4HANA_MOCK",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@app.get("/sap/metadata")
def metadata():
    """Desteklenen endpoint listesi — SAP $metadata yerine basit manifest."""
    return {
        "endpoints": [
            {"path": "/odata/sap/fi/documents",        "method": "GET", "params": ["$top", "$skip", "$filter"]},
            {"path": "/odata/sap/fi/documents/{id}",   "method": "GET"},
            {"path": "/odata/sap/fi/aging",            "method": "GET", "params": ["$top"]},
            {"path": "/odata/sap/treasury/cash-position", "method": "GET"},
        ]
    }