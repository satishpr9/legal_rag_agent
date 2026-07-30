import httpx
import uuid
from typing import List, Dict, Any, Optional
from fastapi import HTTPException

class QdrantService:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.base_url = f"http://{host}:{port}"
        
    async def _request(self, method: str, path: str, json_data: Any = None) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}{path}"
            try:
                if method == "GET":
                    response = await client.get(url, timeout=10.0)
                elif method == "PUT":
                    response = await client.put(url, json=json_data, timeout=30.0)
                elif method == "POST":
                    response = await client.post(url, json=json_data, timeout=30.0)
                elif method == "DELETE":
                    response = await client.delete(url, timeout=10.0)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                # We handle 404 manually for check-existence logic
                if response.status_code == 404:
                    return {"status": "not_found"}
                    
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Qdrant API error: {str(e)}")

    async def collection_exists(self, collection_name: str) -> bool:
        res = await self._request("GET", f"/collections/{collection_name}")
        return res.get("status") != "not_found"

    async def create_collection(self, collection_name: str, vector_size: int = 768) -> bool:
        payload = {
            "vectors": {
                "size": vector_size,
                "distance": "Cosine"
            }
        }
        res = await self._request("PUT", f"/collections/{collection_name}", payload)
        return res.get("status") == "ok" or res.get("result") is True

    async def delete_collection(self, collection_name: str) -> bool:
        res = await self._request("DELETE", f"/collections/{collection_name}")
        return res.get("status") == "ok" or res.get("result") is True

    async def upsert_points(self, collection_name: str, points: List[Dict[str, Any]]) -> bool:
        """
        points list format:
        [
            {
                "id": str(uuid.uuid4()),
                "vector": [0.1, 0.2, ...],
                "payload": {"text": "chunk text", "metadata": {...}}
            }
        ]
        """
        # Ensure collection exists before upserting
        exists = await self.collection_exists(collection_name)
        if not exists:
            vector_size = len(points[0]["vector"]) if points else 768
            await self.create_collection(collection_name, vector_size=vector_size)
            
        payload = {"points": points}
        res = await self._request("PUT", f"/collections/{collection_name}/points?wait=true", payload)
        return res.get("status") == "ok"

    async def search_points(
        self, collection_name: str, query_vector: List[float], limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Searches for similar vectors. Returns results containing payload and similarity score.
        """
        exists = await self.collection_exists(collection_name)
        if not exists:
            return []
            
        payload = {
            "vector": query_vector,
            "limit": limit,
            "with_payload": True,
            "with_vector": False
        }
        res = await self._request("POST", f"/collections/{collection_name}/points/search", payload)
        return res.get("result", [])

    async def delete_document_points(self, collection_name: str, document_id: int) -> bool:
        exists = await self.collection_exists(collection_name)
        if not exists:
            return True
        payload = {
            "filter": {
                "must": [
                    {
                        "key": "document_id",
                        "match": {
                            "value": document_id
                        }
                    }
                ]
            }
        }
        res = await self._request("POST", f"/collections/{collection_name}/points/delete?wait=true", payload)
        return res.get("status") == "ok"
