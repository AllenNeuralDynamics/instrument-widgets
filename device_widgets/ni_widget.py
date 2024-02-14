from device_widgets.base_device_widget import BaseDeviceWidget
import ruamel.yaml
from qtpy.QtWidgets import QWidget, QLineEdit, QLabel, QComboBox, QHBoxLayout, QVBoxLayout, QMainWindow, QSpinBox

class NIWidget(BaseDeviceWidget):

    def __init__(self, daq_object, tasks):
        """Modify BaseDeviceWidget to be specifically for ni daq. .
        :param tasks: tasks for daq"""

        self.daq = daq_object

        # Split up task type
        self.ao_task = tasks['ao_task']
        self.do_task = tasks['do_task']
        self.co_task = tasks['co_task']
        super().__init__(tasks, tasks)
