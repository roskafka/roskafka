import requests
import json

import confluent_kafka
import confluent_kafka.admin

from roskafka.kafka_config import bootstrap_servers, schema_registry
from roskafka.utils import get_msg_type


class Mapping:

    def __init__(self, node, name, source, destination, type):
        self.node = node
        self.name = name
        self.source = source
        self.destination = destination
        self.type = type
        add_mapping(self)


def get_recursive_fields(msg_type_name: str, logger):
    msg_type = get_msg_type(msg_type_name)
    ros_fields = msg_type.get_fields_and_field_types()
    logger.debug(f"parsing ros msg. {msg_type_name}: {ros_fields}")
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


def generate_avro(mapping: Mapping, logger):
    msg_type_name = mapping.type
    schema_name = msg_type_name.split("/")[-1]
    fields = get_recursive_fields(msg_type_name, logger)
    return avro_record(schema_name, fields)


def avro_record(name: str, fields: list):
    return {
        "type": "record",
        "name": name,
        "fields": fields
    }


def create_kafka_topic(name: str, logger):
    admin_client = confluent_kafka.admin.AdminClient({"bootstrap.servers": bootstrap_servers})
    new_topic = confluent_kafka.admin.NewTopic(name, num_partitions=1, replication_factor=1)
    future_topics = admin_client.create_topics([new_topic])
    for topic, future in future_topics.items():
        try:
            future.result()
        except Exception as e:
            logger.error(f"Failed to create kafka topic: {name} err=\"{e}\"")
            raise e
    logger.info(f"Successfully created kafka topic: {name}")


def create_avro_schema(mapping: Mapping, logger):
    schema = generate_avro(mapping, logger)
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
        logger.info(f"Successfully pushed avro schema to registry: {res.text} schema_name=\"{mapping.destination}-value\"")


def add_mapping(mapping: Mapping):
    mapping.node.get_logger().info(f"Adding mapping: {mapping}")
    create_kafka_topic(mapping.destination, mapping.node.get_logger())
    create_avro_schema(mapping, mapping.node.get_logger())


if __name__ == "__main__":
    s = generate_avro(Mapping("node1", "node1", "/robot1/positions", "positions", "std_msgs/msg/String"))
    print(s)
    class MockLogger:
        def debug(self, msg):
            print(msg)

        def info(self, msg):
            print(msg)

    create_kafka_topic("test1", MockLogger())
