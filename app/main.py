import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import cfg
from app.deps import init_milvus_collection
from app.routers import chat, history, upload

app = FastAPI(title="RAG 对话助手", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.allow_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(upload.router, prefix="/api")


@app.on_event("startup")
def startup_event():
    os.makedirs(cfg.UPLOAD_FOLDER, exist_ok=True)
    init_milvus_collection()


@app.get("/")
def root():
    return {"message": "欢迎使用 RAG 对话助手，前往 /docs 查看 API 文档"}
