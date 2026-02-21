from core.controllers.commandValues import CommandValues
from core.controllers.nodeValues import NodeValues
from core.controllers.port import Port

class DataPanelController:
    def __init__(self, port_name =None):
        self.port = Port(port_name=port_name)

    def _isColorValid(self, color):
        if not (0 <= color <= 255):
            raise ValueError(f"Color value not valid")
    
    def _isProgramValid(self, program):
        if not (49 <= program <= 56):
            raise ValueError(f"Program value not valid")

    def setProgram(self, display, program):
        try:
            self._isProgramValid(program=program)
            self.port.send_data([CommandValues.SET_PROGRAM, NodeValues.TEECE_COMMAND_TEXT, display, program])
        except Exception as e:
            print(f"ERROR: {e}")

    def setColorRGB(self, display, colors):
        try:
            [self._isColorValid(color=color) for color in colors]
            self.port.send_data([CommandValues.SET_TEECE_COLOR, NodeValues.TEECE_COLOR, display] + colors)
        except Exception as e:
            print(f"ERROR: {e}")

    