from pymmcore_widgets import ZPlanWidget as ZPlanWidgetMMCore
from qtpy.QtWidgets import QSizePolicy, QHBoxLayout, QWidget, QVBoxLayout, QCheckBox, QDoubleSpinBox, \
    QMessageBox, QPushButton, QLabel, QTabWidget, QApplication
from qtpy.QtCore import Signal, Qt
from qtpy.QtGui import QColor, QMatrix4x4, QVector3D
import numpy as np
from math import tan, radians, sqrt, ceil, floor
from typing import cast
import useq
import enum

class Mode(enum.Enum):
    """Recognized ZPlanWidget modes."""

    TOP_BOTTOM = "top_bottom"
    RANGE_AROUND = "range_around"
    ABOVE_BELOW = "above_below"


class ZPlanWidget(ZPlanWidgetMMCore):
    """Widget to plan out scanning dimension"""

    def __init__(self, z_limits: [float] = None, unit: str = 'um'):
        """:param z_limits: list containing max and min values of z dimension
           :param unit: unit of all size values"""

        self.start = QDoubleSpinBox()

        super().__init__()

        for i in range(self._grid_layout.count()):
            widget = self._grid_layout.itemAt(i).widget()
            if type(widget) == QLabel:
                if widget.text() == 'Bottom:':
                    widget.setText('Start:')
                elif widget.text() == 'Top:':
                    widget.setText('End:')

        # TODO: Hide direction label
        self._bottom_to_top.hide()
        self._top_to_bottom.hide()

        # Add start box
        self.start.valueChanged.connect(self._on_change)
        self.start.setRange(z_limits[0], z_limits[1])
        self._grid_layout.addWidget(QLabel("Start:"), 7, 0, Qt.AlignmentFlag.AlignRight)
        self._grid_layout.addWidget(self.start, 7, 1)
        self._grid_layout.addWidget(QLabel("\u00b5m"), 7, 2, Qt.AlignmentFlag.AlignRight)
        self.setMode('top_bottom')  # Hide labels

        # self.bottom.disconnect()
        # self.bottom.valueChanged.connect()

    def value(self):
        """Overwrite to change how z plan is calculated. Return a list of positions"""

        if self._mode.value == 'top_bottom':
            steps = ceil((self.top.value() - self.bottom.value()) / self.step.value())
            if steps > 0:
                return [self.bottom.value() + (self.step.value() * i) for i in range(steps)]
            else:
                return [self.bottom.value() - (self.step.value() * i) for i in range(abs(steps - 1))]
        elif self._mode.value == 'range_around':
            return [self.start.value() + i for i in useq.ZRangeAround(range=round(self.range.value(), 4),
                                                                      step=self.step.value(),
                                                                      go_up=self._bottom_to_top.isChecked())]
        elif self._mode.value == 'above_below':
            return [self.start.value() + i for i in useq.ZAboveBelow(
                above=round(self.above.value(), 4),
                below=round(self.below.value(), 4),
                step=self.step.value(),
                go_up=self._bottom_to_top.isChecked())]

    def _on_change(self, update_steps: bool = True):
        """Overwrite to change setting step behaviour"""
        val = self.value()

        # update range readout
        self._range_readout.setText(f"Range: {self.currentZRange():.2f} \u00b5m")
        # update steps readout
        if update_steps:
            self.steps.blockSignals(True)
            if val is None:
                self.steps.setValue(0)
            else:
                self.steps.setValue(len(val))
            self.steps.blockSignals(False)
        self.valueChanged.emit(val)

    def setMode(self, mode):
        """Hide start row"""
        if isinstance(mode, str):
            mode = Mode(mode)
        elif isinstance(mode, (bool, type(None))):
            mode = cast("QAction", self.sender()).data()

        for i in range(self._grid_layout.count()):
            widget = self._grid_layout.itemAt(i).widget()
            if (
                    type(
                        widget) == QLabel and widget.text() == 'Start:' or widget.text() == "\u00b5m") or widget == self.start:
                if mode.value == "top_bottom":
                    widget.setVisible(False)
                else:
                    widget.setVisible(True)
        super().setMode(mode)

    # def _on_steps_changed(self, steps: int) -> None:
    #     """Overwrite so if steps increased, z volume is expanded"""
    #     if self._mode.value == 'top_bottom':
    #
    #     elif self._mode.value == "range_around":
    #
    #     elif self._mode == "above_below":
