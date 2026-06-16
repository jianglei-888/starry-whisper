import os
import yaml
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

with open("config/config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
        )
    return _client


def chat_stream(system_prompt: str, history: list):
    """
    流式对话生成器。
    yield 每个 token 的文本片段。
    """
    client = get_client()
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    stream = client.chat.completions.create(
        model=config["llm"]["model"],
        messages=messages,
        temperature=config["llm"]["temperature"],
        max_tokens=config["llm"]["max_tokens"],
        stream=True,
    )

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def chat_sync(system_prompt: str, history: list) -> str:
    """同步对话，返回完整回复。"""
    client = get_client()
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    response = client.chat.completions.create(
        model=config["llm"]["model"],
        messages=messages,
        temperature=config["llm"]["temperature"],
        max_tokens=config["llm"]["max_tokens"],
    )

    return response.choices[0].message.content or ""
