import os

import rclpy
import json
import time

from confluent_kafka import Producer
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.serialization import StringSerializer, SerializationContext, MessageField
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from roskafka.mapping import Mapping
from roskafka.bridge_node import BridgeNode
from roskafka.utils import get_msg_type
from roskafka.utils import msg_to_dict
from roskafka.kafka_config import get_bootstrap_servers, wait_for_schema, get_schema_registry


class RosKafkaMapping(Mapping):

    def close(self):
        self.node.get_logger().debug(f'Destroying subscription for mapping {self.name} ...')
        self.node.destroy_subscription(self.subscriber)
        self._closed = True

    def _msg_handler(self, msg):
        self.node.get_logger().debug(f'Received message from {self.name}: {msg}')
        if time.time() - self.send_interval_seconds > self.last_send:
            value = msg_to_dict(msg)
            key = self.ros_topic.split("/")[0]
            self.node.get_logger().debug(f'Sending message to {self.kafka_topic}: {value}')
            self.producer.produce(
                topic=self.kafka_topic,
                key=self.key_serializer(key),
                value=self.value_serializer(
                    value,
                    SerializationContext(
                        self.kafka_topic,
                        MessageField.VALUE,
                        [
                            ('mapping', self.name.encode('utf-8')),
                            ('ros_topic', self.ros_topic.encode('utf-8')),
                            ('type', self.type.encode('utf-8'))
                        ]
                    )
                )
            )
            self.last_send = time.time()

    def __init__(self, node, name, ros_topic, kafka_topic, type):
        super().__init__(node, name, ros_topic, kafka_topic, type)
        self._closed = False
        try:
            msg_type = get_msg_type(self.type)
        except Exception:
            raise
        self.last_send = 0
        self.send_interval_seconds = 0.1
        node.get_logger().debug(f'Creating KafkaProducer to {self.kafka_topic} for {self.name} ...')
        schema_value = wait_for_schema(self.node, self.kafka_topic)
        self.value_serializer = AvroSerializer(schema_registry_client=get_schema_registry(node), schema_str=schema_value)
        self.key_serializer = StringSerializer('utf_8')
        self.producer = Producer({
            'bootstrap.servers': get_bootstrap_servers(node),
        })

        node.get_logger().debug(f'Creating ROS subscription to {self.ros_topic} for {self.name} ...')
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT ,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        self.subscriber = self.node.create_subscription(
            msg_type,
            self.ros_topic,
            self._msg_handler,
            qos_profile)



    def __del__(self):
        if not self._closed:
            self.close()


class RosKafkaBridge(BridgeNode):

    def add_mapping(self, name, ros_topic, kafka_topic, type):
        mapping = RosKafkaMapping(self, name, ros_topic, kafka_topic, type)
        self._mappings[name] = mapping

    def remove_mapping(self, name):
        if name not in self._mappings:
            raise KeyError()
        self._mappings[name].close()
        del self._mappings[name]

    def __init__(self):
        super().__init__('ros_kafka')


def main(args=None):
    rclpy.init(args=args)
    bridge = RosKafkaBridge()
    rclpy.spin(bridge)
    bridge.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
