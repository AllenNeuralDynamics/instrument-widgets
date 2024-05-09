from qtpy.QtWidgets import QSizePolicy, QTabWidget, QVBoxLayout, QCheckBox, \
    QPushButton, QDoubleSpinBox, QGridLayout, QTableWidget, QButtonGroup, QRadioButton, \
    QHBoxLayout, QLabel, QTableWidgetItem
import numpy as np
from qtpy.QtCore import Signal, Qt

class ChannelPlanWidget(QTabWidget):
    """Widget defining parameters per tile per channel """


    def __init__(self, scan_plan, channels: dict, settings: dict):
        """
        :param scan_plan: ScanPlanWidget associated with scan
        :param channels: dictionary defining channels for instrument
        :param settings: allowed setting for devices
        """

        super().__init__()

        self.steps = {}         # dictionary of number of steps for each tile in each channel
        self.step_size = {}     # dictionary of step size for each tile in each channel

