import sys
from pathlib import Path
from utils import TriState

parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_dir)
from activities import Activities

class Telescope(Activities):
    focuser = None
    camera = None
    focuser_status: None
    camera_status: None
    focuser_future: None
    camera_future: None

    def __init__(self, id, focuser, camera):
        super().__init__()
        self.id = id
        self.focuser = focuser
        self.camera = camera
        self.focuser_status = None
        self.camera_status = None

    @property
    def operational(self) -> TriState:
        fstat = self.focuser_status
        cstat = self.camera_status
        ret: TriState = False

        ret = (fstat.operational if hasattr(fstat, 'operational') else False) and (cstat.operational if hasattr(cstat, 'operational') else False)
        return ret
    
    def status(self) -> dict:
        self.detected = self.focuser.detected and self.camera.detected
        return {
            "detected": self.detected,
            "operational": self.operational,
        }
    
    def info(self):
        return {
            'Equipment': f"telescope-{self.id}",
            'Maker': "Celestron",
            'Model': 'RASA 11-inch',
        }
    