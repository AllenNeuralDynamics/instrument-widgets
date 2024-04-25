from qtpy.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QHBoxLayout, QLabel, QButtonGroup, QRadioButton, QGridLayout
from instrument_widgets.acquisition_widgets.scan_plan_widget import ScanPlanWidget
from instrument_widgets.acquisition_widgets.volume_model import VolumeModel
from instrument_widgets.acquisition_widgets.tile_plan_widget import TilePlanWidget
import numpy as np
import useq


class VolumeWidget(QWidget):
    """Widget to combine scanning, tiling, channel, and model together to ease acquisition setup"""

    def __init__(self,
                 limits=[[float('-inf'), float('inf')], [float('-inf'), float('inf')], [float('-inf'), float('inf')]],
                 coordinate_plane: list[str] = ['x', 'y', 'z'],
                 fov_dimensions: list[float] = [1.0, 1.0, 0],
                 fov_position: list[float] = [0.0, 0.0, 0.0],
                 view_color: str = 'yellow',
                 unit: str = 'um'):
        """
        :param limits: list of limits ordered in [tile_dim[0], tile_dim[1], scan_dim[0]]
        :param coordinate_plane: list describing instrument coordinate plane ordered in [tile_dim[0], tile_dim[1], scan_dim[0]]
        :param fov_dimensions: list of fov_dims which correspond to tiling dimensions
        :param fov_position: list describing fov pos ordered in [tile_dim[0], tile_dim[1], scan_dim[0]]
        :param view_color: color of fov in volume model
        :param unit: unit ALL values will be in
        """
        super().__init__()

        layout = QGridLayout()

        # create model and add extra checkboxes/inputs/buttons to customize volume model
        self.volume_model = VolumeModel(coordinate_plane, fov_dimensions, fov_position, view_color)
        self.fovMoved = self.volume_model.fovMoved  # expose for ease of access
        layout.addWidget(self.volume_model, 0, 1, 1, 2)

        checkboxes = QHBoxLayout()
        path = QCheckBox('Show Path')
        path.setChecked(True)
        path.toggled.connect(self.volume_model.toggle_path_visibility)
        checkboxes.addWidget(path)

        checkboxes.addWidget(QLabel('Plane View: '))
        view_plane = QButtonGroup(self)
        for view in [f'({coordinate_plane[0]}, {coordinate_plane[2]})',
                     f'({coordinate_plane[2]}, {coordinate_plane[1]})',
                     f'({coordinate_plane[0]}, {coordinate_plane[1]})']:
            button = QRadioButton(view)
            button.clicked.connect(lambda clicked, b=button: self.grid_plane_change(b))
            view_plane.addButton(button)
            button.setChecked(True)
            checkboxes.addWidget(button)
        layout.addLayout(checkboxes, 1, 1, 1, 2)

        # create tile plan widgets
        self.tile_plan_widget = TilePlanWidget(limits, fov_dimensions, fov_position, coordinate_plane, unit)
        self.fovStop = self.tile_plan_widget.fovStop  # expose for ease of access
        self.tile_starts = self.tile_plan_widget.grid_position_widgets  # expose for ease of access
        self.anchor_widgets = self.tile_plan_widget.anchor_widgets  # expose for ease of access
        layout.addWidget(self.tile_plan_widget, 0, 0)

        # create scan widgets and initialize first tile
        self.scan_plan_widget = ScanPlanWidget(limits[2], unit)
        self.scan_plan_widget.scan_plan_construction(self.tile_plan_widget.value())
        layout.addWidget(self.scan_plan_widget, 1, 0)

        # hook up tile_plan_widget signals for scan_plan_constructions, volume_model path, and tile start
        self.tile_plan_widget.valueChanged.connect(self.tile_plan_changed)
        self.tile_starts[2].disconnect()  # disconnect to only trigger update graph once
        self.tile_starts[2].valueChanged.connect(lambda value: setattr(self.scan_plan_widget, 'grid_position', value))
        self.anchor_widgets[2].toggled.connect(lambda checked: self.disable_scan_start_widgets(not checked))
        self.disable_scan_start_widgets(True)

        # hook up scan_plan_widget signals to update grid when tiles are changed
        self.scan_plan_widget.tileVisibility.connect(lambda value: setattr(self.volume_model, 'tile_visibility', value))
        self.scan_plan_widget.scanVolume.connect(lambda value: setattr(self.volume_model, 'scan_volumes', value))
        self.scan_plan_widget.scanStart.connect(self.scan_start_changed)

        # When scan changes, scan volume and visibility will also change. To prevent grid unnecessarily updating twice,
        # covertly update model's volumes and visibility and trigger update when setting model's grid coords
        self.scan_plan_widget.scanChanged.connect(self.scan_changed)

        self.limits = limits
        self.coordinate_plane = coordinate_plane
        self.fov_dimensions = fov_dimensions[:2] + [0]  # add 0 if not already included
        self.fov_position = fov_position
        self.unit = unit

        self.setLayout(layout)
        self.show()

    @property
    def fov_position(self):
        return self._fov_position

    @fov_position.setter
    def fov_position(self, value):
        """Update all relevant widgets with new fov_position value"""
        self._fov_position = value

        # update tile plan widget
        for i, anchor in enumerate(self.tile_plan_widget.anchor_widgets):
            if not anchor.isChecked():
                self.tile_starts[i].setValue(value[i])
                # update scan plan widget
                if i == 2:
                    self.scan_plan_widget.grid_position = value[2]
        # update model
        self.volume_model.fov_position = value

    @property
    def fov_dimensions(self):
        return self._fov_dimensions

    @fov_dimensions.setter
    def fov_dimensions(self, value):
        """Update all relevant widgets with new fov_position value"""
        self._fov_dimensions = value

        # update tile plan widget
        self.tile_plan_widget.fov_dimensions = value
        # update volume model
        self.volume_model.fov_dimensions = value

    def tile_plan_changed(self, value: useq.GridFromEdges | useq.GridRowsColumns | useq.GridWidthHeight):
        """When tile plan has been changed, trigger scan plan construction and update volume model path
        :param value: latest tile plan value"""

        self.scan_plan_widget.scan_plan_construction(value)
        self.volume_model.path.setData(pos=
                                       [[self.volume_model.grid_coords[t.row][t.col][i] + .5 * self.fov_dimensions[i]
                                         if self.coordinate_plane[i] in self.volume_model.grid_plane else 0. for i in
                                         range(3)] for t in value])  # update path

    def scan_start_changed(self, value: np.ndarray):
        """When scan start changes, covertly update model's scan volume and trigger change with update grid_coords
        :param value: 2d numpy array of tile starts in the scanning dimension"""

        # When scan start changes, scan volume will also change. To prevent grid unnecessarily updating twice, covertly
        # change volume model scan volumes with updated values and trigger update when setting volume model grid coords
        setattr(self.volume_model, '_scan_volumes', self.scan_plan_widget.scan_volumes)
        setattr(self.volume_model, 'grid_coords', np.dstack((self.tile_plan_widget.tile_positions, value)))

    def scan_changed(self):
        """When tile number or position change, update model's tile visibility, volumes, and grid coordinates"""

        # When scan changes, scan volume and visibility will also change. To prevent grid unnecessarily updating thrice,
        # covertly update model's volumes and visibility and trigger update when setting model's grid coords
        setattr(self.volume_model, '_tile_visibility', self.scan_plan_widget.tile_visibility)
        setattr(self.volume_model, '_scan_volumes', self.scan_plan_widget.scan_volumes)
        setattr(self.volume_model, 'grid_coords', np.dstack((self.tile_plan_widget.tile_positions,
                                                             self.scan_plan_widget.scan_starts)))

        if not self.anchor_widgets[2].isChecked():  # disable start widget for any new widgets
            self.disable_scan_start_widgets(True)

    def grid_plane_change(self, button):
        """Update grid plane and remap path
        :param button: button that was clicked"""

        setattr(self.volume_model, 'grid_plane', tuple(x for x in button.text() if x.isalpha()))
        self.volume_model.path.setData(pos=
                                       [[self.volume_model.grid_coords[t.row][t.col][i] + .5 * self.fov_dimensions[i]
                                         if self.coordinate_plane[i] in self.volume_model.grid_plane else 0. for i in
                                         range(3)] for t in self.tile_plan_widget.value()])  # update path

    def disable_scan_start_widgets(self, disable):
        """Disable all scan start widgets if tile_plan_widget.grid_position_widgets[2] is checked"""

        for i, j in np.ndindex(self.scan_plan_widget.z_plan_widgets.shape):
           self.scan_plan_widget.z_plan_widgets[i][j].start.setDisabled(disable)