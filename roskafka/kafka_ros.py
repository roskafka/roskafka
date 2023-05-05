import rclpy
import rclpy.parameter
import kafka
import threading
from roskafka.bridge_node import BridgeNode
from roskafka.utils import get_msg_type
from roskafka.utils import json_to_msg

class ConsumerThread:

    def __init__(self, name, mapping, publisher, logger):
        self.is_running = False
        def poll():
            consumer = kafka.KafkaConsumer(mapping['source'])
            while self.is_running:
                polling_result = consumer.poll(timeout_ms=1000)
                for topic_partition, consumer_records in polling_result.items():
                    for consumer_record in consumer_records:
                        msg = consumer_record.value
                        logger.debug(f'Received message from {name}: {msg}')
                        logger.debug(f'Sending message to {mapping["destination"]}: {msg}')
                        publisher.publish(json_to_msg(mapping['type'], msg))
        self.thread = threading.Thread(target=poll)

    def start(self):
        self.is_running = True
        self.thread.start()

    def stop(self):
        self.is_running = False


class KafkaRosBridge(BridgeNode):

    def add_mapping(self, name, mapping):
        try:
            msg_type = get_msg_type(mapping['type'])
        except Exception:
            raise
        mapping['publisher'] = self.create_publisher(
            msg_type,
            mapping['destination'],
            10)
        mapping['subscriber'] = ConsumerThread(name, mapping, mapping['publisher'], self.get_logger())
        self.get_logger().debug(f'Starting consumer thread for mapping {name} ...')
        mapping['subscriber'].start()
        self._mappings[name] = mapping

    def remove_mapping(self, name):
        if name not in self._mappings:
            raise KeyError()
        self.get_logger().debug(f'Stopping consumer thread for mapping {name} ...')
        self._mappings[name]['subscriber'].stop()
        self.destroy_publisher(self._mappings[name]['publisher'])
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
