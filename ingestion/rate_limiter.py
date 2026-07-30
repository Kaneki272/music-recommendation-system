from abc import ABC, abstractmethod

class RateLimiterInterface(ABC):
    @abstractmethod
    async def check_quota(self) -> bool:
        pass
        
    @abstractmethod
    async def wait_if_needed(self):
        pass
