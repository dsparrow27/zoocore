import platform
from zoo.libs.pyqt.qt import QtWidgets, QtCore, QtGui
from zoo.libs import iconlib


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, title="", width=600, height=800, icon="",
                 parent=None, showOnInitialize=True):
        super(MainWindow, self).__init__(parent=parent)
        self.setContentsMargins(2, 2, 2, 2)
        self.setDockNestingEnabled(True)
        self.setDocumentMode(True)
        self.title = title
        self.setObjectName(title)
        self.setWindowTitle(title)
        self.resize(width, height)

        self.docks = []
        self.toolBars = {}

        self.addCustomStatusBar()

        self.setupMenuBar()

        self.centralWidget = QtWidgets.QWidget()
        self.setCentralWidget(self.centralWidget)
        self.reapplySettings()
        self.setDockOptions(QtWidgets.QMainWindow.AllowNestedDocks |
                            QtWidgets.QMainWindow.AnimatedDocks)
        if icon:
            if isinstance(icon, QtGui.QIcon):
                self.setWindowIcon(icon)
            else:
                self.setWindowIcon(iconlib.icon(icon))
        if showOnInitialize:
            self.show()

    def addCustomStatusBar(self):
        self.setStatusBar(self.statusBar())
        self.statusBar().showMessage("Status info/tips displayed here..")

    def setupMenuBar(self):
        self.fileMenu = self.menuBar().addMenu("File")
        self.viewMenu = self.menuBar().addMenu("View")
        self.exitAction = QtWidgets.QAction(self)
        self.exitAction.setIcon(iconlib.icon("close"))
        self.exitAction.setText("Close")
        self.exitAction.setShortcut("ctrl+Q")
        self.exitAction.setToolTip("Close's application")
        self.fileMenu.addAction(self.exitAction)
        self.exitAction.triggered.connect(self.close)

    def setCustomCentralWidget(self, widget):
        self.setCentralWidget(widget)

    def addDockWidget(self, area, dockWidget, orientation=QtCore.Qt.Horizontal):
        """Adds a dock widget to the current window at the specified location, if the location already has a
        :param area:QtCore.Qt.DockWidgetArea
        :param dockWidget: QtWidgets.QDockWidget
        :param orientation: QtCore.Qt.Orientation
        """
        self.docks.append(dockWidget)
        # add a show/hide action to the view menu
        self.viewMenu.addAction(dockWidget.toggleViewAction())
        # tabify the dock if obne already exists at the area specified
        for currentDock in self.docks:
            if self.dockWidgetArea(currentDock) == area:
                self.tabifyDockWidget(currentDock, dockWidget)
                return
        super(MainWindow, self).addDockWidget(area, self.dock, orientation)

    def findDock(self, dockName):
        """Returns the dock widget based on the object name passed in as the argument
        :param dockName: str, the objectName to find, docks must be
        :return: QDockWidget
        """
        for dock in self.docks:
            if dock.objectName() == dockName:
                return dock

    def toggleMaximized(self):
        """Toggles the maximized window state
        """
        if self.windowState() and QtCore.Qt.WindowMaximized:
            self.showNormal()
        else:
            self.showMaximized()

    def closeEvent(self, ev):
        """
        saves the window state on the close event
        """
        qsettings = QtCore.QSettings()

        qsettings.beginGroup("mainWindow")
        qsettings.setValue("geometry", self.saveGeometry())
        qsettings.setValue("saveState", self.saveState())
        qsettings.setValue("maximized", self.isMaximized())
        if not self.isMaximized() == True:
            qsettings.setValue("pos", self.pos())
            qsettings.setValue("size", self.size())
        qsettings.endGroup()

        super(MainWindow, self).closeEvent(ev)

    def reapplySettings(self):
        """
        Read window attributes from settings,
        using current attributes as defaults (if settings not exist.)

        Called at QMainWindow initialization, before show().
        """
        qsettings = QtCore.QSettings()

        qsettings.beginGroup("mainWindow")

        # No need for toPoint, etc. : PySide converts types
        self.restoreGeometry(qsettings.value("geometry", self.saveGeometry()))
        self.restoreState(qsettings.value("saveState", self.saveState()))
        self.move(qsettings.value("pos", self.pos()))
        self.resize(qsettings.value("size", self.size()))
        if qsettings.value("maximized", self.isMaximized()):
            self.showMaximized()

        qsettings.endGroup()

    def helpAbout(self, copyrightDate, about, version=1.0):
        """
        This is a helper method for easily adding a generic help messageBox to self
        Creates a about MessageBox
        :param copyrightDate : string , the copyright date for the tool
        :param about : string, the about information
        """
        __version__ = version
        QtWidgets.QMessageBox.about(self, "About" + self.objectName(),
                                    "<b>'About {0}</b> v {1}Copyright &copy; 2007,{2}.All rights reserved.\
                                    <p>Python {3} - Qt {4} - PyQt {5} on {6}".format(copyrightDate, about,
                                                                                     __version__,
                                                                                     platform.python_version(),
                                                                                     QtCore.QT_VERSION_STR,
                                                                                     QtCore.PYQT_VERSION_STR,
                                                                                     platform.system()))


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow("test", showOnInitialize=False)
    dock = dockWidget.DockWidget(win)
    dock.setWindowTitle("testdock")
    dock.setObjectName("testDock")
    win.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)
    win.show()
    sys.exit(app.exec_())