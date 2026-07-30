from abc import ABC, abstractmethod

class SyncStateManagerInterface(ABC):
    @abstractmethod
    async def get_last_cursor(self, entity_type: str) -> str:
        pass
        
    @abstractmethod
    async def update_cursor(self, entity_type: str, cursor: str):
        pass
