import lgpio

GPIO_CLOCK = 23
GPIO_DATA  = 17

print("lgpio module file:", lgpio.__file__)

# try to get version from package metadata
try:
    import importlib.metadata as importlib_metadata
except ImportError:
    import importlib_metadata

try:
    version = importlib_metadata.version("lgpio")
except Exception:
    version = "unknown"

print("lgpio version:", version)