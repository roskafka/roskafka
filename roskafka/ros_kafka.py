# Each import needs to be declared in package.xml
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from kafka import KafkaProducer


class RosKafkaBridge(Node):

    def __init__(self):
        super().__init__('ros_kafka_bridge')
        self.subscription = self.create_subscription(
            String,
            'roskafka',
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
