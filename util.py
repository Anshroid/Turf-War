from enum import Enum

Status = Enum("STATUS", "INIT SETUP RUNNING END")
OwnedBy = Enum("OwnedBy", "YELLOW YELLOW_HOME RED RED_HOME UNOWNED", start=0)

def colour_convert(c: str) -> int:
    return int(c[1:], 16)