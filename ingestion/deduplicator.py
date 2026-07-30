from abc import ABC, abstractmethod

class DeduplicatorInterface(ABC):
    @abstractmethod
    async def is_duplicate(self, isrc_or_id: str) -> bool:
        pass
