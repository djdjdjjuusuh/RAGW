import json
import time
import asyncio
from uuid import uuid4
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse

from app.config import cfg
from app.deps import get_redis
from app.models import ChatRequest
from app.services import rag, llm

router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    redis = get_redis()
    session_id = request.session_id or str(uuid4())
    redis_key = f"chat:session:{session_id}"

    history_items = await redis.lrange(redis_key, 0, -1)
    history_messages = [json.loads(item) for item in history_items]
    parsed_history = [
        {"role": item["role"], "content": item["content"]}
        for item in history_messages
    ]

    user_entry = {"role": "user", "content": request.message}
    await redis.rpush(redis_key, json.dumps(user_entry))
    await redis.expire(redis_key, cfg.REDIS_TTL_SECONDS)
    await redis.zadd("chat:sessions:updated", {session_id: time.time()})
    await redis.hset("chat:session:previews", session_id, request.message[:120])
    await redis.ltrim(redis_key, -cfg.MAX_HISTORY, -1)

    try:
        # 获取已上传的文件列表
        files = await redis.hgetall("chat:file:meta")
        file_info = []
        for file_id, meta_json in files.items():
            try:
                metadata = json.loads(meta_json)
                if metadata.get("status") == "completed":
                    file_info.append({
                        "file_name": metadata.get("file_name", "未知文件"),
                        "chunk_count": metadata.get("chunk_count", 0)
                    })
            except json.JSONDecodeError:
                continue
        
        # 构建文件信息描述
        file_description = ""
        if file_info:
            file_description = "用户已上传的文件：\n"
            for i, file in enumerate(file_info, 1):
                file_description += f"{i}. {file['file_name']}（{file['chunk_count']}个文本片段）\n"
            file_description += "\n"
        
        # 获取相关上下文
        context = await rag.build_rag_context(request.message)
    except Exception as exc:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    system_prompt = (
        "你是一个温暖友好的问答助手，尽量用简洁而可爱的语气回答用户。\n"
        f"{file_description}"
        "如果以下文档检索到相关内容，请优先参考它们：\n\n" + context
    )

    async def save_assistant_text(assistant_text: str):
        assistant_entry = {"role": "assistant", "content": assistant_text}
        await redis.rpush(redis_key, json.dumps(assistant_entry))
        await redis.expire(redis_key, cfg.REDIS_TTL_SECONDS)
        await redis.hset("chat:session:previews", session_id, assistant_text[:120])
        await redis.zadd("chat:sessions:updated", {session_id: time.time()})

    async def generate_and_save_session_name():
        try:
            full_history = await redis.lrange(redis_key, 0, -1)
            messages = [json.loads(item) for item in full_history]
            if len(messages) >= 2:
                session_name = llm.generate_session_name(messages)
                await redis.hset("chat:session:names", session_id, session_name)
        except Exception:
            pass

    def event_generator():
        assistant_text = ""
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"
        try:
            for chunk in llm.stream_chat_response(system_prompt, parsed_history + [user_entry]):
                assistant_text += chunk
                data = {"type": "delta", "text": chunk}
                yield f"data: {json.dumps(data)}\n\n"
        except Exception as exc:
            error_data = {"type": "error", "message": str(exc)}
            yield f"data: {json.dumps(error_data)}\n\n"
            return

        background_tasks.add_task(save_assistant_text, assistant_text)
        background_tasks.add_task(generate_and_save_session_name)
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
