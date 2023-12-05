from abc import ABC, abstractmethod
from utils import Equipment, DriverState

class DriverInterface(ABC):

    def __init__(self, equipment_type: Equipment, equipment_id: int = 0) -> None:
        pass

    @abstractmethod
    def get(self, method: str, **kwargs):
        pass

    @abstractmethod
    def put(self, method: str, params: dict, data: bytes):
        pass

    @property
    @abstractmethod
    def _state(self) -> DriverState:
        pass

    @property
    @abstractmethod
    def status(self) -> str:
        pass

    @property
    @abstractmethod
    def info(self) -> dict:
        pass
