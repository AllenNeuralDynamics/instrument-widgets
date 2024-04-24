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
    volume_model.grid_plane = ('x', 'z')
    scan_plan_widget = ScanPlanWidget()
    tile_plan_widget = TilePlanWidget()
    scan_plan_widget.scan_plan_construction(tile_plan_widget.value())  # initialize first tile

    # hook up tile plan signals
    tile_plan_widget.valueChanged.connect(scan_plan_widget.scan_plan_construction)
    tile_plan_widget.valueChanged.connect(lambda value: volume_model.path.setData(pos=
                                    [[volume_model.grid_coords[pos.row][pos.col][0] + .5*volume_model.fov_dimensions[0] if 'x' in volume_model.grid_plane else 0.,
                                      volume_model.grid_coords[pos.row][pos.col][1] + .5*volume_model.fov_dimensions[1] if 'y' in volume_model.grid_plane else 0.,
                                      volume_model.grid_coords[pos.row][pos.col][2] if 'z' in volume_model.grid_plane else 0.]
                                                                                    for pos in value]))  # update path


    # when changed by z widget, update grid
    scan_plan_widget.tileVisibility.connect(lambda value: setattr(volume_model, 'tile_visibility', value))
    scan_plan_widget.scanVolume.connect(lambda value: setattr(volume_model, 'scan_volumes', value))

    # FIXME: Kinda hacky way to do this? to prevent updating model twice, unhook start to trigger a valueChanged
    #  signal and manually update scan volumes in set_scan_start
    scan_plan_widget.scanStart.connect(lambda: setattr(volume_model, '_scan_volumes', scan_plan_widget.scan_volumes))
    scan_plan_widget.scanStart.connect(lambda value: setattr(volume_model, 'grid_coords',
                                                              np.dstack((tile_plan_widget.tile_positions, value))))

    # bypass triggering update if triggered by scanChanged to only update once
    scan_plan_widget.scanChanged.connect(lambda: setattr(volume_model, '_tile_visibility', scan_plan_widget.tile_visibility))
    scan_plan_widget.scanChanged.connect(lambda: setattr(volume_model, '_scan_volumes', scan_plan_widget.scan_volumes))
    scan_plan_widget.scanChanged.connect(lambda: setattr(volume_model, 'grid_coords',
                                                         np.dstack((tile_plan_widget.tile_positions, scan_plan_widget.scan_starts))))

    sys.exit(app.exec_())