import numpy as np
import pyqtgraph as pg
from pyqtgraph import PlotWidget, GraphItem
from qtpy.QtCore import Signal, Slot


class SignalChangeVar:

    def __set_name__(self, owner, name):
        self.name = f"_{name}"

    def __set__(self, instance, value):
        setattr(instance, self.name, value)  # initially setting attr
        instance.valueChanged.emit(self.name[1:], value)


class WaveformWidget(PlotWidget):

    def plot(self, pos, waveform: str, parameters: list, *args, **kwargs):
        """Plot waveforms on graph"""

        item = DraggableGraphItem(**{'pos': pos, 'waveform': waveform, 'parameters': parameters, **kwargs})
        item.setData(**{'pos': pos, 'waveform': waveform, 'parameters': parameters, **kwargs})
        self.addItem(item)
        return item


class DraggableGraphItem(GraphItem):
    # initialize waveform parameters
    start_time_ms = SignalChangeVar()
    end_time_ms = SignalChangeVar()
    amplitude_volts = SignalChangeVar()
    offset_volts = SignalChangeVar()
    cutoff_frequency_hz = SignalChangeVar()
    max_volts = SignalChangeVar()
    min_volts = SignalChangeVar()
    valueChanged = Signal((str,float))

    def __init__(self, **kwargs):
        self.waveform = None
        self.dragPoint = None
        self.dragOffset = None
        self.parameters = None
        super().__init__(**kwargs)

    def setData(self, **kwds):
        self.data = kwds
        self.pos = self.data['pos']
        self.waveform = self.data['waveform']
        self.parameters = self.data['parameters']

        self.define_waves(self.waveform)

        npts = self.pos.shape[0]
        self.data['adj'] = np.column_stack((np.arange(0, npts - 1), np.arange(1, npts)))
        self.data['data'] = np.empty(npts, dtype=[('index', int)])
        self.data['data']['index'] = np.arange(npts)

        super().setData(**self.data)

    def define_waves(self, waveform: str):
        """Validate and define key indices in waveform"""

        if 'sawtooth' in waveform or 'triangle' in waveform:
            if self.pos.shape[0] != 5:
                raise Exception(f"Waveform {waveform} must have 5 points in data set. "
                                f"Waveform has {self.data['pos'].shape[0]}")

        elif 'square' in waveform:
            if self.pos.shape[0] != 6:
                raise Exception(f"Waveform {waveform} must have 6 points in data set. "
                                f"Waveform has {self.data['pos'].shape[0]}")

        for k in self.data['parameters']:
            setattr(self, k, 0.0)

    def mouseDragEvent(self, ev):

        if ev.isStart():
            pos = ev.buttonDownPos()
            pts = self.scatter.pointsAt(pos)
            if len(pts) == 0:
                ev.ignore()
                return
            self.dragPoint = pts[0]
            ind = pts[0].data()[0]
            self.dragOffsetY = self.pos[ind][1] - pos[1]
            self.dragOffsetX = self.pos[ind][0] - pos[0]

        elif ev.isFinish():
            self.dragPoint = None
            return
        else:
            if self.dragPoint is None:
                ev.ignore()
                return

        ind = self.dragPoint.data()[0]
        if self.waveform == 'square wave':
            self.move_square_wave(ind, ev)
        elif self.waveform == 'sawtooth':
            self.move_sawtooth(ind, ev)

        super().setData(**self.data)
        ev.accept()

    def move_square_wave(self, ind, ev, y_list=[], x_list=[]):
        """Move square wave type waveform"""
        # square wave will have 6 indices
        y_pos = ev.pos()[1] + self.dragOffsetY
        x_pos = ev.pos()[0] + self.dragOffsetX

        if ind in [1, 4] and y_pos <= self.pos[2][1] and y_pos >= 0:
            y_list = [0, 1, 4, 5] if 'min_volts' in self.data['parameters'] else []
        elif ind in [2,3] and y_pos >= self.pos[1][1]:
            y_list = [2,3] if 'max_volts' in self.data['parameters'] else []

        lower_limit_x = self.pos[ind - 1][0] if ind in [1,3] else self.pos[ind - 2][0]
        upper_limit_x = self.pos[ind + 2][0] if ind in [1,3] else self.pos[ind + 1][0]
        if x_pos <= upper_limit_x and x_pos >= lower_limit_x and ind in [1,2,3,4]:
            x_list = [ind + 1, ind] if ind in [1,3] else [ind - 1, ind]

        for i in y_list:
            self.pos[i][1] = ev.pos()[1] + self.dragOffsetY
        for i in x_list:
            self.pos[i][0] = ev.pos()[0] + self.dragOffsetX


        self.start_time_ms = self.pos[1][0]/10
        self.end_time_ms = self.pos[4][0]/10
        if 'min_volts' in self.data['parameters']:
            self.min_volts = self.pos[1][1]
        if 'max_volts' in self.data['parameters']:
            self.max_volts = self.pos[2][1]

    def move_sawtooth(self, ind, ev):
        """Move sawtooth type waveform"""
        # sawtooth will have 5 indices
        if ind == 1 or ind == 3:
            for i in [0, 1, 3, 4]:
                self.pos[i][1] = ev.pos()[1] + self.dragOffsetY
                self.pos[ind][0] = ev.pos()[0] + self.dragOffsetX
        elif ind == 2:
            self.pos[ind][1] = ev.pos()[1] + self.dragOffsetY
            self.pos[ind][0] = ev.pos()[0] + self.dragOffsetX