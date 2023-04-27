# Each import needs to be declared in package.xml
import rclpy
from rclpy.node import Node
from std_msgs.msg import *
from kafka import KafkaProducer
import os
import importlib

def getMsgType(type):
    symbol = os.path.basename(type)
    module = ".".join(os.path.split(os.path.dirname(type)))
    return getattr(importlib.import_module(module), symbol)


class RosKafkaBridge(Node):

    def __init__(self):
        super().__init__('ros_kafka_bridge')
        self.declare_parameter('ros_input_type', 'std_msgs/msg/String')
        self.ros_input_type = self.get_parameter('ros_input_type').get_parameter_value().string_value
        self.get_logger().info(f'Using ROS input type: {self.ros_input_type}')
        self.declare_parameter('ros_input_topic', 'roskafka/in')
        self.ros_input_topic = self.get_parameter('ros_input_topic').get_parameter_value().string_value
        self.get_logger().info(f'Using ROS input topic: {self.ros_input_topic}')
        self.declare_parameter('kafka_output_topic', 'roskafka.out')
        self.kafka_output_topic = self.get_parameter('kafka_output_topic').get_parameter_value().string_value
        self.get_logger().info(f'Using Kafka output topic: {self.kafka_output_topic}')
        self.subscription = self.create_subscription(
            getMsgType(self.ros_input_type),
            self.ros_input_topic,
            self.listener_callback,
            10)
        self.producer = KafkaProducer()

    def listener_callback(self, message):
        self.get_logger().info(f'Received from ROS: {message.data}')
        producerRecord = message.data.encode('utf-8')
        self.producer.send('roskafka.out', producerRecord)


def main(args=None):
    rclpy.init(args=args)
    bridge = RosKafkaBridge()
    rclpy.spin(bridge)
    bridge.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
