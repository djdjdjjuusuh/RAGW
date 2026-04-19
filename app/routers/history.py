import json
from fastapi import APIRouter, HTTPException
from app.deps import get_redis
from app.models import HistoryResponse, SessionPreview

router = APIRouter()


@router.get("/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str):
    redis = get_redis()
    key = f"chat:session:{session_id}"
    items = await redis.lrange(key, 0, -1)
    if items is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = [json.loads(item) for item in items]
    return {"session_id": session_id, "messages": messages}


@router.get("/sessions", response_model=list[SessionPreview])
async def get_sessions():
    redis = get_redis()
    sessions_with_scores = await redis.zrevrange("chat:sessions:updated", 0, -1, withscores=True)
    if not sessions_with_scores:
        return []

    session_ids = [session for session, _ in sessions_with_scores]
    previews = await redis.hmget("chat:session:previews", *session_ids)
    names = await redis.hmget("chat:session:names", *session_ids)
    sessions = []
    for idx, (session_id, score) in enumerate(sessions_with_scores):
        sessions.append(
            {
                "session_id": session_id,
                "preview": previews[idx] or "新对话",
                "name": names[idx] or "新对话",
                "updated_at": float(score) if score else 0,
            }
        )
    return sessions


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    redis = get_redis()
    session_key = f"chat:session:{session_id}"

    await redis.delete(session_key)
    await redis.zrem("chat:sessions:updated", session_id)
    await redis.hdel("chat:session:previews", session_id)
    await redis.hdel("chat:session:names", session_id)

    return {"status": "deleted", "session_id": session_id}
