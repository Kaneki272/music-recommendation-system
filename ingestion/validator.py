from abc import ABC, abstractmethod

class ValidatorInterface(ABC):
    @abstractmethod
    def validate_schema(self, raw_data: dict) -> bool:
        pass
