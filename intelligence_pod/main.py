import asyncio
import logging
import sys
import json
from datetime import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        })

logger = logging.getLogger("data_pod_worker")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

async def main():
    logger.info("data_pod_initialized", extra={"status": "waiting_for_rabbitmq"})
    # Asenkron RabbitMQ tüketici mantığı buraya entegre edilecek
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
