import rclpy.node
import rclpy.parameter
from roskafka.utils import params_to_mappings
from roskafka_interfaces.srv import AddMapping
from roskafka_interfaces.srv import RemoveMapping


class BridgeNode(rclpy.node.Node):

    def _process_params(self):
        params = self.get_parameters_by_prefix('mappings')
        current_mappings = params_to_mappings(params)
        self.get_logger().debug(f'Current parameter values: {str(current_mappings)}')
        previous_mappings = self._mappings
        # Subscribe to new mappings
        new_mappings = current_mappings.keys() - previous_mappings.keys()
        for name in new_mappings:
            self.get_logger().info(f'Found new mapping: {name}')
            try:
                self.add_mapping(name, current_mappings[name]['source'], current_mappings[name]['destination'], current_mappings[name]['type'])
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

    def _add_mapping_service_handler(self, request, response):
        try:
            self.add_mapping(request.name, request.source, request.destination, request.type)
        except Exception as e:
            response.success = False
            response.message = f'Could not add mapping: {e}'
        else:
            self.set_parameters_atomically([
                rclpy.parameter.Parameter(f'mappings.{request.name}.source', value=request.source),
                rclpy.parameter.Parameter(f'mappings.{request.name}.destination', value=request.destination),
                rclpy.parameter.Parameter(f'mappings.{request.name}.type', value=request.type)
            ])
            response.success = True
            response.message = 'Mapping added'
        return response

    def _remove_mapping_service_handler(self, request, response):
        try:
            self.remove_mapping(request.name)
        except KeyError:
            response.success = False
            response.message = 'Mapping not found'
        else:
            response.success = True
            response.message = 'Mapping removed'
        return response

    def __init__(self, name):
        super().__init__(name, allow_undeclared_parameters=True)
        self._mappings = {}
        self.create_service(AddMapping, f'{name}/add_mapping', self._add_mapping_service_handler)
        self.create_service(RemoveMapping, f'{name}/remove_mapping', self._remove_mapping_service_handler)
        self.create_timer(5, self._process_params)
