import rclpy
import rclpy.node
import kafka
from roskafka.utils import get_msg_type
from roskafka.utils import params_to_mappings
from roskafka.utils import msg_to_json
from roskafka_interfaces.srv import AddMapping
from roskafka_interfaces.srv import RemoveMapping

class RosKafkaBridge(rclpy.node.Node):

    def add_mapping(self, name, mapping):
        try:
            msg_type = get_msg_type(mapping['type'])
        except Exception:
            raise
        self.__mappings[name] = mapping
        def handler(msg):
            self.get_logger().debug(f'Received message from {name}: {msg}')
            json_str = msg_to_json(msg)
            self.get_logger().debug(f'Sending message to {mapping["destination"]}: {json_str}')
            self.__producer.send(mapping['destination'], json_str.encode('utf-8'))
        self.__subscriptions[name] = self.create_subscription(
            msg_type,
            mapping['source'],
            handler,
            10)

    def remove_mapping(self, name):
        if name not in self.__mappings:
            raise KeyError()
        self.destroy_subscription(self.__subscriptions[name])
        del self.__mappings[name]
        # Delete existing parameters by setting them to an empty parameter
        self.set_parameters([
            rclpy.parameter.Parameter(f'mappings.{name}.{paramName}') for paramName in self.get_parameters_by_prefix(f'mappings.{name}')
        ])


    def __process_params(self):
        params = self.get_parameters_by_prefix('mappings')
        current_mappings = params_to_mappings(params)
        self.get_logger().debug(f'Current parameter values: {str(current_mappings)}')
        previous_mappings = self.__mappings
        # Subscribe to new mappings
        new_mappings = current_mappings.keys() - previous_mappings.keys()
        for name in new_mappings:
            self.get_logger().info(f'Found new mapping: {name}')
            try:
                self.add_mapping(name, current_mappings[name])
            except Exception as e:
                self.get_logger().error(f'Could not add mapping: {e}')
        # Unsubscribe from old mappings
        old_mappings = previous_mappings.keys() - current_mappings.keys()
        for name in old_mappings:
            self.get_logger().info(f'Old mapping disappeared: {name}')
            self.remove_mapping(name)
            try:
                self.remove_mapping(name)
            except KeyError:
                self.get_logger().error("Mapping not found")

    def __add_mapping_service_handler(self, request, response):
        try:
            self.add_mapping(request.name, {
                'source': request.source,
                'destination': request.destination,
                'type': request.type
            })
        except Exception as e:
            response.success = False
            response.message = f'Could not add mapping: {e}'
        else:
            self.set_parameters([
                rclpy.parameter.Parameter(f'mappings.{request.name}.source', value=request.source),
                rclpy.parameter.Parameter(f'mappings.{request.name}.destination', value=request.destination),
                rclpy.parameter.Parameter(f'mappings.{request.name}.type', value=request.type)
            ])
            response.success = True
            response.message = 'Mapping added'
        return response

    def __remove_mapping_service_handler(self, request, response):
        try:
            self.remove_mapping(request.name)
        except KeyError:
            response.success = False
            response.message = 'Mapping not found'
        else:
            response.success = True
            response.message = 'Mapping removed'
        return response

    def __init__(self):
        super().__init__('ros_kafka', allow_undeclared_parameters=True)
        self.__producer = kafka.KafkaProducer()
        self.__mappings = {}
        self.__subscriptions = {}
        self.create_service(AddMapping, 'ros_kafka/add_mapping', self.__add_mapping_service_handler)
        self.create_service(RemoveMapping, 'ros_kafka/remove_mapping', self.__remove_mapping_service_handler)
        self.__process_params()
        self.create_timer(5, self.__process_params)


def main(args=None):
    rclpy.init(args=args)
    bridge = RosKafkaBridge()
    rclpy.spin(bridge)
    bridge.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
