import rclpy
import rclpy.node
import kafka
from roskafka.utils import get_msg_type

class KafkaRosBridge(rclpy.node.Node):

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
            get_msg_type(self.ros_output_type),
            self.ros_output_topic,
            10)
        self.consumer = kafka.KafkaConsumer(self.kafka_input_topic)
        for consumerRecord in self.consumer:
            message = consumerRecord.value
            self.get_logger().info(f'Received from Kafka: {message}')
            self.publisher.publish(message)


def main(args=None):
    rclpy.init(args=args)
    bridge = KafkaRosBridge()
    rclpy.spin(bridge)
    bridge.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
