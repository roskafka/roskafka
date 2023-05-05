import rclpy
import rclpy.node
import rclpy.parameter
import kafka
import threading
from roskafka.utils import get_msg_type
from roskafka.utils import params_to_mappings
from roskafka.utils import json_to_msg
from roskafka_interfaces.srv import AddMapping
from roskafka_interfaces.srv import RemoveMapping

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


class KafkaRosBridge(rclpy.node.Node):

    def add_mapping(self, name, mapping):
        try:
            msg_type = get_msg_type(mapping['type'])
        except Exception:
            raise
        self.__mappings[name] = mapping
        publisher = self.create_publisher(
            msg_type,
            mapping['destination'],
            10)
        self.__publishers[name] = publisher
        thread = ConsumerThread(name, mapping, publisher, self.get_logger())
        self.get_logger().debug(f'Starting consumer thread for mapping {name} ...')
        thread.start()
        self.__subscriptions[name] = thread

    def remove_mapping(self, name):
        if name not in self.__mappings:
            raise KeyError()
        self.get_logger().debug(f'Stopping consumer thread for mapping {name} ...')
        self.__subscriptions[name].stop()
        self.destroy_publisher(self.__publishers[name])
        del self.__subscriptions[name]
        del self.__publishers[name]
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
        super().__init__('kafka_ros', allow_undeclared_parameters=True)
        self.__mappings = {}
        self.__publishers = {}
        self.__subscriptions = {}
        self.create_service(AddMapping, 'kafka_ros/add_mapping', self.__add_mapping_service_handler)
        self.create_service(RemoveMapping, 'kafka_ros/remove_mapping', self.__remove_mapping_service_handler)
        self.__process_params()
        self.create_timer(5, self.__process_params)


def main(args=None):
    rclpy.init(args=args)
    bridge = KafkaRosBridge()
    rclpy.spin(bridge)
    bridge.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
