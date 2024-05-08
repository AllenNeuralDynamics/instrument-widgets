from qtpy.QtWidgets import QSizePolicy, QWidget, QVBoxLayout, QCheckBox, \
    QPushButton, QDoubleSpinBox, QGridLayout, QTableWidget, QButtonGroup, QRadioButton, \
    QHBoxLayout, QLabel, QTableWidgetItem
import numpy as np
from qtpy.QtCore import Signal, Qt

class ChannelPlanWidget(QWidget):
    """Widget to give an overview of tiles and hide/show ZPlanWidgets"""

    def __init__(self, plane: list, tile_specs: set = set()):
        """
        Create channel plan table and initialize potential input variables based on initial tiles
        :param plane: coordinate plane of scan e.g. [scan[0], scan[1], tiling]
        :param tile_specs: list of parameters defining tiles
        """
        super().__init__()

        layout = QVBoxLayout()

        # TODO: Hide row, column column? Do users want to see that
        self.columns = ['row, column', *plane, f'{plane[2]} steps', f'{plane[2]} step size']
        self.columns += tile_specs - set(self.columns)
        self.tile_items = np.empty([1, 1], dtype=object)  # 2d array dictionary containing correct graph item
        self.tile_items[0, 0] = {}

        # setup table
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)

        self.setLayout(layout)

    def add_tile(self, tile_row, tile_col, table_row = None, **kwargs):
        """Add tile to tile items
        :param tile_row: row of the tile to be added
        :param tile_col: col of the tile to be added NOT table col
        :param table_row: row of the table to place items. If None, place in the next available row"""

        if tile_row + 1 > self.tile_items.shape[0]:  # add row
            self.tile_items = np.vstack((self.tile_items, [{}]*self.tile_items.shape[1]))
        if tile_col + 1 > self.tile_items.shape[1]:  # add column
            self.tile_items = np.hstack((self.tile_items, [[{}] for _ in range(self.tile_items.shape[0])]))

        table_row = table_row if table_row is not None else self.table.rowCount()

        if table_row >= self.table.rowCount():
            self.table.insertRow(table_row)

        self.tile_items[tile_row, tile_col] = {key: QTableWidgetItem(str(kwargs.get(key, ''))) for key in self.columns}
        for header_col, header in enumerate(self.columns):
            self.table.setItem(table_row, header_col, self.tile_items[tile_row, tile_col][header])

    def update_tile(self, row, column):
        """Update row number with the newest information"""

    def delete_row(self, row):
        """Delete row
        :param row: row of the tile to be removed NOT table row"""

        self.table.blockSignals(True)
        for j in range(self.tile_items.shape[1]):
            table_row = self.tile_items[row, j]['row, column'].row()
            self.table.removeRow(table_row)
        self.tile_items = np.delete(self.tile_items, row, axis=0)
        self.table.blockSignals(False)

    def delete_column(self, column):
        """Delete row
        :param row: row of the tile to be added NOT table row
        :param column: col of the tile to be added NOT table col"""

        self.table.blockSignals(True)
        for i in range(self.tile_items.shape[0]):
            table_row = self.tile_items[i, column]['row, column'].row()
            self.table.removeRow(table_row)
        self.tile_items = np.delete(self.tile_items, column, axis=1)
        self.table.blockSignals(False)

