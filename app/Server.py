import socket
import io
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape
from OCP.AIS import AIS_Shape
from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt, QEvent
from OCP.BRep import BRep_Builder
from Display import DisplayManager
from Object import Object
import threading
import sys

sys.path.insert(
    0, "/home/hypocritical/b123d-projs/custom-viewer-testing/viewer-app/"
)  # jank
from SocketCommands import SocketCommands


class SocketServer:
    def __init__(self, displayManager, host="0.0.0.0", port=65432, b123d=None):
        self.HOST = host
        self.PORT = port
        self._socket = None
        self._b123d = b123d
        self._conn = None
        self._connStart = False
        self._recievingObject = False
        self._recievingObjectName = ""
        self._displayManager = displayManager
        self._objectData = b""
        self.objects = []
        self._purgeOldObjects = False

    def _readerThreadFunction(self):
        while self._socket != None:
            try:
                data = self._conn.recv(1000000000)

                self._bytesBuffer.append(data)
            except:
                pass  # Client wasn't ready

    def _startThread(self):
        self._readerThread = threading.Thread(
            target=self._readerThreadFunction, args=(self)
        )

    def _stopThread(self):
        if self._socket == None:
            self._readerThread.join()
            self._readerThread = None
        else:
            raise Exception("_socket Must be set to None before killing the thread!")

    def createServer(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self._socket.setblocking(False)
        self._socket.bind((self.HOST, self.PORT))
        self._socket.listen()

        try:
            self._socket.accept()
        except socket.error as e:
            if e.errno == 11:  # errno.EAGAIN
                pass
            else:
                raise e

    def _bytesIsString(self, bytedata):
        try:
            bytedata.decode()
            return True
        except:
            return False

    def _updateObject(self, name, shape):
        print("Update " + name)

        foundObject = False

        for i, obj in enumerate(self.objects):
            if obj.name == name:
                obj.updateShape(shape)
                self._displayManager.updateObj(obj.aisShape)
                obj.stale = False

                foundObject = True

                break

        if not foundObject:
            ShapeAIS = AIS_Shape(shape)
            newObject = Object(name, -1, ShapeAIS)
            newObject.stale = False

            self.objects.append(newObject)

            self._displayManager.addObj(ShapeAIS)

    def _handleCommands(self):
        if self._connStart:
            self._connStart = False  # Set here incase there is an error

            print("Connection established")

            self._conn.send(SocketCommands.CONNECTION_SUCCESS.name.encode())
        else:
            data = self._conn.recv(1000000000)

            dataLen = len(data)

            if dataLen != 0:
                if not self._recievingObject:
                    data = data.decode("utf-8")

                print(dataLen)

                if not self._recievingObject:
                    if data == SocketCommands.CLOSE_CONNECTION.name:
                        self._purgeOldObjects = True
                        self._conn.close()
                        self._conn = None
                        pass
                    elif data.startswith(SocketCommands.UPDATE_OBJECT.name):
                        self._recievingObject = True
                        self._recievingObjectName = data.split(" ")[1]
                        self._objectData = b""
                else:
                    if (
                        self._bytesIsString(data)
                        and data.decode() == SocketCommands.TRANSMISSION_OVER.name
                    ):
                        print(data.__str__)
                        shape = TopoDS_Shape()
                        builder = BRep_Builder()

                        read_buffer = io.BytesIO(self._objectData)
                        BRepTools.Read_s(shape, read_buffer, builder)
                        read_buffer.close()

                        self._updateObject(self._recievingObjectName, shape)
                        self._recievingObject = False
                        self._recievingObjectName = ""
                    else:
                        self._objectData += data

    # This handles the connection between the user and the DisplayManager,
    # adding and removing objects as instructed by the user.
    def handleConnections(self):
        if self._conn == None:  # Attempt to accept connection
            if self._purgeOldObjects:
                self._purgeOldObjects = False

                for i, obj in enumerate(self.objects):
                    if obj.stale:
                        self.objects.pop(i)

                        self._displayManager.removeObj(obj.aisShape)
                        print("Remove " + obj.name)
                    else:
                        obj.stale = True

            try:
                conn, _ = self._socket.accept()

                print(type(conn))

                self._conn = conn
                self._connStart = True
            except socket.error as e:
                if e.errno == 11:  # errno.EAGAIN
                    pass  # No client available
                else:
                    raise e
        else:  # Handle commands
            self._handleCommands()


if __name__ == "__main__":
    sServer = SocketServer()

    sServer.createServer()
