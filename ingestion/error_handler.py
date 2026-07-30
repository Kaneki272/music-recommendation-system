from abc import ABC, abstractmethod

class ErrorHandlerInterface(ABC):
    @abstractmethod
    async def log_failed_record(self, job_id: str, raw_data: dict, error_reason: str):
        pass
