import logging
import time
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class MilvusService:
    _instance = None
    _client = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_initialized(self):
        if self._initialized:
            return

        from pymilvus import MilvusClient

        uri = settings.MILVUS_URI
        token = settings.MILVUS_TOKEN
        local_path = "./milvus_data/milvus.db"

        if uri:
            logger.info(f"连接远程 Milvus: {uri}")
            if token:
                self._client = MilvusClient(uri=uri, token=token, timeout=30)
            else:
                self._client = MilvusClient(uri=uri, timeout=30)
        else:
            logger.info(f"使用本地 Milvus: {local_path}")
            try:
                import os
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                self._client = MilvusClient(local_path)
            except Exception as e:
                raise RuntimeError(
                    "本地 Milvus 不可用，请在 .env 中配置 MILVUS_URI 连接远程 Milvus "
                    "(Zilliz Cloud 免费注册: https://cloud.zilliz.com)\n"
                    f"原始错误: {e}"
                )

        self._create_collection_if_not_exists()
        self._initialized = True

    def _create_collection_if_not_exists(self):
        from pymilvus import CollectionSchema, FieldSchema, DataType

        collection_name = settings.MILVUS_COLLECTION_NAME
        dim = settings.EMBEDDING_DIM

        if self._client.has_collection(collection_name):
            try:
                desc = self._client.describe_collection(collection_name)
                id_field = next((f for f in desc.get("fields", []) if f.get("name") == "id"), None)
                if id_field and id_field.get("type") == "VARCHAR":
                    logger.info(f"Collection '{collection_name}' 已存在且 schema 正确，加载中...")
                    self._client.load_collection(collection_name)
                    return
                else:
                    logger.warning(
                        f"Collection '{collection_name}' 的 id 字段类型不兼容 (当前为 {id_field.get('type') if id_field else 'N/A'}，需要 VARCHAR)。"
                        f"正在删除旧 Collection 并重新创建..."
                    )
                    self._client.drop_collection(collection_name)
            except Exception:
                logger.warning(f"无法获取 Collection '{collection_name}' 信息，尝试删除重建")
                try:
                    self._client.drop_collection(collection_name)
                except Exception:
                    pass

        logger.info(f"创建 Collection: {collection_name} (dim={dim})")

        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
        ]
        schema = CollectionSchema(fields=fields, description="Document chunks collection")

        self._client.create_collection(
            collection_name=collection_name,
            schema=schema,
        )

        try:
            index_params = self._client.prepare_index_params()
            index_params.add_index(field_name="vector", index_type="IVF_FLAT", metric_type="COSINE", params={"nlist": 128})
            self._client.create_index(
                collection_name=collection_name,
                index_params=index_params,
            )
        except Exception as e:
            logger.warning(f"索引创建跳过 (可能已被自动创建): {e}")

        self._client.load_collection(collection_name)
        time.sleep(1)

    def insert(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> List[str]:
        self._ensure_initialized()

        data: List[Dict[str, Any]] = []
        chunk_ids: List[str] = []

        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            chunk_id = chunk["metadata"].get("chunk_id", "")
            chunk_ids.append(chunk_id)

            data.append({
                "id": chunk_id,
                "vector": emb,
                "content": chunk["content"],
                "source": chunk["metadata"].get("source", ""),
                "title": chunk["metadata"].get("title", ""),
                "document_id": chunk["metadata"].get("document_id", ""),
                "chunk_index": chunk["metadata"].get("chunk_index", 0),
            })

        self._client.insert(collection_name=settings.MILVUS_COLLECTION_NAME, data=data)
        logger.info(f"成功插入 {len(data)} 条向量到 Milvus")
        return chunk_ids

    def delete_by_document_id(self, document_id: str) -> int:
        self._ensure_initialized()

        expr = f'document_id == "{document_id}"'
        res = self._client.query(
            collection_name=settings.MILVUS_COLLECTION_NAME,
            filter=expr,
            output_fields=["id"],
            limit=10000,
        )

        if not res:
            return 0

        ids_to_delete = [r["id"] for r in res]
        self._client.delete(collection_name=settings.MILVUS_COLLECTION_NAME, ids=ids_to_delete)
        logger.info(f"从 Milvus 删除文档 {document_id} 的 {len(ids_to_delete)} 条向量")
        return len(ids_to_delete)

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        self._ensure_initialized()

        results = self._client.search(
            collection_name=settings.MILVUS_COLLECTION_NAME,
            data=[query_embedding],
            limit=top_k,
            output_fields=["content", "source", "title", "document_id", "chunk_index"],
        )

        if not results or not results[0]:
            return []

        formatted: List[Dict[str, Any]] = []
        for hit in results[0]:
            entity = hit.get("entity", {})
            formatted.append({
                "content": entity.get("content", ""),
                "source": entity.get("source", ""),
                "title": entity.get("title", ""),
                "document_id": entity.get("document_id", ""),
                "chunk_index": entity.get("chunk_index", 0),
                "score": hit.get("distance", 0),
            })

        return formatted

    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        self._ensure_initialized()

        expr = f'document_id == "{document_id}"'
        res = self._client.query(
            collection_name=settings.MILVUS_COLLECTION_NAME,
            filter=expr,
            output_fields=["id", "content", "chunk_index", "title", "source"],
            limit=10000,
        )

        return sorted(res, key=lambda x: x.get("chunk_index", 0)) if res else []


milvus_service = MilvusService()
