from zoo.libs.pyqt.qt import QtWidgets, QtGui, QtCore


class CubicPath(QtGui.QGraphicsPathItem):
    contextMenuRequested = QtCore.Signal(object)
    defaultColor = QtGui.QColor(138, 200, 0)
    selectedColor = QtGui.QColor(255, 255, 255)
    hoverColor = QtGui.QColor(255, 255, 255)

    def __init__(self, sourcePoint, destinationPoint=None):
        super(CubicPath, self).__init__()

        self.sourcePoint = sourcePoint
        self.destinationPoint = destinationPoint
        self.defaultPen = QtGui.QPen(self.defaultColor, 1.25, style=QtCore.Qt.DashLine)
        self.defaultPen.setDashPattern([1, 2, 2, 1])
        self.selectedPen = QtGui.QPen(self.selectedColor, 1.7, style=QtCore.Qt.DashLine)
        self.selectedPen.setDashPattern([1, 2, 2, 1])

        self.hoverPen = QtGui.QPen(self.hoverColor, 1.7, style=QtCore.Qt.DashLine)
        self.selectedPen.setDashPattern([1, 2, 2, 1])
        self.hovering = False

        self.setPen(self.defaultPen)
        self.setZValue(-1)
        self.setFlags(self.ItemIsFocusable | self.ItemIsSelectable | self.ItemIsMovable)
        if self._sourcePort and self._destinationPort:
            self.updatePath()
        self.update()

    def hoverLeaveEvent(self, event):
        super(CubicPath, self).hoverEnterEvent(event)
        self.hovering = False
        self.update()

    def hoverEnterEvent(self, event):
        super(CubicPath, self).hoverEnterEvent(event)
        self.hovering = True
        self.update()

    def paint(self, painter, option, widget):
        if self.isSelected():
            painter.setPen(self.selectedPen)
        elif self.hovering:
            painter.setPen(self.hoverPen)
        else:
            painter.setPen(self.defaultPen)
        painter.drawPath(self.path())

    def updatePath(self):

        path = QtGui.QPainterPath()
        path.moveTo(self.sourcePoint)
        ctrl1 = QtCore.QPointF(self.sourcePoint.x(), self.sourcePoint.y())
        path.cubicTo(ctrl1, ctrl1, self.destinationPoint)
        self.setPath(path)

    def setSourcePoint(self, point):
        self.sourcePoint = point
        self.updatePath()

    def setDestinationPoint(self, point):
        self.destinationPoint = point
        self.updatePath()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            event.accept()
            if self.isSelected():
                self.setSelected(False)
            else:
                self.setSelected(True)

            self.update()
        self.destinationPoint = event.pos()

    def mouseMoveEvent(self, event):
        self.destinationPoint = event.pos()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete or event.key() == QtCore.Qt.Key_Backspace:
            self.close()
            event.accept()
            return
        event.ignore()

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)

        self.contextMenuRequested.emit(menu)
        menu.exec_(event.scenePos())
        event.setAccepted(True)
