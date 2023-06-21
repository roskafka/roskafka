# roskafka

## Setup

Download code to ROS 2 workspace:

    mkdir -p ~/ros2_ws/src
    cd ~/ros2_ws/src
    git clone https://gitlab.informatik.hs-furtwangen.de/ss23-forschungsprojekt-7/roskafka.git

Install ROS dependencies:
- [roskafka_interfaces](https://gitlab.informatik.hs-furtwangen.de/ss23-forschungsprojekt-7/roskafka_interfaces)

Install Python dependencies:
- [confluent-kafka](https://pypi.org/project/confluent-kafka/) (tested with version 2.1.1)
- [fastavro](https://pypi.org/project/fastavro/) (tested with version 1.7.4)

Build package:

    cd ~/ros2_ws
    PYTHONWARNINGS=ignore:::setuptools.command.install colcon build --packages-select roskafka

Source package:

    . install/setup.bash


## Startup

There are two ways to start roskafka: using launch files or manually.

### Using launch file

    ros2 launch roskafka roskafka.launch.yaml

Optionally, the log level can be configured using the `log_level` parameter:

    ros2 launch roskafka roskafka.launch.yaml log_level:=debug

### Manually

    ros2 run roskafka kafka_ros &
    ros2 run roskafka ros_kafka &

Optionally, the log level can be configured using the `log_level` parameter:

    ros2 run roskafka kafka_ros --ros-args --log-level kafka_ros:=debug &
    ros2 run roskafka ros_kafka --ros-args --log-level ros_kafka:=debug &


## Configuration

### Mapping Configuration

Mappings are managed via service calls.

#### Add mappings

    ros2 service call /ros_kafka/add_mapping roskafka_interfaces/srv/AddMapping '{name: <mapping_name>, ros_topic: <ros_topic>, kafka_topic: <kafka_topic>, type: <msg_type>}'
    ros2 service call /kafka_ros/add_mapping roskafka_interfaces/srv/AddMapping '{name: <mapping_name>, kafka_topic: <kafka_topic>, ros_topic: <ros_topic>, type: <msg_type>}'

#### Remove mappings

    ros2 service call /ros_kafka/remove_mapping roskafka_interfaces/srv/RemoveMapping '{name: <mapping_name>}'
    ros2 service call /kafka_ros/remove_mapping roskafka_interfaces/srv/RemoveMapping '{name: <mapping_name>}'

#### Templates

The `destination` parameter in the `kafka_ros` mappings can be specified as a
template, e.g., `/${mapping}/pose_from_kafka`. The values for the variables are
substituted from the `metadata` part of the message.

### Kafka Broker Configuration

The Kafka broker can be configured using two environment variables:
- `BOOTSTRAP_SERVERS`: the address of the bootstrap server (defaults to
  `localhost:9092`)
- `SCHEMA_REGISTRY`: the address of the schema registry (defaults to
  `http://localhost:8081`)


## Message Format

The messages sent to Kafka via `ros_kafka` have the following structure:

    {
        "payload": <msg>,
        "metadata": <metadata>
    }

`<msg>` is the serialized ROS 2 message, `<metadata>` an object containing the
name of the mapping (`mapping`), the mapping source (`ros_topic`), and the
mapping destination (`kafka_topic`). This information is also put into the
Kafka header of the message.

The messages that are received by `kafka_ros` expect a similar structure,
except that the mapping source is given as `kafka_topic` and the mapping
destination as `ros_topic`.  Additionally, the `metadata` object can be used
for template substitutions (see above).


## Demo

Run turtlesim and let turtle move in a circle:

    ros2 run turtlesim turtlesim_node
    ros2 topic pub --rate 1 /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 2.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 1.8}}"

Pump messages from `/turtle1/pose` (ROS) to `turtle1_pose` (Kafka):

    ros2 service call /ros_kafka/add_mapping roskafka_interfaces/srv/AddMapping '{name: turtle1, ros_topic: /turtle1/pose, kafka_topic: turtle1_pose, type: turtlesim/msg/Pose}'

Verify that messages are arriving in Kafka:

    kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic turtle1_pose

Pump messages from `turtle1_pose` (Kafka) to `/turtle1/pose_from_kafka` (ROS):

    ros2 service call /kafka_ros/add_mapping roskafka_interfaces/srv/AddMapping '{name: turtle1, kafka_topic: turtle1_pose, ros_topic: /turtle1/pose_from_kafka, type: turtlesim/msg/Pose}'

Verify that messages are arriving in ROS:

    ros2 topic echo /turtle1/pose_from_kafka


## Testing

    colcon test --packages-select roskafka
    colcon test-result --all --verbose
