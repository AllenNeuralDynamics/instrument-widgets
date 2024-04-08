from pyqtgraph.opengl import GLViewWidget, GLBoxItem, GLLinePlotItem, GLScatterPlotItem
from pymmcore_widgets import GridPlanWidget as GridPlanWidgetMMCore
from qtpy.QtWidgets import QMainWindow, QHBoxLayout, QWidget, QVBoxLayout, QCheckBox, QDoubleSpinBox, \
    QMessageBox, QScrollBar
from qtpy.QtCore import Signal, Qt
from qtpy.QtGui import QColor, QMatrix4x4, QVector3D
import numpy as np
from math import tan, radians, sqrt
from instrument_widgets.miscellaneous_widgets.q_scrollable_line_edit import QScrollableLineEdit


class GridWidget(QMainWindow):
    """Widget combining GridPlanWidget and GridViewWidget"""

    def __init__(self, limits: {'x': [float('-inf'), float('inf')], 'y': [float('-inf'), float('inf')]},
                 coordinate_plane: list[str] = ['x', 'y'],
                 fov_dimensions: list[float] = [1.0, 1.0],
                 fov_position: list[float] = [0.0, 0.0],
                 view_color: str = 'yellow',
                 unit: str = 'um'):
        super().__init__()

        self.grid_plan = GridPlanWidget(*limits.values(), unit)
        self.grid_plan.valueChanged.connect(lambda value: setattr(self.grid_view, 'grid_coords',
                                                                  self.grid_plan.tile_positions))

        self.grid_plan.setFixedWidth(self.grid_plan.sizeHint().width() + 30)  # Will take up whole widget if not set
        self.grid_plan.setMinimumHeight(303)

        self.grid_view = GridViewWidget(coordinate_plane, fov_dimensions, fov_position, view_color)
        self.grid_view.setMinimumWidth(303)
        self.grid_view.valueChanged.connect(lambda value: setattr(self, value, getattr(self.grid_view, value)))
        self.grid_plan.path.toggled.connect(self.grid_view.toggle_path_visibility)

        self.fov_position = fov_position
        self.fov_dimensions = fov_dimensions
        self.coordinate_plane = coordinate_plane
        self.planValueChanged = self.grid_plan.valueChanged
        self.viewValueChanged = self.grid_view.valueChanged
        self.fovMoved = self.grid_view.fovMoved

        layout = QHBoxLayout()
        layout.addWidget(self.grid_plan)
        layout.addWidget(self.grid_view)
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)


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


