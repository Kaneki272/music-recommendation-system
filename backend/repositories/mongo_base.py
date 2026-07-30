from typing import Any, List, Optional, TypeVar
from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId
from backend.repositories.base import BaseRepository

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

class MongoBaseRepository(BaseRepository[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def get(self, id: Any) -> Optional[ModelType]:
        document = await self.collection.find_one({"_id": ObjectId(id)})
        return document

    async def get_multi(self, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        cursor = self.collection.find().skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def create(self, *, obj_in: CreateSchemaType) -> ModelType:
        document = obj_in.dict()
        result = await self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def update(self, *, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        update_data = obj_in.dict(exclude_unset=True)
        await self.collection.update_one(
            {"_id": ObjectId(db_obj["_id"])}, {"$set": update_data}
        )
        return await self.get(db_obj["_id"])

    async def remove(self, *, id: Any) -> ModelType:
        obj = await self.get(id)
        await self.collection.delete_one({"_id": ObjectId(id)})
        return obj
