"""
Kafka Consumer
==============
Generic fault-tolerant consumer interface.
"""
import os
import sys
import json
from typing import List, Callable
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

# Temporarily remove local 'kafka' and 'kafka.consumer' from sys.modules
local_kafka = sys.modules.get('kafka')
local_consumer = sys.modules.get('kafka.consumer')

if 'kafka' in sys.modules:
    del sys.modules['kafka']
if 'kafka.consumer' in sys.modules:
    del sys.modules['kafka.consumer']

try:
    from kafka import KafkaConsumer
finally:
    # Restore sys.path and sys.modules
    for p in saved_paths:
        sys.path.insert(0, p)
    if local_kafka:
        sys.modules['kafka'] = local_kafka
    if local_consumer:
        sys.modules['kafka.consumer'] = local_consumer

sys.path.insert(0, local_path)
from utils.helpers import load_config
from utils.logger import get_logger

logger = get_logger("kafka_consumer")
load_dotenv()

class KafkaMessageConsumer:
    def __init__(self, topics: List[str], config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        self.bootstrap_servers = self.config['kafka']['bootstrap_servers']
        self.topics = topics
        self.consumer = self._create_consumer()
        
    def _create_consumer(self) -> KafkaConsumer:
        c_cfg = self.config['kafka']['consumer']
        return KafkaConsumer(
            *self.topics,
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')) if v else None,
            group_id=c_cfg['group_id'],
            auto_offset_reset=c_cfg['auto_offset_reset'],
            enable_auto_commit=c_cfg['enable_auto_commit'],
            max_poll_records=c_cfg['max_poll_records']
        )
        
    def start_consuming(self, message_handler: Callable[[dict], None]):
        logger.info(f"Started consuming from topics: {self.topics}")
        try:
            for message in self.consumer:
                try:
                    message_handler(message.value)
                    self.consumer.commit()
                except Exception as e:
                    logger.error(f"Error handling message at offset {message.offset}: {e}")
                    # In production, commit offset and dump error message or route to DLQ
                    self.consumer.commit()
        except KeyboardInterrupt:
            logger.info("Consuming loop interrupted.")
        finally:
            self.consumer.close()
            logger.info("Kafka Consumer closed.")
            
    def close(self):
        self.consumer.close()
