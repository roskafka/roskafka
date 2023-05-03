import rclpy
import rclpy.node
import kafka
from roskafka.utils import get_msg_type
from roskafka.utils import params_to_mappings
from roskafka.utils import msg_to_json

class RosKafkaBridge(rclpy.node.Node):

    def add_mapping(self, name, mapping):
        def handler(msg):
            self.get_logger().info(f'Received message from {name}: {msg}')
            json_str = msg_to_json(msg)
            self.get_logger().info(f'Sending message to {mapping["to"]}: {json_str}')
            self.__producer.send(mapping['to'], json_str.encode('utf-8'))
        self.__subscriptions[name] = self.create_subscription(
            get_msg_type(mapping['type']),
            mapping['from'],
            handler,
            10)

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
        super().__init__('ros_kafka', allow_undeclared_parameters=True)
        self.__producer = kafka.KafkaProducer()
        self.__mappings = {}
        self.__subscriptions = {}
        self.__process_mappings()
        self.create_timer(5, self.__process_mappings)


def main(args=None):
    rclpy.init(args=args)
    bridge = RosKafkaBridge()
    rclpy.spin(bridge)
    bridge.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
