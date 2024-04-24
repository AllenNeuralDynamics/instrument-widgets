from qtpy.QtWidgets import QSizePolicy, QWidget, QVBoxLayout, QCheckBox, \
    QPushButton, QDoubleSpinBox, QGridLayout, QTableWidget, QButtonGroup, QRadioButton, \
    QHBoxLayout, QLabel, QTableWidgetItem
from qtpy.QtCore import Signal, Qt
from instrument_widgets.acquisition_widgets.grid_plan_widget import GridPlanWidget
from instrument_widgets.acquisition_widgets.scan_plan_widget import ZPlanWidget

class GridWidget(QWidget):
    """Widget combining GridPlanWidget, ZPlanWidget, and GridViewWidget. Note that the x and y refer to the tiling
    dimensions and z is the scanning dimension """

    fovStop = Signal()

    def __init__(self,
                 limits=[[float('-inf'), float('inf')], [float('-inf'), float('inf')], [float('-inf'), float('inf')]],
                 coordinate_plane: list[str] = ['x', 'y', 'z'],
                 fov_dimensions: list[float] = [1.0, 1.0],
                 fov_position: list[float] = [0.0, 0.0, 0.0],
                 unit: str = 'um'):
        super().__init__()

        self.limits = limits
        self.unit = unit

        # setup z plan widget
        self.z_widget = QWidget()  # IMPORTANT: needs to be an attribute so QWidget will stay open
        self.z_plan_table = QTableWidget()  # Table describing z tiles
        self.z_plan_table.setColumnCount(6)
        self.z_plan_table.setHorizontalHeaderLabels(['channel', 'row', 'column', 'z0', 'zend', 'step#'])
        self.z_plan_table.resizeColumnsToContents()
        self.z_plan_table.cellClicked.connect(self.show_z_plan_widget)
        self.z_plan_widgets = [[]]  # 2d list containing z plan widget

        checkbox_layout = QHBoxLayout()

        self.row_order = 'By Acquisition'
        button_layout = QVBoxLayout()
        table_order = QButtonGroup(self.z_widget)
        for view in ['By Row', 'By Column', 'By Acquisition']:
            button = QRadioButton(view)
            button.clicked.connect(lambda clicked, b=button: setattr(self, 'row_order', b.text()))
            button.clicked.connect(lambda clicked: self.z_plan_construction(self.grid_plan.value()))
            table_order.addButton(button)
            button_layout.addWidget(button)
            button.setChecked(True)
        checkbox_layout.addWidget(QLabel('Table Order: '))
        checkbox_layout.addLayout(button_layout)

        layout = QVBoxLayout()
        layout.addWidget(self.z_plan_table)
        layout.addLayout(checkbox_layout)
        self.z_widget.setLayout(layout)
        self.z_widget.setWindowTitle('Tiling Plan')
        self.z_widget.show()



        # expose attributes from grid_plan and grid_view
        self.old_value = self.grid_plan.value()
        self.grid_position = fov_position
        self.fov_position = fov_position
        self.fov_dimensions = fov_dimensions
        self.coordinate_plane = coordinate_plane
        self.planValueChanged = self.grid_plan.valueChanged
        # Check and uncheck tiling anchor to disable first tile start box
        self.anchor_widgets[2].setChecked(True)
        self.anchor_widgets[2].setChecked(False)
        self.z_plan_table.show()

    @property
    def grid_position(self):
        return self._grid_position

    @grid_position.setter
    def grid_position(self, value):
        self._grid_position = value
        if self.grid_plan.grid_position != value:
            self.grid_plan.grid_position = value
        # for tile in self.grid_plan.value().iter_grid_positions():  # need to match row, col
        #     self.z_plan_widgets[tile.row][tile.col].start.setValue(value[2])  # change start for tiles

    @property
    def fov_position(self):
        return self._fov_position

    @fov_position.setter
    def fov_position(self, value):
        self._fov_position = value
        for i in range(3):
            if not self.anchor_widgets[i].isChecked():
                self.grid_position_widgets[i].setValue(value[i])

    @property
    def fov_dimensions(self):
        return self._fov_dimensions

    @fov_dimensions.setter
    def fov_dimensions(self, value):
        self._fov_dimensions = value
        if self.grid_plan.fov_dimensions != value:
            self.grid_plan.fov_dimensions = value

    def toggle_grid_position(self, enable):
        """If grid is anchored, allow user to input grid position"""

        for i in range(3):
            if self.anchor_widgets[i].isChecked() != self.grid_position_widgets[i].isEnabled():  # button was toggled
                self.grid_position_widgets[i].setEnabled(enable)
                if i == 2:  # tiling direction so need to enable/disable start value box in z plan widget
                    for tile in self.grid_plan.value().iter_grid_positions():  # need to match row, col
                        self.z_plan_widgets[tile.row][tile.col].start.setEnabled(enable)
                if not enable:  # Graph is anchored
                    self.grid_position[i] = self.fov_position[i]
        self.grid_plan.relative_to.setDisabled(any([anchor.isChecked() for anchor in self.anchor_widgets]))



    def create_z_table_row(self, z, row, column):
        """Create a correctly formatted row in the z_plan_table under the last row"""
        # need to insert row before adding item
        self.z_plan_table.insertRow(self.z_plan_table.rowCount())
        for j, value in enumerate([row, column, z.value()[0], z.value()[-1], z.steps.value()]):
            item = QTableWidgetItem(str(value))
            item.setFlags(Qt.ItemIsEnabled)  # disable cell
            self.z_plan_table.setItem(self.z_plan_table.rowCount() - 1, j + 1, QTableWidgetItem(item))
        z.valueChanged.connect(lambda val: self.update_z_plan_table(val, row))

    def create_z_plan_widget(self, row, column):
        """Function to create and connect ZPlanWidget"""

        z = ZPlanWidget(self.limits[2], self.unit)
        z.valueChanged.connect(self.grid_coord_construction)
        z.setWindowTitle(f'({row}, {column})')
        z.setVisible(False)
        z.start.setEnabled(self.anchor_widgets[2].isChecked())

        return z

    def create_hide_widget(self, z):
        """Create checkbox to hide ZPlanWidget
        :param z: correlating z widget to hide"""

        hide = QCheckBox('Hide')
        hide.toggled.connect(lambda checked: setattr(z, 'hidden', checked))
        hide.toggled.connect(self.grid_coord_construction)
        return hide

    def update_z_plan_table(self, val, row):
        """Update z plan table with new value"""
        if self.apply_all.isChecked():
            for i in range(self.z_plan_table.rowCount()):
                for j, value in zip([1, 3, 4, 5], [row, val[0], val[-1], len(val)]):
                    if (item := QTableWidgetItem(str(value))) != self.z_plan_table.itemAt(i, j):
                        item.setFlags(Qt.ItemIsEnabled)  # disable cell
                        self.z_plan_table.setItem(i, j, QTableWidgetItem(item))
        else:
            for j, value in zip([1, 3, 4, 5], [row, val[0], val[-1], len(val)]):
                if (item := QTableWidgetItem(str(value))) != self.z_plan_table.itemAt(row, j):
                    item.setFlags(Qt.ItemIsEnabled)  # disable cell
                    self.z_plan_table.setItem(row, j, QTableWidgetItem(item))
        self.z_plan_table.resizeColumnsToContents()

    def show_z_plan_widget(self, row, column):
        """Show z_plan_widget when cell in the row of table is clicked"""

        if self.apply_all.isChecked():
            row = 0
        z_row = int(self.z_plan_table.item(row, 1).text())
        z_column = int(self.z_plan_table.item(row, 2).text())

        # Hide all other z widgets
        for i in range(len(self.z_plan_widgets)):
            for j in range(len(self.z_plan_widgets[0])):
                self.z_plan_widgets[i][j].setVisible(False)

        self.z_plan_widgets[z_row][z_column].setVisible(True)

    # def grid_coord_construction(self, value=None):
    #     """Create current list of x,y,z of planned grid"""
    #
    #     if len(self.z_plan_widgets[0]) != 0:
    #         if self.apply_all.isChecked():
    #             z = self.z_plan_widgets[0][0].value()
    #             # TODO: update other tiles
    #             # set tile_z_dimension first so grid can render properly
    #             self.grid_view.tile_z_dimensions = [z[-1] - z[0]] * len(self.grid_plan.tile_positions)
    #             self.grid_view.tile_visibility = [True] * len(self.grid_plan.tile_positions)
    #             self.grid_view.grid_coords = [(x, y, z[0]) for x, y in self.grid_plan.tile_positions]
    #         else:
    #             tile_z_dimensions = []
    #             tile_xyz = []
    #             tile_visibility = []
    #             tile_xy = self.grid_plan.tile_positions
    #             for i, tile in enumerate(self.grid_plan.value().iter_grid_positions()):  # need to match row, col
    #                 x, y = tile_xy[i]
    #                 z = self.z_plan_widgets[tile.row][tile.col].value()
    #                 tile_xyz.append((x, y, z[0]))
    #                 tile_z_dimensions.append(z[-1] - z[0])
    #                 if not self.z_plan_widgets[tile.row][tile.col].hidden:
    #                     tile_visibility.append(True)
    #                 else:
    #                     tile_visibility.append(False)
    #             self.grid_view.tile_z_dimensions = tile_z_dimensions
    #             self.grid_view.grid_coords = tile_xyz
    #             self.grid_view.tile_visibility = tile_visibility

    def toggle_apply_all(self, checked):
        """If apply all is toggled, disable/enable tab widget accordingly and reconstruct gui coords.
        Also change visible z plan widget"""

        for i in range(len(self.z_plan_widgets)):
            for j in range(len(self.z_plan_widgets[0])):
                self.z_plan_widgets[i][j].setDisabled(checked)
                if checked and (i, j) != (0,0):
                    self.z_plan_widgets[i][j].setVisible(False)
        if len(self.z_plan_widgets[0]) != 0:
            self.z_plan_widgets[0][0].setDisabled(False)  # always enabled
            if checked:
                self.z_plan_widgets[0][0].setVisible(True)

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
