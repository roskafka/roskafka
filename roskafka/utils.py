import os
import importlib
import rosidl_runtime_py


def get_msg_type(type):
    symbol = os.path.basename(type)
    module = ".".join(os.path.split(os.path.dirname(type)))
    return getattr(importlib.import_module(module), symbol)


def params_to_mappings(params):
    mappings = {}
    for key, value in params.items():
        namespace, name = key.split('.', maxsplit=1)
        if namespace not in mappings:
            mappings[namespace] = {}
        mappings[namespace][name] = value.get_parameter_value().string_value
    return mappings


def msg_to_dict(msg):
    return rosidl_runtime_py.message_to_ordereddict(msg)


def dict_to_msg(type_name, values):
    instance = get_msg_type(type_name)()
    rosidl_runtime_py.set_message_fields(instance, values)
    return instance
