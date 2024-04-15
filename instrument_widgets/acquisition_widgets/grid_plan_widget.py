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

    fovStop = Signal()

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

        self._fov_position = (0.0, 0.0)
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

        # TODO: Should these go here? Add fov dimension box?
        # Add extra checkboxes and inputs
        self.path = QCheckBox('Show Path')
        self.path.setChecked(True)

        self.anchor = QCheckBox('Anchor Grid:')
        self.anchor.toggled.connect(self.toggle_grid_position)

        pos_layout = QHBoxLayout()
        self.grid_position_widgets = [QDoubleSpinBox(), QDoubleSpinBox()]
        for axis, box in zip(['x', 'y'], self.grid_position_widgets):
            box.setValue(self.grid_position[0])
            limits = getattr(self, f'_{axis}_limits')
            dec = len(str(limits[0])[str(limits[0]).index('.') + 1:]) if '.' in str(limits[0]) else 0
            box.setDecimals(dec)
            box.setRange(*limits)
            box.setSuffix(f" {unit}")

            box.valueChanged.connect(lambda: setattr(self, 'grid_position', (self.grid_position_widgets[0].value(),
                                                                             self.grid_position_widgets[1].value())))
            box.valueChanged.connect(self._on_change)
            box.setDisabled(True)

        self.stop_stage = QPushButton("HALT FOV")
        self.stop_stage.clicked.connect(lambda: self.fovStop.emit())

        pos_layout.addWidget(self.anchor)
        pos_layout.addWidget(self.grid_position_widgets[0])
        pos_layout.addWidget(self.grid_position_widgets[1])

        layout = QVBoxLayout()
        layout.addWidget(self.path)
        layout.addLayout(pos_layout)
        layout.addWidget(self.stop_stage)
        widget = QWidget()
        widget.setLayout(layout)

        self.widget().layout().children()[-1].children()[0].addRow(widget)

    def toggle_grid_position(self, enable):
        """If grid is anchored, allow user to input grid position"""

        self.grid_position_widgets[0].setEnabled(enable)
        self.grid_position_widgets[1].setEnabled(enable)
        self.relative_to.setDisabled(enable)
        if not enable:  # Graph is anchored
            self.grid_position = self.fov_position

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
    def fov_position(self):
        return self._fov_position

    @fov_position.setter
    def fov_position(self, value):
        self._fov_position = value
        if not self.anchor.isChecked():
            self.grid_position_widgets[0].setValue(value[0])
            self.grid_position_widgets[1].setValue(value[1])
        self._on_change()

    @property
    def grid_position(self):
        return self._grid_position

    @grid_position.setter
    def grid_position(self, value):
        self._grid_position = value
        if (float(self.grid_position_widgets[0].value()), float(self.grid_position_widgets[1].value())) != value:
            self.grid_position_widgets[0].setValue(value[0])
            self.grid_position_widgets[1].setValue(value[1])
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