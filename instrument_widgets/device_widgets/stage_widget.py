from instrument_widgets.base_device_widget import BaseDeviceWidget
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


class StageWidget(BaseDeviceWidget):

    def __init__(self, stage,
                 advanced_user: bool = True):
        """Modify BaseDeviceWidget to be specifically for Stage. Main need is advanced user.
        :param stage: stage object"""
        self.stage_properties = scan_for_properties(stage) if advanced_user else {'position_mm': stage.position_mm}
        self.stage_module = importlib.import_module(stage.__module__)
        super().__init__(type(stage), self.stage_properties)
