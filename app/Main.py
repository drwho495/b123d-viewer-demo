import build123d as b123d
from Display import DisplayManager
from Server import SocketServer

if __name__ == "__main__":
    serverCreated = True

    # Initilize
    displayManager = DisplayManager(b123d)
    displayManager.create_widget()

    sServer = SocketServer(displayManager, b123d=b123d)

    def loopTest():
        print("test")

    try:
        sServer.createServer()
    except Exception as e:
        serverCreated = False
        print("Unable to start server! Error: " + str(e))

    displayManager.addLoopMethod(sServer.handleConnections)
    displayManager.start()
