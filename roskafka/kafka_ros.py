# Each import needs to be declared in package.xml
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from kafka import KafkaConsumer


class KafkaRosBridge(Node):

    def __init__(self):
        super().__init__('kafka_ros_bridge')
        self.declare_parameter('kafka_input_topic', 'roskafka.in')
        self.kafka_input_topic = self.get_parameter('kafka_input_topic').get_parameter_value().string_value
        self.get_logger().info(f'Using input topic: {self.kafka_input_topic}')
        self.publisher = self.create_publisher(
            String,
            'roskafka',
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
