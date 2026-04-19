# 基于 RAG 的大模型对话网站

这是一个基于 FastAPI 后端、React + TypeScript 前端、Redis 缓存、Milvus 向量数据库的 RAG 对话网站 Demo。

## 一键启动
1. 复制 `.env.example` 为 `.env`，并填写 `OPENAI_API_KEY`：
   ```bash
   cp .env.example .env
   ```
2. 启动所有服务：
   ```bash
   docker-compose up --build
   ```
3. 等待服务启动后访问：
   - 前端：`http://localhost:4173`
   - 后端 API：`http://localhost:8000/docs`

## 项目结构
- `app/`：FastAPI 后端源码
- `frontend/`：React + TypeScript 前端源码
- `docker-compose.yml`：包含 Redis、Milvus、etcd、MinIO、后端、前端

## 核心功能
- 对话界面支持流式输出
- 会话历史保存在 Redis 中
- 文件上传后自动解析并建立 Milvus 向量索引
- RAG 检索增强，调用大模型生成回答

## 运行说明
- `OPENAI_API_KEY` 环境变量必须配置；若要使用 DeepSeek 模型，设置 `OPENAI_MODEL=deepseek`
- 文件上传支持 `.txt`, `.pdf`, `.docx`
- 侧边栏可新建会话、切换会话

## 常见命令
- 后端本地开发：
  ```bash
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```
- 前端本地开发：
  ```bash
  cd frontend
  npm install
  npm run dev -- --host 0.0.0.0
  ```

## 注意
- Milvus 存储字段包含 `id`, `text`, `embedding`, `file_name`, `chunk_index`, `upload_time`, `file_id`
- Redis 会话历史保持最近 50 条，TTL 7 天
