from pyqtgraph.opengl import GLViewWidget, GLBoxItem, GLLinePlotItem, GLAxisItem
from pymmcore_widgets import GridPlanWidget as GridPlanWidgetMMCore
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

class GridPlanWidget(GridPlanWidgetMMCore):
    """Widget to plan out grid. Pymmcore already has a great one"""

    clicked = Signal()

    def __init__(self, x_limits: [float] = None, y_limits: [float] = None, unit: str = 'um'):
        """:param x_limits: list containing max and min values of x dimension
           :param  y_limits: list containing max and min values of y dimension
           :param unit: unit of all size values"""

        super().__init__()
        # TODO: should these be properties? or should we assume they stay constant?

        self._x_limits = x_limits or [float('-inf'), float('inf')]
        self._y_limits = y_limits or [float('-inf'), float('inf')]
        self._x_limits.sort()
        self._y_limits.sort()

        self._grid_position = (0.0, 0.0)

        # customize area widgets
        self.area_width.setRange(0.01, self._x_limits[-1] - self._x_limits[0])
        self.area_width.setSuffix(f" {unit}")
        self.area_height.setRange(0.01, self._y_limits[-1] - self._y_limits[0])
        self.area_height.setSuffix(f" {unit}")

        # customize bound widgets
        self.left.setRange(self._x_limits[0], self._x_limits[-1])
        self.left.setSuffix(f" {unit}")
        self.right.setRange(self._x_limits[0], self._x_limits[-1])
        self.right.setSuffix(f" {unit}")
        self.top.setRange(self._y_limits[0], self._y_limits[-1])
        self.top.setSuffix(f" {unit}")
        self.bottom.setRange(self._y_limits[0], self._y_limits[-1])
        self.bottom.setSuffix(f" {unit}")

    @property
    def fov_dimensions(self):
        return [self.fovWidth(), self.fovHeight()]

    @fov_dimensions.setter
    def fov_dimensions(self, value):
        self.setFovWidth(value[0])
        self.area_width.setSingleStep(value[0])
        self.setFovHeight(value[1])
        self.area_height.setSingleStep(value[1])

    @property
    def grid_position(self):
        return self._grid_position

    @grid_position.setter
    def grid_position(self, value):
        self._grid_position = value
        self._on_change()

    @property
    def tile_positions(self):
        """Returns list of tile positions based on widget values"""

        if self._mode != "bounds":
            return [(pos.x + self._grid_position[0], pos.y + self._grid_position[1])
                    for pos in self.value().iter_grid_positions()]
        else:
            return [(pos.x, pos.y)
                    for pos in self.value().iter_grid_positions()]

    def value(self):
        """Overwriting value so Area mode doesn't multiply width and height by 1000"""
        # FIXME: I don't like overwriting this but I don't know what else to do
        over = self.overlap.value()
        _order = cast("OrderMode", self.order.currentEnum())
        common = {
            "overlap": (over, over),
            "mode": _order.value,
            "fov_width": self._fov_width,
            "fov_height": self._fov_height,
        }
        if self._mode.value == 'number':
            return useq.GridRowsColumns(
                rows=self.rows.value(),
                columns=self.columns.value(),
                relative_to=cast("RelativeTo", self.relative_to.currentEnum()).value,
                **common,
            )
        elif self._mode.value == 'bounds':
            return useq.GridFromEdges(
                top=self.top.value(),
                left=self.left.value(),
                bottom=self.bottom.value(),
                right=self.right.value(),
                **common,
            )
        elif self._mode.value == 'area':
            return useq.GridWidthHeight(
                width=self.area_width.value(),
                height=self.area_height.value(),
                relative_to=cast("RelativeTo", self.relative_to.currentEnum()).value,
                **common,
            )
        raise NotImplementedError

    def mousePressEvent(self, a0) -> None:
        """overwrite to emit a clicked signal"""
        self.clicked.emit()
        super().mousePressEvent(a0)
