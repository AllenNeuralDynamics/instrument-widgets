from pymmcore_widgets import ZPlanWidget as ZPlanWidgetMMCore
from qtpy.QtWidgets import QWidget, QDoubleSpinBox, QLabel, QHBoxLayout, QCheckBox, QSizePolicy
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
    tileAdded = Signal(int, int)
    tileRemoved = Signal(int, int)
    tileVisibility = Signal(np.ndarray)
    scanVolume = Signal(np.ndarray)
    scanStart = Signal(np.ndarray)

    def __init__(self, z_limits: [float] = None, unit: str = 'um'):

        super().__init__()

        # initialize values
        self.z_limits = z_limits
        self.unit = unit
        self._grid_position = 0.0

        self.z_plan_widgets = np.empty([0, 1], dtype=object)
        self._tile_visibility = np.ones([1, 1], dtype=bool)  # init as True
        self._scan_starts = np.zeros([0, 1], dtype=float)
        self._scan_volumes = np.zeros([0, 1], dtype=float)

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
        """Set start position of grid for all tiles"""

        # mimic apply all if not checked so  only need to set_scan_start once for (0,0) and other widgets will update
        if not self.apply_all.isChecked():
            # block signals to only trigger graph update once
            self.blockSignals(True)
            self.apply_all.setChecked(True)
            self.blockSignals(False)

            self.z_plan_widgets[0, 0].start.setValue(value)
            self.apply_all.setChecked(False)

        else:
            self.z_plan_widgets[0, 0].start.setValue(value)
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
            widgets = ['step', 'steps']
            if mode.value == 'top_bottom':
                widgets += ['top']
            elif mode.value == 'range_around':
                widgets += ['range']
            else:
                widgets += ['below', 'above']

            for i, j in np.ndindex(self.z_plan_widgets.shape):
                z = self.z_plan_widgets[i][j]
                for name in widgets:  # update necessary widgets with corresponding values
                    getattr(z, name).setValue(getattr(self.z_plan_widgets[0][0], name).value())

        else:
            self._scan_volumes[row, column] = value[-1] - value[0]
        self.scanVolume.emit(self._scan_volumes)

    def update_z_widget(self, z):
        """Update widget with the latest values"""

    @property
    def scan_starts(self):
        """Return the start position of grid"""
        return self._scan_starts

    def set_scan_start(self, widget_value, attr, row, column):
        """create list of scan starts for all tiles. Starts can be set by the start, range, and above input boxes.
         :param widget_value: value from whatever widget was changed
         :param attr: name of input that was changed
         :param row: row of widget changed
         :param column: column of widget changed"""

        z = self.z_plan_widgets[row, column]
        z.blockSignals(True)    # block signal to prevent valueChanged to emit

        value = z.value()
        if self.apply_all.isChecked() and (row, column) == (0, 0):
            self._scan_starts[:, :] = value[0]
            for i, j in np.ndindex(self.z_plan_widgets.shape):
                z = self.z_plan_widgets[i][j]
                getattr(z, attr).setValue(widget_value)
                z.steps.setValue(len(z.value()))

            # covertly update model volume to prevent updating twice
            self._scan_volumes[:, :] = value[-1] - value[0]
            self.scanStart.emit(self._scan_starts)

        else:
            self._scan_starts[row, column] = value
            z.steps.setValue(len(value))
            self._scan_volumes[row, column] = value[-1] - value[0]
            self.scanStart.emit(self._scan_starts)

        z.blockSignals(False)
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
                continue
            else:
                # if not checked, enable all widgets and connect signals: else, disable all and disconnect signals
                self.toggle_signals(z, checked)
                z.setEnabled(not checked)

        if checked:  # if checked, update all widgets with 0, 0 value
            self.blockSignals(True)
            self.set_tile_visibility(self.z_plan_widgets[0][0].hide.isChecked(), 0, 0)
            self.set_scan_start(self.z_plan_widgets[0][0].start.value(), 0, 0)
            self.blockSignals(False)
            self.set_scan_volume(self.z_plan_widgets[0][0].value(), 0, 0)

    def scan_plan_construction(self, value: useq.GridFromEdges | useq.GridRowsColumns | useq.GridWidthHeight):
        """Create new z_plan widget for each new tile """

        if self.z_plan_widgets.shape[0] != value.rows or self.z_plan_widgets.shape[1] != value.columns:
            old_row = self.z_plan_widgets.shape[0]
            old_col = self.z_plan_widgets.shape[1]

            rows = value.rows
            cols = value.columns

            # close old row and column widget
            if rows - old_row < 0:
                for i in range(rows, old_row):
                    for j in range(old_col):
                        self.z_plan_widgets[i][j].close()
                        self.tileRemoved.emit(i, j)
            if cols - old_col < 0:
                for i in range(old_row):
                    for j in range(cols, old_col):
                        self.z_plan_widgets[i][j].close()
                        self.tileRemoved.emit(i, j)

            # resize array to new size
            for array, name in zip([self.z_plan_widgets, self.tile_visibility, self.scan_starts, self.scan_volumes],
                                   ['z_plan_widgets', '_tile_visibility', '_scan_starts', '_scan_volumes']):

                v = array[0, 0] if array.shape != (0,1) else 0  # initialize array with value from first tile
                if rows > old_row:  # add row
                    add_on = [[v] * array.shape[1]] * (rows - old_row)
                    setattr(self, name, np.concatenate((array, add_on), axis=0))
                elif rows < old_row:  # remove row
                    setattr(self, name, np.delete(array, [old_row - x for x in range(1, (old_row - rows) + 1)], axis=0))
                if cols > old_col:  # add column
                    add_on = [[v] * (cols - old_col) for _ in range(array.shape[0])]
                    setattr(self, name, np.concatenate((array, add_on), axis=1))
                elif cols < old_col:  # remove col
                    setattr(self, name, np.delete(array, [old_col - x for x in range(1, (old_col - cols) + 1)], axis=1))

            # update new rows and columns with widgets
            if rows - old_row > 0:
                for i in range(old_row, rows):
                    for j in range(cols):  # take care of any new column values
                        self.create_z_plan_widget(i, j)
            if cols - old_col > 0:
                for i in range(old_row):  # if new rows, already taken care of in previous loop
                    for j in range(old_col, cols):
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
        # FIXME: hacky way to do this? to prevent updating model twice, unhook start, range, and above from valueChanged
        #  signal and manually update scan volumes in set_scan_start
        for name in ['start', 'range', 'above']:
            widget = getattr(z, name)
            widget.disconnect()
            widget.valueChanged.connect(lambda value, attr=name: self.set_scan_start(value, attr, row, column))
        z.valueChanged.connect(lambda value: self.set_scan_volume(value, row, column))
        z.hide.toggled.connect(lambda checked: self.set_tile_visibility(checked, row, column))

        if self.apply_all.isChecked() and (row, column) != (0, 0):  # block signals from widget
            self.toggle_signals(z, True)
            z.setEnabled(False)

        # added label identifying what tile it corresponds to
        z._grid_layout.addWidget(QLabel(f'({row}, {column})'), 7, 1)

        self.tileAdded.emit(row, column)
        # z.show()
        return z

    def toggle_signals(self, z, block):
        """Set signals block or unblocked for start, range, above, and hide
        :param z: z widget to toggle signals from
        :param block: boolean signifying block or unblock"""

        z.blockSignals(block)
        z.steps.blockSignals(block)
        z.start.blockSignals(block)
        z.range.blockSignals(block)
        z.above.blockSignals(block)
        z.hide.blockSignals(block)



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

        #self._range_readout.hide()
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

        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

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
            diff = steps - len(self.value())
            value = (self.step.value() * diff) + self.top.value()
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
        self._on_change(update_steps=False)