import asyncio
import os
import aio_pika
import aiohttp
import json
import logging
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError
from typing import Literal

# -- Log Formatlama --
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage()
        })

logger = logging.getLogger("voiderp_worker")
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# -- Pydantic Şema (Gelen ve Giden Veri Validasyonu) --
class TreasuryTradePayload(BaseModel):
    trade_id: str = Field(..., max_length=64)
    asset_pair: str = Field(..., max_length=16)
    execution_price: float = Field(..., gt=0.0)
    volume: float = Field(..., gt=0.0)
    transaction_type: Literal["BUY", "SELL"]
    sap_btp_reference: str = Field(..., max_length=128)

# -- SAP BTP (Mock) Asenkron İstemcisi --
class SAPBTPClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": "Bearer dev_mock_token_999", 
            "Content-Type": "application/json"
        }

    async def register_trade(self, payload: TreasuryTradePayload) -> None:
        endpoint = f"{self.base_url}/v1/treasury/trades"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.post(endpoint, json=payload.model_dump()) as response:
                    response.raise_for_status()
                    logger.info("sap_btp_registration_success", extra={"trade_id": payload.trade_id, "status_code": response.status})
            except aiohttp.ClientResponseError as http_err:
                logger.error("sap_btp_registration_failed", extra={"trade_id": payload.trade_id, "status_code": http_err.status})
                raise
            except aiohttp.ClientError as net_err:
                logger.error("sap_btp_network_error", extra={"trade_id": payload.trade_id, "error": str(net_err)})
                raise

# -- Mesaj Tüketici (RabbitMQ -> SAP) --
async def process_message(message: aio_pika.abc.AbstractIncomingMessage, sap_client: SAPBTPClient) -> None:
    async with message.process(ignore_processed=True):
        try:
            payload_bytes = message.body.decode()
            trade_payload = TreasuryTradePayload.model_validate_json(payload_bytes)
            
            logger.info("message_received", extra={"trade_id": trade_payload.trade_id})
            
            # Veriyi SAP'ye yolla
            await sap_client.register_trade(trade_payload)
            
            # Başarılı olursa mesajı kuyruktan düşür
            await message.ack()
            logger.info("message_acknowledged", extra={"trade_id": trade_payload.trade_id})
            
        except ValidationError as val_err:
            logger.error("schema_validation_failure", extra={"errors": val_err.errors()})
            await message.reject(requeue=False) # Hatalı format, çöpe at
        except Exception as e:
            logger.error("processing_error", extra={"error": str(e)})
            await message.reject(requeue=True) # Ağ hatası, kuyruğa geri koy

async def main():
    amqp_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
    sap_url = os.getenv("SAP_MOCK_URL", "http://sap_mock:8000")
    queue_name = "treasury_trades_queue"

    logger.info("worker_starting", extra={"rabbitmq": amqp_url, "sap_mock": sap_url})
    
    sap_client = SAPBTPClient(base_url=sap_url)
    
    # RabbitMQ'ya bağlan
    connection = await aio_pika.connect_robust(amqp_url)
    
    async with connection:
        channel = await connection.channel()
        # QoS (Prefetch Count): Scale-to-Zero için Kritik. Worker başına eşzamanlı maksimum 5 mesaj alınır.
        await channel.set_qos(prefetch_count=5)
        
        queue = await channel.declare_queue(queue_name, durable=True)
        
        logger.info("worker_ready_and_listening", extra={"queue_name": queue_name})
        
        # Mesajları dinlemeye başla
        await queue.consume(lambda msg: process_message(msg, sap_client))
        
        # Programı canlı tut
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
