from device_widgets.base_device_widget import BaseDeviceWidget
from qtpy.QtCore import Qt
import importlib
from device_widgets.miscellaneous_widgets.q_scrollable_float_slider import QScrollableFloatSlider

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

class LaserWidget(BaseDeviceWidget):

    def __init__(self, laser,
                 color: str = 'blue'):  # TODO: Is it okay to pass in device and not use it except to find properties?
        """Modify BaseDeviceWidget to be specifically for laser. Main need is adding slider .
        :param laser: laser object
        :param color: color of laser slider"""
        self.laser_properties = scan_for_properties(laser)
        self.laser_module = importlib.import_module(laser.__module__)
        self.slider_color = color
        super().__init__(type(laser), self.laser_properties)

        self.add_power_slider()

    def add_power_slider(self):
        """Redo power widget to be slider"""

        textbox = self.power_setpoint_mw_widget
        textbox.validator().setRange(0.0, self.max_power_mw, decimals=2)  # Todo: how to handle minimum power?
        textbox.validator().fixup = self.power_slider_fixup
        textbox.editingFinished.connect(lambda: slider.setValue(round(float(textbox.text()))))

        slider = QScrollableFloatSlider(orientation=Qt.Horizontal)
        slider.setStyleSheet("QSlider::groove:horizontal {border: 1px solid #777;height: 10px;border-radius: 4px;}"
                             "QSlider::handle:horizontal {background-color: grey; width: 16px; height: 20px; "
                             "line-height: 20px; margin-top: -5px; margin-bottom: -5px; border-radius: 10px; }"
                             f"QSlider::sub-page:horizontal {{background: {self.slider_color};border: 1px solid #777;"
                             f"height: 10px;border-radius: 4px;}}")

        slider.setMinimum(0)  # Todo: is it always zero?
        slider.setMaximum(int(self.max_power_mw))
        slider.setValue(int(self.power_setpoint_mw))
        slider.sliderMoved.connect(lambda value: textbox.setText(str(value)))
        slider.sliderReleased.connect(lambda: setattr(self, 'power_setpoint_mw', float(slider.value())))
        slider.sliderReleased.connect(lambda: self.ValueChangedInside.emit('power_setpoint_mw'))

        self.power_setpoint_mw_widget_slider = slider
        self.property_widgets['power_setpoint_mw'].layout().addWidget(self.create_widget('H', text=textbox,
                                                                                         slider=slider))

    def power_slider_fixup(self, value):
        """Fix entered values that are larger than max power"""

        self.power_setpoint_mw_widget.setText(str(self.max_power_mw))
        self.power_setpoint_mw_widget.editingFinished.emit()