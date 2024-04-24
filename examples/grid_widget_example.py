from instrument_widgets.acquisition_widgets.scan_plan_widget import ScanPlanWidget
from instrument_widgets.acquisition_widgets.volume_model import VolumeModel
from instrument_widgets.acquisition_widgets.tile_plan_widget import TilePlanWidget
from qtpy.QtWidgets import QApplication
import sys
from time import time
import numpy as np

if __name__ == "__main__":
    app = QApplication(sys.argv)

    volume_model = VolumeModel()
    volume_model.grid_plane = ('x', 'y')
    scan_plan_widget = ScanPlanWidget()
    tile_plan_widget = TilePlanWidget()
    scan_plan_widget.scan_plan_construction(tile_plan_widget.value())  # initialize first tile

    # todo: update path
    tile_plan_widget.valueChanged.connect(scan_plan_widget.scan_plan_construction)

    # todo: update tile visability
    # todo: grid coords
    scan_plan_widget.scanChanged.connect(lambda: setattr(volume_model, 'tile_visibility', scan_plan_widget.tile_visibility))
    scan_plan_widget.scanChanged.connect(lambda: setattr(volume_model, 'scan_volumes', scan_plan_widget.scan_volumes))

    scan_plan_widget.scanChanged.connect(lambda: setattr(volume_model, 'grid_coords',
                                                         np.dstack((tile_plan_widget.tile_positions, scan_plan_widget.scan_starts))))


    sys.exit(app.exec_())