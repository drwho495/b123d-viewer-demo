# # Import build123d functionality.
from libs.occt_widget import OCCTWidget
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import (
    pyqtSlot,
    QMetaObject,
    Q_ARG,
    pyqtSignal,
    QThread,
    Qt,
    QEvent,
    QTimer,
    QEventLoop,
)
import OCP
import time


class DisplayThread(QThread):
    result_ready = pyqtSignal(int)

    def __init__(self, displayManager):
        self.displayManager = displayManager
        super().__init__()

    def run(self):
        self.sleep(1)


class DisplayManager:
    def __init__(self, b123d):
        self._b123d = b123d
        self._app = None
        self._widget = None
        self._time = 0
        self._runUpdateObj = True
        self._objUpdate = 1
        self._loopMethods = []
        self._displayedObjects = []

    def addObj(self, AIS_Shape):
        self._displayedObjects.append(object)

        self._widget.context.Display(AIS_Shape, True)

    def removeObj(self, AIS_Shape):
        self._displayedObjects.append(object)

        self._widget.context.Remove(AIS_Shape, True)

    def updateObj(self, AIS_Shape):
        self._displayedObjects.append(object)

        self._widget.context.Remove(AIS_Shape, True)
        self._widget.context.Display(AIS_Shape, True)  # Bug Workaround

    def create_widget(self):
        self._app = QApplication([""])
        # app.exec()

        self._widget = OCCTWidget()
        self._widget.show()

    def addLoopMethod(self, function):
        self._loopMethods.append(function)

    def loop(self):
        # print("test")
        """# Old testing loop
        if time.time() - self._time > 3 and self._objUpdate <= 2:
            self._time = time.time()

            self.updateObj(self._objUpdate)

            self._objUpdate += 1

            print("update obj")
        """

        for method in self._loopMethods:
            method()

    def start(self):
        self._time = time.time()

        self.timer = QTimer()
        self.timer.timeout.connect(self.loop)
        self.timer.start(0)

        self._app.exec_()


if __name__ == "__main__":
    import build123d as b123d

    display = DisplayManager(b123d)

    display.create_widget()
    display.start()
