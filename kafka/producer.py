"""
Kafka Producer
==============
Generic fault-tolerant producer with retry mechanisms.
"""
import os
import sys
import json
from typing import Any, Dict
from dotenv import load_dotenv

# Temporarily remove local directories and the local 'kafka' module from sys.modules
# to import the external kafka-python package
local_path = os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))).lower()
current_dir = os.path.normpath(os.path.dirname(os.path.abspath(__file__))).lower()
cwd = os.path.normpath(os.getcwd()).lower()

saved_paths = []
for p in list(sys.path):
    p_norm = os.path.normpath(os.path.abspath(p)).lower() if p else ''
    if p_norm in [local_path, current_dir, cwd] or p == '':
        sys.path.remove(p)
        saved_paths.append(p)

# Temporarily remove local 'kafka' and 'kafka.producer' from sys.modules
local_kafka = sys.modules.get('kafka')
local_producer = sys.modules.get('kafka.producer')

if 'kafka' in sys.modules:
    del sys.modules['kafka']
if 'kafka.producer' in sys.modules:
    del sys.modules['kafka.producer']

try:
    from kafka import KafkaProducer
finally:
    # Restore sys.path and sys.modules
    for p in saved_paths:
        sys.path.insert(0, p)
    if local_kafka:
        sys.modules['kafka'] = local_kafka
    if local_producer:
        sys.modules['kafka.producer'] = local_producer

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import load_config
from utils.logger import get_logger

logger = get_logger("kafka_producer")
load_dotenv()

class KafkaMessageProducer:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        self.bootstrap_servers = self.config['kafka']['bootstrap_servers']
        self.producer = self._create_producer()
        
    def _create_producer(self) -> KafkaProducer:
        p_cfg = self.config['kafka']['producer']
        return KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks=p_cfg['acks'],
            retries=p_cfg['retries'],
            linger_ms=p_cfg['linger_ms'],
            compression_type=p_cfg['compression_type']
        )
        
    def send_message(self, topic: str, value: Any, key: Any = None):
        try:
            key_bytes = str(key).encode('utf-8') if key else None
            future = self.producer.send(topic, value=value, key=key_bytes)
            # Asynchronous block verification block (optional metadata log)
            record_metadata = future.get(timeout=10)
            logger.debug(f"Message sent to {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")
        except Exception as e:
            logger.error(f"Error sending message to Kafka: {e}")
            # Redirect to DLQ if configured
            if topic != self.config['kafka']['topics']['dlq']:
                self.send_to_dlq(value, str(e))
                
    def send_to_dlq(self, payload: Any, error_msg: str):
        dlq_topic = self.config['kafka']['topics']['dlq']
        dlq_payload = {
            "original_payload": payload,
            "error": error_msg,
            "failed_at": json.dumps(str(datetime.now())) if 'datetime' in sys.modules else "now"
        }
        try:
            self.producer.send(dlq_topic, value=dlq_payload)
            logger.warning(f"Error recorded. Message rerouted to DLQ topic: {dlq_topic}")
        except Exception as ex:
            logger.error(f"Double fault: Failed to write to DLQ: {ex}")
            
    def flush(self):
        self.producer.flush()
        
    def close(self):
        self.producer.close()
        logger.info("Kafka Producer connection closed.")
