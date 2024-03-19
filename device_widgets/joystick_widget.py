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


class JoystickWidget(BaseDeviceWidget):

    def __init__(self, joystick,
                 advanced_user: bool = True):
        """Modify BaseDeviceWidget to be specifically for Joystick.
        :param joystic: joystick object"""

        properties = scan_for_properties(joystick) if advanced_user else {'joystick_mapping': joystick.joystick_mapping}
        super().__init__(type(joystick), properties)
        self.stage_axes = joystick.stage_axes
        self.create_axis_combo_box()

    def create_axis_combo_box(self):
        """Transform Instrument Axis text box into combo box and allow selection of only available axes"""

        for joystick_axis, specs in self.joystick_mapping.items():
            unused = list(
                set(self.stage_axes) - set(axis['instrument_axis'] for axis in self.joystick_mapping.values()))
            unused.append(specs['instrument_axis'])
            old_widget = getattr(self, f'joystick_mapping.{joystick_axis}.instrument_axis_widget')
            new_widget = self.create_combo_box(f'joystick_mapping.{joystick_axis}.instrument_axis', unused)
            old_widget.parentWidget().layout().replaceWidget(old_widget, new_widget)
            setattr(self, f'joystick_mapping.{joystick_axis}.instrument_axis_widget', new_widget)
            new_widget.currentTextChanged.connect(self.update_axes_selection)

    def update_axes_selection(self):
        """When joystick axis mapped to new stage axis, update available stage axis"""

        for joystick_axis, specs in self.joystick_mapping.items():
            unused = list(set(self.stage_axes) - set(ax['instrument_axis'] for ax in self.joystick_mapping.values()))
            unused.append(specs['instrument_axis'])
            widget = getattr(self, f'joystick_mapping.{joystick_axis}.instrument_axis_widget')
            # block signals to not trigger currentTextChanged
            widget.blockSignals(True)
            widget.clear()
            widget.addItems(unused)
            widget.setCurrentText(specs['instrument_axis'])
            widget.blockSignals(False)
