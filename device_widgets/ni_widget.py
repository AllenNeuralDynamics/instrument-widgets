from device_widgets.base_device_widget import BaseDeviceWidget
from qtpy.QtWidgets import QTreeWidget, QTreeWidgetItem
from qtpy.QtCore import Qt
from device_widgets.miscellaneous_widgets.q_scrollable_float_slider import QScrollableFloatSlider
from device_widgets.waveform_widget import WaveformWidget
import numpy as np
from scipy import signal
from qtpy.QtCore import Slot


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

        # create waveform widget
        self.waveform_widget = WaveformWidget()

        # create tree widget
        self.tree = QTreeWidget()
        # format configured widgets into tree
        for tasks, widgets in self.property_widgets.items():
            header = QTreeWidgetItem(self.tree, [self.label_maker(tasks)])
            self.create_tree_widget(tasks, header)

        self.tree.setHeaderLabels(['Tasks', 'Values'])
        self.tree.setColumnCount(2)

        # Set up waveform widget
        graph_parent = QTreeWidgetItem(self.tree, ['Graph'])
        graph_child = QTreeWidgetItem(graph_parent)
        self.tree.setItemWidget(graph_child, 1, self.waveform_widget)
        graph_parent.addChild(graph_child)

        self.setCentralWidget(self.tree)
        # self.tree.expandAll()

    def update_waveform(self, name):
        """Add waveforms to waveform widget"""

        name_lst = name.split('.')
        task_type = name_lst[0]
        port_name = '.'.join(name_lst[:name_lst.index("ports") + 2])
        wl = name_lst[-1]
        if not getattr(self, f'{port_name}.{wl}_plot_item', False):
            waveform = getattr(self, f'{port_name}.waveform')
            kwargs = {
                'sampling_frequency_hz': getattr(self, f'{task_type}.timing.sampling_frequency_hz'),
                'period_time_ms': getattr(self, f'{task_type}.timing.period_time_ms'),
                'start_time_ms': getattr(self, f'{port_name}.parameters.start_time_ms.channels.{wl}'),
                'end_time_ms': getattr(self, f'{port_name}.parameters.end_time_ms.channels.{wl}'),
                'rest_time_ms': getattr(self, f'{task_type}.timing.rest_time_ms')
            }

            if waveform == 'square wave':
                kwargs['max_volts'] = getattr(self, f'{port_name}.parameters.max_volts.channels.{wl}', 5)
                kwargs['min_volts'] = getattr(self, f'{port_name}.parameters.min_volts.channels.{wl}', 0)
                voltages = square_wave(**kwargs)
                maximum_points = np.where(voltages == (kwargs['max_volts']))[0]
                y = [kwargs['min_volts'], kwargs['min_volts'], voltages[maximum_points[0]], voltages[maximum_points[-1]],
                     kwargs['min_volts'], kwargs['min_volts']]
                x = [0, maximum_points[0] - 1, maximum_points[0], maximum_points[-1], maximum_points[-1] + 1, len(voltages)]
            else:
                kwargs['amplitude_volts'] = getattr(self, f'{port_name}.parameters.amplitude_volts.channels.{wl}')
                kwargs['offset_volts'] = getattr(self, f'{port_name}.parameters.offset_volts.channels.{wl}')
                kwargs['cutoff_frequency_hz'] = getattr(self, f'{port_name}.parameters.cutoff_frequency_hz.channels.{wl}')
                if waveform == 'sawtooth':
                    voltages = sawtooth(**kwargs)
                else:
                    voltages = triangle_wave(**kwargs)

                max_point = np.argmax(voltages)
                min_value = kwargs['offset_volts']-kwargs['amplitude_volts']
                pre_rise_point = np.where(voltages[:max_point] == min_value)[0][-1]
                post_rise_point = np.where(voltages[max_point:] == min_value)[0][0] + max_point
                y = [voltages[0], voltages[pre_rise_point], voltages[max_point], voltages[post_rise_point], voltages[-1]]
                x = [0, pre_rise_point, max_point, post_rise_point, len(voltages)]
                # y = voltages
                # x = np.linspace(0, len(voltages), len(voltages))

            item = self.waveform_widget.plot(pos=np.column_stack((x, y)),
                                             waveform=waveform,
                                             parameters= getattr(self, f'{port_name}.parameters').keys()
                                             )
            item.valueChanged[str, float].connect(lambda var, val: self.waveform_value_changed(
                f'{port_name}.parameters.{var}.channels.{wl}',val))
            setattr(self, f'{port_name}.{wl}_plot_item', item)

    @Slot(str, float)
    def waveform_value_changed(self, name, value):
        """Update textbox if waveform is changed"""
        textbox = getattr(self, f'{name}_widget')
        decimals = 0 if 'time' in name else 3
        textbox.setText(str(round(value, decimals)))
        textbox.editingFinished.emit()

    def remodel_timing_widgets(self, name, widget):
        """Remodel timing widget with driver options"""
        path = name.split('.')
        if options := self.check_driver_variables(path[-1]):
            widget = self.create_attribute_widget(name, 'combo', options)

        elif path[-1] in ['trigger_port', 'output_port']:
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
            widget.setDisabled(True)  # can't change waveform for now. Maybe implemented later on if useful

        return widget

    def create_sliders(self, name):
        """Create slide bars for channel widgets"""

        textbox = getattr(self, f'{name}_widget')
        slider = QScrollableFloatSlider(orientation=Qt.Horizontal)
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
        textbox.editingFinished.connect(lambda: self.update_waveform(name))

        slider.sliderMoved.connect(lambda value: textbox.setText(str(value)))
        slider.sliderMoved.connect(lambda: self.ValueChangedInside.emit(name))
        slider.sliderMoved.connect(lambda: setattr(self, name, float(slider.value())))
        slider.sliderMoved.connect(lambda: self.update_waveform(name))

        setattr(self, f'{name}_slider', slider)

    def create_tree_widget(self, name, parent=None):
        """Recursive function to format nested dictionary of ni task items"""

        parent = self.tree if parent is None else parent
        dictionary = self.pathGet(self.__dict__, name.split('.'))
        items = []
        for key, value in dictionary.items():
            id = f'{name}.{key}'
            if widget := getattr(self, f'{id}_widget', False):
                item = QTreeWidgetItem(parent, [key])
                if 'channel' in name:
                    self.update_waveform(id)
                    self.create_sliders(id)
                    widget = self.create_widget('H', t=getattr(self, f'{id}_widget'), s=getattr(self, f'{id}_slider'))
                elif 'timing' in name:
                    widget = self.remodel_timing_widgets(id, widget)
                elif key in ['port', 'waveform']:
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


