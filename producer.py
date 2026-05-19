import asyncio
import aio_pika
import json
import uuid
import random
import logging
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("treasury_producer")

class TreasuryTradePayload(BaseModel):
    trade_id: str = Field(..., max_length=64)
    asset_pair: str = Field(..., max_length=16)
    execution_price: float = Field(..., gt=0.0)
    volume: float = Field(..., gt=0.0)
    transaction_type: Literal["BUY", "SELL"]
    sap_btp_reference: str = Field(..., max_length=128)

async def generate_mock_trades(channel: aio_pika.abc.AbstractChannel, count: int = 5):
    exchange = channel.default_exchange
    queue_name = "treasury_trades_queue"
    
    asset_pairs = ["EUR/USD", "USD/TRY", "XAU/USD", "BTC/USD"]
    
    for i in range(count):
        payload = TreasuryTradePayload(
            trade_id=f"TRD-{uuid.uuid4().hex[:8].upper()}",
            asset_pair=random.choice(asset_pairs),
            execution_price=round(random.uniform(1.0, 2000.0), 4),
            volume=round(random.uniform(10.0, 500.0), 2),
            transaction_type=random.choice(["BUY", "SELL"]),
            sap_btp_reference=f"SAP-BTP-{uuid.uuid4().hex[:12].upper()}"
        )
        
        message_body = payload.model_dump_json().encode('utf-8')
        
        message = aio_pika.Message(
            body=message_body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
            message_id=payload.trade_id
        )
        
        await exchange.publish(message, routing_key=queue_name)
        logger.info(f"Yayınlandı: {payload.trade_id} | {payload.transaction_type} {payload.volume} {payload.asset_pair}")
        
        await asyncio.sleep(random.uniform(0.1, 0.5))

async def main():
    # CRITICAL FIX: Mac terminalinden Docker içindeki RabbitMQ'ya bağlanmak için localhost kullanılmalı.
    amqp_url = "amqp://guest:guest@localhost:5672/"
    
    logger.info("RabbitMQ'ya bağlanılıyor...")
    connection = await aio_pika.connect_robust(amqp_url)
    
    async with connection:
        channel = await connection.channel()
        await channel.declare_queue("treasury_trades_queue", durable=True)
        
        logger.info("Test verileri (Mock Trades) oluşturuluyor...")
        await generate_mock_trades(channel, count=10)
        logger.info("Veri basımı tamamlandı.")

if __name__ == "__main__":
    asyncio.run(main())