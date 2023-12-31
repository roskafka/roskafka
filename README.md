# roskafka

roskafka is a ROS (Robot Operating System) 2 package that enables communication between ROS 2 and Apache Kafka.

## Setup

1. Install Python dependencies (for example with pip):

    - [confluent-kafka](https://pypi.org/project/confluent-kafka/) (tested with version 2.1.1)
    - [fastavro](https://pypi.org/project/fastavro/) (tested with version 1.7.4)

2. Source ROS 2:

        source /opt/ros/humble/setup.bash

3. Download code to ROS 2 workspace:

        mkdir -p ~/ros2_ws/src
        cd ~/ros2_ws/src
        git clone https://gitlab.informatik.hs-furtwangen.de/ss23-forschungsprojekt-7/roskafka.git

4. Install ROS 2 dependencies:

    - [roskafka_interfaces](https://gitlab.informatik.hs-furtwangen.de/ss23-forschungsprojekt-7/roskafka_interfaces)

5. Build package:

        cd ~/ros2_ws
        PYTHONWARNINGS=ignore:::setuptools.command.install colcon build --packages-select roskafka


## Usage

1. Open a new terminal: Always source a workspace from a different terminal than the one you used `colcon build`.

2. Source ROS 2:

        source /opt/ros/humble/setup.bash

3. Source workspace:

        source install/setup.bash

4. Start roskafka:

    There are two ways to start roskafka: using launch files or manually.

    - Using launch file

            ros2 launch roskafka roskafka.launch.yaml

        Optionally, the log level can be configured using the `log_level` parameter:

            ros2 launch roskafka roskafka.launch.yaml log_level:=debug

    - Manually

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
    ros2 service call /kafka_ros/add_mapping roskafka_interfaces/srv/AddMapping '{name: <mapping_name>, ros_topic: <ros_topic>, kafka_topic: <kafka_topic>, type: <msg_type>}'

#### Remove mappings

    ros2 service call /ros_kafka/remove_mapping roskafka_interfaces/srv/RemoveMapping '{name: <mapping_name>}'
    ros2 service call /kafka_ros/remove_mapping roskafka_interfaces/srv/RemoveMapping '{name: <mapping_name>}'

#### Templates

The `ros_topic` field in the `kafka_ros` mappings can be parameterized using
template strings. Currently, only one substitution is supported: `${key}`,
which refers to the key of the Kafka message.

This mechanism can be used to enable 1:N mappings from Kafka to ROS, e.g., to
route messages from a single Kafka topic to the matching namespaced robot.

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
destination as `ros_topic`. Additionally, template substitutions can be used in
the `ros_topic` field (see above).


## Demo

Run turtlesim and let turtle move in a circle:

    ros2 run turtlesim turtlesim_node
    ros2 topic pub --rate 1 /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 2.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 1.8}}"

Pump messages from `/turtle1/pose` (ROS) to `turtle1_pose` (Kafka):

    ros2 service call /ros_kafka/add_mapping roskafka_interfaces/srv/AddMapping '{name: turtle1, ros_topic: /turtle1/pose, kafka_topic: turtle1_pose, type: turtlesim/msg/Pose}'

Verify that messages are arriving in Kafka:

    kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic turtle1_pose

Pump messages from `turtle1_pose` (Kafka) to `/turtle1/pose_from_kafka` (ROS):

    ros2 service call /kafka_ros/add_mapping roskafka_interfaces/srv/AddMapping '{name: turtle1, ros_topic: /turtle1/pose_from_kafka, kafka_topic: turtle1_pose, type: turtlesim/msg/Pose}'

Verify that messages are arriving in ROS:

    ros2 topic echo /turtle1/pose_from_kafka


## Testing

    colcon test --packages-select roskafka
    colcon test-result --all --verbose


## Flow

- Add mapping: ros-topic, kafka-topic (type inferred from ros-topic)
  - get ros type from topic
  - create kafka topic
  - (Generic: any robot name can be used)
- start mapping: ros_kafka/kafka_ros ros-topic, kafka-topic
  - get avro type from registry
  - subscribe to topic
  - publish to topic

- New Node Mapping Config
