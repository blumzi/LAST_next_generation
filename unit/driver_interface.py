from abc import ABC, abstractmethod
from utils import Equipment

class DriverInterface(ABC):

    def __init__(self, equipment_type: Equipment, equipment_id: int = 0) -> None:
        self.task = task

    @abstractmethod
    def get(self, method: str, **kwargs):
        pass

    @abstractmethod
    def put(self, method: str, params: dict, data: bytes):
        pass

    @property
    @abstractmethod
    def available(self) -> bool:
        pass

    @property
    @abstractmethod
    def reason_for_not_available(self) -> str:
        pass