from abc import ABC, abstractmethod

class DriverInterface(ABC):

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
    