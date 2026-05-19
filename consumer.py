import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pika
from pika.exceptions import AMQPConnectionError, StreamLostError
from pydantic import BaseModel, RootModel, ValidationError

# Yapılandırılmış loglama
logging.basicConfig(level=logging.INFO, format='%(name)s | %(asctime)s %(message)s')
logger = logging.getLogger("voiderp_consumer")

QUEUE_MAP: Dict[str, str] = {
    "voiderp.financial": "financial_analysis",
    "voiderp.risk":      "risk_evaluation",
    "voiderp.decisions": "decision_summary",
}

_consumer_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()

SHARED_AGENT_STATE: Dict[str, Any] = {
    "financial_analysis": None,
    "risk_evaluation": None,
    "decision_summary": None
}
_state_lock = threading.Lock()

# Pydantic Veri Doğrulama Modelleri
class IncomingPayload(RootModel[Dict[str, Any]]):
    """Kuyruktan gelen ham verinin bir JSON nesnesi (sözlük) olduğunu doğrular."""
    pass

class AgentStateEnvelope(BaseModel):
    """UI katmanına iletilecek verinin standart şeması."""
    data: Dict[str, Any]
    received_at: str
    status: str

def _build_connection(amqp_url: str) -> pika.BlockingConnection:
    params = pika.URLParameters(amqp_url)
    params.heartbeat = 60
    params.blocked_connection_timeout = 30
    return pika.BlockingConnection(params)

def _consumer_loop(amqp_url: str) -> None:
    while not _stop_event.is_set():
        try:
            conn = _build_connection(amqp_url)
            channel = conn.channel()

            for queue_name in QUEUE_MAP:
                channel.queue_declare(queue=queue_name, durable=True)

            def make_callback(agent_key: str):
                def callback(ch: pika.adapters.blocking_connection.BlockingChannel, 
                             method: pika.spec.Basic.Deliver, 
                             properties: pika.spec.BasicProperties, 
                             body: bytes) -> None:
                    try:
                        raw_data = json.loads(body)
                        
                        # Pydantic ile payload doğrulaması
                        validated_payload = IncomingPayload.model_validate(raw_data).model_dump()
                        
                        # Pydantic ile envelope doğrulaması
                        envelope = AgentStateEnvelope(
                            data=validated_payload,
                            received_at=datetime.now(timezone.utc).isoformat(),
                            status="ok"
                        )
                        
                        # Thread-safe write
                        with _state_lock:
                            SHARED_AGENT_STATE[agent_key] = envelope.model_dump()
                        
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        
                        logger.info(json.dumps({
                            "event": "message_received",
                            "agent": agent_key,
                            "status": "ack"
                        }))
                        
                    except json.JSONDecodeError as exc:
                        logger.error(json.dumps({
                            "event": "json_decode_error",
                            "agent": agent_key,
                            "error": str(exc)
                        }))
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    except ValidationError as exc:
                        logger.error(json.dumps({
                            "event": "payload_validation_error",
                            "agent": agent_key,
                            "error": exc.errors()
                        }))
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                        
                return callback

            for queue_name, agent_key in QUEUE_MAP.items():
                channel.basic_consume(
                    queue=queue_name,
                    on_message_callback=make_callback(agent_key),
                )

            logger.info(json.dumps({
                "event": "consumer_started",
                "action": "processing_data_events"
            }))
            
            while not _stop_event.is_set() and conn.is_open:
                conn.process_data_events(time_limit=1)

            if conn.is_open:
                conn.close()

        except (AMQPConnectionError, StreamLostError) as exc:
            logger.warning(json.dumps({
                "event": "rabbitmq_disconnected",
                "error": str(exc),
                "action": "reconnecting",
                "delay_s": 5
            }))
            time.sleep(5)
        except Exception as exc:
            logger.error(json.dumps({
                "event": "unexpected_consumer_error",
                "error": str(exc),
                "action": "reconnecting",
                "delay_s": 5
            }))
            time.sleep(5)

def start_consumer(amqp_url: str) -> None:
    global _consumer_thread, _stop_event

    if _consumer_thread and _consumer_thread.is_alive():
        return

    _stop_event.clear()
    _consumer_thread = threading.Thread(
        target=_consumer_loop,
        args=(amqp_url,),
        daemon=True,
        name="voiderp_consumer_thread",
    )
    _consumer_thread.start()
    
    logger.info(json.dumps({
        "event": "thread_started",
        "thread_id": _consumer_thread.ident,
        "status": "active"
    }))

def stop_consumer() -> None:
    _stop_event.set()
    if _consumer_thread:
        _consumer_thread.join(timeout=2.0)
        logger.info(json.dumps({
            "event": "thread_stopped",
            "status": "gracefully_terminated"
        }))