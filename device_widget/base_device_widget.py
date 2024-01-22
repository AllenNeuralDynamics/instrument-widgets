from qtpy.QtCore import Signal, Slot
from qtpy.QtGui import QValidator, QIntValidator, QDoubleValidator
from qtpy.QtWidgets import QWidget, QLineEdit, QLabel, QComboBox, QHBoxLayout, QVBoxLayout
from inspect import signature, getfullargspec, currentframe, getfile
import os
import importlib
import enum


class BaseDeviceWidget(QWidget):
    ValueChangedOutside = Signal((str,))
    ValueChangedInside = Signal((str,))

    def __init__(self, device_class, device_driver: str, properties: dict):
        """Base widget for devices like camera, laser, stage, ect. Widget will scan properties of
        device object and create editable inputs for each if not in device_widget class of device. If no device_widget
        class is provided, then all properties are exposed
        :param device_class: class of device object
        :param device_driver: string of driver of device
        :param properties: dictionary contain properties displayed in widget as keys and initial values as values"""

        super().__init__()
        self.device_class = device_class
        self.device_driver = importlib.import_module(device_driver)
        self.property_widgets = self.create_property_widgets(properties)

        widget = self.create_widget('V', **self.property_widgets)
        self.setLayout(widget.layout())
        self.show()

        self.ValueChangedOutside[str].connect(self.update_property_widget)  # Trigger update when property value changes

    def create_property_widgets(self, properties: dict):
        """Create input widgets based on properties
         :param properties: dictionary containing properties within a class and mapping to values"""

        widgets = {}
        for name, value in properties.items():
            setattr(self, name, value)  # Add device properties as widget properties
            input_widgets = {'label': QLabel(self.label_maker(name))}
            attr = getattr(self.device_class, name)
            arg_type = type(value)  # getfullargspec(getattr(attr, 'fset')).annotations
            search_name = arg_type.__name__ if arg_type.__name__ in dir(self.device_driver) else name

            # Create combo boxes if there are preset options
            if input_specs := self.check_driver_variables(search_name):
                boxes = {}
                if arg_type == str or type(arg_type) == enum.EnumMeta:
                    boxes[name] = self.create_combo_box(name, input_specs.keys())
                    setattr(self, f"{name}_widget", boxes[name])  # add attribute for widget input for easy access
                    curr_text = value if arg_type == str else value.name
                    boxes[name].setCurrentText(curr_text)
                elif arg_type == dict:
                    for k, v in input_specs.items():
                        label = QLabel(self.label_maker(k))
                        box = self.create_combo_box(name + '.' + k, v.keys())
                        setattr(self, f"{name}.{k}_widget", box)  # add attribute for widget input for easy access
                        box.setCurrentText(value[k])
                        boxes[k] = self.create_widget('V', l=label, q=box)
                input_widgets = {**input_widgets, 'widget': self.create_widget('H', **boxes)}

            # If no found options, create an editable text box
            else:
                input_widgets[name] = self.create_text_box(name, value)
                setattr(self, f"{name}_widget", input_widgets[name]) # add attribute for widget input for easy access

            widgets[name] = self.create_widget(struct='H', **input_widgets)
            widgets[name].setToolTip(attr.__doc__)  # Set tooltip to properties docstring

            if not getattr(attr, 'fset', False):  # Constant, unchangeable attribute
                widgets[name].setDisabled(True)

        return widgets

    def check_driver_variables(self, name: str):
        """Check if there is variable in device driver that has name of
        property to inform input widget type and values
        :param name: name of property to search for"""

        driver_vars = self.device_driver.__dict__
        for variable in driver_vars:
            if name.lower() in variable.lower():  # TODO: plurals that contain ies?
                if type(driver_vars[variable]) == dict:
                    return driver_vars[variable]
                elif type(driver_vars[variable]) == enum.EnumMeta:  # if enum
                    enum_class = getattr(self.device_driver, name)
                    return {i.name: i.value for i in enum_class}

    def create_text_box(self, name, value):
        """Convenience function to build editable text boxes and add initial value and validator
                :param name: name to emit when text is edited is changed
                :param value: initial value to add to box"""

        value_type = type(value)
        textbox = QLineEdit(str(value))
        textbox.editingFinished.connect(lambda: setattr(self, name, value_type(textbox.text())))
        textbox.editingFinished.connect(lambda: self.ValueChangedInside.emit(name))
        arg_type = type(value)
        if arg_type in (float, int):
            validator = QIntValidator() if arg_type == int else QDoubleValidator()
            textbox.setValidator(validator)
        return textbox

    def create_combo_box(self, name, items: list):
        """Convenience function to build combo boxes and add items
        :param name: name to emit when combobox index is changed
        :param items: items to add to combobox"""

        box = QComboBox()
        box.addItems(items)

        name_lst = name.split('.')
        if len(name_lst) == 1:  # name refers to attribute
            box.currentTextChanged.connect(lambda value: setattr(self, name, value))
        else:  # name is a dictionary and key pair split by .
            box.currentTextChanged.connect(lambda value: getattr(self, name_lst[0]).__setitem__(name_lst[1], value))
        # emit signal when changed so outside listener can update. needs to be after changing attribute
        box.currentTextChanged.connect(lambda: self.ValueChangedInside.emit(name))
        return box

    @Slot(str)
    def update_property_widget(self, name):
        """Update property widget. Triggers when attribute has been changed outside of widget
        :param name: name of attribute and widget"""

        value = getattr(self, name)
        if type(value) != dict:     # single widget to set value for
            widget = getattr(self, f'{name}_widget')
            widget.blockSignals(True)   # block signal indicating change
            widget_type = type(widget)
            if widget_type == QLineEdit:
                widget.setText(str(value))
            elif widget_type == QComboBox:
                widget.setCurrentText(str(value))
            widget.blockSignals(False)
        else:
            for k, v in value.items():      # multiple widgets to set values for. Assuming combo box, may change
                widget = getattr(self, f'{name}.{k}_widget')
                widget.blockSignals(True)  # block signal indicating change
                widget.setCurrentText(v)
                widget.blockSignals(False)


    def __setattr__(self, name, value):
        """Overwrite __setattr__ to trigger update if property is changed"""
        self.__dict__[name] = value
        if currentframe().f_back.f_locals.get('self', None) is None:  # call from outside so update widgets
            self.ValueChangedOutside.emit(name)

    def create_widget(self, struct: str, **kwargs):
        """Creates either a horizontal or vertical layout populated with widgets
        :param struct: specifies whether the layout will be horizontal, vertical, or combo
        :param kwargs: all widgets contained in layout"""

        layouts = {'H': QHBoxLayout(), 'V': QVBoxLayout()}
        widget = QWidget()
        if struct == 'V' or struct == 'H':
            layout = layouts[struct]
            for arg in kwargs.values():
                layout.addWidget(arg)

        elif struct == 'VH' or 'HV':
            bin0 = {}
            bin1 = {}
            j = 0
            for v in kwargs.values():
                bin0[str(v)] = v
                j += 1
                if j == 2:
                    j = 0
                    bin1[str(v)] = self.create_widget(struct=struct[0], **bin0)
                    bin0 = {}
            return self.create_widget(struct=struct[1], **bin1)

        layout.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(layout)
        return widget

    def label_maker(self, string):
        """Removes underscores from variable names and capitalizes words
        :param string: string to make label out of
        """

        label = string.split('_')
        label = [words.capitalize() for words in label]
        label = " ".join(label)
        return label
