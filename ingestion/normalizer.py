from abc import ABC, abstractmethod

class NormalizerInterface(ABC):
    @abstractmethod
    def normalize_to_domain_model(self, raw_data: dict) -> dict:
        pass
