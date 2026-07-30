from abc import ABC, abstractmethod
from typing import Dict, Any

class OAuthProviderInterface(ABC):
    @abstractmethod
    async def get_authorization_url(self) -> str:
        pass
        
    @abstractmethod
    async def fetch_user_data(self, authorization_code: str) -> Dict[str, Any]:
        pass
