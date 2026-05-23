import logging
import time
import threading
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class MilvusService:
    _instance = None
    _client = None
    _initialized = False
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_initialized(self):
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            from pymilvus import MilvusClient

            uri = settings.MILVUS_URI
            token = settings.MILVUS_TOKEN
            import os
            _backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            local_path = os.path.join(_backend_dir, "milvus_data", "milvus.db")

            if uri:
                logger.info(f"连接远程 Milvus: {uri}")
                if token:
                    self._client = MilvusClient(uri=uri, token=token, timeout=30)
                else:
                    self._client = MilvusClient(uri=uri, timeout=30)
            else:
                logger.info(f"使用本地 Milvus: {local_path}")
                try:
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

    def _has_org_field(self) -> bool:
        fields = self._get_schema_field_names()
        return "organization_id" in fields

    def _check_collection_compatible(self, collection_name: str) -> bool:
        from pymilvus import DataType
        desc = self._client.describe_collection(collection_name)
        required_fields = {"id": DataType.VARCHAR, "created_at": DataType.VARCHAR, "version": DataType.INT64}
        existing_fields = {f["name"]: f["type"] for f in desc.get("fields", [])}
        for field_name, field_type in required_fields.items():
            if field_name not in existing_fields:
                return False
            if existing_fields[field_name] != field_type:
                return False
        return True

    def _create_collection_if_not_exists(self):
        from pymilvus import CollectionSchema, FieldSchema, DataType

        collection_name = settings.MILVUS_COLLECTION_NAME
        dim = settings.EMBEDDING_DIM

        if self._client.has_collection(collection_name):
            try:
                if self._check_collection_compatible(collection_name):
                    logger.info(f"Collection '{collection_name}' 已存在且 schema 兼容，加载中...")
                    self._client.load_collection(collection_name)
                    return
                else:
                    logger.error(
                        f"!!! Collection '{collection_name}' schema 不兼容（缺少必要字段）!!!\n"
                        f"!!! 旧数据不会被自动删除，请手动处理: 可以先从 Milvus 导出数据，然后删除 Collection 重建 !!!\n"
                        f"!!! 如果直接删除 Collection，所有已索引的数据将丢失 !!!"
                    )
                    raise RuntimeError(
                        f"Milvus Collection '{collection_name}' schema 不兼容。"
                        f"请手动处理迁移后再启动服务。"
                    )
            except Exception as e:
                logger.error(f"检查 Collection '{collection_name}' 时出错: {e}")
                raise

        logger.info(f"创建 Collection: {collection_name} (dim={dim})")

        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=32),
            FieldSchema(name="version", dtype=DataType.INT64),
            FieldSchema(name="organization_id", dtype=DataType.VARCHAR, max_length=64),
        ]
        schema = CollectionSchema(fields=fields, description="Document chunks collection")

        self._client.create_collection(
            collection_name=collection_name,
            schema=schema,
        )

        try:
            index_params = self._client.prepare_index_params()
            index_params.add_index(
                field_name="vector",
                index_type="HNSW",
                metric_type="COSINE",
                params={
                    "M": settings.MILVUS_HNSW_M,
                    "efConstruction": settings.MILVUS_HNSW_EF_CONSTRUCTION,
                },
            )
            self._client.create_index(
                collection_name=collection_name,
                index_params=index_params,
            )
            logger.info(f"向量索引 HNSW 创建成功 (M={settings.MILVUS_HNSW_M}, efConstruction={settings.MILVUS_HNSW_EF_CONSTRUCTION})")
        except Exception as e:
            logger.warning(f"向量索引创建跳过 (可能已被自动创建): {e}")

        for scalar_field in ["document_id", "chunk_index", "organization_id"]:
            try:
                self._client.create_index(
                    collection_name=collection_name,
                    field_name=scalar_field,
                    index_type="INVERTED",
                )
                logger.info(f"标量索引已创建: {scalar_field}")
            except Exception as e:
                logger.warning(f"标量索引创建跳过 ({scalar_field}): {e}")

        self._client.load_collection(collection_name)
        time.sleep(1)

    def insert(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]], org_id: str | None = None) -> List[str]:
        self._ensure_initialized()

        from datetime import datetime, timezone, timedelta
        CST = timezone(timedelta(hours=8))
        now_iso = datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")

        schema_fields = self._get_schema_field_names()

        data: List[Dict[str, Any]] = []
        chunk_ids: List[str] = []

        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            chunk_id = chunk["metadata"].get("chunk_id", "")
            chunk_ids.append(chunk_id)

            entry = {
                "id": chunk_id,
                "vector": emb,
                "content": chunk["content"],
                "source": chunk["metadata"].get("source", ""),
                "title": chunk["metadata"].get("title", ""),
                "document_id": chunk["metadata"].get("document_id", ""),
                "chunk_index": chunk["metadata"].get("chunk_index", 0),
                "created_at": now_iso,
                "version": chunk["metadata"].get("version", 1),
            }

            if "organization_id" in schema_fields:
                entry["organization_id"] = org_id or ""

            entry.update(self._fill_extra_schema_fields(schema_fields, entry, chunk))

            data.append(entry)

        self._client.insert(collection_name=settings.MILVUS_COLLECTION_NAME, data=data)
        self._client.flush(collection_name=settings.MILVUS_COLLECTION_NAME)
        logger.info(f"成功插入 {len(data)} 条向量到 Milvus")
        return chunk_ids

    def _get_schema_field_names(self) -> set:
        desc = self._client.describe_collection(settings.MILVUS_COLLECTION_NAME)
        return {f["name"] for f in desc.get("fields", [])}

    def _fill_extra_schema_fields(
        self,
        schema_fields: set,
        entry: Dict[str, Any],
        chunk: Dict[str, Any],
    ) -> Dict[str, Any]:
        extra: Dict[str, Any] = {}
        for field_name in schema_fields:
            if field_name in entry or field_name in ("vector",):
                continue
            if field_name == "big_context":
                extra["big_context"] = chunk["content"]
            else:
                extra[field_name] = ""
        return extra

    def delete_by_document_id(self, document_id: str) -> int:
        self._ensure_initialized()

        expr = f'document_id == "{document_id}"'
        try:
            delete_res = self._client.delete(
                collection_name=settings.MILVUS_COLLECTION_NAME,
                filter=expr,
            )
            deleted_count = len(delete_res) if isinstance(delete_res, (list, dict)) else 0
            if hasattr(delete_res, "delete_count"):
                deleted_count = delete_res.delete_count
        except Exception as e:
            logger.warning(f"Milvus delete by expression 失败, 回退到先查后删: {e}")
            ids_to_delete: list[str] = []
            offset = 0
            batch_size = 10000
            while True:
                res = self._client.query(
                    collection_name=settings.MILVUS_COLLECTION_NAME,
                    filter=expr,
                    output_fields=["id"],
                    limit=batch_size,
                    offset=offset,
                )
                if not res:
                    break
                ids_to_delete.extend(r["id"] for r in res)
                offset += batch_size
            if ids_to_delete:
                for i in range(0, len(ids_to_delete), batch_size):
                    batch = ids_to_delete[i:i + batch_size]
                    self._client.delete(collection_name=settings.MILVUS_COLLECTION_NAME, ids=batch)
            deleted_count = len(ids_to_delete)

        logger.info(f"从 Milvus 删除文档 {document_id} 的 {deleted_count} 条向量")
        return deleted_count

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        org_id: str | None = None,
        document_ids: List[str] | None = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_initialized()
        search_start = time.time()

        filter_parts = []
        if self._has_org_field():
            filter_parts.append(f'organization_id == "{org_id or ""}"')
        if document_ids is not None:
            if len(document_ids) == 0:
                return []
            ids_str = ", ".join(f'"{did}"' for did in document_ids)
            filter_parts.append(f"document_id in [{ids_str}]")
        filter_expr = " and ".join(filter_parts) if filter_parts else None

        try:
            results = self._client.search(
                collection_name=settings.MILVUS_COLLECTION_NAME,
                data=[query_embedding],
                limit=top_k,
                output_fields=["content", "source", "title", "document_id", "chunk_index", "created_at", "version"],
                search_params={"ef": settings.MILVUS_HNSW_EF_SEARCH},
                filter=filter_expr,
            )
        except Exception as e:
            logger.error(f"[Milvus 检索] ❌ 检索失败: {type(e).__name__}: {e}")
            return []

        if not results or not results[0]:
            logger.info(f"[Milvus 检索] 无结果返回, 耗时: {time.time() - search_start:.4f}s")
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
                "created_at": entity.get("created_at", ""),
                "version": entity.get("version", 1),
            })

        elapsed = time.time() - search_start
        logger.info(f"[Milvus 检索] 召回数={len(formatted)}, top_k={top_k}, 耗时={elapsed:.4f}s")
        if formatted:
            logger.info(f"[Milvus 检索] 相似度详情 (COSINE distance, 越小越相似):")
            for i, r in enumerate(formatted[:10]):
                similarity = 1.0 - r['score'] / 2.0
                logger.info(f"  #{i+1}: doc_id={r['document_id']}, chunk_index={r['chunk_index']}, "
                           f"distance={r['score']:.6f}, ~similarity={similarity:.4f}, "
                           f"created_at={r.get('created_at', 'N/A')}, "
                           f"title={r.get('title', 'N/A')[:40]}")
        else:
            logger.info(f"[Milvus 检索] 无相关结果")

        return formatted

    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        self._ensure_initialized()

        expr = f'document_id == "{document_id}"'
        res = self._client.query(
            collection_name=settings.MILVUS_COLLECTION_NAME,
            filter=expr,
            output_fields=["id", "content", "chunk_index", "title", "source", "created_at", "version"],
            limit=10000,
        )

        return sorted(res, key=lambda x: x.get("chunk_index", 0)) if res else []

    def get_all_chunks(self) -> List[Dict[str, Any]]:
        self._ensure_initialized()

        all_chunks: List[Dict[str, Any]] = []
        offset = 0
        batch_size = 1000

        output_fields = ["id", "content", "chunk_index", "title", "source", "document_id", "created_at", "version"]
        if self._has_org_field():
            output_fields.append("organization_id")

        while True:
            res = self._client.query(
                collection_name=settings.MILVUS_COLLECTION_NAME,
                filter="id != ''",
                output_fields=output_fields,
                limit=batch_size,
                offset=offset,
            )
            if not res:
                break
            all_chunks.extend(res)
            offset += batch_size

        return all_chunks

    def get_total_count(self) -> int:
        self._ensure_initialized()

        try:
            stats = self._client.get_collection_stats(settings.MILVUS_COLLECTION_NAME)
            return stats.get("row_count", 0)
        except Exception:
            all_chunks = self.get_all_chunks()
            return len(all_chunks)


milvus_service = MilvusService()