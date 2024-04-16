from pymmcore_widgets import ZPlanWidget as ZPlanWidgetMMCore
from qtpy.QtWidgets import QWidget, QDoubleSpinBox, QLabel
from qtpy.QtCore import Qt, Signal
from math import ceil
import useq

class ZPlanWidget(ZPlanWidgetMMCore):
    """Widget to plan out scanning dimension"""

    clicked = Signal()

    def __init__(self, z_limits: [float] = None, unit: str = 'um', parent: QWidget | None = None):
        """:param z_limits: list containing max and min values of z dimension
           :param unit: unit of all size values"""

        self.start = QDoubleSpinBox()
        super().__init__(parent)

        for i in range(self._grid_layout.count()):
            widget = self._grid_layout.itemAt(i).widget()

            if type(widget) == QLabel:
                if widget.text() == 'Bottom:':
                    widget.setText('')
                elif widget.text() == 'Top:':
                    widget.setText('End:')
                elif widget.text() == '\u00b5m':
                    widget.setText(unit)


        # TODO: Hide direction label
        self._bottom_to_top.hide()
        self._top_to_bottom.hide()

        # Add start box
        self.start.valueChanged.connect(self._on_change)
        self.start.setRange(z_limits[0], z_limits[1])
        self._grid_layout.addWidget(QLabel("Start:"), 4, 0, Qt.AlignmentFlag.AlignRight)
        self._grid_layout.addWidget(self.start, 4, 1)

        # self.bottom.disconnect()
        # self.bottom.valueChanged.connect()

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


    # def _on_steps_changed(self, steps: int) -> None:
    #     """Overwrite so if steps increased, z volume is expanded"""
    #     if self._mode.value == 'top_bottom':
    #
    #     elif self._mode.value == "range_around":
    #
    #     elif self._mode == "above_below":
