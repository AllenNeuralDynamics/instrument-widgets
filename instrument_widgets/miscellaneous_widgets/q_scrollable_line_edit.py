from qtpy.QtWidgets import QLineEdit
from qtpy.QtGui import QIntValidator, QDoubleValidator

class QScrollableLineEdit(QLineEdit):
    """Widget inheriting from QLineEdit that allows value to be scrollable"""
    def wheelEvent(self, event):
        super().wheelEvent(event)
        if self.validator() is not None and type(self.validator()) in [QIntValidator, QDoubleValidator]:
            if type(self.validator()) == QDoubleValidator:
                new_value = float(self.text())+10**(-self.validator().decimals())
            elif type(self.validator()) == QIntValidator:
                new_value = int(self.text())+1
            self.setText(str(new_value))
            self.editingFinished.emit()


