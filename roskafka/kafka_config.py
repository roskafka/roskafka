import os

from confluent_kafka.schema_registry import SchemaRegistryClient


schema_registry = os.environ.get("SCHEMA_REGISTRY", "http://localhost:8081")
bootstrap_servers = os.environ.get("BOOTSTRAP_SERVERS", "localhost:9092")

sr = SchemaRegistryClient({"url": schema_registry})


def wait_for_schema(node, topic):
    import rclpy
    max_retries = 10
    retries = 0
    while True:
        try:
            schema = sr.get_latest_version(topic + "-value").schema
            return schema
        except Exception:
            retries += 1
            if retries >= max_retries:
                raise Exception(f"Could not get schema for topic {topic}")
            rclpy.spin_once(node, timeout_sec=1.0)
