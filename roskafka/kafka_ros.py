import rclpy
import rclpy.parameter
import json
import threading
import string

from roskafka.mapping import Mapping
from roskafka.bridge_node import BridgeNode
from roskafka.utils import get_msg_type
from roskafka.utils import dict_to_msg


class ConsumerThread:

    def __init__(self, mapping):
        self.is_running = False
        try:
            self.msg_type = get_msg_type(mapping.type)
        except Exception:
            raise
        self.consumer = kafka.KafkaConsumer(mapping.source, bootstrap_servers="localhost:9092")

        def poll():
            while self.is_running:
                polling_result = self.consumer.poll(timeout_ms=1000)
                for topic_partition, consumer_records in polling_result.items():
                    for consumer_record in consumer_records:
                        mapping.node.get_logger().debug(f'Received message from {mapping.name}: {consumer_record.value}')
                        msg = json.loads(consumer_record.value)
                        destination = string.Template(mapping.destination).substitute(msg['metadata'])
                        if destination not in mapping.publishers:
                            mapping.publishers[destination] = mapping.node.create_publisher(
                                self.msg_type,
                                destination,
                                10)
                            mapping.node.get_logger().info(f'Created publisher for destination {mapping.destination}')
                        mapping.node.get_logger().debug(f'Sending message to {mapping.destination}: {msg["payload"]}')
                        mapping.publishers[destination].publish(dict_to_msg(mapping.type, msg['payload']))
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

    def __init__(self, node, name, source, destination, type):
        super().__init__(node, name, source, destination, type)
        self._closed = False
        self.node.get_logger().debug(f'Starting consumer thread for mapping {name} ...')
        self.subscriber = ConsumerThread(self)
        self.subscriber.start()
        self.publishers = {}

    def __del__(self):
        if not self._closed:
            self.close()


class KafkaRosBridge(BridgeNode):

    def add_mapping(self, name, source, destination, type):
        mapping = KafkaRosMapping(self, name, source, destination, type)
        self._mappings[name] = mapping

    def remove_mapping(self, name):
        if name not in self._mappings:
            raise KeyError()
        self._mappings[name].close()
        # Delete existing parameters by setting them to an empty parameter
        self.set_parameters_atomically([
            rclpy.parameter.Parameter(f'mappings.{name}.{paramName}') for paramName in self.get_parameters_by_prefix(f'mappings.{name}')
        ])
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
