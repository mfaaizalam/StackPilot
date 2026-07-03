from qdrant_client import QdrantClient
from app.core.config import settings
from qdrant_client.models import Filter,FieldCondition,MatchValue
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct
)
from qdrant_client.models import PayloadSchemaType
from qdrant_client.models import PointIdsList
class QdrantService:
    COLLECTION_NAME = "ai-assistant"

    def __init__(self):
        self.client = QdrantClient(
            url =settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        self.create_collection()
        self.create_payload_indexes()

        # Create Vector Collection
    def create_collection(self):
        collections = self.client.get_collections().collections
        names = [collection.name for collection in collections]

        if self.COLLECTION_NAME not in names:
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=384,
                    distance=Distance.COSINE
                )
            )

            # Create Vector Payload index
    def create_payload_indexes(self):
        try:
            self.client.create_payload_index(
            collection_name=self.COLLECTION_NAME,
            field_name="board_id",
            field_schema=PayloadSchemaType.INTEGER
            )
        except Exception:
            pass

             # Insert Vector
    def insert_vector(
            self,
            embedding:list[float],
            point_id:int,
            payload:dict
        ):
            self.client.upsert(
                collection_name = self.COLLECTION_NAME,
                points=[
                    PointStruct(
                        id =point_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
        # Search Vector 
    def search_vectors(
        self,
        embedding:list[float],  # User ke question ka vector.
        board_id:int,           # Sirf isi board ke vectors search karne hain.
        limit:int = 5           # Top 5 most similar results lao.
        ):
            # Qdrant ko search request bhej rahe ho.
            results = self.client.query_points(
                collection_name=self.COLLECTION_NAME, #kis collection mein search karna hai
                query=embedding, # user ke question ka vector hai.
                query_filter=Filter(
                     must=[
                          FieldCondition(
                               key = "board_id",
                               match =MatchValue(value = board_id)
                          )
                     ]
                ),
                limit=limit
            )
            return results.points
    def delete_vector(
              self,
              point_id:int
    ):
        self.client.delete(
               collection_name=self.COLLECTION_NAME,
                points_selector=PointIdsList(
                points=[point_id]
                )
        )
qdrant =QdrantService()


# QdrantClient
# QdrantClient Qdrant library ki class hai jo hamari application ko Qdrant Cloud se connect karti hai.
# url aur api_key
# url aur api_key constructor ke parameters hain, jin ki madad se Qdrant se connection banta hai.
# self.client
# self.client ek connection object hai jisme Qdrant ka connection store hota hai. Isi object ke through hum get_collections(), create_collection(), search() aur upsert() jaise methods use karte hain.
# get_collections() aur create_collection()
# Ye methods humne nahi banaye; ye QdrantClient class hume pehle se provide karti hai.