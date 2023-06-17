import requests
import json

import rclpy
import confluent_kafka

from roskafka.mapping import Mapping
from roskafka.bridge_node import BridgeNode
from roskafka.kafka_config import bootstrap_servers, schema_registry
from roskafka.utils import get_msg_type


def get_recursive_fields(msg_type_name: str):
    msg_type = get_msg_type(msg_type_name)
    ros_fields = msg_type.get_fields_and_field_types()
    print(f"{msg_type_name}: {ros_fields}")
    fields = []
    for key, msg_type in ros_fields.items():
        if "/" in msg_type:
            msg_string = msg_type.split("/")[0] + "/msg/" + msg_type.split("/")[1]
            inner_fields = get_recursive_fields(msg_string)
            field = avro_record(key, inner_fields)
        else:
            field = {"name": key, "type": msg_type}
            # TODO: maybe map ROS types to Avro types, but they already seem to be the same
        fields.append(field)
    return fields


def generate_avro(mapping: Mapping):
    msg_type_name = mapping.type
    schema_name = msg_type_name.split("/")[-1]
    fields = get_recursive_fields(msg_type_name)
    return avro_record(schema_name, fields)


def avro_record(name: str, fields: list):
    return {
        "type": "record",
        "name": name,
        "fields": fields
    }


def create_kafka_topic(name: str):
    admin_client = confluent_kafka.admin.AdminClient({"bootstrap.servers": bootstrap_servers})
    new_topic = confluent_kafka.admin.NewTopic(name, num_partitions=1, replication_factor=1)
    admin_client.create_topics([new_topic])
    print(f"Successfully created kafka topic: {name}")


def create_avro_schema(mapping: Mapping):
    schema = generate_avro(mapping)
    request_content = {
        "schema": json.dumps(schema)  # schema needs to be a string and not a dict
    }
    res = requests.post(f"{schema_registry}/subjects/{mapping.destination}-value/versions",
                        data=json.dumps(request_content),
                        headers={"Content-Type": "application/vnd.schemaregistry.v1+json"})
    # TODO: save avsc file to disk
    if not res.ok:
        raise Exception(
            f"Error: could not push avro schema to registry:  err=\"{res.text}\" status=\"{res.status_code}\"")
    else:
        print(f"Successfully pushed avro schema to registry: {res.text} schema_name=\"{mapping.destination}-value\"")


class RosKafkaSetup(BridgeNode):

    def add_mapping(self, name, source, destination, type):
        mapping = Mapping(self, name, source, destination, type)
        print(f"Adding mapping: {mapping}")
        create_kafka_topic(mapping.destination)
        create_avro_schema(mapping)
        self._mappings[name] = mapping

    def remove_mapping(self, name):
        if name not in self._mappings:
            raise KeyError()
        self._mappings[name].close()
        # Delete existing parameters by setting them to an empty parameter
        self.set_parameters_atomically([
            rclpy.parameter.Parameter(f'mappings.{name}.{paramName}') for paramName in
            self.get_parameters_by_prefix(f'mappings.{name}')
        ])
        del self._mappings[name]
        # TODO: delete topic and schema from registry?

    def __init__(self):
        super().__init__('ros_kafka_setup')
        self.get_logger().info("Starting ros_kafka_setup node...")


def main(args=None):
    rclpy.init(args=args)
    bridge = RosKafkaSetup()
    rclpy.spin(bridge)
    bridge.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

# if __name__ == "__main__":
#     schema = generate_avro(Mapping("node1", "node1", "/robot1/positions", "positions", "std_msgs/msg/String"))
#     print(schema)
