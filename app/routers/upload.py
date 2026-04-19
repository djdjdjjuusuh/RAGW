import json
import shutil
import asyncio
import time
from uuid import uuid4
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from app.config import cfg
from app.deps import get_redis
from app.services import rag
from app.utils.file_parser import parse_file, split_text

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    if background_tasks is None:
        raise HTTPException(status_code=400, detail="需要后台任务处理")

    upload_folder = Path(cfg.UPLOAD_FOLDER)
    upload_folder.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid4())
    filename = file.filename
    target_path = upload_folder / f"{file_id}_{filename}"

    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    redis = get_redis()
    await redis.hset(
        "chat:file:meta",
        file_id,
        json.dumps({"file_name": filename, "status": "processing", "upload_time": str(time.time())}),
    )

    background_tasks.add_task(process_upload_task, str(target_path), filename, file_id)
    return {"file_id": file_id, "status": "processing", "message": "文件已接收，正在后台解析与索引。"}


async def process_upload_task(file_path: str, file_name: str, file_id: str):
    redis = get_redis()
    try:
        text = await asyncio.to_thread(parse_file, file_path)
        chunks = split_text(text, chunk_size=cfg.CHUNK_SIZE, max_chars=2048)
        if not chunks:
            raise ValueError("未提取到有效文本内容。")

        await rag.insert_document_chunks(file_name, file_id, chunks)
        await redis.hset(
            "chat:file:meta",
            file_id,
            json.dumps({"file_name": file_name, "status": "completed", "chunk_count": len(chunks)}),
        )
    except Exception as exc:
        await redis.hset(
            "chat:file:meta",
            file_id,
            json.dumps({"file_name": file_name, "status": "failed", "error": str(exc)}),
        )


@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    redis = get_redis()
    meta = await redis.hget("chat:file:meta", file_id)
    if not meta:
        raise HTTPException(status_code=404, detail="文件不存在或已删除")

    await rag.delete_file_vectors(file_id)
    await redis.hdel("chat:file:meta", file_id)
    return {"file_id": file_id, "status": "deleted"}


@router.get("/upload-status/{file_id}")
async def get_upload_status(file_id: str):
    redis = get_redis()
    meta = await redis.hget("chat:file:meta", file_id)
    if not meta:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        metadata = json.loads(meta)
        return {
            "file_id": file_id,
            "status": metadata.get("status", "unknown"),
            "chunk_count": metadata.get("chunk_count", 0),
            "error": metadata.get("error", None),
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="元数据解析失败")


@router.get("/files")
async def get_files():
    redis = get_redis()
    all_files = await redis.hgetall("chat:file:meta")
    files = []
    for file_id, meta_json in all_files.items():
        try:
            metadata = json.loads(meta_json)
            files.append({
                "file_id": file_id,
                "file_name": metadata.get("file_name", "未知文件"),
                "status": metadata.get("status", "unknown"),
                "chunk_count": metadata.get("chunk_count", 0),
                "upload_time": metadata.get("upload_time", ""),
                "error": metadata.get("error", None),
            })
        except json.JSONDecodeError:
            continue
    files.sort(key=lambda x: x.get("upload_time", ""), reverse=True)
    return files