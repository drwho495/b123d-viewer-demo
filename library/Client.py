import socket
import sys
import io
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape  # Need this for creating an empty shape
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt, QEvent
from build123d import *
import build123d as b123d
import json

location = "/".join(__file__.split("/")[0 : len(__file__.split("/")) - 2])
sys.path.insert(0, location)  # less jank than before, but still jank

from SocketCommands import SocketCommands
import time

# wheel = import_step(
# "/home/hypocritical/b123d-projs/sideplate/imports/3625-0100-0104.step"
# )


class SocketClient:
    def __init__(self, host="0.0.0.0", port=65432, b123d=None):
        self._HOST = host
        self._PORT = port
        self._socket = None
        self._b123d = b123d

    def close(self):
        self._sendJson(
            {"Message": SocketCommands.CLOSE_CONNECTION.name}, 0.1
        )  # .close() isn't working?
        self._socket = None

    def _recvJson(self, size=1024):
        data = self._socket.recv(1024).decode()

        try:
            jsonData = json.loads(data)

            return jsonData
        except:
            raise Exception("The server did not return JSON!")

    def connect(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        status = True

        try:
            self._socket.connect((self._HOST, self._PORT))
            self._sendJson({"Message": SocketCommands.CONNECTION_SUCCESS.name})
            data = self._recvJson()

            if data["Message"] == SocketCommands.CONNECTION_SUCCESS.name:
                status = True

            # time.sleep(0.1)  # Wait for the server to be ready to recieve new message

            # self.close()
        except Exception as e:
            print("Connection failed! Error: " + str(e))

            status = False

        return status

    def _send(self, bytecode: bytes, timeout=0):
        time.sleep(timeout)

        self._socket.sendall(bytecode)

    def _sendJson(self, command, timeout=0):
        jsonBytes = json.dumps(command).encode()

        self._send(jsonBytes, timeout)

    def _waitForMsg(self, timeout=10):
        oldTimeout = self._socket.gettimeout()
        # self._socket.settimeout(timeout)

        data = self._socket.recv(1024).decode()

        print(data)

        try:
            jsonData = json.loads(data)

            return jsonData, data
        except:
            return None, data

    def sendObject(self, name, part, forceUpdate):
        # Might need to be moved to a library #
        if hasattr(part, "part"):
            ocpShape = part.part.wrapped
        elif hasattr(part, "wrapped"):
            ocpShape = part.wrapped

        print(ocpShape)

        if ocpShape.IsNull():
            print(Exception("shape is null!"))

        write_buffer = io.BytesIO()
        BRepTools.Write_s(ocpShape, write_buffer)

        serialized_bytes = write_buffer.getvalue()
        write_buffer.close()

        if self._socket != None:
            # self._send(SocketCommands.UPDATE_OBJECT.name.encode(), 0.05)
            # self._send(name.encode(), 0.05)
            # self._send(str(len(serialized_bytes)).encode(), 0.05)

            self._sendJson(
                {
                    "Message": SocketCommands.UPDATE_OBJECT.name,
                    "Name": name,
                    "ShapeDataSize": str(len(serialized_bytes)),
                    "ForceUpdate": forceUpdate,
                },
                0.1,
            )

            print(len(serialized_bytes))

            jsonMsg, _ = self._waitForMsg()

            print(jsonMsg)
            
            if jsonMsg != None and jsonMsg["Message"] == SocketCommands.READY.name:
                self._send(serialized_bytes, 0.05)
                self._waitForMsg()

                return True
            elif jsonMsg != None and jsonMsg["Message"] == SocketCommands.SKIP_OBJECT.name:
                return False

if __name__ == "__main__":
    sClient = SocketClient(b123d=b123d)
    status = sClient.connect()

    print(status)

    with BuildPart() as part:
        with Locations((0, 0, 0)):
            Box(5, 5, 5)

    startTime = time.time()

    sClient.sendObject("hello2", part, False)

    print(time.time() - startTime)

    sClient.close()
