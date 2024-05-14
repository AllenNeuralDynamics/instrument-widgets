from qtpy.QtWidgets import QTabWidget, QApplication, QTabBar, QWidget, QPushButton, QStyle, \
    QMenu, QToolButton, QAction, QTableWidget, QTableWidgetItem, QSizePolicy, QComboBox
import numpy as np
from qtpy.QtCore import Signal, Qt
import sys


class ChannelPlanWidget(QTabWidget):
    """Widget defining parameters per tile per channel """

    channelAdded = Signal([str])

    def __init__(self, channels: dict, settings: dict):
        """
        :param channels: dictionary defining channels for instrument
        :param settings: allowed setting for devices
        """

        super().__init__()

        self.channels = channels
        self.settings = settings

        self.steps = {}  # dictionary of number of steps for each tile in each channel
        self.step_size = {}  # dictionary of step size for each tile in each channel

        self._tile_volumes = np.zeros([0, 0], dtype=float)  # array of tile starts and ends. Constant for every channel

        self.tab_bar = ChannelPlanTabBar()
        self.tab_bar.setMovable(True)
        self.setTabBar(self.tab_bar)

        self.channel_order = QComboBox()
        self.channel_order.addItems(['Sequential', 'Interleaved', ])
        self.setCornerWidget(self.channel_order)

        # add tab with button to add channels
        self.add_tool = QToolButton()
        self.add_tool.setText('+')
        menu = QMenu()
        for channel in self.channels:
            action = QAction(str(channel), self)
            action.triggered.connect(lambda clicked, ch=channel: self.add_channel(ch))
            menu.addAction(action)
        self.add_tool.setMenu(menu)
        self.add_tool.setPopupMode(QToolButton.InstantPopup)
        self.insertTab(0, QWidget(), '')  # insert dummy qwidget
        self.tab_bar.setTabButton(0, QTabBar.RightSide, self.add_tool)

        self._apply_all = True  # external flag to dictate behaviour of added tab

    @property
    def apply_all(self):
        return self._apply_all

    @apply_all.setter
    def apply_all(self, value):
        """When apply all is toggled, update existing channels"""

        if self._apply_all != value:
            for tab_index in range(self.count() - 1):  # skip add tab
                channel = self.tabText(tab_index)
                table = getattr(self, f'{channel}_table')

                for i in range(1, table.rowCount()):  # skip first row
                    for j in range(table.columnCount() - 1):  # skip last column
                        item = table.item(i, j)
                        self.enable_item(item, not value)
                        if value:
                            item.setText(table.item(0, j).text())
        self._apply_all = value

    @property
    def tile_volumes(self):
        return self._tile_volumes

    @tile_volumes.setter
    def tile_volumes(self, value: np.array):
        """When tile dims is updated, update size of channel arrays"""

        for tab_index in range(self.count() - 1):  # skip add tab
            channel = self.tabText(tab_index)
            table = getattr(self, f'{channel}_table')
            for i in range(table.columnCount() - 1):  # skip row, column
                header = table.horizontalHeaderItem(i).text()
                getattr(self, header)[channel] = np.resize(getattr(self, header)[channel], value.shape)
            self.step_size[channel] = np.resize(self.step_size[channel], value.shape)
            self.steps[channel] = np.resize(self.steps[channel], value.shape)

        self._tile_volumes = value

    def enable_item(self, item, enable):
        """Change flags for enabling/disabling items in channel_plan table"""

        flags = QTableWidgetItem().flags()
        if not enable:
            flags &= ~Qt.ItemIsEditable
        else:
            flags |= Qt.ItemIsEditable
            flags |= Qt.ItemIsEnabled
            flags |= Qt.ItemIsSelectable
        item.setFlags(flags)

    def add_channel(self, channel):
        """Add channel to acquisition"""

        setattr(self, f'{channel}_table', QTableWidget())
        table = getattr(self, f'{channel}_table')
        table.cellChanged.connect(self.cell_edited)

        columns = ['step_size', 'steps']
        for device_type, devices in self.channels[channel].items():
            for device in devices:
                for setting in self.settings.get(device_type, []):
                    if not hasattr(self, f'{device}_{setting}'):
                        setattr(self, f'{device}_{setting}', {})
                    getattr(self, f'{device}_{setting}')[channel] = np.zeros(self._tile_volumes.shape)
                    columns.append(f'{device}_{setting}')
        columns.append('row, column')

        self.steps[channel] = np.zeros(self._tile_volumes.shape, dtype=int)
        self.step_size[channel] = np.zeros(self._tile_volumes.shape, dtype=float)

        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.resizeColumnsToContents()
        table.setColumnHidden(len(columns) - 1, True)  # hide row, column header since it will only be used internally
        table.verticalHeader().hide()
        self.insertTab(0, table, channel)
        self.setCurrentIndex(0)

        # add button to remove channel
        button = QPushButton('x')
        button.setMaximumWidth(20)
        button.setMaximumHeight(20)
        button.pressed.connect(lambda: self.remove_channel(channel))
        self.tab_bar.setTabButton(0, QTabBar.RightSide, button)

        # remove channel from add_tool menu
        menu = self.add_tool.menu()
        for action in menu.actions():
            if action.text() == channel:
                menu.removeAction(action)
        self.add_tool.setMenu(menu)

        self.channelAdded.emit(channel)

    def add_channel_rows(self, channel, order: list):
        """Add rows to channel table in specific order of tiles
        :param order: list of tile order e.g. [[0,0], [0,1]]"""

        table = getattr(self, f'{channel}_table')
        table.blockSignals(True)
        table.clearContents()
        table.setRowCount(0)

        arrays = []
        # iterate through columns to find relevant arrays to update
        for i in range(table.columnCount() - 1):  # skip row, column
            arrays.append(getattr(self, table.horizontalHeaderItem(i).text())[channel])

        for tile in order:
            table_row = table.rowCount()
            table.insertRow(table_row)
            item = QTableWidgetItem(str(tile))
            table.setItem(table_row, table.columnCount() - 1, item)
            for column, array in enumerate(arrays):
                item = QTableWidgetItem(str(array[*tile]))
                table.setItem(table_row, column, item)
                item.setText(str(array[*tile]))
                if table_row != 0:  # first row/tile always enabled
                    self.enable_item(item, not self.apply_all)
        table.blockSignals(False)

    def remove_channel(self, channel):
        """Remove channel from acquisition"""

        table = getattr(self, f'{channel}_table')
        index = self.indexOf(table)

        self.removeTab(index)

        # remove key from attributes
        for i in range(table.columnCount() - 1):  # skip row, column
            header = table.horizontalHeaderItem(i).text()
            del getattr(self, header)[channel]

        # add channel back to add_tool
        menu = self.add_tool.menu()
        action = QAction(channel, self)
        action.triggered.connect(lambda clicked, ch=channel: self.add_channel(ch))
        menu.addAction(action)
        self.add_tool.setMenu(menu)

        del table

    def cell_edited(self, row, column):
        """Update table based on cell edit"""

        channel = self.tabText(self.currentIndex())
        table = getattr(self, f'{channel}_table')

        table.blockSignals(True)  # block signals so updating cells doesn't trigger cell edit again
        tile_index = [int(x) for x in table.item(row, table.columnCount() - 1).text() if x.isdigit()]

        if column in [0, 1]:
            volume = self.tile_volumes[*tile_index]
            index = tile_index if not self.apply_all else [slice(None), slice(None)]
            if column == 0:  # step_size changed so round to fit in volume
                steps = round(volume / float(table.item(row, 0).text()))
                step_size = round(volume / steps, 4) if steps != 0 else 0
                self.steps[channel][*index] = steps
            else:  # step number changed
                step_size = round(volume / float(table.item(row, 1).text()), 4)
                steps = round(volume / step_size) if step_size != 0 else 0
                self.step_size[channel][*index] = step_size

            table.item(row, 0).setText(str(step_size))
            table.item(row, 1).setText(str(steps))

        array = getattr(self, table.horizontalHeaderItem(column).text())[channel]
        if self.apply_all:
            array[:, :] = float(table.item(row, column).text())  # TODO: how to deal with different types?
            for i in range(1, table.rowCount()):
                item_0 = table.item(0, column)
                table.item(i, column).setText(item_0.text())
                if column == 0:  # update steps as well
                    table.item(i, column + 1).setText(str(steps))
                elif column == 1:  # update step_szie as well
                    table.item(i, column - 1).setText(str(step_size))
        else:
            array[*tile_index] = float(table.item(row, column).text())

        table.blockSignals(False)


class ChannelPlanTabBar(QTabBar):
    """TabBar that will keep add channel tab at end"""

    def __init__(self):

        super(ChannelPlanTabBar, self).__init__()
        self.tabMoved.connect(self.tab_index_check)

    def tab_index_check(self, prev_index, curr_index):
        """Keep last tab as last tab"""

        if prev_index == self.count() - 1:
            self.moveTab(curr_index, prev_index)

    def mouseMoveEvent(self, ev):
        """Make last tab immovable"""
        index = self.currentIndex()
        if index == self.count() - 1:  # last tab is immovable
            return
        super().mouseMoveEvent(ev)
