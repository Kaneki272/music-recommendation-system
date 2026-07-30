from abc import ABC, abstractmethod

class JobTrackerInterface(ABC):
    @abstractmethod
    async def start_job(self, job_name: str):
        pass
        
    @abstractmethod
    async def complete_job(self, job_id: str, records_processed: int, records_failed: int):
        pass
