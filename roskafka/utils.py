import os
import importlib
import rosidl_runtime_py
import rclpy


def get_msg_type(type):
    symbol = os.path.basename(type)
    module = ".".join(os.path.split(os.path.dirname(type)))
    return getattr(importlib.import_module(module), symbol)


def msg_to_dict(msg):
    return rosidl_runtime_py.message_to_ordereddict(msg)


def dict_to_msg(type_name, values):
    instance = get_msg_type(type_name)()
    rosidl_runtime_py.set_message_fields(instance, values)
    return instance
