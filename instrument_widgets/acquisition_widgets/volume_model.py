from pyqtgraph.opengl import GLViewWidget, GLBoxItem, GLLinePlotItem, GLAxisItem
from qtpy.QtWidgets import QMessageBox, QSizePolicy
from qtpy.QtCore import Signal, Qt
from qtpy.QtGui import QColor, QMatrix4x4, QVector3D, QQuaternion
from math import tan, radians, sqrt
from time import time
import numpy as np

# TODO: Use this else where to. Consider moving it so we don't have to copy paste?
class SignalChangeVar:

    def __set_name__(self, owner, name):
        self.name = f"_{name}"

    def __set__(self, instance, value):
        setattr(instance, self.name, value)  # initially setting attr
        instance.valueChanged.emit(self.name[1:])

    def __get__(self, instance, value):
        return getattr(instance, self.name)


class VolumeModel(GLViewWidget):
    """Widget to display configured acquisition grid.  Note that the x and y refer to the tiling
    dimensions and z is the scanning dimension """

    fov_dimensions = SignalChangeVar()
    fov_position = SignalChangeVar()
    grid_coords = SignalChangeVar()
    grid_plane = SignalChangeVar()
    scan_volumes = SignalChangeVar()
    tile_visibility = SignalChangeVar()
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

        super().__init__(rotationMethod='quaternion')

        self.coordinate_plane = coordinate_plane
        self.fov_dimensions = fov_dimensions
        self.fov_position = fov_position
        self.grid_plane = (self.coordinate_plane[0], self.coordinate_plane[1])  # plane currently being viewed

        self.scan_volumes = np.zeros([1, 1])  # 2d list detailing volume of tiles
        self.grid_coords = np.zeros([1, 1, 3])  # 2d list detailing start position of tiles
        self.grid_BoxItems = []   # 2D list detailing boxitems in grid
        self.tile_visibility = np.array([[True]])  # 2d list detailing visibility of tiles

        self.path = GLLinePlotItem(color=QColor('lime'))    # data set externally since tiles are assumed out of order
        self.addItem(self.path)

        self.fov_view = GLBoxItem()
        self.fov_view.setColor(QColor(view_color))
        self.fov_view.setSize(*self.fov_dimensions)
        self.fov_view.setTransform(QMatrix4x4(1, 0, 0, self.fov_position[0],
                                              0, 1, 0, self.fov_position[1],
                                              0, 0, 1, self.fov_position[2],
                                              0, 0, 0, 1))
        self.addItem(self.fov_view)

        self.valueChanged[str].connect(self.update_model)
        self.resized.connect(self._update_opts)

        self._update_opts()

    def update_model(self, attribute_name):
        """Update attributes of grid
        :param attribute_name: name of attribute to update"""

        #print('updating', attribute_name)
        if attribute_name == 'fov_position':
            # update fov_pos
            x = self.fov_position[0] if self.coordinate_plane[0] in self.grid_plane else 0
            y = self.fov_position[1] if self.coordinate_plane[1] in self.grid_plane else 0
            z = self.fov_position[2] if self.coordinate_plane[2] in self.grid_plane else 0
            self.fov_view.setTransform(QMatrix4x4(1, 0, 0, x,
                                                  0, 1, 0, y,
                                                  0, 0, 1, z,
                                                  0, 0, 0, 1))

        else:
            # ignore plane that is not being viewed. TODO: IS this what we want?
            fov_x = self.fov_dimensions[0] if self.coordinate_plane[0] in self.grid_plane else 0
            fov_y = self.fov_dimensions[1] if self.coordinate_plane[1] in self.grid_plane else 0
            self.fov_view.setSize(fov_x, fov_y, 0.0)

            # faster to remove every box than parse which ones have changes
            for box in self.grid_BoxItems:
                self.removeItem(box)
            self.grid_BoxItems = []

            for row in range(len(self.grid_coords)):
                for column in range(len(self.grid_coords[0])):
                    coord = self.grid_coords[row][column]

                    x = coord[0] if self.coordinate_plane[0] in self.grid_plane else 0
                    y = coord[1] if self.coordinate_plane[1] in self.grid_plane else 0
                    z = coord[2] if self.coordinate_plane[2] in self.grid_plane else 0

                    z_size = self.scan_volumes[row, column] if self.coordinate_plane[2] in self.grid_plane else 0
                    box = GLBoxItem()
                    box.setSize(fov_x, fov_y, z_size)
                    box.setTransform(QMatrix4x4(1, 0, 0, x,
                                                0, 1, 0, y,
                                                0, 0, 1, z,
                                                0, 0, 0, 1))
                    box.setColor('white')
                    box.setVisible(self.tile_visibility[row, column])
                    self.grid_BoxItems.append(box)
                    self.addItem(box)
        self._update_opts()

    def toggle_path_visibility(self, visible):
        """Slot for a radio button to toggle visibility of path"""

        if visible:
            self.path.setVisible(True)
        else:
            self.path.setVisible(False)

    def _update_opts(self):
        """Update view of widget. Note that x/y notation refers to horizontal/vertical dimensions of grid view"""

        plane = self.grid_plane
        coords = self.grid_coords.reshape([-1, 3]) # flatten array
        # set rotation
        if plane == (self.coordinate_plane[0], self.coordinate_plane[1]):
            self.opts['rotation'] = QQuaternion(-1, 0, 0, 0)
        else:
            self.opts['rotation'] = QQuaternion(-.7, 0, -.7, 0) if \
                plane == (self.coordinate_plane[2], self.coordinate_plane[1]) else QQuaternion(-.7, .7, 0, 0)
            # take into account end of tile and account for difference in size if z included in view
            dimensions = self.scan_volumes.flatten() # flatten array
            coords = np.concatenate((coords, [[x, y, z + sz] for (x,y,z), sz in zip(coords, dimensions)]))


        extrema = {'x_min': min([x for x, y, z in coords]), 'x_max': max([x for x, y, z in coords]),
                   'y_min': min([y for x, y, z in coords]), 'y_max': max([y for x, y, z in coords]),
                   'z_min': min([z for x, y, z in coords]), 'z_max': max([z for x, y, z in coords])}

        fov = {**{axis: dim for axis, dim in zip(['x', 'y'], self.fov_dimensions)}, 'z': 0}
        pos = {axis: dim for axis, dim in zip(['x', 'y', 'z'], self.fov_position)}
        distances = {'xy': [sqrt((pos[plane[0]] - x) ** 2 + (pos[plane[1]] - y) ** 2) for x, y, z in coords],
                     'xz': [sqrt((pos[plane[0]] - x) ** 2 + (pos[plane[1]] - z) ** 2) for x, y, z in coords],
                     'zy': [sqrt((pos[plane[0]] - z) ** 2 + (pos[plane[1]] - y) ** 2) for x, y, z in coords]}
        max_index = distances[''.join(plane)].index(max(distances[''.join(plane)], key=abs))
        furthest_tile = {'x': coords[max_index][0],
                         'y': coords[max_index][1],
                         'z': coords[max_index][2]}
        center = {}

        # Horizontal sizing, if fov_position is within grid or farthest distance is between grid tiles
        if extrema[f'{plane[0]}_min'] <= pos[plane[0]] <= extrema[f'{plane[0]}_max'] or \
                abs(furthest_tile[plane[0]] - pos[plane[0]]) < abs(
            extrema[f'{plane[0]}_max'] - extrema[f'{plane[0]}_min']):
            center[plane[0]] = ((extrema[f'{plane[0]}_min'] + extrema[f'{plane[0]}_max']) / 2) + fov[plane[0]] / 2
            horz_dist = ((extrema[f'{plane[0]}_max'] - extrema[f'{plane[0]}_min']) + (fov[plane[0]] * 2)) / 2 * tan(
                radians(self.opts['fov']))
        else:
            center[plane[0]] = ((pos[plane[0]] + furthest_tile[plane[0]]) / 2) + fov[plane[0]] / 2
            horz_dist = (abs(pos[plane[0]] - furthest_tile[plane[0]]) + (fov[plane[0]] * 2)) / 2 * tan(
                radians(self.opts['fov']))

        # Vertical sizing, if fov_position is within grid or farthest distance is between grid tiles
        if extrema[f'{plane[1]}_min'] <= pos[plane[1]] <= extrema[f'{plane[1]}_max'] or \
                abs(furthest_tile[plane[1]] - pos[plane[1]]) < abs(
            extrema[f'{plane[1]}_max'] - extrema[f'{plane[1]}_min']):
            center[plane[1]] = ((extrema[f'{plane[1]}_min'] + extrema[f'{plane[1]}_max']) / 2) + fov[plane[1]] / 2
            # View doesn't scale when changing vertical size so take into account the dif between the height and width
            vert_dist = ((extrema[f'{plane[1]}_max'] - extrema[f'{plane[1]}_min']) + (fov[plane[1]] * 2)) / 2 * tan(
                radians(self.opts['fov'])) * (self.size().width() / self.size().height())

        else:
            center[plane[1]] = ((pos[plane[1]] + furthest_tile[plane[1]]) / 2) + fov[plane[1]] / 2
            vert_dist = (abs(pos[plane[1]] - furthest_tile[plane[1]]) + (fov[plane[1]] * 2)) / 2 * tan(
                radians(self.opts['fov'])) * (self.size().width() / self.size().height())

        self.opts['distance'] = horz_dist if horz_dist > vert_dist else vert_dist
        self.opts['center'] = QVector3D(
            center.get('x', 0),
            center.get('y', 0),
            center.get('z', 0))
        self.update()

    def move_fov_query(self, new_fov_pos):
        """Message box asking if user wants to move fov position"""

        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Question)
        msgBox.setText(f"Do you want to move the field of view from {[round(x, 2) for x in self.fov_position]} to"
                       f"{[round(x, 2) for x in new_fov_pos]}?")
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

            # create dictionaries of from fov and pos
            fov = {**{axis: dim for axis, dim in zip(self.coordinate_plane[:2], self.fov_dimensions)}, 'z': 0}
            pos = {axis: dim for axis, dim in zip(self.coordinate_plane, self.fov_position)}

            transform_dict = {grid: stage for grid, stage in zip(['x', 'y', 'z'], self.coordinate_plane)}
            other_dim = [dim for dim in transform_dict if dim not in plane][0]
            transform = [transform_dict[plane[0]], transform_dict[plane[1]], transform_dict[other_dim]]

            center = {'x': self.opts['center'].x(), 'y': self.opts['center'].y(), 'z': self.opts['center'].z()}
            h_ax = self.grid_plane[0]
            v_ax = self.grid_plane[1]

            new_pos = {transform[0]: (center[h_ax] - horz_dist + horz_scale) - .5 * fov[transform[0]],
                       transform[1]: (center[v_ax] + vert_dist - vert_scale) - .5 * fov[transform[1]],
                       transform[2]: pos[transform[2]]}
            return_value = self.move_fov_query([new_pos['x'], new_pos['y'], new_pos['z']])
            if return_value == QMessageBox.Ok:
                self.fov_position = [new_pos['x'], new_pos['y'], new_pos['z']]
                self.grid_plane = plane  # make sure grid plane remains the same
                self.fovMoved.emit([new_pos['x'], new_pos['y'], new_pos['z']])

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
