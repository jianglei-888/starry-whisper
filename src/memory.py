import asyncio
import yaml
from src import database as db
from src.agent import chat_sync

with open("config/config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

SUMMARY_PROMPT = """请对以下对话生成摘要，200字以内中文，提取情绪标签。
对话：
{conversation}
直接返回JSON：{{"summary":"摘要","mood_keywords":["情绪1"]}}"""

PROFILE_UPDATE_PROMPT = """根据以下对话，提取用户的关键信息。只提取明确提到的信息，不要推测。

当前用户画像：
{current_profile}

最新对话：
{conversation}

请用JSON格式返回更新后的信息（只包含需要更新的字段）：
{{"nickname": "用户提到的名字（如有）", "preferences": {{"key": "value"}}}}"""

import json
import re


def _extract_json(text: str) -> dict:
    """从 LLM 回复中提取 JSON。"""
    # 尝试找 JSON 块
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


async def generate_summary(session_id: str) -> dict | None:
    """对话结束时生成摘要（长期记忆）。"""
    threshold = config["memory"]["summary_threshold"]
    count = await db.get_session_message_count(session_id)
    if count < threshold:
        return None

    messages = await db.get_session_messages(session_id)
    conversation = "\n".join(f"{m['role']}: {m['content']}" for m in messages)

    prompt = SUMMARY_PROMPT.format(conversation=conversation)

    # 重试最多 2 次，应对 LLM 偶尔返回空内容
    data = {}
    for attempt in range(2):
        result = await asyncio.to_thread(chat_sync, prompt, [])
        data = _extract_json(result)
        if data:
            break
        print(f"[memory] 摘要生成为空，重试 {attempt + 1}/2，session={session_id[:8]}")

    if not data:
        print(f"[memory] 摘要生成失败，session={session_id[:8]}")
        return None

    summary = data.get("summary", "")
    moods = data.get("mood_keywords", [])

    if summary:
        await db.save_memory(session_id, summary, moods)

    return data


async def update_user_profile_from_chat(session_id: str):
    """从最新对话中更新用户画像。"""
    messages = await db.get_session_messages(session_id)
    if len(messages) < 3:
        return

    conversation = "\n".join(f"{m['role']}: {m['content']}" for m in messages[-10:])
    current_profile = await db.get_user_profile()

    prompt = PROFILE_UPDATE_PROMPT.format(
        current_profile=json.dumps(current_profile, ensure_ascii=False),
        conversation=conversation,
    )
    result = await asyncio.to_thread(chat_sync, prompt, [])

    data = _extract_json(result)
    if not data:
        return

    nickname = data.get("nickname")
    preferences = data.get("preferences")
    await db.update_user_profile(nickname=nickname, preferences=preferences)


async def get_context_for_prompt() -> tuple[list, dict]:
    """获取记忆上下文，用于构建 system prompt。"""
    limit = config["memory"]["memory_context_count"]
    memories = await db.get_recent_memories(limit)
    user_profile = await db.get_user_profile()
    return memories, user_profile
