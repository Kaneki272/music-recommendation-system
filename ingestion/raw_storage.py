from abc import ABC, abstractmethod

class RawStorageInterface(ABC):
    @abstractmethod
    async def save_raw_json(self, provider: str, resource_type: str, data: dict) -> str:
        """Returns the storage path or URI"""
        pass
