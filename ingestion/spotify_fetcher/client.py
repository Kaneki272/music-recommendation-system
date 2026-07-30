from abc import ABC, abstractmethod

class SpotifyClientInterface(ABC):
    @abstractmethod
    async def fetch_artist(self, spotify_id: str) -> dict:
        pass
        
    @abstractmethod
    async def fetch_album_tracks(self, album_id: str) -> list[dict]:
        pass
