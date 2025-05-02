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

location = "/".join(__file__.split("/")[0 : len(__file__.split("/")) - 2])
sys.path.insert(0, location)  # less jank than before, but still jank

from SocketCommands import SocketCommands
from SocketState import SocketState

DEBUG_INFO = False

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
        self._recievingObjectName = ""
        self._recievingObjectForceUpdate = False
        self._recievingObjectID = -1
        self._recievingObjectStep = 0
        self._displayManager = displayManager
        self._objectData = b""
        self.objects = []
        self._purgeOldObjects = False

    def _send(self, bytecode, timeout=0):
        time.sleep(timeout)

        try:
            self._conn.sendall(bytecode)
        except socket.error as e:
            if e.errno == 104:
                print("unhandled closing of the socket!")
                self._conn = None

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

            debug("Connection established")

            self._socketState = SocketState.RECIEVING_COMMANDS.name
            self._send(SocketCommands.CONNECTION_SUCCESS.name.encode())
        else:
            data = self._conn.recv(1000000000)

            dataLen = len(data)

            if dataLen != 0:
                if not self._socketState == SocketState.RECIEVING_OBJECT_SHAPE.name:
                    data = data.decode("utf-8")

                debug(self._socketState)
                print(data)

                if data == SocketCommands.CLOSE_CONNECTION.name:
                    self._purgeOldObjects = True
                    self._conn.close()
                    self._conn = None
                    pass
                    

                if self._socketState == SocketState.RECIEVING_COMMANDS.name:
                    if data == SocketCommands.UPDATE_OBJECT.name:
                        self._socketState = SocketState.RECIEVING_OBJECT_NAME.name
                        self._objectData = b""
                    elif data == SocketCommands.UPDATE_OBJECT_PROP.name:
                        self._socketState = SocketState.RECIEVING_OBJECT_DATA.name

                        self._recievingObjectStep = 0
                        self._recievingObjectName = ""
                        self._recievingObjectID = 0
                        self._recievingObjectForceUpdate = False
                    elif data == SocketCommands.GET_OBJECT_ID.name:
                        debug(self._socketState)

                        self._socketState = SocketState.SEND_OBJECT_DATA.name
                    elif data == SocketCommands.SKIP_OBJECT.name:
                        self._socketState = SocketState.SKIP_OBJECT.name
                elif self._socketState == SocketState.RECIEVING_OBJECT_SHAPE.name:
                    if (
                        self._bytesIsString(data)
                        and data.decode() == SocketCommands.TRANSMISSION_OVER.name
                    ):
                        debug("Decode shape")
                        shape = TopoDS_Shape()
                        builder = BRep_Builder()

                        read_buffer = io.BytesIO(self._objectData)
                        BRepTools.Read_s(shape, read_buffer, builder)
                        read_buffer.close()

                        self._updateObject(self._recievingObjectName, shape)
                        self._socketState = SocketState.RECIEVING_COMMANDS.name
                        self._recievingObjectName = ""
                    else:
                        self._objectData += data
                elif self._socketState == SocketState.RECIEVING_OBJECT_NAME.name:
                    if type(data) == str:
                        debug(data)

                        self._recievingObjectName = data
                        self._socketState = SocketState.RECIEVING_OBJECT_SHAPE.name
                elif self._socketState == SocketState.RECIEVING_OBJECT_DATA.name:
                    if type(data) == str:
                        debug(data)

                        if self._recievingObjectStep == 0:
                            self._recievingObjectName = data

                            debug(self._recievingObjectName)
                        elif self._recievingObjectStep == 1:
                            if data == "True":  # bool() doesn't seem to work
                                self._recievingObjectForceUpdate = True
                            elif data == "False":
                                self._recievingObjectForceUpdate = False
                        else:
                            debug(data)

                            try:
                                self._recievingObjectID = float(data)

                                debug(self._recievingObjectID)
                            except Exception as e:
                                debug(str(e))
                                self._recievingObjectID = -1

                            for obj in self.objects:
                                if obj.name == self._recievingObjectName:
                                    obj.forceUpdate = self._recievingObjectForceUpdate
                                    obj.id = self._recievingObjectID
                                    debug("update: " + obj.name)
                                    break
                            
                            self._socketState = SocketState.RECIEVING_COMMANDS.name
                        self._recievingObjectStep += 1

                elif self._socketState == SocketState.SEND_OBJECT_DATA.name:
                    id = -1

                    for obj in self.objects:
                        if obj.name == data:
                            id = obj.id
                            break

                    self._send(str(id).encode())

                    self._socketState = SocketState.RECIEVING_COMMANDS.name
                elif self._socketState == SocketState.SKIP_OBJECT.name:                    
                    for obj in self.objects:
                        if obj.name == data:
                            obj.stale = False
                            break

                    self._socketState = SocketState.RECIEVING_COMMANDS.name

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
