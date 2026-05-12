import os

def ensure_write_allowed():
    if os.getenv("ASANA_MODE") == "read_only":
        raise Exception("Write operations disabled")
