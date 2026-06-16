import os
import uuid
import json
import yaml
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src import database as db
from src.agent import chat_stream, chat_sync
from src.prompts import build_system_prompt, PERSONALITY_PRESETS
from src.memory import generate_summary, update_user_profile_from_chat, get_context_for_prompt

with open("config/config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

app = FastAPI(title="AI陪伴助手")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
AVATAR_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "avatars")


# ========== 页面 ==========

@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join(FRONTEND_DIR, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/style.css")
async def css():
    return FileResponse(os.path.join(FRONTEND_DIR, "style.css"), media_type="text/css")


@app.get("/app.js")
async def js():
    return FileResponse(os.path.join(FRONTEND_DIR, "app.js"), media_type="application/javascript")


@app.get("/avatar/{filename}")
async def get_avatar(filename: str):
    path = os.path.join(AVATAR_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path)
    return FileResponse(os.path.join(FRONTEND_DIR, "default_avatar.svg"))


# ========== 聊天 API ==========

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


@app.post("/api/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    await db.create_session(session_id)
    await db.save_message(session_id, "user", req.message)

    # 构建上下文
    history = await db.get_recent_messages(session_id, config["memory"]["history_limit"])
    # 去掉最后一条（就是刚保存的用户消息，会在 history 末尾）
    if history and history[-1]["role"] == "user":
        history = history[:-1]

    memories, user_profile = await get_context_for_prompt()
    companion = await db.get_companion_profile()

    system_prompt = build_system_prompt(
        nickname=companion["nickname"],
        personality_type=companion["personality_type"],
        personality_desc=companion["personality_desc"],
        memories=memories,
        user_profile=user_profile,
    )

    # 构建完整历史（含当前消息）
    full_history = history + [{"role": "user", "content": req.message}]

    async def generate():
        full_reply = []
        try:
            for token in chat_stream(system_prompt, full_history):
                full_reply.append(token)
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

        # 保存 AI 回复
        reply_text = "".join(full_reply)
        if reply_text:
            await db.save_message(session_id, "assistant", reply_text)

        yield f"data: {json.dumps({'done': True, 'session_id': session_id}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/messages/{session_id}")
async def get_messages(session_id: str):
    """获取指定会话的所有消息。"""
    msgs = await db.get_session_messages(session_id)
    for msg in msgs:
        msg["created_at"] = msg["created_at"] + "Z"
    return {"messages": msgs, "session_id": session_id}


@app.get("/api/sessions")
async def list_sessions():
    """列出最近的会话，附带首条用户消息作为预览。"""
    sessions = await db.get_sessions_list()
    return {"sessions": sessions}


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    await db.delete_session(session_id)
    return {"status": "ok"}


@app.post("/api/session/end")
async def end_session(session_id: str = Form(...)):
    """会话结束时生成摘要和更新用户画像。"""
    await generate_summary(session_id)
    await update_user_profile_from_chat(session_id)
    return {"status": "ok"}


# ========== 设置 API ==========

@app.get("/api/settings")
async def get_settings():
    companion = await db.get_companion_profile()
    user = await db.get_user_profile()
    return {
        "companion": companion,
        "user": user,
        "presets": {k: v["name"] for k, v in PERSONALITY_PRESETS.items()},
    }


class SettingsRequest(BaseModel):
    nickname: str | None = None
    personality_type: str | None = None
    personality_desc: str | None = None


@app.post("/api/settings")
async def update_settings(req: SettingsRequest):
    await db.update_companion_profile(
        nickname=req.nickname,
        personality_type=req.personality_type,
        personality_desc=req.personality_desc,
    )
    return {"status": "ok"}


@app.post("/api/avatar")
async def upload_avatar(file: UploadFile = File(...)):
    os.makedirs(AVATAR_DIR, exist_ok=True)

    # 清理旧头像
    companion = await db.get_companion_profile()
    if companion.get("avatar_path") and companion["avatar_path"].startswith("/avatar/"):
        old_filename = companion["avatar_path"].replace("/avatar/", "")
        old_path = os.path.join(AVATAR_DIR, old_filename)
        if os.path.exists(old_path):
            os.remove(old_path)

    # 保存新头像
    ext = os.path.splitext(file.filename)[1] or ".png"
    filename = f"avatar_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    filepath = os.path.join(AVATAR_DIR, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    avatar_url = f"/avatar/{filename}"
    await db.update_companion_profile(avatar_path=avatar_url)

    return {"status": "ok", "avatar_url": avatar_url}


@app.post("/api/memory/clear")
async def clear_memory():
    await db.clear_all_messages()
    return {"status": "ok"}


# ========== 初始化 ==========

@app.on_event("startup")
async def startup():
    await db.init_db()

