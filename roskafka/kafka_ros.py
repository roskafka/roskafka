# Each import needs to be declared in package.xml
import rclpy
from rclpy.node import Node
from std_msgs.msg import *
from kafka import KafkaConsumer
import os
import importlib

def getMsgType(type):
    symbol = os.path.basename(type)
    module = ".".join(os.path.split(os.path.dirname(type)))
    return getattr(importlib.import_module(module), symbol)


class KafkaRosBridge(Node):

    def __init__(self):
        super().__init__('kafka_ros_bridge')
        self.declare_parameter('ros_output_type', 'std_msgs/msg/String')
        self.ros_output_type = self.get_parameter('ros_output_type').get_parameter_value().string_value
        self.get_logger().info(f'Using ROS output type: {self.ros_output_type}')
        self.declare_parameter('ros_output_topic', 'roskafka/out')
        self.ros_output_topic = self.get_parameter('ros_output_topic').get_parameter_value().string_value
        self.get_logger().info(f'Using ROS output topic: {self.ros_output_topic}')
        self.declare_parameter('kafka_input_topic', 'roskafka.in')
        self.kafka_input_topic = self.get_parameter('kafka_input_topic').get_parameter_value().string_value
        self.get_logger().info(f'Using Kafka input topic: {self.kafka_input_topic}')
        self.publisher = self.create_publisher(
            getMsgType(self.ros_output_type),
            self.ros_output_topic,
            10)
        self.consumer = KafkaConsumer(self.kafka_input_topic)
        for consumerRecord in self.consumer:
            msg = String()
            msg.data = consumerRecord.value.decode('utf-8')
            self.get_logger().info(f'Received from Kafka: {msg.data}')
            self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    bridge = KafkaRosBridge()
    rclpy.spin(bridge)
    bridge.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
