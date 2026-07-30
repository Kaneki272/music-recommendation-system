from abc import ABC, abstractmethod

class LoaderInterface(ABC):
    @abstractmethod
    async def bulk_upsert(self, domain_models: list[dict]):
        pass
