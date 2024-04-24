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
    tileVisibility = Signal(np.ndarray)
    scanVolume = Signal(np.ndarray)
    scanStart = Signal(np.ndarray)

    def __init__(self, z_limits: [float] = None, unit: str = 'um'):

        super().__init__()

        # initialize values
        self.z_limits = z_limits
        self.unit = unit
        self._grid_position = 0.0

        self.z_plan_widgets = np.empty([0], dtype=object)
        self._tile_visibility = np.ones([1], dtype=bool)  # init as True
        self._scan_starts = np.empty([0], dtype=float)
        self._scan_volumes = np.empty([0], dtype=float)

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
            if self.z_plan_widgets[0, 0].start.value() != value:
                for i, j in np.ndindex(self.z_plan_widgets.shape):
                    self.z_plan_widgets[i][j].start.setValue(value)  # change start for tiles
            self._grid_position = value

    @property
    def scan_volumes(self):
        """Return the start position of grid"""
        return self._scan_volumes

    def set_scan_volume(self, value, row, column):
        """create list of scanning volume sizes of all tiles. Tile dimension are arranged in """

        if self.apply_all.isChecked() and (row, column) == (0, 0):
            self._scan_volumes[:, :] = value[-1] - value[0]
            mode = self.z_plan_widgets[0][0].mode()

            if mode.value == 'top_bottom':
                widgets = ['top']
            elif mode.value == 'range_around':
                widgets = ['range']
            else:
                widgets = ['below', 'above']

            for i, j in np.ndindex(self.z_plan_widgets.shape):
                z = self.z_plan_widgets[i][j]
                for name in widgets:  # update necessary widgets with corresponding values
                    getattr(z, name).setValue(getattr(self.z_plan_widgets[0][0], name).value())

        else:
            self._scan_volumes[row, column] = value[-1] - value[0]
        self.scanVolume.emit(self._scan_volumes)

    @property
    def scan_starts(self):
        """Return the start position of grid"""
        return self._scan_starts

    def set_scan_start(self, value, row, column):
        """create list of scanning volume sizes of all tiles. Tile dimension are arranged in """
        if self.apply_all.isChecked() and (row, column) == (0, 0):
            self._scan_starts[:, :] = value
            for i, j in np.ndindex(self.z_plan_widgets.shape):
                z = self.z_plan_widgets[i][j]
                z.start.setValue(value)
            # FIXME: Kinda hacky way to do this? to prevent updating model twice, unhook start to trigger a valueChanged
            #  signal and manually update scan volumes in set_scan_start
            volume_value = self.z_plan_widgets[0][0].value()
            self._scan_volumes[:, :] = volume_value[-1] - volume_value[0]
            self.scanStart.emit(self._scan_starts)

        else:
            self._scan_starts[row, column] = value
            self.scanStart.emit(self._scan_starts)

    @property
    def tile_visibility(self):
        """Return the start position of grid"""
        return self._tile_visibility

    def set_tile_visibility(self, checked, row, column):
        """create list of which tiles are visable"""

        # update tile_visibility and z widgets to new value if apply all and 0, 0
        if self.apply_all.isChecked() and (row, column) == (0, 0):
            self._tile_visibility[:, :] = not checked
            for i, j in np.ndindex(self.z_plan_widgets.shape):
                z = self.z_plan_widgets[i][j]
                z.hide.setChecked(checked)
        else:
            self._tile_visibility[row, column] = not checked

        self.tileVisibility.emit(self._tile_visibility)

    def toggle_apply_all(self, checked):
        """If apply all is toggled, disable/enable tab widget accordingly and reconstruct gui coords.
        Also change visible z plan widget"""

        for row, column in np.ndindex(self.z_plan_widgets.shape):
            z = self.z_plan_widgets[row][column]

            if (row, column) == (0, 0):  # skip (0,0) tile since always enabled and connected
                if checked:
                    self.blockSignals(True)  # block signals to prevent grid updating more than once
                    self.set_scan_volume(z.value(), 0, 0)
                    self.set_scan_start(z.start.value(), 0, 0)
                    self.blockSignals(False)
                    self.set_tile_visibility(z.hide.isChecked(), 0, 0)

            else:
                # if not checked, enable all widgets and connect signals: else, disable all and disconnect signals
                z.blockSignals(checked)
                z.start.blockSignals(checked)
                z.hide.blockSignals(checked)
                z.setEnabled(not checked)
                z.setVisible(not checked)

    def scan_plan_construction(self, value: useq.GridFromEdges | useq.GridRowsColumns | useq.GridWidthHeight):
        """Create new z_plan widget for each new tile """

        if self.z_plan_widgets.shape[0] != value.rows or self.z_plan_widgets.shape[1] != value.columns:
            old_row = self.z_plan_widgets.shape[0]
            old_col = self.z_plan_widgets.shape[1] if old_row != 0 else 0

            # close old row and column widget
            if value.rows - old_row < 0:
                for i in range(value.rows, old_row):
                    for j in range(old_col):
                        self.z_plan_widgets[i][j].close()
            if value.columns - old_col < 0:
                for i in range(old_row):
                    for j in range(value.columns, old_col):
                        self.z_plan_widgets[i][j].close()

            # resize array to new size
            for array, name in zip([self.z_plan_widgets, self.tile_visibility, self.scan_starts, self.scan_volumes],
                                   ['z_plan_widgets', '_tile_visibility', '_scan_starts', '_scan_volumes']):
                setattr(self, name, np.resize(array, (value.rows, value.columns)))
            # update new rows and columns with widgets
            if value.rows - old_row > 0:
                for i in range(old_row, value.rows):
                    for j in range(value.columns):  # take care of any new column values
                        self.create_z_plan_widget(i, j)
            if value.columns - old_col > 0:
                for i in range(old_row):  # if new rows, already taken care of in previous loop
                    for j in range(old_col, value.columns):
                        self.create_z_plan_widget(i, j)

        self.scanChanged.emit()

    def create_z_plan_widget(self, row, column):
        """Function to create and connect ZPlanWidget"""

        z = ZPlanWidget(self.z_limits, self.unit)
        self.z_plan_widgets[row, column] = z
        z.setWindowTitle(f'({row}, {column})')

        # update widget with appropriate values
        z.start.setValue(self._scan_starts[row, column])
        z.hide.setChecked(not self._tile_visibility[row, column])
        z.top.setValue(self._scan_volumes[row, column] + self._scan_starts[row, column])

        # connect signals
        # FIXME: Kinda hacky way to do this? to prevent updating model twice, unhook start to trigger a valueChanged
        #  signal and manually update scan volumes in set_scan_start
        z.start.disconnect()
        z.start.valueChanged.connect(lambda value: self.set_scan_start(value, row, column))
        z.valueChanged.connect(lambda value: self.set_scan_volume(value, row, column))
        z.hide.toggled.connect(lambda checked: self.set_tile_visibility(checked, row, column))

        if self.apply_all.isChecked() and (row, column) != (0, 0):  # block signals from widget
            z.blockSignals(True)
            z.start.blockSignals(True)
            z.hide.blockSignals(True)
            z.setEnabled(False)
            z.setVisible(False)

        z.show()
        return z


class ZPlanWidget(ZPlanWidgetMMCore):
    """Widget to plan out scanning dimension"""

    clicked = Signal()

    def __init__(self, z_limits: [float] = None, unit: str = 'um', parent: QWidget | None = None):
        """:param z_limits: list containing max and min values of z dimension
           :param unit: unit of all size values"""

        self.start = QDoubleSpinBox()

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
