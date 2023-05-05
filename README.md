# roskafka

Initial setup:

    mkdir -p ~/ros2_ws/src
    cd ~/ros2_ws/src
    git clone https://gitlab.informatik.hs-furtwangen.de/ss23-forschungsprojekt-7/roskafka.git

Build roskafka:

    cd ~/ros2_ws
    PYTHONWARNINGS=ignore:::setuptools.command.install colcon build

Source roskafka:

    . install/setup.bash

Run roskafka either using its launch file:

    ros2 launch roskafka roskafka.launch.yaml [log_level:=debug]

Or, run roskafka manually:

    ros2 run roskafka kafka_ros [--ros-args --log-level kafka_ros:=debug] &
    ros2 run roskafka ros_kafka [--ros-args --log-level ros_kafka:=debug] &

Prepare mapping file between ROS and Kafka (`ros_kafka.yaml`):

    /ros_kafka:
      ros__parameters:
        mappings:
          turtle1:
            from: "/turtle1/pose"
            to: "turtle1_pose"
            type: "turtlesim/msg/Pose"
        use_sim_time: false

Prepare mapping file between Kafka and ROS (`kafka_ros.yaml`):

    /kafka_ros:
      ros__parameters:
        mappings:
          turtle1:
            from: "turtle1_pose"
            to: "/turtle1/pose_from_kafka"
            type: "turtlesim/msg/Pose"
        use_sim_time: false

Provide mappings to bridge nodes:

    ros2 param load /ros_kafka ros_kafka.yaml
    ros2 param load /kafka_ros kafka_ros.yaml

Run turtlesim and let turtle move in a circle:

    ros2 run turtlesim turtlesim_node
    ros2 topic pub --rate 1 /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 2.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 1.8}}"

Verify messages in Kafka:

    kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic turtle1_pose

Verify messages in ROS:

    ros2 topic echo /turtle1/pose_from_kafka
