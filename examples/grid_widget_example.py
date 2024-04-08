from instrument_widgets.acquisition_widgets.grid_widget import GridWidget
from qtpy.QtWidgets import QApplication
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = GridWidget(limits={'x':[-10000, 10000], 'y':[-10000,10000]}, fov_dimensions=[106, 79])
    widget.show()
    #widget.fov_position = (100, 100)
    #x_limits_um=[-100, 100], y_limits_um=[-100,100], fov_dimensions=[10615.616, 7958.72]
    sys.exit(app.exec_())