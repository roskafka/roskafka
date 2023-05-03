import os
import importlib

def get_msg_type(type):
    symbol = os.path.basename(type)
    module = ".".join(os.path.split(os.path.dirname(type)))
    return getattr(importlib.import_module(module), symbol)
