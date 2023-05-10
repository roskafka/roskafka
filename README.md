# roskafka

## Setup

Initial setup:

    mkdir -p ~/ros2_ws/src
    cd ~/ros2_ws/src
    git clone https://gitlab.informatik.hs-furtwangen.de/ss23-forschungsprojekt-7/roskafka.git

Build package:

    cd ~/ros2_ws
    PYTHONWARNINGS=ignore:::setuptools.command.install colcon build --packages-select roskafka

Source package:

    . install/setup.bash

## Startup

There are two ways to start roskafka: using launch files or manually.

### Using launch file

    ros2 launch roskafka roskafka.launch.yaml [log_level:=debug]

### Manually

    ros2 run roskafka kafka_ros [--ros-args --log-level kafka_ros:=debug] &
    ros2 run roskafka ros_kafka [--ros-args --log-level ros_kafka:=debug] &

## Configuration

There are two ways to configure roskafka: using parameter files or using
services.

### Using parameter files

Prepare mapping file (`mapping.yaml`):

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

Provide mappings to bridge nodes:

    ros2 param load /ros_kafka mapping.yaml
    ros2 param load /kafka_ros mapping.yaml

### Using services

    ros2 service call /ros_kafka/add_mapping roskafka_interfaces/srv/AddMapping '{name: <mapping_name>, source: <ros_topic>, destination: <kafka_topic>, type: <msg_type>}'
    ros2 service call /kafka_ros/add_mapping roskafka_interfaces/srv/AddMapping '{name: <mapping_name>, source: <kafka_topic>, destination: <ros_topic>, type: <msg_type>}'

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
