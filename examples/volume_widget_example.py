from instrument_widgets.acquisition_widgets.volume_widget import VolumeWidget
from qtpy.QtWidgets import QApplication
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    volume_widget = VolumeWidget(tile_specs={'power_mw', 'binning'})

    sys.exit(app.exec_())