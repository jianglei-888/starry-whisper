"""API 接口测试。"""
import io
import json
import pytest
import pytest_asyncio


class TestHealthAndPages:
    """页面和基础路由。"""

    @pytest.mark.asyncio
    async def test_index_page(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "星夜私语" in resp.text

    @pytest.mark.asyncio
    async def test_css(self, client):
        resp = await client.get("/style.css")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_js(self, client):
        resp = await client.get("/app.js")
        assert resp.status_code == 200


class TestSettings:
    """设置接口。"""

    @pytest.mark.asyncio
    async def test_get_settings(self, client):
        resp = await client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "companion" in data
        assert "user" in data
        assert "presets" in data
        assert data["companion"]["nickname"] == "小伴"

    @pytest.mark.asyncio
    async def test_update_nickname(self, client):
        resp = await client.post("/api/settings", json={"nickname": "小夜"})
        assert resp.status_code == 200

        resp = await client.get("/api/settings")
        assert resp.json()["companion"]["nickname"] == "小夜"

    @pytest.mark.asyncio
    async def test_update_personality(self, client):
        resp = await client.post("/api/settings", json={
            "personality_type": "custom",
            "personality_desc": "你是一个爱讲冷笑话的人"
        })
        assert resp.status_code == 200

        resp = await client.get("/api/settings")
        data = resp.json()
        assert data["companion"]["personality_type"] == "custom"
        assert "冷笑话" in data["companion"]["personality_desc"]


class TestAvatar:
    """头像上传。"""

    @pytest.mark.asyncio
    async def test_upload_avatar(self, client):
        # 最小合法 PNG
        png_data = (
            b'\x89PNG\r\n\x1a\n'
            b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde'
            b'\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01'
            b'\x00\x05\x18\xd8N'
            b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
        )
        resp = await client.post(
            "/api/avatar",
            files={"file": ("test.png", png_data, "image/png")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["avatar_url"].startswith("/avatar/")
        assert data["avatar_url"].endswith(".png")

    @pytest.mark.asyncio
    async def test_avatar_appears_in_settings(self, client):
        png_data = (
            b'\x89PNG\r\n\x1a\n'
            b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde'
            b'\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01'
            b'\x00\x05\x18\xd8N'
            b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
        )
        await client.post("/api/avatar", files={"file": ("test.png", png_data, "image/png")})

        resp = await client.get("/api/settings")
        assert resp.json()["companion"]["avatar_path"] is not None

    @pytest.mark.asyncio
    async def test_avatar_endpoint_returns_file(self, client):
        png_data = (
            b'\x89PNG\r\n\x1a\n'
            b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde'
            b'\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01'
            b'\x00\x05\x18\xd8N'
            b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
        )
        upload_resp = await client.post(
            "/api/avatar",
            files={"file": ("test.png", png_data, "image/png")},
        )
        avatar_url = upload_resp.json()["avatar_url"]

        resp = await client.get(avatar_url)
        assert resp.status_code == 200
        assert len(resp.content) > 0

    @pytest.mark.asyncio
    async def test_missing_avatar_returns_default(self, client):
        resp = await client.get("/avatar/nonexistent.png")
        assert resp.status_code == 200  # 返回默认 SVG


class TestMemoryClear:
    """清除记忆。"""

    @pytest.mark.asyncio
    async def test_clear_memory(self, client, temp_db):
        await temp_db.create_session("test")
        await temp_db.save_message("test", "user", "消息")

        resp = await client.post("/api/memory/clear")
        assert resp.status_code == 200

        msgs = await temp_db.get_recent_messages("test", 10)
        assert len(msgs) == 0


class TestSessionEndpoints:
    """会话相关接口。"""

    @pytest.mark.asyncio
    async def test_get_messages_empty_session(self, client):
        resp = await client.get("/api/messages/nonexistent")
        assert resp.status_code == 200
        assert resp.json()["messages"] == []

    @pytest.mark.asyncio
    async def test_get_messages(self, client, temp_db):
        await temp_db.create_session("s1")
        await temp_db.save_message("s1", "user", "你好")
        await temp_db.save_message("s1", "assistant", "嗯你好")

        resp = await client.get("/api/messages/s1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["messages"]) == 2
        assert data["messages"][0]["content"] == "你好"
        assert data["messages"][1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_list_sessions(self, client, temp_db):
        await temp_db.create_session("s1")
        await temp_db.save_message("s1", "user", "msg1")
        await temp_db.create_session("s2")
        await temp_db.save_message("s2", "user", "msg2")

        resp = await client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sessions"]) == 2
        assert data["sessions"][0]["msg_count"] >= 1


class TestChat:
    """聊天接口（需要 mock LLM）。"""

    @pytest.mark.asyncio
    async def test_chat_returns_stream(self, client, mock_llm_stream):
        resp = await client.post(
            "/api/chat",
            json={"message": "你好"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    @pytest.mark.asyncio
    async def test_chat_stream_contains_tokens(self, client, mock_llm_stream):
        resp = await client.post(
            "/api/chat",
            json={"message": "你好"},
        )
        body = resp.text
        lines = [l for l in body.split("\n") if l.startswith("data: ")]
        assert len(lines) > 0

        # 最后一条应该包含 done 和 session_id
        last_data = json.loads(lines[-1][6:])
        assert last_data["done"] is True
        assert "session_id" in last_data

    @pytest.mark.asyncio
    async def test_chat_saves_messages(self, client, mock_llm_stream, temp_db):
        resp = await client.post("/api/chat", json={"message": "测试消息"})
        body = resp.text
        lines = [l for l in body.split("\n") if l.startswith("data: ")]
        last_data = json.loads(lines[-1][6:])
        session_id = last_data["session_id"]

        msgs = await temp_db.get_recent_messages(session_id, 10)
        assert any(m["content"] == "测试消息" for m in msgs)
        # AI 回复也应保存
        assert any(m["role"] == "assistant" for m in msgs)

    @pytest.mark.asyncio
    async def test_chat_reuses_session(self, client, mock_llm_stream):
        # 第一次
        resp1 = await client.post("/api/chat", json={"message": "第一条"})
        sid1 = json.loads([l for l in resp1.text.split("\n") if l.startswith("data: ")][-1][6:])["session_id"]

        # 第二次，带 session_id
        resp2 = await client.post("/api/chat", json={"message": "第二条", "session_id": sid1})
        sid2 = json.loads([l for l in resp2.text.split("\n") if l.startswith("data: ")][-1][6:])["session_id"]

        assert sid1 == sid2

    @pytest.mark.asyncio
    async def test_chat_creates_new_session_each_time(self, client, mock_llm_stream):
        resp1 = await client.post("/api/chat", json={"message": "第一条"})
        resp2 = await client.post("/api/chat", json={"message": "第二条"})

        sid1 = json.loads([l for l in resp1.text.split("\n") if l.startswith("data: ")][-1][6:])["session_id"]
        sid2 = json.loads([l for l in resp2.text.split("\n") if l.startswith("data: ")][-1][6:])["session_id"]

        assert sid1 != sid2