def sawtooth(sampling_frequency_hz: float,
             period_time_ms: float,
             start_time_ms: float,
             end_time_ms: float,
             rest_time_ms: float,
             amplitude_volts: float,
             offset_volts: float,
             cutoff_frequency_hz: float
             ):
    time_samples_ms = np.linspace(0, 2 * np.pi,
                                  int(((period_time_ms - start_time_ms) / 1000) * sampling_frequency_hz))
    waveform = offset_volts + amplitude_volts * signal.sawtooth(t=time_samples_ms,
                                                                width=end_time_ms / period_time_ms)
    # add in delay
    delay_samples = int((start_time_ms / 1000) * sampling_frequency_hz)
    waveform = np.pad(array=waveform,
                      pad_width=(delay_samples, 0),
                      mode='constant',
                      constant_values=(offset_volts - amplitude_volts)
                      )

    # add in rest
    rest_samples = int((rest_time_ms / 1000) * sampling_frequency_hz)
    waveform = np.pad(array=waveform,
                      pad_width=(0, rest_samples),
                      mode='constant',
                      constant_values=(offset_volts - amplitude_volts)
                      )
    return waveform


def square_wave(sampling_frequency_hz: float,
                period_time_ms: float,
                start_time_ms: float,
                end_time_ms: float,
                rest_time_ms: float,
                max_volts: float,
                min_volts: float
                ):
    time_samples = int(((period_time_ms + rest_time_ms) / 1000) * sampling_frequency_hz)
    start_sample = int((start_time_ms / 1000) * sampling_frequency_hz)
    end_sample = int((end_time_ms / 1000) * sampling_frequency_hz)
    waveform = np.zeros(time_samples) + min_volts
    waveform[start_sample:end_sample] = max_volts

    return waveform


def triangle_wave(sampling_frequency_hz: float,
                  period_time_ms: float,
                  start_time_ms: float,
                  end_time_ms: float,
                  rest_time_ms: float,
                  amplitude_volts: float,
                  offset_volts: float,
                  cutoff_frequency_hz: float
                  ):
    # sawtooth with end time in center of waveform
    waveform = sawtooth(sampling_frequency_hz,
                        period_time_ms,
                        start_time_ms,
                        (period_time_ms - start_time_ms) / 2,
                        rest_time_ms,
                        amplitude_volts,
                        offset_volts,
                        cutoff_frequency_hz
                        )

    return waveform
