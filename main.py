import sys
from viewController import ViewController
from PyQt5.QtWidgets import *


class MyApp:
    def __init__(self):
        self.myViewController = ViewController()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    myApp = MyApp()
    app.exec_()