import asyncio
import os
import aio_pika
import aiohttp
import json
import logging
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Literal

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage()
        })

logger = logging.getLogger("voiderp_control_pod")
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class EvaluatedTradePayload(BaseModel):
    trade_id: str
    asset_pair: str
    execution_price: float
    volume: float
    transaction_type: Literal["BUY", "SELL"]
    sap_btp_reference: str
    risk_status: Literal["NOMINAL", "HIGH_RISK"]
    evaluation_timestamp: str

class SAPBTPClient:
    def __init__(self, base_url): 
        self.base_url = base_url
        
    async def register_trade(self, payload: EvaluatedTradePayload):
        async with aiohttp.ClientSession(headers={"Authorization": "Bearer token", "Content-Type": "application/json"}) as session:
            async with session.post(f"{self.base_url}/v1/treasury/trades", json=payload.model_dump()) as resp:
                resp.raise_for_status()
                logger.info("sap_btp_execution_success", extra={"trade_id": payload.trade_id, "status": resp.status})

async def execute_trade(message: aio_pika.abc.AbstractIncomingMessage, sap_client: SAPBTPClient, exchange: aio_pika.abc.AbstractExchange):
    async with message.process(ignore_processed=True):
        try:
            trade = EvaluatedTradePayload.model_validate_json(message.body.decode())
            
            # Streamlit arayüzü için standartlaştırılmış UI çıktısı
            decision_payload = {
                "summary": {
                    "trade_id": trade.trade_id,
                    "asset_pair": trade.asset_pair,
                    "sap_btp_status": "pending"
                },
                "orchestrator_action": "",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            if trade.risk_status == "HIGH_RISK":
                logger.warning("trade_blocked_high_risk", extra={"trade_id": trade.trade_id})
                decision_payload["orchestrator_action"] = "BLOCKED_HIGH_RISK"
                decision_payload["summary"]["sap_btp_status"] = "aborted"
            else:
                await sap_client.register_trade(trade)
                decision_payload["orchestrator_action"] = "EXECUTE_TREASURY_SWAP"
                decision_payload["summary"]["sap_btp_status"] = "synced"
            
            # CRITICAL FIX: Streamlit'in dinlediği kuyruğa karbon kopya (dual-publish) basımı
            out_message = aio_pika.Message(
                body=json.dumps(decision_payload).encode('utf-8'),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json"
            )
            await exchange.publish(out_message, routing_key="voiderp.decisions")
            
            await message.ack()
        except Exception as e:
            logger.error("control_error", extra={"error": str(e)})
            await message.reject(requeue=True)

async def connect_with_retry(amqp_url, retries=5, delay=3):
    for attempt in range(1, retries + 1):
        try:
            return await aio_pika.connect_robust(amqp_url)
        except Exception:
            if attempt == retries: 
                raise
            await asyncio.sleep(delay)

async def main():
    amqp_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
    sap_url = os.getenv("SAP_MOCK_URL", "http://sap_mock:8000")
    
    sap_client = SAPBTPClient(base_url=sap_url)
    connection = await connect_with_retry(amqp_url)
    
    async with connection:
        channel = await connection.channel()
        exchange = channel.default_exchange # Streamlit'e publish yapabilmek için exchange tanımlandı
        
        await channel.set_qos(prefetch_count=5)
        in_queue = await channel.declare_queue("control_queue", durable=True)
        
        # Streamlit kuyruğunun var olduğunu garantiye al (Race condition önlemi)
        await channel.declare_queue("voiderp.decisions", durable=True)
        
        logger.info("control_pod_listening", extra={"queue": "control_queue"})
        
        # execute_trade fonksiyonuna exchange parametresi geçirildi
        await in_queue.consume(lambda msg: execute_trade(msg, sap_client, exchange))
        await asyncio.Future()

if __name__ == "__main__": 
    asyncio.run(main())