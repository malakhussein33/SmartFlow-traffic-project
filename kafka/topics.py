"""
Kafka Topic Manager
===================
Manages topic verification and creation.
"""
import os
import sys
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

# Temporarily remove local 'kafka' from sys.modules. We also remove 'kafka.admin'
# (though it usually is not a local package, we do it for completeness)
local_kafka = sys.modules.get('kafka')
local_admin = sys.modules.get('kafka.admin')

if 'kafka' in sys.modules:
    del sys.modules['kafka']
if 'kafka.admin' in sys.modules:
    del sys.modules['kafka.admin']

try:
    from kafka.admin import KafkaAdminClient, NewTopic
finally:
    # Restore sys.path and sys.modules
    for p in saved_paths:
        sys.path.insert(0, p)
    if local_kafka:
        sys.modules['kafka'] = local_kafka
    if local_admin:
        sys.modules['kafka.admin'] = local_admin

sys.path.insert(0, local_path)
from utils.helpers import load_config
from utils.logger import get_logger

logger = get_logger("kafka_topics")
load_dotenv()

class KafkaTopicManager:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = load_config(config_path)
        self.bootstrap_servers = self.config['kafka']['bootstrap_servers']
        self.topics = self.config['kafka']['topics']
        self.admin_client = self._create_admin_client()
        
    def _create_admin_client(self) -> KafkaAdminClient:
        try:
            client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                client_id='topic_manager'
            )
            logger.info("Kafka Admin Client initialized.")
            return client
        except Exception as e:
            logger.error(f"Failed to create Admin Client: {e}")
            raise e
            
    def create_all_topics(self):
        existing_topics = self.admin_client.list_topics()
        new_topics = []
        
        # Define topics configuration
        topic_configs = [
            (self.topics['traffic'], 3, 1),
            (self.topics['weather'], 1, 1),
            (self.topics['prediction'], 1, 1),
            (self.topics['dlq'], 1, 1)
        ]
        
        for name, partitions, replication in topic_configs:
            if name not in existing_topics:
                new_topics.append(NewTopic(
                    name=name,
                    num_partitions=partitions,
                    replication_factor=replication
                ))
                logger.info(f"Preparing to create topic '{name}' (partitions={partitions}, replication={replication}).")
            else:
                logger.info(f"Topic '{name}' already exists.")
                
        if new_topics:
            try:
                self.admin_client.create_topics(new_topics=new_topics, validate_only=False)
                logger.info("All new topics created successfully.")
            except Exception as e:
                logger.error(f"Failed to create topics: {e}")
        else:
            logger.info("No new topics needed creation.")
            
    def close(self):
        self.admin_client.close()
        logger.info("Admin Client closed.")

if __name__ == '__main__':
    manager = KafkaTopicManager()
    try:
        manager.create_all_topics()
    finally:
        manager.close()
