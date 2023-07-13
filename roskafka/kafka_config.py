import os

from confluent_kafka.schema_registry import SchemaRegistryClient


schema_registries = {}


def get_schema_registry_url():
    return os.getenv("SCHEMA_REGISTRY", "http://localhost:8081")


def get_schema_registry():
    schema_registry_url = get_schema_registry_url()
    if schema_registry_url not in schema_registries:
        schema_registries[schema_registry_url] = SchemaRegistryClient({"url": schema_registry_url})
    return schema_registries[schema_registry_url]


def get_bootstrap_servers():
    return os.getenv("BOOTSTRAP_SERVERS", "localhost:9092")


def wait_for_schema(node, topic):
    import rclpy
    max_retries = 10
    retries = 0
    while True:
        try:
            schema = get_schema_registry().get_latest_version(topic + "-value").schema
            return schema
        except Exception:
            retries += 1
            if retries >= max_retries:
                raise Exception(f"Could not get schema for topic {topic}")
            rclpy.spin_once(node, timeout_sec=1.0)
