import logging
import time
from .base import BaseStage

class Stage(BaseStage):

    def __init__(self, hardware_axis: str, instrument_axis: str):
        self.log = logging.getLogger(__name__ + "." + self.__class__.__name__)
        self.hardware_axis = hardware_axis.upper()
        self.instrument_axis = instrument_axis.lower()
        self.simulated_position = 0
        self.simulated_speed = 0

    def move_relative(self, position: float, wait: bool = True):
        w_text = "" if wait else "NOT "
        self.log.info(f"relative move by: {self.hardware_axis}={position} mm and {w_text}waiting.")
        move_time_s = position/self.simulated_speed
        self.simulated_position += position
        if wait:
            time.sleep(move_time_s)

    def move_absolute(self, position: float, wait: bool = True):
        w_text = "" if wait else "NOT "
        self.log.info(f"absolute move to: {self.hardware_axis}={position} mm and {w_text}waiting.")
        move_time_s = abs(self.simulated_position - position)/self.simulated_speed
        self.simulated_position = position
        if wait:
            time.sleep(move_time_s)

    def setup_stage_scan(self, fast_axis_start_position: float,
                               slow_axis_start_position: float,
                               slow_axis_stop_position: float,
                               frame_count: int, frame_interval_um: float,
                               strip_count: int, pattern: str,
                               retrace_speed_percent: int):

        self.simulated_position = fast_axis_start_position

    @property
    def position(self):
        return {self.instrument_axis: self.simulated_position}

    @property
    def speed_mm_s(self):
        return self.simulated_speed

    @speed_mm_s.setter
    def speed_mm_s(self, speed_mm_s: float):
        self.simulated_speed = speed_mm_s

    def zero_in_place(self):
        self.simulated_position = 0