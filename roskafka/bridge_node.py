import rclpy.node
from roskafka_interfaces.srv import AddMapping
from roskafka_interfaces.srv import RemoveMapping


class BridgeNode(rclpy.node.Node):

    def _add_mapping_service_handler(self, request, response):
        try:
            self.add_mapping(request.name, request.kafka_topic, request.ros_topic, request.type)
        except Exception as e:
            self.get_logger().error(e)
            response.success = False
            response.message = f'Could not add mapping: {e}'
        else:
            response.success = True
            response.message = 'Mapping added'
        return response

    def _remove_mapping_service_handler(self, request, response):
        try:
            self.remove_mapping(request.name)
        except KeyError:
            response.success = False
            response.message = 'Mapping not found'
        except Exception as e:
            response.success = False
            response.message = f'Could not remove mapping: {e}'
        else:
            response.success = True
            response.message = 'Mapping removed'
        return response

    def __init__(self, name):
        super().__init__(name)
        self._mappings = {}
        self.create_service(AddMapping, f'{name}/add_mapping', self._add_mapping_service_handler)
        self.create_service(RemoveMapping, f'{name}/remove_mapping', self._remove_mapping_service_handler)
