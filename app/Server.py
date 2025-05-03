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
import time
import json

location = "/".join(__file__.split("/")[0 : len(__file__.split("/")) - 2])
sys.path.insert(0, location)  # less jank than before, but still jank

from SocketCommands import SocketCommands
from SocketState import SocketState

DEBUG_INFO = True


def debug(str):
    if DEBUG_INFO:
        print(str)


class SocketServer:
    def __init__(self, displayManager, host="0.0.0.0", port=65432, b123d=None):
        self.HOST = host
        self.PORT = port
        self._socket = None
        self._b123d = b123d
        self._conn = None
        self._connStart = False
        self._socketState = SocketState.RECIEVING_COMMANDS.name
        self._recievingObjectIndex = 0
        self._recievingObjectShapeSize = 0
        self._recievingObjectForceUpdate = False
        self._displayManager = displayManager
        self._objectData = b""
        self.objects = []
        self._purgeOldObjects = False
        self._lastObjectDataSize = 0

    def _send(self, bytecode, timeout=0):
        time.sleep(timeout)

        try:
            self._conn.sendall(bytecode)
        except socket.error as e:
            if e.errno == 104:
                print("unhandled closing of the socket!")
                self._conn = None

    def _sendJson(self, command, timeout=0):
        jsonBytes = json.dumps(command).encode()

        self._send(jsonBytes, timeout)

    def _recvJson(self, size=1024):
        data = self._conn.recv(size)

        try:
            jsonData = json.loads(data.decode())

            return jsonData, data
        except Exception as e:
            debug("Recieve JSON Error: " + str(e))
            # debug(data.decode())

            return None, data

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
        # self._socket.settimeout(.5)

        try:
            self._socket.accept()
        except socket.error as e:
            if e.errno == 11:  # errno.EAGAIN
                pass
            else:
                raise e

    def _getActiveObjectIndex(self, name):
        foundObject = False

        for i, obj in enumerate(self.objects):
            if obj.name == name:
                return i

        if not foundObject:
            newObject = Object(name, 0, None)
            newObject.stale = False
            self.objects.append(newObject)

            return len(self.objects) - 1

    def _handleCommands(self):
        if self._connStart:
            self._connStart = False  # Set here incase there is an error

            debug("Connection established")

            self._socketState = SocketState.RECIEVING_COMMANDS.name
            self._sendJson({"Message": SocketCommands.CONNECTION_SUCCESS.name})
        else:
            # data = self._conn.recv(1000000000)
            jsonData, data = self._recvJson(1000000000)

            dataLen = len(data)

            if dataLen != 0:
                if not self._socketState == SocketState.RECIEVING_OBJECT_SHAPE.name:
                    data = data.decode()

                debug(jsonData)
                # debug(len(data))

                if jsonData != None and jsonData["Message"] == SocketCommands.CLOSE_CONNECTION.name:
                    self._purgeOldObjects = True
                    self._conn.close()
                    self._conn = None
                    pass

                if jsonData != None and self._socketState == SocketState.RECIEVING_COMMANDS.name:
                    if jsonData["Message"] == SocketCommands.UPDATE_OBJECT.name:
                        self._objectData = b""
                        self._recievingObjectIndex = self._getActiveObjectIndex(jsonData["Name"])
                        self._recievingObjectShapeSize = int(jsonData["ShapeDataSize"])
                        self._recievingObjectForceUpdate = jsonData["ForceUpdate"]
                        self.objects[self._recievingObjectIndex].stale = False

                        if self._recievingObjectShapeSize == self.objects[self._recievingObjectIndex].shapeDataSize:
                            self._socketState = SocketState.RECIEVING_COMMANDS.name
                            self._sendJson({"Message": SocketCommands.SKIP_OBJECT.name})

                            debug("skip")
                        else:
                            self._socketState = SocketState.RECIEVING_OBJECT_SHAPE.name

                            self._sendJson({"Message": SocketCommands.READY.name})
                        
                        self.objects[self._recievingObjectIndex].shapeDataSize = self._recievingObjectShapeSize
                    """
                    elif jsonData["Message"] == SocketCommands.UPDATE_OBJECT_PROP.name:
                        self._socketState = SocketState.RECIEVING_OBJECT_DATA.name

                        self._recievingObjectName = jsonData["Name"]
                        self._recievingObjectID = 0
                        self._recievingObjectForceUpdate = False
                    
                    elif data == SocketCommands.GET_OBJECT_ID.name:
                        debug(self._socketState)

                        self._socketState = SocketState.SEND_OBJECT_DATA.name
                    elif data == SocketCommands.SKIP_OBJECT.name:
                        self._socketState = SocketState.SKIP_OBJECT.name
                    """

                elif self._socketState == SocketState.RECIEVING_OBJECT_SHAPE.name:
                    self._objectData += data

                    print(len(self._objectData))

                    if len(self._objectData) == self._recievingObjectShapeSize:
                        debug("Decode shape")
                        shape = TopoDS_Shape()
                        builder = BRep_Builder()

                        debug(len(self._objectData))

                        self._send(SocketCommands.READY.name.encode())

                        read_buffer = io.BytesIO(self._objectData)
                        BRepTools.Read_s(shape, read_buffer, builder)
                        read_buffer.close()

                        if self.objects[self._recievingObjectIndex].new:
                            self.objects[self._recievingObjectIndex].aisShape = AIS_Shape(shape)

                            self._displayManager.addObj(self.objects[self._recievingObjectIndex].aisShape)
                            self.objects[self._recievingObjectIndex].new = False
                        else:
                            self.objects[self._recievingObjectIndex].updateShape(shape)
                            self._displayManager.updateObj(self.objects[self._recievingObjectIndex].aisShape)

                        self._socketState = SocketState.RECIEVING_COMMANDS.name
                        self._recievingObjectName = ""
                        self._recievingObjectShapeSize = 0

                        debug("done")

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
                        debug("Remove " + obj.name)
                    else:
                        obj.stale = True

            try:
                conn, _ = self._socket.accept()

                debug(type(conn))

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
