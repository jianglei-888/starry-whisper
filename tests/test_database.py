"""数据库操作测试。"""
import pytest
import pytest_asyncio


class TestInit:
    """数据库初始化。"""

    @pytest.mark.asyncio
    async def test_tables_created(self, temp_db):
        """初始化后所有表都存在。"""
        import aiosqlite
        async with aiosqlite.connect(temp_db.DB_PATH) as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [r[0] for r in await cursor.fetchall()]
        assert "messages" in tables
        assert "memories" in tables
        assert "user_profile" in tables
        assert "companion_profile" in tables
        assert "sessions" in tables

    @pytest.mark.asyncio
    async def test_default_companion_profile(self, temp_db):
        """companion_profile 有默认数据。"""
        profile = await temp_db.get_companion_profile()
        assert profile["nickname"] == "小伴"
        assert profile["personality_type"] == "warm"

    @pytest.mark.asyncio
    async def test_default_user_profile(self, temp_db):
        """user_profile 有默认空数据。"""
        profile = await temp_db.get_user_profile()
        assert profile["nickname"] is None
        assert profile["preferences"] == {}


class TestMessages:
    """消息 CRUD。"""

    @pytest.mark.asyncio
    async def test_save_and_get_messages(self, temp_db):
        """保存消息后能正确读取。"""
        await temp_db.create_session("s1")
        await temp_db.save_message("s1", "user", "你好")
        await temp_db.save_message("s1", "assistant", "嗯，你好")

        msgs = await temp_db.get_recent_messages("s1", limit=10)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "你好"
        assert msgs[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_message_count(self, temp_db):
        """消息计数正确。"""
        await temp_db.create_session("s2")
        for i in range(5):
            await temp_db.save_message("s2", "user", f"msg{i}")

        count = await temp_db.get_session_message_count("s2")
        assert count == 5

    @pytest.mark.asyncio
    async def test_recent_messages_limit(self, temp_db):
        """get_recent_messages 按 limit 截取。"""
        await temp_db.create_session("s3")
        for i in range(25):
            await temp_db.save_message("s3", "user", f"msg{i}")

        msgs = await temp_db.get_recent_messages("s3", limit=20)
        assert len(msgs) == 20
        # 应该是最后 20 条（msg5 ~ msg24）
        assert msgs[0]["content"] == "msg5"

    @pytest.mark.asyncio
    async def test_messages_ordered_by_id(self, temp_db):
        """消息按 ID 顺序返回。"""
        await temp_db.create_session("s4")
        await temp_db.save_message("s4", "user", "第一条")
        await temp_db.save_message("s4", "assistant", "第二条")
        await temp_db.save_message("s4", "user", "第三条")

        msgs = await temp_db.get_recent_messages("s4", limit=10)
        assert [m["content"] for m in msgs] == ["第一条", "第二条", "第三条"]

    @pytest.mark.asyncio
    async def test_clear_all_messages(self, temp_db):
        """清除所有消息和记忆。"""
        await temp_db.create_session("s5")
        await temp_db.save_message("s5", "user", "要被清除")
        await temp_db.save_memory("s5", "摘要", ["情绪"])

        await temp_db.clear_all_messages()

        msgs = await temp_db.get_recent_messages("s5", limit=10)
        assert len(msgs) == 0
        mems = await temp_db.get_recent_memories(5)
        assert len(mems) == 0


class TestMemories:
    """记忆操作。"""

    @pytest.mark.asyncio
    async def test_save_and_get_memories(self, temp_db):
        """保存记忆后能正确读取。"""
        await temp_db.save_memory("s1", "用户说工作压力大", ["压力", "疲惫"])
        await temp_db.save_memory("s1", "用户喜欢猫", ["开心"])

        mems = await temp_db.get_recent_memories(5)
        assert len(mems) == 2
        # 最新的在前（id DESC）
        assert mems[0]["summary"] == "用户喜欢猫"
        assert mems[0]["mood_keywords"] == ["开心"]
        assert mems[1]["summary"] == "用户说工作压力大"
        assert mems[1]["mood_keywords"] == ["压力", "疲惫"]

    @pytest.mark.asyncio
    async def test_memories_limit(self, temp_db):
        """get_recent_memories 按 limit 截取。"""
        for i in range(8):
            await temp_db.save_memory("s1", f"记忆{i}", [])

        mems = await temp_db.get_recent_memories(3)
        assert len(mems) == 3


class TestCompanionProfile:
    """陪伴者配置。"""

    @pytest.mark.asyncio
    async def test_update_nickname(self, temp_db):
        await temp_db.update_companion_profile(nickname="小夜")
        profile = await temp_db.get_companion_profile()
        assert profile["nickname"] == "小夜"

    @pytest.mark.asyncio
    async def test_update_personality(self, temp_db):
        await temp_db.update_companion_profile(personality_type="custom", personality_desc="自定义风格")
        profile = await temp_db.get_companion_profile()
        assert profile["personality_type"] == "custom"
        assert profile["personality_desc"] == "自定义风格"

    @pytest.mark.asyncio
    async def test_update_avatar(self, temp_db):
        await temp_db.update_companion_profile(avatar_path="/avatar/test.png")
        profile = await temp_db.get_companion_profile()
        assert profile["avatar_path"] == "/avatar/test.png"

    @pytest.mark.asyncio
    async def test_update_preserves_other_fields(self, temp_db):
        """只更新部分字段，不影响其他字段。"""
        await temp_db.update_companion_profile(nickname="小夜", avatar_path="/avatar/a.png")
        await temp_db.update_companion_profile(personality_type="quiet")

        profile = await temp_db.get_companion_profile()
        assert profile["nickname"] == "小夜"  # 没被覆盖
        assert profile["personality_type"] == "quiet"


class TestUserProfile:
    """用户画像。"""

    @pytest.mark.asyncio
    async def test_update_nickname(self, temp_db):
        await temp_db.update_user_profile(nickname="小明")
        profile = await temp_db.get_user_profile()
        assert profile["nickname"] == "小明"

    @pytest.mark.asyncio
    async def test_update_preferences(self, temp_db):
        await temp_db.update_user_profile(preferences={"喜欢": "猫", "职业": "程序员"})
        profile = await temp_db.get_user_profile()
        assert profile["preferences"]["喜欢"] == "猫"
