from typing import Optional
from motor.motor_asyncio import AsyncIOMotorCollection
from backend.repositories.mongo_base import MongoBaseRepository
from backend.models.mongo.tracking import UserInteraction

class InteractionRepository(MongoBaseRepository[UserInteraction, UserInteraction, UserInteraction]):
    def __init__(self, collection: AsyncIOMotorCollection):
        super().__init__(collection)

    async def get_interaction_count(self, user_id: str) -> int:
        """
        Gets the total historical interaction count for a specific user.
        """
        return await self.collection.count_documents({"user_id": user_id})
