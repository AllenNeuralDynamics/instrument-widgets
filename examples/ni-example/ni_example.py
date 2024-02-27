from voxel.devices.daq.ni import DAQ
from device_widgets.ni_widget import NIWidget
from qtpy.QtWidgets import QApplication
import sys
from qtpy.QtCore import Slot
import os
from pathlib import Path
import threading
from time import sleep
from ruamel.yaml import YAML
from device_widgets.base_device_widget import BaseDeviceWidget

INSTRUMENT_YAML = Path('C:\\Users\\micah.woodard\\Projects\\device-widgets\\examples\\'
                        'resources\\simulated_instrument.yaml')

@Slot(str)
def widget_property_changed(name, device, widget):
    """Slot to signal when widget has been changed
    :param name: name of attribute and widget"""

    name_lst = name.split('.')
    print('widget', name, ' changed to ', getattr(widget, name_lst[0]))
    value = getattr(widget, name_lst[0])
    setattr(device, name_lst[0], value)
    print('Device', name, ' changed to ', getattr(device, name_lst[0]))
    for k, v in widget.property_widgets.items():
        instrument_value = getattr(device, k)
        print(k, instrument_value)
        #setattr(widget, k, instrument_value)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # set up daq
    config = YAML(typ='safe', pure=True).load(INSTRUMENT_YAML)

    daq_tasks = config['instrument']['devices']['daqs']['PCIe-6738']['tasks']
    ao_task = daq_tasks['ao_task']
    do_task = daq_tasks['do_task']
    co_task = daq_tasks['co_task']

    daq_object = DAQ("Dev2")
    daq_object.add_task(ao_task, 'ao')
    daq_object.add_task(do_task, 'do')
    daq_object.add_task(co_task, 'co')
    daq_object.generate_waveforms(ao_task, 'ao', '488')
    daq_object.generate_waveforms(do_task, 'do', '488')
    daq_object.write_ao_waveforms()
    daq_object.write_do_waveforms()
    daq_tasks = NIWidget(daq_object, daq_tasks)
    daq_tasks.show()

    daq_tasks.ValueChangedInside[str].connect(
        lambda value, dev=daq_object, widget=daq_tasks,: widget_property_changed(value, dev, widget))

    sys.exit(app.exec_())

    # sys.exit(app.exec_())