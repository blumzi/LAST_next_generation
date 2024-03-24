from abc import ABC, abstractmethod
from utils import Equipment
from datetime import datetime


class DriverInterface(ABC):

    _detected: bool = False

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
    def detected(self) -> bool:
        pass

    @property
    @abstractmethod
    def responding(self) -> bool:
        pass

    @property
    @abstractmethod
    def last_response(self) -> datetime:
        pass

    @property
    @abstractmethod
    def status(self) -> str:
        pass

    @property
    @abstractmethod
    def info(self) -> dict:
        pass
