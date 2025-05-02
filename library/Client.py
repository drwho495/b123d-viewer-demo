import socket
import sys
import io
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape  # Need this for creating an empty shape
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt, QEvent
from build123d import *
import build123d as b123d

sys.path.insert(
    0, "/home/hypocritical/b123d-projs/custom-viewer-testing/viewer-app/"
)  # jank
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
        self._send(
            SocketCommands.CLOSE_CONNECTION.name.encode(), 0.1
        )  # .close() isn't working?
        self._socket = None

    def connect(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        status = True

        try:
            self._socket.connect((self._HOST, self._PORT))
            self._send(SocketCommands.CONNECTION_SUCCESS.name.encode())
            data = self._socket.recv(1024).decode("utf-8")

            if data == SocketCommands.CONNECTION_SUCCESS.name:
                status = True

            # time.sleep(0.1)  # Wait for the server to be ready to recieve new message

            # self.close()
        except Exception as e:
            print("Connection failed! Error: " + str(e))

            status = False

        return status

    def _send(self, bytecode, timeout=0):
        time.sleep(timeout)

        self._socket.sendall(bytecode)

    def sendObject(self, name, part):
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
            self._send((SocketCommands.UPDATE_OBJECT.name + " " + name).encode(), 0)

            print(len(serialized_bytes))

            self._send(serialized_bytes, 0.1)
            self._send(SocketCommands.TRANSMISSION_OVER.name.encode(), 0.1)


# print(str(wheel.bounding_box()))

if __name__ == "__main__":
    sClient = SocketClient(b123d=b123d)
    status = sClient.connect()

    print(status)

    with BuildPart() as part:
        with Locations((0, 0, 0)):
            Box(15, 15, 15)

    startTime = time.time()

    sClient.sendObject("hello", part)

    print(time.time() - startTime)

    sClient.close()