class GridPlanWidget(GridPlanWidgetMMCore):
    """Widget to plan out grid. Pymmcore already has a great one"""

    def __init__(self, x_limits: [float] = None, y_limits: [float] = None, unit: str = 'um'):
        super().__init__()
        # TODO: should these be properties? or should we assume they stay constant?

        self._x_limits = x_limits or [float('-inf'), float('inf')]
        self._y_limits = y_limits or [float('-inf'), float('inf')]
        self._x_limits.sort()
        self._y_limits.sort()

        self._fov_position = (0.0, 0.0)
        self._grid_position = (0.0, 0.0)

        # customize area widgets
        self.area_width.setRange(0.01, self._x_limits[-1] - self._x_limits[0])
        self.area_width.setSuffix(f" {unit}")
        self.area_height.setRange(0.01, self._y_limits[-1] - self._y_limits[0])
        self.area_height.setSuffix(f" {unit}")

        # customize bound widgets
        self.left.setRange(self._x_limits[0], self._x_limits[-1])
        self.left.setSuffix(f" {unit}")
        self.right.setRange(self._x_limits[0], self._x_limits[-1])
        self.right.setSuffix(f" {unit}")
        self.top.setRange(self._y_limits[0], self._y_limits[-1])
        self.top.setSuffix(f" {unit}")
        self.bottom.setRange(self._y_limits[0], self._y_limits[-1])
        self.bottom.setSuffix(f" {unit}")

        # TODO: Should these go here? Add fov dimension box?
        # Add extra checkboxes and inputs
        self.path = QCheckBox('Show Path')
        self.path.setChecked(True)

        self.anchor = QCheckBox('Anchor Grid:')
        self.anchor.toggled.connect(self.toggle_grid_position)

        pos_layout = QHBoxLayout()
        self.grid_position_widgets = [QDoubleSpinBox(), QDoubleSpinBox()]
        for axis, box in zip(['x', 'y'], self.grid_position_widgets):
            box.setValue(self.grid_position[0])
            box.setRange(*getattr(self, f'_{axis}_limits'))
            box.setSuffix(f" {unit}")

            box.valueChanged.connect(lambda: setattr(self, 'grid_position', (self.grid_position_widgets[0].value(),
                                                                             self.grid_position_widgets[1].value())))
            box.valueChanged.connect(self._on_change)
            box.setDisabled(True)

        pos_layout.addWidget(self.anchor)
        pos_layout.addWidget(self.grid_position_widgets[0])
        pos_layout.addWidget(self.grid_position_widgets[1])

        layout = QVBoxLayout()
        layout.addWidget(self.path)
        layout.addLayout(pos_layout)
        widget = QWidget()
        widget.setLayout(layout)

        self.widget().layout().children()[-1].children()[0].addRow(widget)

    def toggle_grid_position(self, enable):
        """If grid is anchored, allow user to input grid position"""

        self.grid_position_widgets[0].setEnabled(enable)
        self.grid_position_widgets[1].setEnabled(enable)
        self.relative_to.setDisabled(enable)
        if not enable:  # Graph is anchored
            self.grid_position = self.fov_position

    @property
    def fov_dimensions(self):
        return (self.fovWidth(), self.fovHeight())

    @fov_dimensions.setter
    def fov_dimensions(self, value):
        self.setFovWidth(value[0])
        self.setFovHeight(value[1])

    @property
    def fov_position(self):
        return self._fov_position

    @fov_position.setter
    def fov_position(self, value):

        self._fov_position = value
        if not self.anchor.isChecked():
            self.grid_position_widgets[0].setValue(value[0])
            self.grid_position_widgets[1].setValue(value[1])
        self._on_change()

    @property
    def grid_position(self):
        return self._grid_position

    @grid_position.setter
    def grid_position(self, value):
        self._grid_position = value
        if (float(self.grid_position_widgets[0].value()), float(self.grid_position_widgets[1].value())) != value:
            self.grid_position_widgets[0].setValue(value[0])
            self.grid_position_widgets[1].setValue(value[1])
            self._on_change()

    @property
    def tile_positions(self):
        """Returns list of tile positions based on widget values"""

        if self._mode != "bounds":
            return [(pos.x + self._grid_position[0], pos.y + self._grid_position[1])
                    for pos in self.value().iter_grid_positions()]
        else:
            return [(pos.x, pos.y)
                    for pos in self.value().iter_grid_positions()]


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
    valueChanged = Signal((str))
    fovMoved = Signal((list))

    def __init__(self,
                 coordinate_plane: list[str] = ['x', 'y'],
                 fov_dimensions: list[float] = [1.0, 1.0],
                 fov_position: list[float] = [0.0, 0.0],
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
        self.grid_coords = [(0, 0)]
        self.grid_BoxItems = []
        self.grid_LinePlotItem = GLLinePlotItem()
        self.addItem(self.grid_LinePlotItem)

        self.fov_view = GLBoxItem()
        self.fov_view.setColor(QColor(view_color))
        self.fov_view.setSize(*self.fov_dimensions, 0.0)
        self.fov_view.setTransform(QMatrix4x4(1, 0, 0, self.fov_position[0],
                                              0, 1, 0, self.fov_position[1],
                                              0, 0, 1, 0,
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

        point = GLScatterPlotItem(pos=(53.0, 39.5, 0),
                                  size=50)
        point.setData(pos=(53.0, 39.5, 0), size=50, pxMode=False)
        self.addItem(point)

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
        elif attribute_name == 'grid_coords':
            self.update_grid()

        self._update_opts()

    def update_grid(self):
        """Update displayed grid"""

        for box in self.grid_BoxItems:
            self.removeItem(box)
        self.grid_BoxItems = []

        for x, y in self.grid_coords:
            box = GLBoxItem()
            box.setSize(*self.fov_dimensions, 0.0)
            box.setTransform(QMatrix4x4(1, 0, 0, x,
                                        0, 1, 0, y,
                                        0, 0, 1, 0,
                                        0, 0, 0, 1))
            self.grid_BoxItems.append(box)
            self.addItem(box)
        path_offset = [fov * .5 for fov in self.fov_dimensions]
        path = np.array([*[[x + path_offset[0], y + path_offset[1], 0] for x, y in self.grid_coords]])
        self.grid_LinePlotItem.setData(pos=path, color=QColor('lime'))

    def toggle_path_visibility(self, visible):
        """Slot for a radio button to toggle visibility of path"""

        if visible:
            self.grid_LinePlotItem.setVisible(True)
        else:
            self.grid_LinePlotItem.setVisible(False)

    def _update_opts(self):
        """Update view of widget"""

        extrema = {'x_min': min([x for x, y in self.grid_coords]), 'x_max': max([x for x, y in self.grid_coords]),
                   'y_min': min([y for x, y in self.grid_coords]), 'y_max': max([y for x, y in self.grid_coords])}

        x_fov = self.fov_dimensions[0]
        y_fov = self.fov_dimensions[1]

        x_pos = self.fov_position[0]
        y_pos = self.fov_position[1]

        distances = [sqrt((x_pos - x) ** 2 + (y_pos - y) ** 2) for x, y in self.grid_coords]
        max_index = distances.index(max(distances, key=abs))
        furthest_tile = {'x': self.grid_coords[max_index][0],
                         'y': self.grid_coords[max_index][1]}
        # if fov_position is within grid or farthest distance is between grid tiles
        if extrema['x_min'] <= x_pos <= extrema['x_max'] or \
                abs(furthest_tile['x'] - x_pos) < abs(extrema['x_max'] - extrema['x_min']):
            x_center = ((extrema['x_min'] + extrema['x_max']) / 2) + x_fov / 2
            x_dist = ((extrema['x_max'] - extrema['x_min']) + (x_fov * 2)) / 2 * tan(radians(self.opts['fov']))

        else:
            x_center = ((x_pos + furthest_tile['x']) / 2) + x_fov / 2
            x_dist = (abs(x_pos - furthest_tile['x']) + (x_fov * 2)) / 2 * tan(radians(self.opts['fov']))

        if extrema['y_min'] <= y_pos <= extrema['y_max'] or \
                abs(furthest_tile['y'] - y_pos) < abs(extrema['y_max'] - extrema['y_min']):
            y_center = ((extrema['y_min'] + extrema['y_max']) / 2) + y_fov / 2
            # View does not scale when changing vertical size of widget so for y_dist we need to take into account the
            # difference between the height and width
            y_dist = ((extrema['y_max'] - extrema['y_min']) + (y_fov * 2)) / 2 * tan(radians(self.opts['fov'])) \
                     * (self.size().width() / self.size().height())

        else:
            y_center = ((y_pos + furthest_tile['y']) / 2) + y_fov / 2
            y_dist = (abs(y_pos - furthest_tile['y']) + (y_fov * 2)) / 2 * tan(radians(self.opts['fov'])) \
                     * (self.size().width() / self.size().height())

        self.opts['distance'] = x_dist if x_dist > y_dist else y_dist
        self.opts['center'] = QVector3D(
            x_center,
            y_center,
            0)

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

        if event.button() == Qt.LeftButton:
            # Translate mouseclick x, y into view widget x, y
            x_dist = self.opts['distance'] / tan(radians(self.opts['fov']))
            y_dist = self.opts['distance'] / tan(radians(self.opts['fov'])) * (
                    self.size().height() / self.size().width())
            x_scale = ((event.x() * 2 * x_dist) / self.size().width())
            y_scale = ((event.y() * 2 * y_dist) / self.size().height())
            x = (self.opts['center'].x() - x_dist + x_scale) - .5 * self.fov_dimensions[0]
            y = (self.opts['center'].y() + y_dist - y_scale) - .5 * self.fov_dimensions[1]
            new_fov = (round(x, 2), round(y, 2))
            return_value = self.move_fov_query(new_fov)
            if return_value == QMessageBox.Ok:
                self.fov_position = new_fov  # TODO: How to handle this with real stage
                self.fovMoved.emit(new_fov)
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
