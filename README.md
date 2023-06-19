# roskafka

## Setup

Download code to ROS 2 workspace:

    mkdir -p ~/ros2_ws/src
    cd ~/ros2_ws/src
    git clone https://gitlab.informatik.hs-furtwangen.de/ss23-forschungsprojekt-7/roskafka.git

Install ROS dependencies:
- [roskafka_interfaces](https://gitlab.informatik.hs-furtwangen.de/ss23-forschungsprojekt-7/roskafka_interfaces)

Install Python dependencies:
- [confluent-kafka](https://pypi.org/project/confluent-kafka/)
- [fastavro](https://pypi.org/project/fastavro/)

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

There are two ways to configure mappings in roskafka: using parameter files or
using services.

#### Using parameter files

Prepare mapping file (`mappings.yaml`):

    /ros_kafka:
      ros__parameters:
        mappings:
          <mapping_name>:
            source: <ros_topic>
            destination: <kafka_topic>
            type: <msg_type>
        use_sim_time: false
    /kafka_ros:
      ros__parameters:
        mappings:
          <mapping_name>:
            source: <kafka_topic>
            destination: <ros_topic>
            type: <msg_type>
        use_sim_time: false

Provide mappings after starting the bridge nodes:

    ros2 param load /ros_kafka mappings.yaml
    ros2 param load /kafka_ros mappings.yaml

Alternatively, the mappings can be provided when starting the bridge nodes:

    ros2 run roskafka kafka_ros --ros-args --params-file mappings.yaml &
    ros2 run roskafka ros_kafka --ros-args --params-file mappings.yaml &

#### Using services

    ros2 service call /ros_kafka/add_mapping roskafka_interfaces/srv/AddMapping '{name: <mapping_name>, source: <ros_topic>, destination: <kafka_topic>, type: <msg_type>}'
    ros2 service call /kafka_ros/add_mapping roskafka_interfaces/srv/AddMapping '{name: <mapping_name>, source: <kafka_topic>, destination: <ros_topic>, type: <msg_type>}'

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
name of the mapping (`mapping`), the mapping source (`source`), and the mapping
destination (`destination`). This information is also put into the Kafka header
of the message.

The messages that are received by `kafka_ros` expect the same structure. The
`metadata` object can be used for template substitutions (see above).


## Demo

Run turtlesim and let turtle move in a circle:

    ros2 run turtlesim turtlesim_node
    ros2 topic pub --rate 1 /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 2.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 1.8}}"

Pump messages from `/turtle1/pose` (ROS) to `turtle1_pose` (Kafka):

    ros2 service call /ros_kafka/add_mapping roskafka_interfaces/srv/AddMapping '{name: turtle1, source: /turtle1/pose, destination: turtle1_pose, type: turtlesim/msg/Pose}'

Verify that messages are arriving in Kafka:

    kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic turtle1_pose

Pump messages from `turtle1_pose` (Kafka) to `/turtle1/pose_from_kafka` (ROS):

    ros2 service call /kafka_ros/add_mapping roskafka_interfaces/srv/AddMapping '{name: turtle1, source: turtle1_pose, destination: /turtle1/pose_from_kafka, type: turtlesim/msg/Pose}'

Verify that messages are arriving in ROS:

    ros2 topic echo /turtle1/pose_from_kafka


## Testing

    colcon test --packages-select roskafka
    colcon test-result --all --verbose
