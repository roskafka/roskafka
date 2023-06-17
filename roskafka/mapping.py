from roskafka.ros_kafka_setup import add_mapping


class Mapping:

    def __init__(self, node, name, source, destination, type):
        self.node = node
        self.name = name
        self.source = source
        self.destination = destination
        self.type = type
        add_mapping(self.node, self.name, self.source, self.destination, self.type)
