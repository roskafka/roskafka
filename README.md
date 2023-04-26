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

Run roskafka using its launch file:

    ros2 launch roskafka roskafka.launch.yaml ros_input_topic:=roskafka/in ros_output_topic:=roskafka/out kafka_input_topic:=roskafka.in kafka_output_topic:=roskafka.out

Run roskafka manually:

    ros2 run roskafka kafka_ros &
    ros2 run roskafka ros_kafka &

Run Kafka:

    kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic roskafka.out
    kafka-console-producer.sh --bootstrap-server localhost:9092 --topic roskafka.in
