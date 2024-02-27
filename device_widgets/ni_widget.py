from device_widgets.base_device_widget import BaseDeviceWidget
from qtpy.QtWidgets import QTreeWidget, QTreeWidgetItem
from qtpy.QtCore import Qt
from device_widgets.miscellaneous_widgets.q_scrollable_float_slider import QScrollableFloatSlider


class NIWidget(BaseDeviceWidget):

    def __init__(self, daq, tasks):
        """Modify BaseDeviceWidget to be specifically for ni daq.
        :param tasks: tasks for daq"""

        # initialize base widget to create convenient widgets and signals
        super().__init__(daq, tasks)
        # available channels    #TODO: this seems pretty hard coded?  A way to avoid this?
        self.ao_physical_chans = [x.replace(f'{daq.id}/', '') for x in daq.ao_physical_chans]
        self.co_physical_chans = [x.replace(f'{daq.id}/', '') for x in daq.co_physical_chans]
        self.do_physical_chans = [x.replace(f'{daq.id}/', '') for x in daq.do_physical_chans]
        self.dio_ports = [x.replace(f'{daq.id}/', '') for x in daq.dio_ports]

        # create tree widget
        self.tree = QTreeWidget()
        # format configured widgets into tree
        for tasks, widgets in self.property_widgets.items():
            header = QTreeWidgetItem(self.tree, [self.label_maker(tasks)])
            self.create_tree_widget(tasks, header)

        self.setCentralWidget(self.tree)
        self.tree.setHeaderLabels(['Tasks', 'Values'])
        self.tree.setColumnCount(2)
        #self.tree.expandAll()

    def remodel_timing_widgets(self, name, widget):
        """Remodel timing widget with driver options"""
        path = name.split('.')
        if options := self.check_driver_variables(path[-1]):
            widget = self.create_attribute_widget(name, 'combo', options)

        elif path[-1] == 'trigger_port':
            widget = self.create_attribute_widget(name, 'combo', self.dio_ports)

        return widget

    def remodel_port_widgets(self, name, widget):
        """Remodel port widgets with possible ports and waveforms"""
        path = name.split('.')
        task = path[0][:2]

        if path[-1] == 'port':
            options = getattr(self, f'{task}_physical_chans')
            widget = self.create_attribute_widget(name, 'combo', options)

        elif path[-1] == 'waveform':
            options = self.check_driver_variables(f'{task}_waveforms')
            widget = self.create_attribute_widget(name, 'combo', options)

        return widget

    def create_sliders(self, name):
        """Create slide bars for channel widgets"""

        textbox = getattr(self, f'{name}_widget')
        slider = QScrollableFloatSlider(orientation=Qt.Horizontal)
        print(name, textbox)
        if 'time' in name:
            maximum = getattr(self, 'ao_task.timing.period_time_ms')
            slider.setMaximum(maximum)
            textbox.validator().setRange(0.0, maximum, decimals=0)
        elif 'volt' in name:
            path = name.split('.')
            slider.divisor = 1000
            maximum = getattr(self, f'{".".join(path[0:3])}.device_max_volts')
            slider.setMaximum(maximum)
            textbox.validator().setRange(0.0, maximum, decimals=3)

        slider.setMinimum(0)  # Todo: is it always zero?
        slider.setValue(getattr(self, f'{name}'))

        textbox.validator().fixup = lambda value=None: self.textbox_fixup(value, name)
        textbox.editingFinished.connect(lambda: slider.setValue(float(textbox.text())))

        slider.sliderMoved.connect(lambda value: textbox.setText(str(value)))
        slider.sliderMoved.connect(lambda: self.ValueChangedInside.emit(name))
        slider.sliderMoved.connect(lambda: setattr(self, name, float(slider.value())))

        setattr(self, f'{name}_slider', slider)

    def create_tree_widget(self, name, parent=None):
        """Recursive function to format nested dictionary of ni task items"""

        parent = self.tree if parent is None else parent
        print(name)
        dictionary = self.pathGet(self.__dict__, name.split('.'))
        items = []
        for key, value in dictionary.items():
            id = f'{name}.{key}'
            if widget := getattr(self, f'{id}_widget', False):
                item = QTreeWidgetItem(parent, [key])
                if 'channel' in name:
                    self.create_sliders(id)
                    widget = self.create_widget('H', t=getattr(self, f'{id}_widget'), s=getattr(self, f'{id}_slider'))
                elif 'timing' in name:
                    widget = self.remodel_timing_widgets(id, widget)
                elif 'ports' in name and key in ['port', 'waveform']:
                    widget = self.remodel_port_widgets(id, widget)
                self.tree.setItemWidget(item, 1, widget)
            else:
                item = QTreeWidgetItem(parent, [key])
                children = self.create_tree_widget(f'{name}.{key}', item)
                item.addChildren(children)
            items.append(item)
        return items

    def textbox_fixup(self, value, name):
        """Fix entered values that are larger than maximum"""
        textbox = getattr(self, f'{name}_widget')
        slider = getattr(self, f'{name}_slider')
        maximum = slider.maximum()
        textbox.setText(str(maximum))
        textbox.editingFinished.emit()
