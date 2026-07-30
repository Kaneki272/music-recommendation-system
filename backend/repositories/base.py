from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Any

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

class BaseRepository(ABC, Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    @abstractmethod
    async def get(self, id: Any) -> Optional[ModelType]:
        pass

    @abstractmethod
    async def get_multi(self, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        pass

    @abstractmethod
    async def create(self, *, obj_in: CreateSchemaType) -> ModelType:
        pass

    @abstractmethod
    async def update(self, *, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        pass

    @abstractmethod
    async def remove(self, *, id: Any) -> ModelType:
        pass
