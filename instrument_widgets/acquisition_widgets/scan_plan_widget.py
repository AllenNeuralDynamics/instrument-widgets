from pymmcore_widgets import ZPlanWidget as ZPlanWidgetMMCore
from qtpy.QtWidgets import QWidget, QDoubleSpinBox, QLabel, QHBoxLayout, QCheckBox
from qtpy.QtCore import Qt, Signal
from math import ceil
import useq
import enum
import numpy as np
from time import time

class Mode(enum.Enum):
    """Recognized ZPlanWidget modes."""

    TOP_BOTTOM = "top_bottom"
    RANGE_AROUND = "range_around"
    ABOVE_BELOW = "above_below"


class ScanPlanWidget(QWidget):
    """Widget that organizes a matrix of ZPlanWidget"""

    scanChanged = Signal()
    tileVisibility = Signal(list)
    scanVolume = Signal(list)
    def __init__(self, z_limits: [float] = None, unit: str = 'um'):

        super().__init__()

        # initialize values
        self.z_limits = z_limits
        self.unit = unit
        self._grid_position = 0.0

        self.z_plan_widgets = np.empty([0], dtype=object)
        self._tile_visibility = np.empty([0], dtype=object)
        self._scan_starts = np.empty([0], dtype=object)
        self._scan_volumes = np.empty([0], dtype=object)

        checkbox_layout = QHBoxLayout()
        self.apply_all = QCheckBox('Apply to All')
        self.apply_all.setChecked(True)
        self.apply_all.toggled.connect(self.toggle_apply_all)
        # self.apply_all.toggled.connect(self.grid_coord_construction)
        checkbox_layout.addWidget(self.apply_all)
        self.setLayout(checkbox_layout)

        self.show()

    @property
    def grid_position(self):
        """Return the start position of grid"""
        return self._grid_position

    @grid_position.setter
    def grid_position(self, value):
        """Set start position of grid"""
        # TODO: Can't set grid position if apply all isn't checked. Is this the functionality we want?
        if self.apply_all.isChecked():
            if self.z_plan_widgets[0,0].start.value() != value:
                for i in range(self.z_plan_widgets.shape[0]):
                    for j in range(self.z_plan_widgets.shape[1]):
                        self.z_plan_widgets[i, j].start.setValue(value)  # change start for tiles
            self._grid_position = value

    @property
    def scan_volumes(self):
        """Return the start position of grid"""
        return self._scan_volumes

    def set_scan_volume(self, value, row, column):
        """create list of scanning volume sizes of all tiles. Tile dimension are arranged in """

        if self.apply_all.isChecked():
            self._scan_volumes[row, column] = self.z_plan_widgets[0, 0].value()[-1]-self.z_plan_widgets[0, 0].value()[0]

        else:
            self._scan_volumes[row, column] = value[-1] - value[0]
        self.scanVolume.emit(self._scan_volumes)

    @property
    def scan_starts(self):
        """Return the start position of grid"""
        return self._scan_starts

    def set_scan_start(self, value, row, column):
        """create list of scanning volume sizes of all tiles. Tile dimension are arranged in """

        if self.apply_all.isChecked():
            self._scan_starts[row, column] = self.z_plan_widgets[0, 0].value()[0]

        else:
            self._scan_starts[row, column] = value[0]

    @property
    def tile_visibility(self):
        """Return the start position of grid"""
        return self._tile_visibility

    def set_tile_visibility(self, checked, row, column):
        """create list of which tiles are visable"""

        if self.apply_all.isChecked():
            self._tile_visibility[row, column] = self.z_plan_widgets[0, 0].hide.isChecked()

        else:
            self._tile_visibility[row, column] = checked
        self.tileVisibility.emit(self._tile_visibility)

    def toggle_apply_all(self, checked):
        """If apply all is toggled, disable/enable tab widget accordingly and reconstruct gui coords.
        Also change visible z plan widget"""

        for i in range(self.z_plan_widgets.shape[0]):
            for j in range(self.z_plan_widgets.shape[1]):
                self.z_plan_widgets[i, j].setDisabled(checked)
        self.z_plan_widgets[0, 0].setDisabled(False)  # always enabled

    def scan_plan_construction(self, value: useq.GridFromEdges | useq.GridRowsColumns | useq.GridWidthHeight):
        """Create new z_plan widget for each new tile """

        if self.z_plan_widgets.shape[0] != value.rows or self.z_plan_widgets.shape[1] != value.columns:
            old_row = self.z_plan_widgets.shape[0]
            old_col = self.z_plan_widgets.shape[1] if old_row != 0 else 0

            # resize array to new size
            for array, name in zip([self.z_plan_widgets, self.tile_visibility, self.scan_starts, self.scan_volumes],
                                   ['z_plan_widgets', '_tile_visibility', '_scan_starts', '_scan_volumes']):
                setattr(self, name, np.resize(array, (value.rows, value.columns)))

            # update new rows and columns
            row_start = old_row if value.rows - old_row > 0 else 0
            column_start = old_col if value.columns - old_col > 0 else 0

            if value.rows - old_row > 0 or value.columns - old_col > 0:
                for i in range(row_start, value.rows):
                    for j in range(column_start, value.columns):

                        self.create_z_plan_widget(i, j)

        self.scanChanged.emit()

    def create_z_plan_widget(self, row, column):
        """Function to create and connect ZPlanWidget"""

        z = ZPlanWidget(self.z_limits, self.unit)
        self.z_plan_widgets[row, column] = z
        z.setWindowTitle(f'({row}, {column})')
        #z.show()


        # update values with appropriate values
        z_ref = z if not self.apply_all.isChecked() else self.z_plan_widgets[0, 0]
        self._scan_volumes[row, column] = z_ref.value()[-1] - z_ref.value()[0]
        self._scan_starts[row, column] = z_ref.start.value()
        self._tile_visibility[row, column] = not z_ref.hide.isChecked()

        # connect signals
        z.valueChanged.connect(lambda value: self.set_scan_volume(value, row, column))
        z.start.valueChanged.connect(lambda value: self.set_scan_start(value, row, column))
        z.hide.toggled.connect(lambda checked: self.set_tile_visibility(checked, row, column))
        z.valueChanged.connect(self.scanChanged.emit)

        return z


