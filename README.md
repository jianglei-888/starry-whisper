# AI陪伴助手 v1

深夜陪伴聊天应用，一个有温度的AI伙伴。

## 功能

- **自定义人设**：4种预设风格（温暖倾听/轻松朋友/安静陪伴/知心姐姐）+ 自定义描述
- **头像上传**：上传任何图片作为AI伙伴的头像
- **跨会话记忆**：记住之前的对话内容和你的近况
- **流式输出**：打字机效果，实时显示回复
- **深色主题**：夜间友好，不刺眼
- **桌面应用**：独立窗口，420×700 手机聊天比例

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env`，填入你的 API Key：

```bash
cp .env.example .env
```

编辑 `.env`：
```
LLM_API_KEY=sk-你的API密钥
LLM_BASE_URL=你的BASE_URL
LLM_MODEL=模型
```

### 3. 启动

```bash
python src/main.py
```

## 项目结构

```
├── config/config.yaml    # LLM参数、窗口配置
├── src/
│   ├── main.py           # 入口：pywebview 桌面窗口
│   ├── api.py            # FastAPI 路由
│   ├── agent.py          # LLM 调用（流式）
│   ├── prompts.py        # 人设 prompt 模板
│   ├── memory.py         # 跨会话记忆管理
│   └── database.py       # SQLite 操作
├── frontend/
│   ├── index.html        # 聊天界面
│   ├── style.css         # 深色主题样式
│   └── app.js            # 前端逻辑
└── data/
    ├── companion.db      # SQLite 数据库（自动创建）
    └── avatars/          # 头像文件
```

## 也可以直接浏览器访问

启动后访问 `http://127.0.0.1:8765`，不一定要用桌面窗口。

## 配置说明

`config/config.yaml` 可调整：
- `llm.temperature`：回复随机性（0.8 默认，越高越随机）
- `memory.history_limit`：每次对话取最近多少条消息
- `memory.summary_threshold`：消息超过多少条时生成长期记忆摘要
