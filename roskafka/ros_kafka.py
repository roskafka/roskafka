import rclpy
import kafka
from roskafka.bridge_node import BridgeNode
from roskafka.utils import get_msg_type
from roskafka.utils import msg_to_json

class RosKafkaBridge(BridgeNode):

    def add_mapping(self, name, mapping):
        try:
            msg_type = get_msg_type(mapping['type'])
        except Exception:
            raise
        def handler(msg):
            self.get_logger().debug(f'Received message from {name}: {msg}')
            json_str = msg_to_json(msg)
            self.get_logger().debug(f'Sending message to {mapping["destination"]}: {json_str}')
            self._producer.send(mapping['destination'], json_str.encode('utf-8'), headers=[
                ('mapping', name.encode('utf-8')),
                ('source', mapping['source'].encode('utf-8')),
                ('type', mapping['type'].encode('utf-8'))
            ])
        mapping['subscriber'] = self.create_subscription(
            msg_type,
            mapping['source'],
            handler,
            10)
        self._mappings[name] = mapping

    def remove_mapping(self, name):
        if name not in self._mappings:
            raise KeyError()
        self.destroy_subscription(self._mappings[name]['subscriber'])
        # Delete existing parameters by setting them to an empty parameter
        self.set_parameters([
            rclpy.parameter.Parameter(f'mappings.{name}.{paramName}') for paramName in self.get_parameters_by_prefix(f'mappings.{name}')
        ])
        del self._mappings[name]

    def __init__(self):
        super().__init__('ros_kafka')
        self._producer = kafka.KafkaProducer()


def main(args=None):
    rclpy.init(args=args)
    bridge = RosKafkaBridge()
    rclpy.spin(bridge)
    bridge.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
