from enum import Enum

SEP = "|"
EOL = "\n"

class State(str, Enum):
    CONNECTED = "CONNECTED"
    IDENTIFIED = "IDENTIFIED"
    JOINED = "JOINED"

class CMD(str, Enum):
    ID_REQ = "ID_REQ"
    ID_RES = "ID_RES"

    JOIN = "JOIN"
    JOIN_ACK = "JOIN_ACK"
    LEAVE = "LEAVE"
    LEAVE_ACK = "LEAVE_ACK"

    ROOMS_REQ = "ROOMS_REQ"
    ROOMS_RES = "ROOMS_RES"

    MSG = "MSG"
    MSG_ACK = "MSG_ACK"

    WHISPER = "WHISPER"
    WHISPER_ACK = "WHISPER_ACK"

    HIST_REQ = "HIST_REQ"
    HIST_RES = "HIST_RES"

    SUM_REQ = "SUM_REQ"
    SUM_ACK = "SUM_ACK"
    SUM_RES = "SUM_RES"

    FILE_REQ = "FILE_REQ"
    FILE_OFFER = "FILE_OFFER"
    FILE_ACK = "FILE_ACK"
    FILE_START = "FILE_START"
    FILE_DATA = "FILE_DATA"
    FILE_END = "FILE_END"

    PIN_SET = "PIN_SET"
    PIN_ACK = "PIN_ACK"
    PIN_GET = "PIN_GET"
    PIN_RES = "PIN_RES"
    PIN_CLEAR = "PIN_CLEAR"

    SCHED_ADD = "SCHED_ADD"
    SCHED_ACK = "SCHED_ACK"
    SCHED_LIST = "SCHED_LIST"
    SCHED_RES = "SCHED_RES"
    SCHED_CLEAR = "SCHED_CLEAR"

    NOTICE = "NOTICE"
    ERROR = "ERROR"
    QUIT = "QUIT"

class ERROR_CODE(str, Enum):
    INVALID_STATE = "ERR_400_INVALID_STATE"
    INVALID_ROOM = "ERR_400_INVALID_ROOM"
    DUPLICATE_ID = "ERR_409_DUPLICATE_ID"

def encode(cmd, from_id="-", target="-", payload="-"):
    if hasattr(cmd, "value"):
        cmd = cmd.value
    return f"{cmd}{SEP}{from_id}{SEP}{target}{SEP}{payload}{EOL}"

def decode_line(line: str):
    p = line.strip().split(SEP)
    if len(p) != 4:
        return None
    return {
        "cmd": p[0],
        "from": p[1],
        "target": p[2],
        "payload": p[3],
    }