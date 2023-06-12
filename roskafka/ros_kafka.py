import os

import rclpy
import json

from confluent_kafka import Producer
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.serialization import StringSerializer, SerializationContext, MessageField

from roskafka.mapping import Mapping
from roskafka.bridge_node import BridgeNode
from roskafka.utils import get_msg_type
from roskafka.utils import msg_to_dict

schema_registry = os.environ.get("SCHEMA_REGISTRY", "http://localhost:8081")
bootstrap_servers = os.environ.get("BOOTSTRAP_SERVERS", "localhost:9092")

sr = SchemaRegistryClient({"url": schema_registry})


class RosKafkaMapping(Mapping):

    def close(self):
        self.node.get_logger().debug(f'Destroying subscription for mapping {self.name} ...')
        self.node.destroy_subscription(self.subscriber)
        self._closed = True

    def _msg_handler(self, msg):
        self.node.get_logger().debug(f'Received message from {self.name}: {msg}')
        value = msg_to_dict(msg)
        key = self.source  # TODO: get robot name from parameter
        self.node.get_logger().debug(f'Sending message to {self.destination}: {value}')
        self.producer.produce(
            topic=self.destination,
            key=self.key_serializer(key),
            value=self.value_serializer(
                value,
                SerializationContext(
                    self.destination,
                    MessageField.VALUE,
                    [
                        ('mapping', self.name.encode('utf-8')),
                        ('source', self.source.encode('utf-8')),
                        ('type', self.type.encode('utf-8'))
                    ]
                )
            )
        )

    def __init__(self, node, name, source, destination, type):
        super().__init__(node, name, source, destination, type)
        self._closed = False
        try:
            msg_type = get_msg_type(self.type)
        except Exception:
            raise
        node.get_logger().debug(f'Creating KafkaProducer to {self.destination} for {self.name} ...')
        schema_value = sr.get_latest_version(f"{self.destination}-value").schema
        self.value_serializer = AvroSerializer(schema_registry_client=sr, schema_str=schema_value)
        self.key_serializer = StringSerializer('utf_8')
        self.producer = Producer({
            'bootstrap.servers': bootstrap_servers,
        })

        node.get_logger().debug(f'Creating ROS subscription to {self.source} for {self.name} ...')
        self.subscriber = self.node.create_subscription(
            msg_type,
            self.source,
            self._msg_handler,
            10)

    def __del__(self):
        if not self._closed:
            self.close()


class RosKafkaBridge(BridgeNode):

    def add_mapping(self, name, source, destination, type):
        mapping = RosKafkaMapping(self, name, source, destination, type)
        self._mappings[name] = mapping

    def remove_mapping(self, name):
        if name not in self._mappings:
            raise KeyError()
        self._mappings[name].close()
        # Delete existing parameters by setting them to an empty parameter
        self.set_parameters_atomically([
            rclpy.parameter.Parameter(f'mappings.{name}.{paramName}') for paramName in
            self.get_parameters_by_prefix(f'mappings.{name}')
        ])
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
