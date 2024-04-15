from pyqtgraph.opengl import GLViewWidget, GLBoxItem, GLLinePlotItem, GLAxisItem
from qtpy.QtWidgets import QSizePolicy, QWidget, QVBoxLayout, QCheckBox, \
    QMessageBox, QTabWidget, QApplication
from qtpy.QtCore import Signal, Qt
from qtpy.QtGui import QColor, QMatrix4x4, QVector3D
import numpy as np
from math import tan, radians, sqrt
import enum
from instrument_widgets.acquisition_widgets.grid_plan_widget import GridPlanWidget
from instrument_widgets.acquisition_widgets.z_plan_widget import ZPlanWidget

class GridWidget:
    """Widget combining GridPlanWidget and GridViewWidget"""

    def __init__(self, limits: {'x_limits': [float('-inf'), float('inf')], 'y_limits': [float('-inf'), float('inf')],
                                'z_limits': [float('-inf'), float('inf')]},
                 coordinate_plane: list[str] = ['x', 'y', 'z'],
                 fov_dimensions: list[float] = [1.0, 1.0],
                 fov_position: list[float] = [0.0, 0.0, 0.0],
                 view_color: str = 'yellow',
                 unit: str = 'um'):
        super().__init__()

        self.limits = limits
        self.unit = unit

        self.grid_plan = GridPlanWidget(limits['x_limits'], limits['y_limits'], unit=unit)
        self.grid_plan.setMaximumHeight(333)
        self.grid_plan.setMaximumWidth(333)
        self.grid_plan.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)
        self.grid_plan.setWindowTitle('X Y Plan')
        self.grid_plan.show()

        self.grid_view = GridViewWidget(coordinate_plane, fov_dimensions, fov_position, view_color)
        self.grid_view.valueChanged.connect(lambda value: setattr(self, value, getattr(self.grid_view, value)))
        self.grid_view.setMinimumHeight(333)
        self.grid_view.setMinimumWidth(333)
        self.grid_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.grid_view.setWindowTitle('Grid View')
        self.grid_view.show()

        self.z_grid_plan = QWidget()
        self.z_plan_tab = QTabWidget()
        self.apply_all = QCheckBox('Apply to All')
        self.apply_all.setChecked(True)
        self.apply_all.toggled.connect(self.toggle_apply_all)
        self.apply_all.toggled.connect(self.grid_coord_construction)

        layout = QVBoxLayout()
        layout.addWidget(self.z_plan_tab)
        layout.addWidget(self.apply_all)
        self.z_grid_plan.setLayout(layout)
        self.z_grid_plan.setWindowTitle('Z Plan')
        self.z_grid_plan.show()

        self.old_tiles = self.grid_plan.value()
        self.grid_plan.valueChanged.connect(self.z_plan_construction)
        self.grid_plan.path.toggled.connect(self.grid_view.toggle_path_visibility)

        # expose attributes from grid_plan and grid_view
        self.fov_position = fov_position
        self.fov_dimensions = fov_dimensions
        self.coordinate_plane = coordinate_plane
        self.planValueChanged = self.grid_plan.valueChanged
        self.viewValueChanged = self.grid_view.valueChanged
        self.fovMoved = self.grid_view.fovMoved
        self.fovStop = self.grid_plan.fovStop

        app = QApplication.instance()
        app.focusChanged.connect(self.toggle_focus)

    def toggle_focus(self):
        """toggle view based on focus of widgets"""

        if self.grid_plan.isActiveWindow():
            self.grid_view.coordinate_plane = ('x', 'y')
            self.grid_view._update_opts()
        elif self.z_grid_plan.isActiveWindow():
            self.grid_view.coordinate_plane = ('x', 'z')
            self.grid_view._update_opts()

    def z_plan_construction(self, value):
        """Create new z_plan widget for each new tile """

        if value != self.old_tiles:
            for i in range(self.z_plan_tab.count() - 1, -1, -1):  # stepping down
                self.z_plan_tab.widget(i).deleteLater()
                self.z_plan_tab.removeTab(i)

            self.z_plan_widgets = []
            for i, tile in enumerate(value.iter_grid_positions()):
                z = ZPlanWidget(self.limits['z_limits'], self.unit)
                self.z_plan_tab.addTab(z, f"({tile.row}, {tile.col})")
                z.valueChanged.connect(self.grid_coord_construction)
            self.old_tiles = value

        self.toggle_apply_all(self.apply_all.checkState())
        if self.z_plan_tab.count() > 0:
            self.grid_coord_construction()

    def grid_coord_construction(self, value=None):
        """Create current list of x,y,z of planned grid"""

        if self.apply_all.checkState():
            z_range = self.z_plan_tab.widget(0).value()
            z = self.z_plan_tab.widget(0).value()[0]
            self.grid_view.grid_coords = [(x, y, z) for x, y in self.grid_plan.tile_positions]
            self.grid_view.tile_dimensions = [abs(z_range[-1] - z_range[0]) for i in
                                              range(len(self.grid_plan.tile_positions))]
        else:
            coords = []
            for i, coord in enumerate(self.grid_plan.tile_positions):
                x, y = coord
                z = self.z_plan_tab.widget(i).value()[0]
                coords.append((x, y, z))
            self.grid_view.grid_coords = coords
            self.grid_view.tile_dimensions = [abs(self.z_plan_tab.widget(i).value()[-1] -
                                                  self.z_plan_tab.widget(i).value()[0]) for i in
                                              range(self.z_plan_tab.count())]

    def toggle_apply_all(self, checked):
        """If apply all is toggled, disable/enable tab widget accordingly and reconstruct gui coords"""

        if checked:  # if checked, set first tab as active
            self.z_plan_tab.setCurrentIndex(0)
        # disable or enable tab based on checked or not
        for i in range(1, self.z_plan_tab.count()):
            self.z_plan_tab.setTabEnabled(i, not checked)

    @property
    def fov_position(self):
        return self._fov_position

    @fov_position.setter
    def fov_position(self, value):
        self._fov_position = value
        if self.grid_view.fov_position != value:
            self.grid_view.fov_position = value
        if self.grid_plan.fov_position != value:
            self.grid_plan.fov_position = value

    @property
    def fov_dimensions(self):
        return self._fov_dimensions

    @fov_dimensions.setter
    def fov_dimensions(self, value):
        self._fov_dimensions = value
        if self.grid_view.fov_dimensions != value:
            self.grid_view.fov_dimensions = value
        if self.grid_plan.fov_dimensions != value:
            self.grid_plan.fov_dimensions = value

    def tile_configuration(self):
        """Provide tile configuration in configuration a voxel acquisition is expecting.
        grid_plan tiles are in order of acquisition"""

        tiles = []
        for tile, specs in zip(self.grid_plan.tile_positions, self.grid_plan.value().iter_grid_positions()):
            tiles.append({
                'tile_number': {self.coordinate_plane[0]: specs.row, self.coordinate_plane[1]: specs.col},
                'position_mm': {axis: coord for axis, coord in zip(self.coordinate_plane[:2], tile)}
            })
        return tiles



