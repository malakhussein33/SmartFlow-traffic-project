"""
Unit Tests - Kafka Broker Integration
======================================
Verifies message serializations and routing using MagicMock mocks.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from kafka.producer import KafkaMessageProducer

class TestKafkaIntegration(unittest.TestCase):
    @patch('kafka.producer.KafkaProducer')
    def test_send_message_triggers_kafka_send(self, mock_kafka):
        # Setup mock producer instance
        mock_instance = MagicMock()
        mock_kafka.return_value = mock_instance
        
        producer_client = KafkaMessageProducer()
        payload = {"sensor_id": "SENSOR_01", "vehicle_count": 100}
        
        producer_client.send_message("traffic-stream", payload)
        
        # Verify underlying Kafka library send was triggered
        mock_instance.send.assert_called_once()

if __name__ == '__main__':
    unittest.main()