class ZPlanWidget(ZPlanWidgetMMCore):
    """Widget to plan out scanning dimension"""

    clicked = Signal()

    def __init__(self, z_limits: [float] = None, unit: str = 'um', parent: QWidget | None = None):
        """:param z_limits: list containing max and min values of z dimension
           :param unit: unit of all size values"""

        self.start = QDoubleSpinBox()
        self.hidden = False

        super().__init__(parent)

        z_limits = z_limits if z_limits is not None else [float('-inf'), float('inf')]

        for i in range(self._grid_layout.count()):
            widget = self._grid_layout.itemAt(i).widget()

            if type(widget) == QLabel:
                if widget.text() == 'Bottom:':
                    widget.setText('')
                elif widget.text() == 'Top:':
                    widget.setText('End:')
                elif widget.text() == '\u00b5m':
                    widget.setText(unit)

        self._range_readout.hide()
        self._bottom_to_top.hide()
        self._top_to_bottom.hide()
        self.layout().children()[-1].itemAt(2).widget().hide()  # Direction label

        # Add start box
        self.start.valueChanged.connect(self._on_change)
        self.start.setRange(z_limits[0], z_limits[1])
        self._grid_layout.addWidget(QLabel("Start:"), 4, 0, Qt.AlignmentFlag.AlignRight)
        self._grid_layout.addWidget(self.start, 4, 1)

        self.hide = QCheckBox('Hide')
        self.hide.toggled.connect(lambda checked: setattr(self, 'hidden', checked))
        self.hide.toggled.connect(lambda checked: self.valueChanged.emit(self.value()))
        self._grid_layout.addWidget(self.hide, 7, 0)

    def value(self):
        """Overwrite to change how z plan is calculated. Return a list of positions"""

        if self._mode.value == 'top_bottom':
            steps = ceil((self.top.value() - self.start.value()) / self.step.value())
            if steps > 0:
                return [self.start.value() + (self.step.value() * i) for i in range(steps)]
            else:
                return [self.start.value() - (self.step.value() * i) for i in range(abs(steps - 1))]
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

    def mousePressEvent(self, a0) -> None:
        """overwrite to emit a clicked signal"""
        self.clicked.emit()
        super().mousePressEvent(a0)

    def _on_steps_changed(self, steps: int) -> None:
        """Overwrite so if steps increased, z volume is expanded"""

        if self._mode.value == 'top_bottom':
            value = self.step.value() + self.top.value() if steps > len(
                self.value()) else self.top.value() - self.step.value()
            self.top.setValue(value)
        elif self._mode.value == "range_around":
            value = (self.step.value() * steps) - 1
            self.range.blockSignals(True)
            self.range.setValue(value)
            self.range.blockSignals(False)
        elif self._mode.value == "above_below":
            # don't allow changes to be made in this mode?
            value = steps - 1 if steps > len(self.value()) else steps + 1
            self.steps.blockSignals(True)
            self.steps.setValue(value)
            self.steps.blockSignals(False)
