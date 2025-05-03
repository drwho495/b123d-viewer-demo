from enum import Enum


class SocketCommands(Enum):
    CLOSE_CONNECTION = 1
    CONNECTION_SUCCESS = 2
    GET_OBJECT_ID_FROM_NAME = 3  # followed by name
    UPDATE_OBJECT = 4  # followed by name
    READY = 5
    RECIEVED = 6
    TRANSMISSION_OVER = b"TRANSMISSION_OVER"
    UPDATE_OBJECT_PROP = 8
    GET_OBJECT_ID = 9
    SKIP_OBJECT = 10