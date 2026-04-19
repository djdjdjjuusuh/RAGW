import json
from hello_agents import HelloAgentsLLM
from app.config import cfg


def stream_chat_response(system_prompt: str, messages: list[dict]):
    if not cfg.OPENAI_API_KEY:
        fallback = "未配置 API_KEY，助手无法生成答案。"
        for char in fallback:
            yield char
        return
    
    llm = HelloAgentsLLM(
        model="deepseek-chat",
        base_url="https://api.deepseek.com",
        api_key=cfg.OPENAI_API_KEY
    )
    
    prompt_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        response = llm.think(messages=prompt_messages)
        if response is None:
            yield from "抱歉，助手暂时无法回应。"
            return
        if isinstance(response, str):
            yield from response
            return
        for chunk in response:
            if chunk:
                yield chunk
    except Exception as exc:
        error_msg = f"LLM 调用失败：{exc}"
        for char in error_msg:
            yield char


def generate_session_name(messages: list[dict]) -> str:
    if not cfg.OPENAI_API_KEY:
        return "新对话"

    llm = HelloAgentsLLM(
        model="deepseek-chat",
        base_url="https://api.deepseek.com",
        api_key=cfg.OPENAI_API_KEY
    )

    conversation_text = "\n".join([f"{msg['role']}: {msg['content'][:200]}" for msg in messages[-6:]])

    name_prompt = f"""请根据以下对话内容，生成一个简短的中文会话名称（不超过20个字符），用来概括这个对话的主题。

对话内容：
{conversation_text}

要求：
1. 名称要简洁、有意义，能概括对话主题
2. 不要包含特殊符号，只用中文、英文、数字
3. 不要使用引号
4. 直接返回名称，不要任何解释

示例：
- "Python 编程问题"
- "Git 使用技巧"
- "项目架构讨论"
- "代码审查反馈"

请直接返回名称："""

    try:
        response = llm.think(messages=[{"role": "user", "content": name_prompt}])
        if response and isinstance(response, str):
            name = response.strip()
            if len(name) > 20:
                name = name[:20]
            return name or "新对话"
        return "新对话"
    except Exception:
        return "新对话"
