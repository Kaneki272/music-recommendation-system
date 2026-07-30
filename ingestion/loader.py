from abc import ABC, abstractmethod
from typing import List, Dict, Any

class LoaderInterface(ABC):
    @abstractmethod
    async def bulk_upsert(self, domain_models: List[Dict[str, Any]], batch_size: int = 100):
        """
        Idempotent bulk upsert. Must process in batches to avoid memory/DB limits.
        If a record exists (by ISRC/Spotify ID), it updates. If not, it inserts.
        """
        pass
