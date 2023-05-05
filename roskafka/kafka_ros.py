import rclpy
import rclpy.node
import kafka
import threading
from roskafka.utils import get_msg_type
from roskafka.utils import params_to_mappings
from roskafka.utils import json_to_msg

class KafkaRosBridge(rclpy.node.Node):

    def add_mapping(self, name, mapping):
        publisher = self.create_publisher(
            get_msg_type(mapping['type']),
            mapping['to'],
            10)
        def poll():
            consumer = kafka.KafkaConsumer(mapping['from'])
            for consumerRecord in consumer:
                msg = consumerRecord.value
                self.get_logger().info(f'Received message from {name}: {msg}')
                publisher.publish(json_to_msg(mapping['type'], msg))
        thread = threading.Thread(target=poll)
        thread.start()

    def remove_mapping(self, name):
        self.__subscriptions[name].destroy()

    def __process_mappings(self):
        params = self.get_parameters_by_prefix('mappings')
        previous_mappings = self.__mappings
        current_mappings = params_to_mappings(params)
        self.get_logger().debug(f'Current mappings: {str(current_mappings)}')
        # Subscribe to new mappings
        new_mappings = current_mappings.keys() - previous_mappings.keys()
        for name in new_mappings:
            self.get_logger().info(f'Found new mapping: {name}')
            self.add_mapping(name, current_mappings[name])
        # Unsubscribe from old mappings
        old_mappings = previous_mappings.keys() - current_mappings.keys()
        for name in old_mappings:
            self.get_logger().info(f'Old mapping disappeared: {name}')
            self.remove_mapping(name)
        self.__mappings = current_mappings

    def __init__(self):
        super().__init__('kafka_ros', allow_undeclared_parameters=True)
        self.__mappings = {}
        self.__subscriptions = {}
        self.__process_mappings()
        self.create_timer(5, self.__process_mappings)


def main(args=None):
    rclpy.init(args=args)
    bridge = KafkaRosBridge()
    rclpy.spin(bridge)
    bridge.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
