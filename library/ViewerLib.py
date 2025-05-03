import build123d as b123d
from Client import SocketClient
import time

_port = 65432
_address = "0.0.0.0"
_objects = []


def set_port(newPort):
    port = newPort


def set_address(newAddress):
    address = newAddress


def addObject(name, object, forceUpdate=False):
    global _objects
    _objects.append(
        {"Name": name, "Object": object, "ForceUpdate": forceUpdate}
    )


def update():
    # Create client obj, get the old object IDs and update the objects that are set to be updated
    global _objects

    startTime = time.time()

    sClient = SocketClient(_address, _port, b123d)
    sClient.connect()

    if len(_objects) != 0:
        for obj in _objects:
            part = obj["Object"]
            name = obj["Name"]
            forceUpdate = obj["ForceUpdate"]
            
            sClient.sendObject(name, part, forceUpdate)

    sClient.close()

    print(time.time() - startTime)

    _objects = []
