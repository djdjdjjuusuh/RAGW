from hello_agents import HelloAgentsLLM


def test_hello_agents():
    llm = HelloAgentsLLM(
        model="deepseek-chat",
        base_url="https://api.deepseek.com",
        api_key="sk-2125b05d55c649f587c0b1685ea6c2ae")
    prompt = "请用中文介绍一下 hello-agents。"
    messages = [{"role": "user", "content": prompt}]
    llm_response = llm.think(messages=messages)
    for chunk in llm_response:
        print(chunk, end="")


if __name__ == "__main__":
    test_hello_agents()