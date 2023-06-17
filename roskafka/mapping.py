import requests
import json

import rclpy
import confluent_kafka

from roskafka.kafka_config import bootstrap_servers, schema_registry
from roskafka.utils import get_msg_type


class Mapping:

    def __init__(self, node, name, source, destination, type):
        self.node = node
        self.name = name
        self.source = source
        self.destination = destination
        self.type = type
        add_mapping(self.node, self.name, self.source, self.destination, self.type)


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


def add_mapping(node, name, source, destination, mapping_type):
    mapping = Mapping(node, name, source, destination, mapping_type)
    print(f"Adding mapping: {mapping}")
    create_kafka_topic(mapping.destination)
    create_avro_schema(mapping)


if __name__ == "__main__":
    s = generate_avro(Mapping("node1", "node1", "/robot1/positions", "positions", "std_msgs/msg/String"))
    print(s)
