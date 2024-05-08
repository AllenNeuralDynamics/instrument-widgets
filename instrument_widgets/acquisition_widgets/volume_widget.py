from qtpy.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QHBoxLayout, QLabel, QButtonGroup, QRadioButton, \
    QGridLayout, QTableWidgetItem
from instrument_widgets.acquisition_widgets.scan_plan_widget import ScanPlanWidget
from instrument_widgets.acquisition_widgets.volume_model import VolumeModel
from instrument_widgets.acquisition_widgets.tile_plan_widget import TilePlanWidget
from instrument_widgets.acquisition_widgets.channel_plan_widget import ChannelPlanWidget
from qtpy.QtCore import Qt, Signal
import numpy as np
import useq


class VolumeWidget(QWidget):
    """Widget to combine scanning, tiling, channel, and model together to ease acquisition setup"""

    def __init__(self,
                 limits=[[float('-inf'), float('inf')], [float('-inf'), float('inf')], [float('-inf'), float('inf')]],
                 coordinate_plane: list[str] = ['x', 'y', 'z'],
                 fov_dimensions: list[float] = [1.0, 1.0, 0],
                 fov_position: list[float] = [0.0, 0.0, 0.0],
                 tile_specs=set(),
                 view_color: str = 'yellow',
                 unit: str = 'um'):
        """
        :param tile_specs: list of parameters defining tiles
        :param limits: list of limits ordered in [tile_dim[0], tile_dim[1], scan_dim[0]]
        :param coordinate_plane: list describing instrument coordinate plane ordered in [tile_dim[0], tile_dim[1], scan_dim[0]]
        :param fov_dimensions: list of fov_dims which correspond to tiling dimensions
        :param fov_position: list describing fov pos ordered in [tile_dim[0], tile_dim[1], scan_dim[0]]
        :param view_color: color of fov in volume model
        :param unit: unit ALL values will be in
        """
        super().__init__()

        self.layout = QGridLayout()

        # create model and add extra checkboxes/inputs/buttons to customize volume model
        self.volume_model = VolumeModel(coordinate_plane, fov_dimensions, fov_position, view_color)
        self.fovMoved = self.volume_model.fovMoved  # expose for ease of access
        self.layout.addWidget(self.volume_model, 0, 1, 1, 2)

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
        self.layout.addLayout(checkboxes, 1, 1, 1, 2)

        # create tile plan widgets
        self.tile_plan_widget = TilePlanWidget(limits, fov_dimensions, fov_position, coordinate_plane, unit)
        self.fovStop = self.tile_plan_widget.fovStop  # expose for ease of access
        self.tile_starts = self.tile_plan_widget.grid_position_widgets  # expose for ease of access
        self.anchor_widgets = self.tile_plan_widget.anchor_widgets  # expose for ease of access
        self.layout.addWidget(self.tile_plan_widget, 0, 0)

        # create scan widgets
        self.scan_plan_widget = ScanPlanWidget(limits[2], unit)
        self.layout.addWidget(self.scan_plan_widget, 1, 0)

        # create channel plan widget
        self.channel_plan = ChannelPlanWidget(coordinate_plane, tile_specs)
        self.channel_plan.table.cellChanged.connect(self.table_changed)
        self.channel_plan.table.currentCellChanged.connect(self.toggle_z_show)
        self.layout.addWidget(self.channel_plan, 2, 0, 1, 2)

        # hook up tile_plan_widget signals for scan_plan_constructions, volume_model path, and tile start
        self.tile_plan_widget.valueChanged.connect(lambda value: self.tile_plan_widget.setEnabled(False))
        self.tile_plan_widget.valueChanged.connect(self.tile_plan_changed)
        self.tile_starts[2].disconnect()  # disconnect to only trigger update graph once
        self.tile_starts[2].valueChanged.connect(lambda value: setattr(self.scan_plan_widget, 'grid_position', value))
        self.anchor_widgets[2].toggled.connect(self.toggle_z_anchor)
        self.disable_scan_start_widgets(True)

        # hook up scan_plan_widget signals to update grid and channel plan when tiles are changed
        self.scan_plan_widget.scanChanged.connect(self.update_model)
        #self.scan_plan_widget.tileAdded.connect(self.tile_added)
        # self.scan_plan_widget.rowRemoved.connect(self.channel_plan.delete_row)
        # self.scan_plan_widget.columnRemoved.connect(self.channel_plan.delete_column)
        self.scan_plan_widget.apply_all.toggled.connect(self.toggle_apply_all)

        # update tile position if volume model is updated
        #self.volume_model.valueChanged.connect(self.tile_pos_changed)

        self.limits = limits
        self.coordinate_plane = coordinate_plane
        self.fov_dimensions = fov_dimensions[:2] + [0]  # add 0 if not already included
        self.fov_position = fov_position
        self.unit = unit

        # initialize first tile and add to layout
        self.scan_plan_widget.scan_plan_construction(self.tile_plan_widget.value())
        self.layout.addWidget(self.scan_plan_widget.z_plan_widgets[0, 0], 2, 2)
        self.scan_plan_widget.z_plan_widgets[0, 0].setVisible(True)
        self.scan_plan_widget.z_plan_widgets[0, 0].start.valueChanged.connect(self.update_scan_start)

        self.setLayout(self.layout)
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

    def update_model(self):
        """When scan changes, update model"""

        # if rows or columns removed, update table. Must do before updating graph
        if self.channel_plan.tile_items.shape[0] > self.scan_plan_widget.z_plan_widgets.shape[0]:
            for i in range(self.channel_plan.tile_items.shape[0], self.scan_plan_widget.z_plan_widgets.shape[0], -1):
                self.channel_plan.delete_row(i-1)
        elif self.channel_plan.tile_items.shape[1] > self.scan_plan_widget.z_plan_widgets.shape[1]:
            for j in range(self.channel_plan.tile_items.shape[1], self.scan_plan_widget.z_plan_widgets.shape[1], -1):
                self.channel_plan.delete_column(j-1)

        # When scan changes, update model
        setattr(self.volume_model, '_scan_volumes', self.scan_plan_widget.scan_volumes)
        setattr(self.volume_model, '_tile_visibility', self.scan_plan_widget.tile_visibility)
        setattr(self.volume_model, 'grid_coords', np.dstack((self.tile_plan_widget.tile_positions,
                                                             self.scan_plan_widget.scan_starts)))

        #clear table and add back tiles in the correct order
        self.channel_plan.table.clear()
        self.channel_plan.table.setHorizontalHeaderLabels(self.channel_plan.columns)
        self.channel_plan.table.setRowCount(0)
        for tile in self.tile_plan_widget.value():
            self.tile_added(tile.row, tile.col)

        if not self.anchor_widgets[2].isChecked():  # disable start widget for any new widgets
            self.disable_scan_start_widgets(True)
        self.tile_plan_widget.setEnabled(True)

    def grid_plane_change(self, button):
        """Update grid plane and remap path
        :param button: button that was clicked"""

        setattr(self.volume_model, 'grid_plane', tuple(x for x in button.text() if x.isalpha()))
        self.volume_model.path.setData(pos=
                                       [[self.volume_model.grid_coords[t.row][t.col][i] + .5 * self.fov_dimensions[i]
                                         if self.coordinate_plane[i] in self.volume_model.grid_plane else 0. for i in
                                         range(3)] for t in self.tile_plan_widget.value()])  # update path

    def tile_added(self, row, column):
        """Add new tile to channel_plan with relevant info"""

        self.channel_plan.table.blockSignals(True)
        z = self.scan_plan_widget.z_plan_widgets[row, column]
        kwargs = {'row, column': [row, column],
                  self.coordinate_plane[0]: self.tile_plan_widget.tile_positions[row][column][0],
                  self.coordinate_plane[1]: self.tile_plan_widget.tile_positions[row][column][1],
                  self.coordinate_plane[2]: z.start.value(),
                  f'{self.coordinate_plane[2]} steps': z.steps.value(),
                  f'{self.coordinate_plane[2]} step size': z.step.value()}

        if row + 1 > self.channel_plan.tile_items.shape[0]:  # add row
            self.channel_plan.tile_items = np.vstack((self.channel_plan.tile_items, [{}] * self.channel_plan.tile_items.shape[1]))
        if column + 1 > self.channel_plan.tile_items.shape[1]:  # add column
            self.channel_plan.tile_items = np.hstack((self.channel_plan.tile_items, [[{}] for _ in range(self.channel_plan.tile_items.shape[0])]))

        row_count = self.channel_plan.table.rowCount()
        self.channel_plan.table.insertRow(row_count)

        for header_col, header in enumerate(self.channel_plan.columns):
            self.channel_plan.tile_items[row, column][header] = QTableWidgetItem(str(kwargs.get(header, '')))
            self.channel_plan.table.setItem(row_count, header_col, self.channel_plan.tile_items[row, column][header])

        row_items = self.channel_plan.tile_items[row, column]
        # set correct cells disabled based on current widget state
        disable = list(kwargs.keys()) if self.scan_plan_widget.apply_all.isChecked() and (row, column) != (0, 0) else \
            ['row, column', self.coordinate_plane[0], self.coordinate_plane[1]]

        flags = QTableWidgetItem().flags()
        flags &= ~Qt.ItemIsEditable
        for var in disable:
            row_items[var].setFlags(flags)
        # additionally disable z if not anchored in that dimension
        if not self.anchor_widgets[2].isChecked():
            row_items[self.coordinate_plane[2]].setFlags(flags)

        # connect z widget signals to trigger update
        z.valueChanged.connect(lambda value: self.change_table(value, z, row_items))

        self.channel_plan.table.blockSignals(False)

        # add new tile to layout
        self.layout.addWidget(self.scan_plan_widget.z_plan_widgets[row, column], 2, 2)
        self.scan_plan_widget.z_plan_widgets[row, column].setVisible(False)

    def change_table(self, value, z_widget, row_items):
        """If z widget is changed, update table"""

        print(z_widget.windowTitle(), 'update')
        self.undercover_update_item(value[0], row_items['z'])
        self.undercover_update_item(len(value), row_items['z steps'])
        self.undercover_update_item(z_widget.step.value(), row_items['z step size'])

    def table_changed(self, row, column):
        """Update z widget if table is edited"""

        item = self.channel_plan.table.item(row, column)
        if column in [3, 4, 5]:
            coords = self.channel_plan.table.item(row, 0).text().replace('[', '').replace(']', '').split(',')
            tile_row, tile_column = [int(x) for x in coords]
            z = self.scan_plan_widget.z_plan_widgets[tile_row, tile_column]
            if column == 3:
                z.start.setValue(float(item.text()))
            elif column == 4:
                z.steps.setValue(int(item.text()))
            elif column == 5:
                z.step.setValue(float(item.text()))

    def undercover_update_item(self, value, item):
        """Update table with latest z value"""

        self.channel_plan.table.blockSignals(True)
        item.setText(str(value))
        self.channel_plan.table.blockSignals(False)

    def update_scan_start(self, value):
        """If apply all is checked and tile 0,0 start is updated, update tile_start widget in teh scan dimension"""

        if self.scan_plan_widget.apply_all.isChecked():
            self.tile_starts[2].setValue(value)

    def tile_pos_changed(self, attribute):
        """If volume model grid coord changes, update table"""

        if attribute == 'grid_coords':
            headers = self.coordinate_plane[:2]
            for row, column in np.ndindex(self.scan_plan_widget.z_plan_widgets.shape):
                row_items = self.channel_plan.tile_items[row][column]
                self.undercover_update_item(self.volume_model.grid_coords[row, column, 0], row_items[headers[0]])
                self.undercover_update_item(self.volume_model.grid_coords[row, column, 1], row_items[headers[1]])

    def disable_scan_start_widgets(self, disable):
        """Disable all scan start widgets if tile_plan_widget.grid_position_widgets[2] is checked"""

        for i, j in np.ndindex(self.scan_plan_widget.z_plan_widgets.shape):
            self.scan_plan_widget.z_plan_widgets[i][j].start.setDisabled(disable)

    def toggle_z_anchor(self, checked):
        """Toggle state of widget if z anchor is toggled"""

        self.disable_scan_start_widgets(not checked)
        if self.scan_plan_widget.apply_all.isChecked():
            item = self.channel_plan.table.item(0, 3)
            self.toggle_item_flags(item, checked)
        else:
            for row in range(self.channel_plan.table.rowCount()):
                item = self.channel_plan.table.item(row, 3)
                self.toggle_item_flags(item, checked)

    def toggle_apply_all(self, checked):
        """Enable/disable all channel plan cells when apply all is toggled"""

        # disable tilestart and anchor widget it apply all isn't checked
        self.tile_starts[2].setEnabled(checked if self.anchor_widgets[2].isChecked() else False)
        self.anchor_widgets[2].setEnabled(checked)

        for row, column in np.ndindex(self.channel_plan.tile_items.shape):
            if (row, column) == (0, 0):
                continue  # 0, 0 always enabled and editable
            row_items = self.channel_plan.tile_items[row][column]
            headers = self.channel_plan.columns[3:6] if self.anchor_widgets[2].isChecked() else \
                self.channel_plan.columns[4:6]

            for key in headers:
                self.toggle_item_flags(row_items[key], not checked)

        if not checked:
            self.channel_plan.table.blockSignals(True)
            self.channel_plan.table.setCurrentCell(0, 0)
            self.channel_plan.table.blockSignals(False)

        if checked:
            hide_row, hide_col = [int(x) for x in
                                  self.channel_plan.table.item(self.channel_plan.table.currentRow(), 0).text() if
                                  x.isdigit()]
            self.scan_plan_widget.z_plan_widgets[hide_row, hide_col].setVisible(False)

            self.scan_plan_widget.z_plan_widgets[0, 0].setVisible(True)

    def toggle_item_flags(self, item, enable):
        """Change flags for enabling/disabling items in channel_plan table"""

        flags = QTableWidgetItem().flags()
        if not enable:
            flags &= ~Qt.ItemIsEditable
        else:
            flags |= Qt.ItemIsEditable
            flags |= Qt.ItemIsEnabled
            flags |= Qt.ItemIsSelectable
        item.setFlags(flags)

    def toggle_z_show(self, current_row, current_column, previous_row, previous_column):
        """If apply all is not checked, show corresponding z widget for selected row"""

        if not self.scan_plan_widget.apply_all.isChecked():
            hide_row, hide_col = [int(x) for x in self.channel_plan.table.item(previous_row, 0).text() if x.isdigit()]
            self.scan_plan_widget.z_plan_widgets[hide_row, hide_col].setVisible(False)

            show_row, show_col = [int(x) for x in self.channel_plan.table.item(current_row, 0).text() if x.isdigit()]
            self.scan_plan_widget.z_plan_widgets[show_row, show_col].setVisible(True)
