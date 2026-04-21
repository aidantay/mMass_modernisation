import importlib


def __getattr__(name):
    try:
        return importlib.import_module(f".{name}", __name__)
    except ImportError:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
