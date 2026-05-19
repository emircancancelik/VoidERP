import asyncio
import os
import aio_pika
import json
import logging
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ValidationError
from typing import Literal

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage()
        })

logger = logging.getLogger("voiderp_data_pod")
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class RawTradePayload(BaseModel):
    trade_id: str = Field(..., max_length=64)
    asset_pair: str = Field(..., max_length=16)
    execution_price: float = Field(..., gt=0.0)
    volume: float = Field(..., gt=0.0)
    transaction_type: Literal["BUY", "SELL"]
    sap_btp_reference: str = Field(..., max_length=128)

async def process_and_forward(message: aio_pika.abc.AbstractIncomingMessage, exchange: aio_pika.abc.AbstractExchange):
    async with message.process(ignore_processed=True):
        try:
            trade = RawTradePayload.model_validate_json(message.body.decode())
            
            # 1. Pipeline Kopyası (Yapay Zeka İçin Dokunulmamış Ham Veri)
            agent_message = aio_pika.Message(
                body=trade.model_dump_json().encode('utf-8'), 
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json"
            )
            await exchange.publish(agent_message, routing_key="intelligence_queue")
            
            # 2. UI Kopyası (Streamlit panels.py 'render_financial_panel' Şemasına Kesin Uyum)
            trade_value = trade.execution_price * trade.volume
            revenue = trade_value if trade.transaction_type == "SELL" else 0.0
            expenses = trade_value if trade.transaction_type == "BUY" else 0.0
            
            financial_ui_payload = {
                "status": "ok",
                "revenue": revenue,
                "expenses": expenses,
                "net_cash_flow": revenue - expenses,
                "collection_rate_pct": 98.5,
                "invoices": {
                    "total": 150,
                    "paid": 142,
                    "overdue": 8,
                    "overdue_amount": 12500
                }
            }
            
            ui_message = aio_pika.Message(
                body=json.dumps(financial_ui_payload).encode('utf-8'),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json"
            )
            await exchange.publish(ui_message, routing_key="voiderp.financial")
            
            await message.ack()
            
        except ValidationError as val_err:
            logger.error("schema_validation_failure", extra={"errors": val_err.errors()})
            await message.reject(requeue=False)
        except Exception as exc:
            logger.error("data_processing_error", extra={"error": str(exc)})
            await message.reject(requeue=True)

async def connect_with_retry(amqp_url: str, retries: int = 5, delay: int = 3) -> aio_pika.abc.AbstractRobustConnection:
    for attempt in range(1, retries + 1):
        try:
            return await aio_pika.connect_robust(amqp_url)
        except Exception as exc:
            if attempt == retries: raise
            await asyncio.sleep(delay)

async def main():
    amqp_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    connection = await connect_with_retry(amqp_url)
    
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)
        
        in_queue = await channel.declare_queue("treasury_trades_queue", durable=True)
        await channel.declare_queue("intelligence_queue", durable=True)
        await channel.declare_queue("voiderp.financial", durable=True)
        
        await in_queue.consume(lambda msg: process_and_forward(msg, channel.default_exchange))
        await asyncio.Future()

if __name__ == "__main__": 
    asyncio.run(main())