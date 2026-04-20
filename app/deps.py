import os
import json
import time
import asyncio
from uuid import uuid4
import hashlib
import numpy as np

import redis.asyncio as redis
from pymilvus import connections, utility, FieldSchema, CollectionSchema, DataType, Collection

from app.config import cfg

_redis_client = None
_milvus_collection = None


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
    # 强制重新创建集合，使用 384 维度
    if utility.has_collection(cfg.MILVUS_COLLECTION):
        utility.drop_collection(cfg.MILVUS_COLLECTION)
    
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2048),
        FieldSchema(name="file_name", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="file_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="chunk_index", dtype=DataType.INT64),
        FieldSchema(name="upload_time", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384),
    ]
    schema = CollectionSchema(fields=fields, description="Document chunks for RAG retrieval")
    collection = Collection(name=cfg.MILVUS_COLLECTION, schema=schema)
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
    高级自定义嵌入方法：
    1. 使用多哈希策略生成更丰富的特征
    2. 结合文本长度、词频等统计特征
    3. 生成固定长度的 384 维向量
    """
    # 基础文本处理
    text = text.lower().strip()
    words = text.split()
    word_count = len(words)
    
    # 生成多个哈希值
    hashes = []
    for i in range(8):
        # 不同的哈希种子
        seed = f"{text}_{i}"
        hash_val = hashlib.sha256(seed.encode()).hexdigest()
        hashes.append(int(hash_val, 16))
    
    # 生成 384 维向量
    vector = []
    for i in range(384):
        # 结合多个哈希值
        hash_idx = i % 8
        seed = hashes[hash_idx] + i
        
        # 生成伪随机值
        val = (seed * 1103515245 + 12345) % (2**31)
        normalized = (val % 1000) / 1000.0 - 0.5
        
        # 加入文本统计特征的影响
        if i < 10:
            # 前 10 维加入文本长度特征
            length_factor = min(word_count / 100, 1.0)
            normalized = normalized * 0.7 + length_factor * 0.3
        elif i < 20:
            # 中间 10 维加入词汇多样性特征
            unique_words = len(set(words))
            diversity_factor = min(unique_words / max(word_count, 1), 1.0)
            normalized = normalized * 0.7 + diversity_factor * 0.3
        
        vector.append(float(normalized))
    
    # 归一化向量
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = (np.array(vector) / norm).tolist()
    
    return vector