# TODO: Use this else where to. Consider moving it so we don't have to copy paste?
class SignalChangeVar:

    def __set_name__(self, owner, name):
        self.name = f"_{name}"

    def __set__(self, instance, value):
        setattr(instance, self.name, value)  # initially setting attr
        instance.valueChanged.emit(self.name[1:])

    def __get__(self, instance, value):
        return getattr(instance, self.name)


class GridViewWidget(GLViewWidget):
    """Widget to display configured acquisition grid"""
    # initialize waveform parameters
    fov_dimensions = SignalChangeVar()
    fov_position = SignalChangeVar()
    grid_coords = SignalChangeVar()
    tile_dimensions = SignalChangeVar()
    valueChanged = Signal((str))
    fovMoved = Signal((list))

    def __init__(self,
                 coordinate_plane: list[str] = ['x', 'y', 'z'],
                 fov_dimensions: list[float] = [1.0, 1.0],
                 fov_position: list[float] = [0.0, 0.0, 0.0],
                 view_color: str = 'yellow'):
        """GLViewWidget to display proposed grid of acquisition
        :param coordinate_plane: coordinate plane displayed on widget.
        Needed to move stage to correct coordinate position?
        :param fov_dimensions: dimensions of field of view in coordinate plane
        :param fov_position: position of fov
        :param view_color: optional color of fov box"""

        super().__init__()

        # TODO: units? Checks?
        self.coordinate_plane = coordinate_plane
        self.fov_dimensions = fov_dimensions
        self.fov_position = fov_position
        self.grid_plane = ['x', 'y']    # plane currently being viewed
        self.tile_dimensions = [0.0]
        self.grid_coords = [(0, 0, 0)]
        self.grid_BoxItems = []
        self.grid_LinePlotItem = GLLinePlotItem()
        self.addItem(self.grid_LinePlotItem)

        self.fov_view = GLBoxItem()
        self.fov_view.setColor(QColor(view_color))
        self.fov_view.setSize(*self.fov_dimensions, 0.0)
        self.fov_view.setTransform(QMatrix4x4(1, 0, 0, self.fov_position[0],
                                              0, 1, 0, self.fov_position[1],
                                              0, 0, 1, self.fov_position[2],
                                              0, 0, 0, 1))
        self.addItem(self.fov_view)

        # Correctly set view of graph
        self.opts['azimuth'] = 270
        self.opts['elevation'] = 90

        self.valueChanged[str].connect(self.update_view)
        self.resized.connect(self._update_opts)

        self.opts['center'] = QVector3D(self.fov_position[0] + self.fov_dimensions[0] / 2,
                                        self.fov_position[1] + self.fov_dimensions[1] / 2,
                                        0)
        y_dist = (self.fov_dimensions[1] * 2) / 2 * tan(radians(self.opts['fov'])) \
                 * (self.size().width() / self.size().height())
        x_dist = (self.fov_dimensions[0] * 2) / 2 * tan(radians(self.opts['fov']))
        self.opts['distance'] = x_dist if x_dist > y_dist else y_dist

        axis = GLAxisItem()
        axis.setSize(50, 50, 50)
        self.addItem(axis)

    def update_view(self, attribute_name):
        """Update attributes of grid
        :param attribute_name: name of attribute to update"""

        if attribute_name == 'fov_dimensions':
            self.fov_view.setSize(*self.fov_dimensions, 0.0)
        elif attribute_name == 'fov_position':
            self.fov_view.setTransform(QMatrix4x4(1, 0, 0, self.fov_position[0],
                                                  0, 1, 0, self.fov_position[1],
                                                  0, 0, 1, 0,
                                                  0, 0, 0, 1))
        elif attribute_name == 'grid_coords' or attribute_name == 'tile_dimensions':
            self.update_grid()

        self._update_opts()

    def update_grid(self):
        """Update displayed grid"""

        for box in self.grid_BoxItems:
            self.removeItem(box)
        self.grid_BoxItems = []
        for coord, tile_dimension in zip(self.grid_coords, self.tile_dimensions):
            x, y, z = coord
            box = GLBoxItem()
            box.setSize(*self.fov_dimensions, tile_dimension)
            box.setTransform(QMatrix4x4(1, 0, 0, x,
                                        0, 1, 0, y,
                                        0, 0, 1, z,
                                        0, 0, 0, 1))
            self.grid_BoxItems.append(box)
            self.addItem(box)
        path_offset = [fov * .5 for fov in self.fov_dimensions]
        path = np.array([*[[x + path_offset[0], y + path_offset[1], z] for x, y, z in self.grid_coords]])
        self.grid_LinePlotItem.setData(pos=path, color=QColor('lime'))

    def toggle_path_visibility(self, visible):
        """Slot for a radio button to toggle visibility of path"""

        if visible:
            self.grid_LinePlotItem.setVisible(True)
        else:
            self.grid_LinePlotItem.setVisible(False)

    def _update_opts(self):
        """Update view of widget. Note that x/y notation refers to horizontal/vertical dimensions of grid view"""

        plane = self.grid_plane
        coords = self.grid_coords
        if plane == ('x', 'y'):
            self.opts['elevation'] = 90
        elif plane == ('x', 'z') or plane == ('y', 'z'):
            self.opts['elevation'] = 0
            # take into account end of tile and account for difference in size
            coords = self.grid_coords + \
                   [(axis[0], axis[1], axis[2]+size) for axis, size in zip(self.grid_coords, self.tile_dimensions)]

        extrema = {'x_min': min([x for x, y, z in coords]), 'x_max': max([x for x, y, z in coords]),
                   'y_min': min([y for x, y, z in coords]), 'y_max': max([y for x, y, z in coords]),
                   'z_min': min([z for x, y, z in coords]), 'z_max': max([z for x, y, z in coords])}

        fov = {**{axis: dim for axis, dim in zip(['x', 'y'], self.fov_dimensions)}, 'z':10}
        pos = {axis: dim for axis, dim in zip(['x', 'y', 'z'], self.fov_position)}
        distances = {'xy': [sqrt((pos[plane[0]] - x) ** 2 + (pos[plane[1]] - y) ** 2) for x, y, z in coords],
                     'xz': [sqrt((pos[plane[0]] - x) ** 2 + (pos[plane[1]] - z) ** 2) for x, y, z in coords],
                     'yz': [sqrt((pos[plane[0]] - y) ** 2 + (pos[plane[1]] - z) ** 2) for x, y, z in coords]}
        max_index = distances[''.join(plane)].index(max(distances[''.join(plane)], key=abs))
        furthest_tile = {'x': coords[max_index][0],
                         'y': coords[max_index][1],
                         'z': coords[max_index][2]}
        center = {}

        # if fov_position is within grid or farthest distance is between grid tiles
        # Horizontal sizing 
        if extrema[f'{plane[0]}_min'] <= pos[plane[0]] <= extrema[f'{plane[0]}_max'] or \
                abs(furthest_tile[plane[0]] - pos[plane[0]]) < abs(extrema[f'{plane[0]}_max'] - extrema[f'{plane[0]}_min']):
            center[plane[0]] = ((extrema[f'{plane[0]}_min'] + extrema[f'{plane[0]}_max']) / 2) + fov[plane[0]] / 2
            horz_dist = ((extrema[f'{plane[0]}_max'] - extrema[f'{plane[0]}_min']) + (fov[plane[0]] * 2)) / 2 * tan(
                radians(self.opts['fov']))

        else:
            center[plane[0]] = ((pos[plane[0]] + furthest_tile[plane[0]]) / 2) + fov[plane[0]] / 2
            horz_dist = (abs(pos[plane[0]] - furthest_tile[plane[0]]) + (fov[plane[0]] * 2)) / 2 * tan(
                radians(self.opts['fov']))
        # Vertical sizing
        if extrema[f'{plane[1]}_min'] <= pos[plane[1]] <= extrema[f'{plane[1]}_max'] or \
                abs(furthest_tile[plane[1]] - pos[plane[1]]) < abs(extrema[f'{plane[1]}_max'] - extrema[f'{plane[1]}_min']):
            center[plane[1]] = ((extrema[f'{plane[1]}_min'] + extrema[f'{plane[1]}_max']) / 2) + fov[plane[1]] / 2
            # View doesn't scale when changing vertical size of widget so for vert_dist we need to take into account the
            # difference between the height and width
            vert_dist = ((extrema[f'{plane[1]}_max'] - extrema[f'{plane[1]}_min']) + (fov[plane[1]] * 2)) / 2 * tan(
                radians(self.opts['fov'])) \
                     * (self.size().width() / self.size().height())

        else:
            center[plane[1]] = ((pos[plane[1]] + furthest_tile[plane[1]]) / 2) + fov[plane[1]] / 2
            vert_dist = (abs(pos[plane[1]] - furthest_tile[plane[1]]) + (fov[plane[1]] * 2)) / 2 * tan(
                radians(self.opts['fov'])) \
                     * (self.size().width() / self.size().height())

        self.opts['distance'] = horz_dist if horz_dist > vert_dist else vert_dist
        self.opts['center'] = QVector3D(
            center.get('x', 0),
            center.get('y', 0),
            center.get('z', 0))

    def move_fov_query(self, new_fov_pos):
        """Message box asking if user wants to move fov position"""
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Question)
        msgBox.setText(f"Do you want to move the field of view from {self.fov_position} to"
                       f"{new_fov_pos}?")
        msgBox.setWindowTitle("Moving FOV")
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

        return msgBox.exec()

    def mousePressEvent(self, event):
        """Override mouseMoveEvent so user can't change view
        and allow user to move fov easier"""

        plane = self.grid_plane
        if event.button() == Qt.LeftButton:
            # Translate mouseclick x, y into view widget coordinate plane.
            horz_dist = self.opts['distance'] / tan(radians(self.opts['fov']))
            vert_dist = self.opts['distance'] / tan(radians(self.opts['fov'])) * (
                    self.size().height() / self.size().width())
            horz_scale = ((event.x() * 2 * horz_dist) / self.size().width())
            vert_scale = ((event.y() * 2 * vert_dist) / self.size().height())

            # create dictionaries of from fov and pos #TODO: should we jsut make them dictionaries in the first place?
            fov = {**{axis: dim for axis, dim in zip(self.coordinate_plane[:2], self.fov_dimensions)}, 'z': 0}
            pos = {axis: dim for axis, dim in zip(self.coordinate_plane, self.fov_position)}


            transform_dict = {grid: stage for grid, stage in zip(['x', 'y', 'z'], self.coordinate_plane)}
            other_dim = [dim for dim in transform_dict if dim not in plane][0]
            transform = [transform_dict[plane[0]], transform_dict[plane[1]], transform_dict[other_dim]]

            new_pos = {transform[0]: (self.opts['center'].x() - horz_dist + horz_scale) - .5 * fov[transform[0]],
                       transform[1]: (self.opts['center'].y() + vert_dist - vert_scale) - .5 * fov[transform[1]],
                       transform[2]: pos[transform[2]]}

            return_value = self.move_fov_query(new_pos)
            if return_value == QMessageBox.Ok:
                self.fov_position = [new_pos['x'], new_pos['y'], new_pos['z']]
                self.fovMoved.emit(new_pos)
            else:
                return

    def mouseMoveEvent(self, event):
        """Override mouseMoveEvent so user can't change view"""
        pass

    def wheelEvent(self, event):
        """Override wheelEvent so user can't change view"""
        pass

    def keyPressEvent(self, event):
        """Override keyPressEvent so user can't change view"""
        pass

    def keyReleaseEvent(self, event):
        """Override keyPressEvent so user can't change view"""
        pass
