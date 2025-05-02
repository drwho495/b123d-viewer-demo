import build123d as b123d
from Client import SocketClient
import time

_port = 65432
_address = "0.0.0.0"
_objects = []


def _generateID(object):
    part = None

    if hasattr(object, "part"):
        part = object.part
    elif hasattr(object, "bounding_box"):
        part = object
    else:
        return -1

    try:
        bBox = part.bounding_box().size
        id = (
            len(part.edges())
            + len(part.vertices())
            + len(part.faces())
            + bBox.X
            + bBox.Y
            + bBox.Z
        )

        return id
    except:
        return -1


def set_port(newPort):
    port = newPort


def set_address(newAddress):
    address = newAddress


def addObject(name, object, forceUpdate=False):
    id = _generateID(object)

    _objects.append(
        {"Name": name, "Object": object, "ForceUpdate": forceUpdate, "ID": id}
    )

def update():
    # Create client obj, get the old object IDs and update the objects that are set to be updated

    startTime = time.time()

    sClient = SocketClient(_address, _port, b123d)
    sClient.connect()

    for obj in _objects:
        part = obj["Object"]
        name = obj["Name"]
        forceUpdate = obj["ForceUpdate"]
        id = obj["ID"]

        oldID = sClient.getObjectID(name)

        print(id)
        print(oldID)

        if oldID != id:
            sClient.sendObject(name, part, forceUpdate, id)
        else:
            print("Skip: " + name)

            sClient.skipObject(name)

    sClient.close()

    print(time.time() - startTime)

    pass
