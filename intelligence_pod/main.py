import asyncio
import os
import json
import logging
import signal
from datetime import datetime, timezone
from typing import Literal, Any, Dict

import aio_pika
from pydantic import BaseModel, ValidationError
from aio_pika.exceptions import AMQPConnectionError, AMQPChannelError

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module if hasattr(record, 'module') else record.name,
            "message": record.getMessage()
        })

logger = logging.getLogger("voiderp_intelligence_pod")
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

class ValidatedTradePayload(BaseModel):
    trade_id: str
    asset_pair: str
    execution_price: float
    volume: float
    transaction_type: Literal["BUY", "SELL"]
    sap_btp_reference: str

class EvaluatedTradePayload(ValidatedTradePayload):
    risk_status: Literal["NOMINAL", "HIGH_RISK"]
    evaluation_timestamp: str


class IntelligenceProcessor:
    """
    Tüm AMQP bağlantı ve kanal (channel) durumunu yöneten izole sınıf.
    Callback metodları sınıfın bir parçası olduğu için self.channel 
    üzerinden güvenli asenkron I/O işlemleri yapabilir.
    """
    def __init__(self, amqp_url: str):
        self._amqp_url: str = amqp_url
        self.connection: aio_pika.abc.AbstractRobustConnection | None = None
        self.channel: aio_pika.abc.AbstractRobustChannel | None = None

    async def connect_with_retry(self, max_retries: int = 5, retry_delay: int = 3) -> None:
        for attempt_index in range(1, max_retries + 1):
            try:
                self.connection = await aio_pika.connect_robust(self._amqp_url)
                self.channel = await self.connection.channel()
                await self.channel.set_qos(prefetch_count=10)
                logger.info("rabbitmq_connection_established")
                return
            except AMQPConnectionError:
                if attempt_index == max_retries:
                    raise
                logger.warning("connection_retry", extra={"attempt": attempt_index, "delay": retry_delay})
                await asyncio.sleep(retry_delay)
        raise AMQPConnectionError("maximum_connection_retries_exceeded")

    async def process_trade_signal(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        async with message.process(requeue=True):
            try:
                trade_payload = ValidatedTradePayload.model_validate_json(message.body.decode('utf-8'))
            except ValidationError as val_err:
                logger.error("schema_validation_failure", extra={"validation_errors": val_err.errors()})
                return 

            risk_classification: Literal["NOMINAL", "HIGH_RISK"] = "HIGH_RISK" if trade_payload.volume > 400.0 else "NOMINAL"
            
            evaluated_payload = EvaluatedTradePayload(
                **trade_payload.model_dump(), 
                risk_status=risk_classification, 
                evaluation_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            if not self.channel:
                logger.error("channel_not_initialized")
                return

            # DÜZELTME: Hatalı aiormq sızıntısı engellendi. Sınıfın kendi üst seviye aio_pika kanalı kullanılıyor.
            exchange = self.channel.default_exchange
            
            control_message_payload = aio_pika.Message(
                body=evaluated_payload.model_dump_json().encode('utf-8'), 
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json"
            )
            await exchange.publish(control_message_payload, routing_key="control_queue")
            
            trade_notional_value = trade_payload.execution_price * trade_payload.volume
            
            risk_ui_payload: Dict[str, Any] = {
                "upcoming_payments": [
                    {"label": "SAP BTP License", "due_date": "2026-05-25", "amount": 4500, "urgency": "medium"},
                    {"label": "Liquidity Provider", "due_date": "2026-05-22", "amount": trade_notional_value * 0.05, "urgency": "high"}
                ],
                "overdue_receivables": [
                    {"counterparty": "OTC Desk", "days_overdue": 2, "amount": 54000}
                ],
                "cash_flow_risks": [
                    {
                        "risk": "High Volatility Shift", 
                        "probability": 0.85 if risk_classification == "HIGH_RISK" else 0.15, 
                        "impact": "high"
                    }
                ]
            }
            
            ui_message_payload = aio_pika.Message(
                body=json.dumps(risk_ui_payload).encode('utf-8'),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json"
            )
            
            await exchange.publish(ui_message_payload, routing_key="voiderp.risk")
            logger.info("risk_evaluated", extra={"trade_id": trade_payload.trade_id, "risk_classification": risk_classification})


async def main() -> None:
    amqp_url: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
    processor = IntelligenceProcessor(amqp_url)
    
    try:
        await processor.connect_with_retry()
    except AMQPConnectionError as conn_err:
        logger.critical("rabbitmq_connection_failed", extra={"error_details": str(conn_err)})
        return

    try:
        in_queue = await processor.channel.declare_queue("intelligence_queue", durable=True)
        await processor.channel.declare_queue("control_queue", durable=True)
        await processor.channel.declare_queue("voiderp.risk", durable=True)
        
        logger.info("intelligence_pod_listening", extra={"target_queue": "intelligence_queue"})
        
        await in_queue.consume(processor.process_trade_signal)
        
        shutdown_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, shutdown_event.set)
        
        await shutdown_event.wait()
        
    except AMQPChannelError as chan_err:
        logger.error("amqp_channel_error", extra={"error_details": str(chan_err)})
    finally:
        logger.info("intelligence_pod_shutting_down", extra={"status": "terminating_connection"})
        if processor.connection and not processor.connection.is_closed:
            await processor.connection.close()

if __name__ == "__main__": 
    try:
        asyncio.run(main())
    except asyncio.CancelledError:
        logger.info("event_loop_cancelled", extra={"status": "shutdown_complete"})