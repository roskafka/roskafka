import os

from confluent_kafka.schema_registry import SchemaRegistryClient


schema_registries = {}


def get_schema_registry_url(node):
    return os.environ["SCHEMA_REGISTRY"]
    return node.declare_parameter('schema_registry').get_parameter_value().string_value


def get_schema_registry(node):
    schema_registry_url = get_schema_registry_url(node)
    if schema_registry_url not in schema_registries:
        schema_registries[schema_registry_url] = SchemaRegistryClient({"url": schema_registry_url})
    return schema_registries[schema_registry_url]


def get_bootstrap_servers(node):
    return os.environ["BOOTSTRAP_SERVERS"]
    return node.declare_parameter('bootstrap_servers').get_parameter_value().string_value


def wait_for_schema(node, topic):
    import rclpy
    max_retries = 10
    retries = 0
    while True:
        try:
            schema = get_schema_registry(node).get_latest_version(topic + "-value").schema
            return schema
        except Exception:
            retries += 1
            if retries >= max_retries:
                raise Exception(f"Could not get schema for topic {topic}")
            rclpy.spin_once(node, timeout_sec=1.0)
