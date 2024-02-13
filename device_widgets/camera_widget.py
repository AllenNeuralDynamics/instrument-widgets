from device_widgets.base_device_widget import BaseDeviceWidget
from qtpy.QtGui import QValidator, QIntValidator, QDoubleValidator, QIcon
from qtpy.QtWidgets import QPushButton, QStyle
import sys
import importlib

def scan_for_properties(device):
    """Scan for properties with setters and getters in class and return dictionary
    :param device: object to scan through for properties
    """

    prop_dict = {}
    for attr_name in dir(device):
        attr = getattr(type(device), attr_name, None)
        if isinstance(attr, property) and getattr(device, attr_name) != None:
            prop_dict[attr_name] = getattr(device, attr_name)

    return prop_dict


class CameraWidget(BaseDeviceWidget):

    def __init__(self, camera):     # TODO: Is it okay to pass in device and not use it except to find properties?
        """Modify BaseDeviceWidget to be specifically for camera. Main need are adding roi validator,
        live view button, and snapshot button.
        :param camera: camera object"""
        self.camera_properties = scan_for_properties(camera)
        self.camera_module = importlib.import_module(camera.__module__)
        super().__init__(type(camera), self.camera_properties)

        self.add_roi_validator()
        self.add_live_button()
        self.add_snapshot_button()


    def add_live_button(self):
        """Add live button"""

        button = QPushButton('Live')
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        button.setIcon(icon)
        widget = self.centralWidget()
        self.setCentralWidget(self.create_widget('V', live=button, widget=widget))
        setattr(self, 'live_button', button)

    def add_snapshot_button(self):
        """Add snapshot button"""

        button = QPushButton('Snapshot')
        # icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        # button.setIcon(icon)
        widget = self.centralWidget()
        self.setCentralWidget(self.create_widget('V', live=button, widget=widget))
        setattr(self, 'snapshot_button', button)

    def add_roi_validator(self):
        """Add checks on inputs to roi widgets"""
        if 'roi' in self.camera_properties.keys():
            for k in self.camera_properties['roi'].keys():
                getattr(self, f'roi.{k}_widget').disconnect()  # Disconnect all calls
                getattr(self, f'roi.{k}_widget').editingFinished.connect(lambda key=k: self.roi_validator(key))

    def roi_validator(self, k):
        """Check if input value adheres to max, min, divisor variables in module"""
        module_dict = self.camera_module.__dict__
        widget = getattr(self, f'roi.{k}_widget')
        value = int(widget.text())
        KEY = k.upper()
        specs = {'min': module_dict.get(f'MIN_{KEY}', 0),
                 'max': module_dict.get(f'MAX_{KEY}', value),
                 'divisor' : module_dict.get(f'DIVISIBLE_{KEY}', 1)}
        widget.blockSignals(True)
        if value < specs['min']:
            value = specs['min']
        elif value > specs['max']:
            value = specs['max']
        elif value%specs['divisor'] != 0:
            value = round(value/specs['divisor'])*specs['divisor']
        getattr(self, 'roi').__setitem__(k, value)
        widget.setText(str(value))
        self.ValueChangedInside.emit(f'roi.{k}')
        widget.blockSignals(False)



