import numpy as np
from pyqtgraph import PlotWidget, TextItem, mkPen, mkBrush, ScatterPlotItem, setConfigOption, setConfigOptions
from qtpy.QtWidgets import QApplication, QGraphicsEllipseItem
from qtpy.QtCore import Signal, QTimer, Property, QObject, Slot
import sys
from math import sin, cos, pi, atan, degrees, radians

setConfigOptions(background=.95, antialias=True)


class FilterWheelWidget(PlotWidget):
    ValueChangedInside = Signal((str,))

    def __init__(self, filters: list[str], radius=10, **kwargs):
        """Simple scroll widget for filter wheel
        :param filters: list possible filters"""

        super().__init__(**kwargs)

        self._timeline = TimeLine(loopCount=1, interval=50)
        self.setMouseEnabled(x=False, y=False)
        self.showAxes(False, False)

        self.filters = filters
        self.radius = radius

        angles = [2 * pi / len(self.filters) * i for i in range(len(self.filters))]
        points = {}
        for angle, slot in zip(angles, filters):
            point = FilterItem(text=str(slot), anchor=(.5, .5), color='black')
            point.setPos((self.radius + 1) * cos(angle),
                         (self.radius + 1) * sin(angle))
            point.pressed.connect(self.move_wheel)
            self.addItem(point)
            points[slot] = point

        wheel = QGraphicsEllipseItem(-self.radius, -self.radius, self.radius * 2, self.radius * 2)
        wheel.setPen(mkPen((0, 0, 0, 100)))
        wheel.setBrush(mkBrush((128, 128, 128)))
        self.addItem(wheel)

        self.notch = ScatterPlotItem(pos=[[(self.radius - 3) * cos(0),
                                           (self.radius - 3) * sin(0)]], size=100)
        self.addItem(self.notch)

        self.setAspectLocked(1)
    def set_index(self, slot_name):
        filter_index = self.filters.index(slot_name)
        angle = [2 * pi / len(self.filters) * i for i in range(len(self.filters))][filter_index]
        self.move_wheel(slot_name, ((self.radius + 1) * cos(angle),(self.radius + 1) * sin(angle)))

    def move_wheel(self, name, slot_pos):

        self.ValueChangedInside.emit(name)
        notch_pos = [self.notch.getData()[0][0],self.notch.getData()[1][0]]
        thetas = []
        for x,y in [notch_pos, slot_pos]:
            if y > 0 > x or (y < 0 and x < 0):
                thetas.append(180+degrees(atan(y/x)))
            elif y < 0 < x:
                thetas.append(360+degrees(atan(y/x)))
            else:
                thetas.append(degrees(atan(y/x)))

        notch_theta, slot_theta = thetas
        delta_theta = slot_theta-notch_theta
        if slot_theta > notch_theta and delta_theta <= 180:
            step_size = 1
        elif slot_theta > notch_theta and delta_theta > 180:
            step_size = -1
            slot_theta = (slot_theta - notch_theta) - 360
        else:
            step_size = -1
        self._timeline.stop()
        self._timeline = TimeLine(loopCount=1, interval=50, step_size=step_size)
        self._timeline.setFrameRange(notch_theta, slot_theta)
        self._timeline.frameChanged.connect(self.generate_data)
        self._timeline.start()

    @Slot(float)
    def generate_data(self, i):
        self.notch.setData(pos=[[(self.radius - 3) * cos(radians(i)),
                                 (self.radius - 3) * sin(radians(i))]])

class FilterItem(TextItem):
    pressed = Signal((str, list))

    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)
        self.pressed.emit(self.textItem.toPlainText(), self.pos())


class TimeLine(QObject):
    frameChanged = Signal(float)

    def __init__(self, interval=60, loopCount=1, step_size=1, parent=None):
        super(TimeLine, self).__init__(parent)
        self._stepSize = step_size
        self._startFrame = 0
        self._endFrame = 0
        self._loopCount = loopCount
        self._timer = QTimer(self, timeout=self.on_timeout)
        self._counter = 0
        self._loop_counter = 0
        self.setInterval(interval)

    def on_timeout(self):

        if (self._startFrame <= self._counter <= self._endFrame and self._stepSize > 0) or \
                (self._startFrame >= self._counter >= self._endFrame and self._stepSize < 0):
            self.frameChanged.emit(self._counter)
            self._counter += self._stepSize
        else:
            self._counter = 0
            self._loop_counter += 1
        if self._loopCount > 0:
            if self._loop_counter >= self.loopCount():
                self._timer.stop()

    def setLoopCount(self, loopCount):
        self._loopCount = loopCount

    def loopCount(self):
        return self._loopCount

    interval = Property(int, fget=loopCount, fset=setLoopCount)

    def setInterval(self, interval):
        self._timer.setInterval(interval)

    def interval(self):
        return self._timer.interval()

    interval = Property(int, fget=interval, fset=setInterval)

    def setFrameRange(self, startFrame, endFrame):
        self._startFrame = startFrame
        self._endFrame = endFrame

    @Slot()
    def start(self):
        self._counter = self._startFrame
        self._loop_counter = 0
        self._timer.start()

    def stop(self):
        self._timer.stop()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    filterwheel = FilterWheelWidget(['405', '488', '561', '638', '594'])
    filterwheel.show()
    filterwheel.set_index('561')
    sys.exit(app.exec_())
