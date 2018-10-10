from qt import QtCore, QtGui, QtWidgets


METHOD_MASK = 0
METHOD_STYLESHEET = 1


class RoundButton(QtWidgets.QPushButton):
    """
    A nice rounded button. Two methods to rendering it out currently.
    You can use this like a QPushButton

    Mask:
    Mask will cut the button into a circle. It also allows for custom stylesheets.
    The downside though is that it is pixelated when drawing it out.

    .. code-block:: python

        roundBtn = RoundButton(self, "Hello World", method=Method.Mask)
        roundBtn.setMethod(Method.Mask)  # Use this if you want to set it after

    Stylesheet:
    Style sheet creates a smooth circle button, no pixelation. However for rectangle buttons,
    it wont be round and the user wont be able to use their own stylesheet.

    .. code-block:: python

        roundBtn = RoundButton(self, "Hello World", method=Method.StyleSheet)
        roundBtn.setMethod(Method.StyleSheet)  # Use this if you want to set it after
        roundBtn.setFixedSize(QtCore.QSize(24,24))  # Square dimensions recommended

    """

    def __init__(self, parent=None, text=None, icon=None, method=METHOD_STYLESHEET):
        super(RoundButton, self).__init__(parent=parent,text=text, icon=icon)
        self.method = method

    def setMethod(self, method=METHOD_MASK):
        """Set the method of rendering, Method.Mask or Method.StyleSheet

        StyleSheet:
            - Can't have own stylesheet
            - Smooth Rendering

        Mask:
            - Pixelated edges
            - Can set custom stylesheet

        :param method: Method.Mask or Method.StyleSheet
        :type method: int
        :return:
        """
        self.method = method

    def resizeEvent(self, event):
        """Resize and update based on the method

        :return:
        """

        if self.method == METHOD_MASK:
            self.setMask(QtGui.QRegion(self.rect(), QtGui.QRegion.Ellipse))
        elif self.method == METHOD_STYLESHEET:
            radius = min(self.rect().width()*0.5, self.rect().width()*0.5)
            self.setStyleSheet("border-radius: {}px;".format(radius))

        super(RoundButton, self).resizeEvent(event)
