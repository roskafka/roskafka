import requests
import json
import re

import confluent_kafka
import confluent_kafka.admin
from confluent_kafka import KafkaError, KafkaException

from roskafka.kafka_config import bootstrap_servers, schema_registry
from roskafka.utils import get_msg_type

# sequence msg type: sequence<irobot_create_msgs/msg/HazardDetection>
sequence_regex = re.compile(r"sequence<(.*)>")
array_regex = re.compile(r"(.*)\[(.*)]")

avro_schema_namespace = "de.hfu"


class Mapping:

    def __init__(self, node, name, kafka_topic, ros_topic, type):
        self.node = node
        self.name = name
        self.kafka_topic = kafka_topic
        self.ros_topic = ros_topic
        self.type = type
        add_mapping(self)


def ros_type_to_avro_type(ros_type):
    return {
        'bool': 'boolean',
        'boolean': 'boolean',
        'byte': 'int',
        'char': 'string',
        'float': 'float',
        'float32': 'float',
        'float64': 'double',
        'int8': 'int',
        'int16': 'int',
        'int32': 'int',
        'int64': 'long',
        'uint8': 'int',
        'uint16': 'int',
        'uint32': 'int',
        'uint64': 'long',
        'string': 'string',
        'time': 'long',
        'duration': 'long'
    }.get(ros_type, ros_type)


def msg_type_to_importable_name(msg_type_name):
    if array_regex.match(msg_type_name):
        msg_type_name = array_regex.match(msg_type_name).group(1)
    return msg_type_name.split("/")[0] + "/msg/" + msg_type_name.split("/")[1]


def get_recursive_fields(msg_type_name: str, existing_records: dict[str, str], logger):
    msg_type = get_msg_type(msg_type_name)
    ros_fields = msg_type.get_fields_and_field_types()
    logger.debug(f"parsing ros msg. {msg_type_name}: {ros_fields}")
    fields = []
    for key, field_msg_type in ros_fields.items():
        if sequence_regex.match(field_msg_type):
            field_msg_type_name = sequence_regex.match(field_msg_type).group(1)
            field = {"name": key, "type": {"type": "array", "items": get_field(field_msg_type_name, existing_records, logger)}}
        elif array_regex.match(field_msg_type):
            field_msg_type_name = array_regex.match(field_msg_type).group(1)
            field = {"name": key, "type": {"type": "array", "items": get_field(field_msg_type_name, existing_records, logger)}}
        else:
            field = {"name": key, "type": get_field(field_msg_type, existing_records, logger)}
        fields.append(field)
    return fields


def get_field(field_msg_type: str, existing_records: dict[str, str], logger):
    if "/" in field_msg_type:
        if field_msg_type in existing_records:
            field = avro_schema_namespace + "." + existing_records[field_msg_type]
        else:
            msg_string = msg_type_to_importable_name(field_msg_type)
            logger.debug(f"{msg_string=}")
            inner_fields = get_recursive_fields(msg_string, existing_records, logger)
            record_name = field_msg_type.split("/")[-1]
            field = avro_record(record_name, inner_fields)
            existing_records[field_msg_type] = record_name
    else:
        avro_type = ros_type_to_avro_type(field_msg_type)
        field = avro_type
    return field


def generate_avro(ros_type: str, logger):
    schema_name = ros_type.split("/")[-1]
    # TODO: maybe instead of package all in one avro schema we should create one avro schema per msg type
    # TODO: Otherwise it could happen, that when a msg references itself, we can recursion errors
    existing_records = {}
    fields = get_recursive_fields(ros_type, existing_records, logger)
    record = avro_record(schema_name, fields)
    record["namespace"] = avro_schema_namespace
    return record


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
            logger.info(f"Successfully created kafka topic: {name}")
        except KafkaException as e:
            err = e.args[0]
            if err.code() == KafkaError.TOPIC_ALREADY_EXISTS:
                logger.debug(f"Topic already exists: {name}")
            else:
                raise
        except Exception as e:
            logger.error(f"Failed to create kafka topic: {name} err=\"{e}\"")
            raise


def create_avro_schema(mapping: Mapping, logger):
    schema = generate_avro(mapping.type, logger)
    logger.debug(f"final avro schema:\n{json.dumps(schema)}")
    request_content = {
        "schema": json.dumps(schema)  # schema needs to be a string and not a dict
    }
    schema_name = f"{mapping.kafka_topic}-value"
    res = requests.post(f"{schema_registry}/subjects/{schema_name}/versions",
                        data=json.dumps(request_content),
                        headers={"Content-Type": "application/vnd.schemaregistry.v1+json"})
    if not res.ok:
        raise Exception(
            f"Error: could not push avro schema to registry:  err=\"{res.text}\" status=\"{res.status_code}\"")
    else:
        logger.info(f"Successfully pushed avro schema to registry: {res.text} {schema_name=}")


def add_mapping(mapping: Mapping):
    mapping.node.get_logger().info(f"Adding mapping: {mapping}")
    create_kafka_topic(mapping.kafka_topic, mapping.node.get_logger())
    create_avro_schema(mapping, mapping.node.get_logger())


if __name__ == "__main__":
    class MockLogger:
        def debug(self, msg):
            print(msg)

        def info(self, msg):
            print(msg)

    s = generate_avro("irobot_create_msgs/msg/HazardDetectionVector", MockLogger())
    print("avro schema:")
    print(json.dumps(s, indent=2))

    # create_kafka_topic("test1", MockLogger())
