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
            'chatter',
            self.listener_callback,
            10)
        self.producer = KafkaProducer(bootstrap_servers='localhost:9092')

    def listener_callback(self, msg):
        self.get_logger().info('I heard: "%s"' % msg.data)
        self.producer.send('ros', msg.data.encode())


def main(args=None):

    rclpy.init(args=args)

    bridge = RosKafkaBridge()

    rclpy.spin(bridge)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    bridge.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
