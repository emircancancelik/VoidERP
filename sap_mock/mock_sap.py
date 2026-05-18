import logging
import json
import sys
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        })

logger = logging.getLogger("mock_sap_btp")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

app = FastAPI(title="Mock SAP BTP OData Service")

class TreasuryTradePayload(BaseModel):
    trade_id: str = Field(..., max_length=64)
    asset_pair: str = Field(..., max_length=16)
    execution_price: float = Field(..., gt=0.0)
    volume: float = Field(..., gt=0.0)
    transaction_type: Literal["BUY", "SELL"]
    sap_btp_reference: str = Field(..., max_length=128)

@app.post("/v1/treasury/trades", status_code=201)
async def create_treasury_trade(payload: TreasuryTradePayload, request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.error("mock_sap_unauthorized_access", extra={"ip": request.client.host})
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    logger.info("mock_sap_trade_registered", extra={"trade_id": payload.trade_id})
    return {"d": {"TradeId": payload.trade_id, "Status": "PROCESSED_IN_MOCK"}}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
