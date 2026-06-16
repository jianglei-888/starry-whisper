"""共享 fixtures：临时数据库、测试客户端、mock LLM。"""
import os
import sys
import asyncio
import tempfile
import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine

# 确保从项目根目录导入
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src import database as db
from src.api import app


# ========== 数据库 fixtures ==========

@pytest_asyncio.fixture
async def temp_db(tmp_path):
    """用临时数据库替换真实数据库，测试结束后自动清理。"""
    db_path = str(tmp_path / "test.db")
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    with patch.object(db, "_engine", test_engine):
        await db.init_db()
        yield db
    await test_engine.dispose()


# ========== HTTP 客户端 fixtures ==========

@pytest_asyncio.fixture
async def client(temp_db):
    """带临时数据库的异步 HTTP 测试客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ========== Mock LLM fixtures ==========

MOCK_REPLY = "嗯，我在听。慢慢说，不着急。"


@pytest.fixture
def mock_llm_stream():
    """Mock 流式 LLM 响应。"""

    class FakeChunk:
        def __init__(self, content):
            self.choices = [MagicMock()]
            self.choices[0].delta = MagicMock()
            self.choices[0].delta.content = content

    chunks = [FakeChunk(c) for c in MOCK_REPLY]

    with patch("src.agent.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = iter(chunks)
        MockOpenAI.return_value = mock_client
        with patch("src.agent._client", mock_client):
            yield mock_client


@pytest.fixture
def mock_llm_sync():
    """Mock 同步 LLM 响应（用于记忆摘要生成）。"""

    class FakeMessage:
        def __init__(self):
            self.content = '{"summary": "测试摘要", "mood_keywords": ["测试"], "key_info": "无"}'

    class FakeResponse:
        def __init__(self):
            self.choices = [MagicMock()]
            self.choices[0].message = FakeMessage()

    with patch("src.agent.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = FakeResponse()
        MockOpenAI.return_value = mock_client
        with patch("src.agent._client", mock_client):
            yield mock_client


@pytest.fixture
def mock_llm_profile():
    """Mock 用户画像更新的 LLM 响应。"""

    class FakeMessage:
        def __init__(self):
            self.content = '{"nickname": "小明", "preferences": {"喜欢": "猫"}}'

    class FakeResponse:
        def __init__(self):
            self.choices = [MagicMock()]
            self.choices[0].message = FakeMessage()

    with patch("src.memory.chat_sync", return_value='{"nickname": "小明", "preferences": {"喜欢": "猫"}}'):
        yield
