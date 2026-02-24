from core.controllers.holo_controller import HoloController
from core.controllers.datapanel_controller import DataPanelController

class holo_colors:
    def __init__(self, port_name=None):
        self.port_name = port_name
        self.holoController = HoloController(port_name=port_name)
        self.dataPanelController = DataPanelController(port_name=port_name)

    def holoColorEmotions(self, colors: list[list]):
        self.holoController.changeHoloRGBColor(3, 0, colors[0])
        self.holoController.changeHoloRGBColor(4, 0, colors[1])
        self.holoController.changeHoloRGBColor(5, 0, colors[2])

        self.dataPanelController.setColorRGB(3, colors[3])