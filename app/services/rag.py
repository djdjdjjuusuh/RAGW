import time
import asyncio
from app.deps import get_milvus_collection, embed_text


async def search_similar_chunks(query: str, top_k: int = 4) -> list[dict]:
    collection = get_milvus_collection()
    # 先 flush 确保数据写入，然后重新加载以包含最新数据
    await asyncio.to_thread(collection.flush)
    await asyncio.to_thread(collection.load)
    query_embedding = await embed_text(query)
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
    results = collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        output_fields=["text", "file_name", "chunk_index", "upload_time"],
    )

    documents = []
    for hits in results:
        for hit in hits:
            if not hasattr(hit, "entity"):
                continue
            entity = hit.entity
            text = entity.get("text") if hasattr(entity, "get") else getattr(entity, "text", "")
            file_name = entity.get("file_name") if hasattr(entity, "get") else getattr(entity, "file_name", "")
            chunk_index = entity.get("chunk_index") if hasattr(entity, "get") else getattr(entity, "chunk_index", 0)
            upload_time = entity.get("upload_time") if hasattr(entity, "get") else getattr(entity, "upload_time", "")
            documents.append(
                {
                    "text": text or "",
                    "file_name": file_name or "",
                    "chunk_index": chunk_index or 0,
                    "upload_time": upload_time or "",
                    "score": float(hit.score),
                }
            )
    return documents


async def build_rag_context(query: str) -> str:
    chunks = await search_similar_chunks(query)
    if not chunks:
        return ""

    context_parts = []
    for chunk in chunks:
        context_parts.append(
            f"文件: {chunk['file_name']} | 段落: {chunk['chunk_index']}\n{chunk['text']}"
        )
    return "\n\n---\n\n".join(context_parts)


async def insert_document_chunks(file_name: str, file_id: str, chunk_texts: list[str]) -> None:
    collection = get_milvus_collection()
    embeddings = []
    for chunk in chunk_texts:
        vector = await embed_text(chunk)
        embeddings.append(vector)

    file_names = [file_name] * len(chunk_texts)
    file_ids = [file_id] * len(chunk_texts)
    chunk_indexes = list(range(len(chunk_texts)))
    upload_times = [time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())] * len(chunk_texts)

    records = [chunk_texts, file_names, file_ids, chunk_indexes, upload_times, embeddings]
    await asyncio.to_thread(collection.insert, records)
    await asyncio.to_thread(collection.flush)


async def delete_file_vectors(file_id: str) -> int:
    collection = get_milvus_collection()
    # Milvus 2.3.0 只能基于主键删除，先搜索找到对应的主键
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
    # 使用一个假的向量进行搜索，只需要匹配 file_id
    import hashlib
    fake_vector = []
    hash_val = int(hashlib.sha256(file_id.encode()).hexdigest(), 16)
    for i in range(1536):
        seed = hash_val + i
        val = (seed * 1103515245 + 12345) % (2**31)
        normalized = (val % 1000) / 1000.0 - 0.5
        fake_vector.append(normalized)
    
    try:
        results = collection.search(
            data=[fake_vector],
            anns_field="embedding",
            param=search_params,
            limit=1000,  # 足够大的数量
            expr=f'file_id == "{file_id}"',
            output_fields=["id"]
        )
        
        # 提取所有匹配的主键 ID
        ids_to_delete = []
        for hits in results:
            for hit in hits:
                if hasattr(hit, "entity"):
                    entity = hit.entity
                    if hasattr(entity, "id"):
                        ids_to_delete.append(entity.id)
                    elif hasattr(entity, "get") and entity.get("id"):
                        ids_to_delete.append(entity.get("id"))
        
        # 基于主键删除
        if ids_to_delete:
            id_expr = f"id in [{','.join(map(str, ids_to_delete))}]"
            await asyncio.to_thread(collection.delete, expr=id_expr)
            await asyncio.to_thread(collection.flush)
    except Exception:
        # 如果搜索失败，跳过向量删除，只删除元数据
        pass
    return 0
