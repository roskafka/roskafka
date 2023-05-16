import rclpy
import kafka
import json
from roskafka.mapping import Mapping
from roskafka.bridge_node import BridgeNode
from roskafka.utils import get_msg_type
from roskafka.utils import msg_to_dict


class RosKafkaMapping(Mapping):

    def close(self):
        self.node.get_logger().debug(f'Destroying subscription for mapping {self.name} ...')
        self.node.destroy_subscription(self.subscriber)
        self._closed = True

    def _msg_handler(self, msg):
        self.node.get_logger().debug(f'Received message from {self.name}: {msg}')
        producer_record = json.dumps({
            'payload': msg_to_dict(msg),
            'metadata': {
                'mapping': self.name,
                'source': self.source,
                'type': self.type
            }
        })
        self.node.get_logger().debug(f'Sending message to {self.destination}: {producer_record}')
        self.producer.send(self.destination, producer_record.encode('utf-8'), headers=[
            ('mapping', self.name.encode('utf-8')),
            ('source', self.source.encode('utf-8')),
            ('type', self.type.encode('utf-8'))
        ])

    def __init__(self, node, name, source, destination, type):
        super().__init__(node, name, source, destination, type)
        self._closed = False
        try:
            msg_type = get_msg_type(self.type)
        except Exception:
            raise
        node.get_logger().debug(f'Creating KafkaProducer to {self.destination} for {self.name} ...')
        self.producer = kafka.KafkaProducer()

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
            rclpy.parameter.Parameter(f'mappings.{name}.{paramName}') for paramName in self.get_parameters_by_prefix(f'mappings.{name}')
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
