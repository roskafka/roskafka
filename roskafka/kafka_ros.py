import string
import threading

import rclpy
from confluent_kafka import Consumer
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField

from roskafka.bridge_node import BridgeNode
from roskafka.kafka_config import get_bootstrap_servers, wait_for_schema, get_schema_registry
from roskafka.mapping import Mapping
from roskafka.utils import dict_to_msg
from roskafka.utils import get_msg_type


class ConsumerThread:

    def __init__(self, mapping: "KafkaRosMapping"):
        self.is_running = False
        try:
            self.msg_type = get_msg_type(mapping.type)
        except Exception:
            raise
        self.consumer = Consumer({
            'bootstrap.servers': get_bootstrap_servers(mapping.node),
            'group.id': 'kafka-ros',
            'auto.offset.reset': 'earliest'
        })
        schema_value = wait_for_schema(mapping.node, mapping.kafka_topic)
        self.value_deserializer = AvroDeserializer(schema_registry_client=get_schema_registry(mapping.node), schema_str=schema_value)
        self.consumer.subscribe([mapping.kafka_topic])

        def poll():
            while self.is_running:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue

                key = msg.key()
                data = self.value_deserializer(msg.value(), SerializationContext(mapping.kafka_topic, MessageField.VALUE))
                if data is not None:
                    mapping.node.get_logger().debug(f'Received message from {mapping.name}: {data}')
                    destination = string.Template(mapping.ros_topic).substitute({"robot": key})
                    if destination not in mapping.publishers:
                        mapping.publishers[destination] = mapping.node.create_publisher(
                            self.msg_type,
                            destination,
                            10)
                        mapping.node.get_logger().info(f'Created publisher from {mapping.kafka_topic} to {mapping.ros_topic}')
                    mapping.node.get_logger().debug(f'Sending message to {destination}: {data}')
                    mapping.publishers[destination].publish(dict_to_msg(mapping.type, data))

        self.thread = threading.Thread(target=poll)

    def start(self):
        self.is_running = True
        self.thread.start()

    def stop(self):
        self.is_running = False


class KafkaRosMapping(Mapping):

    def close(self):
        self.node.get_logger().debug(f'Stopping consumer thread for mapping {self.name} ...')
        self.subscriber.stop()
        self.node.get_logger().debug(f'Destroying publishers for mapping {self.name} ...')
        for publisher in self.publishers.values():
            self.node.destroy_publisher(publisher)
        self._closed = True

    def __init__(self, node, name, ros_topic, kafka_topic, type):
        super().__init__(node, name, ros_topic, kafka_topic, type)
        self._closed = False
        self.node.get_logger().debug(f'Starting consumer thread for mapping {name} ...')
        self.subscriber = ConsumerThread(self)
        self.subscriber.start()
        self.publishers = {}


    def __del__(self):
        if not self._closed:
            self.close()


class KafkaRosBridge(BridgeNode):

    def add_mapping(self, name, ros_topic, kafka_topic, type):
        mapping = KafkaRosMapping(self, name, ros_topic, kafka_topic, type)
        self._mappings[name] = mapping

    def remove_mapping(self, name):
        if name not in self._mappings:
            raise KeyError()
        self._mappings[name].close()
        del self._mappings[name]

    def __init__(self):
        super().__init__('kafka_ros')


def main(args=None):
    rclpy.init(args=args)
    bridge = KafkaRosBridge()
    rclpy.spin(bridge)
    bridge.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
