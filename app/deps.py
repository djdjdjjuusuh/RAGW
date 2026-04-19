import os
import json
import time
import asyncio
from uuid import uuid4

import redis.asyncio as redis
from pymilvus import connections, utility, FieldSchema, CollectionSchema, DataType, Collection

from app.config import cfg

_redis_client = None
_milvus_collection = None
_embed_model = None


def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(cfg.REDIS_URL, decode_responses=True)
    return _redis_client


def _connect_milvus_with_retry(max_attempts: int = 10, delay_seconds: int = 3):
    for attempt in range(1, max_attempts + 1):
        try:
            connections.connect(host=cfg.MILVUS_HOST, port=cfg.MILVUS_PORT)
            return
        except Exception as exc:
            if attempt == max_attempts:
                raise
            time.sleep(delay_seconds)


def init_milvus_collection():
    global _milvus_collection
    if _milvus_collection is not None:
        return _milvus_collection

    _connect_milvus_with_retry()
    if not utility.has_collection(cfg.MILVUS_COLLECTION):
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2048),
            FieldSchema(name="file_name", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="file_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(name="upload_time", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
        ]
        schema = CollectionSchema(fields=fields, description="Document chunks for RAG retrieval")
        collection = Collection(name=cfg.MILVUS_COLLECTION, schema=schema)
        index_params = {"index_type": "IVF_FLAT", "metric_type": "COSINE", "params": {"nlist": 128}}
        collection.create_index(field_name="embedding", index_params=index_params)
        collection.load()
    else:
        collection = Collection(cfg.MILVUS_COLLECTION)
        if not collection.has_index(index_name="embedding"):
            index_params = {"index_type": "IVF_FLAT", "metric_type": "COSINE", "params": {"nlist": 128}}
            collection.create_index(field_name="embedding", index_params=index_params)
        collection.load()

    _milvus_collection = collection
    return _milvus_collection


def get_milvus_collection():
    if _milvus_collection is None:
        return init_milvus_collection()
    return _milvus_collection


async def embed_text(text: str):
    """
    生成简单的哈希向量表示（不使用 embedding 模型）。
    使用文本内容的哈希值生成固定维度的向量。
    """
    import hashlib
    hash_val = int(hashlib.sha256(text.encode()).hexdigest(), 16)
    # 生成 1536 维向量（与 OpenAI embedding 兼容）
    vector = []
    for i in range(1536):
        seed = hash_val + i
        # 使用简单的伪随机生成器
        val = (seed * 1103515245 + 12345) % (2**31)
        normalized = (val % 1000) / 1000.0 - 0.5
        vector.append(normalized)
    return vector
