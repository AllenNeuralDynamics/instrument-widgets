from instrument_widgets.acquisition_widgets.grid_widget import GridWidget
from qtpy.QtWidgets import QApplication
import sys

def print_stuff(value):
    print('value ', value)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = GridWidget(limits={'x_limits':[-10000, 10000], 'y_limits':[-10000,10000],
                                'z_limits':[-10000,10000]}, fov_dimensions=[106, 79])
    # widget.z_grid_plan.valueChanged.connect(print_stuff)
    #widget.fov_position = (100, 100)
    #x_limits_um=[-100, 100], y_limits_um=[-100,100], fov_dimensions=[10615.616, 7958.72]
    sys.exit(app.exec_())