# roskafka

Initial setup:

    mkdir -p ~/ros2_ws/src
    cd ~/ros2_ws/src
    git clone https://gitlab.informatik.hs-furtwangen.de/ss23-forschungsprojekt-7/roskafka.git

Build and run roskafka:

    cd ~/ros2_ws
    PYTHONWARNINGS=ignore:::setuptools.command.install colcon build
    . install/setup.bash
    ros2 run roskafka kafka_ros &
    ros2 run roskafka ros_kafka &

Run Kafka:

    kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic roskafka.out
    kafka-console-producer.sh --bootstrap-server localhost:9092 --topic roskafka.in
