import rclpy
import rclpy.parameter
import kafka
import json
import threading
import string
from roskafka.bridge_node import BridgeNode
from roskafka.utils import get_msg_type
from roskafka.utils import dict_to_msg


class ConsumerThread:

    def __init__(self, node, name, mapping):
        self.is_running = False

        def poll():
            try:
                msg_type = get_msg_type(mapping['type'])
            except Exception:
                raise
            consumer = kafka.KafkaConsumer(mapping['source'])
            while self.is_running:
                polling_result = consumer.poll(timeout_ms=1000)
                for topic_partition, consumer_records in polling_result.items():
                    for consumer_record in consumer_records:
                        node.get_logger().debug(f'Received message from {name}: {consumer_record.value}')
                        msg = json.loads(consumer_record.value)
                        destination = string.Template(mapping['destination']).substitute(msg['metadata'])
                        if destination not in mapping['publishers']:
                            mapping['publishers'][destination] = node.create_publisher(
                                msg_type,
                                destination,
                                10)
                            node.get_logger().info(f'Created publisher for destination {destination}')
                        node.get_logger().debug(f'Sending message to {destination}: {msg["payload"]}')
                        mapping['publishers'][destination].publish(dict_to_msg(mapping['type'], msg['payload']))
        self.thread = threading.Thread(target=poll)

    def start(self):
        self.is_running = True
        self.thread.start()

    def stop(self):
        self.is_running = False


class KafkaRosBridge(BridgeNode):

    def add_mapping(self, name, mapping):
        mapping['publishers'] = {}
        mapping['subscriber'] = ConsumerThread(self, name, mapping)
        self.get_logger().debug(f'Starting consumer thread for mapping {name} ...')
        mapping['subscriber'].start()
        self._mappings[name] = mapping

    def remove_mapping(self, name):
        if name not in self._mappings:
            raise KeyError()
        self.get_logger().debug(f'Stopping consumer thread for mapping {name} ...')
        self._mappings[name]['subscriber'].stop()
        for _, publisher in self._mappings[name]['publishers'].items():
            self.destroy_publisher(publisher)
        # Delete existing parameters by setting them to an empty parameter
        self.set_parameters([
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
