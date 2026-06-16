"""Prompt 生成测试。"""
import pytest
from src.prompts import build_system_prompt, PERSONALITY_PRESETS


class TestPersonalityPresets:
    """预设风格。"""

    def test_all_presets_exist(self):
        assert set(PERSONALITY_PRESETS.keys()) == {"warm", "playful", "quiet", "sister"}

    def test_preset_has_required_fields(self):
        for key, preset in PERSONALITY_PRESETS.items():
            assert "name" in preset, f"{key} missing 'name'"
            assert "desc" in preset, f"{key} missing 'desc'"
            assert len(preset["desc"]) > 50, f"{key} desc too short"


class TestBuildSystemPrompt:
    """system prompt 组装。"""

    def test_basic_prompt(self):
        prompt = build_system_prompt(nickname="小伴", personality_type="warm")
        assert "小伴" in prompt
        assert "倾听" in prompt or "温暖" in prompt
        assert "深夜" in prompt

    def test_playful_style(self):
        prompt = build_system_prompt(personality_type="playful")
        assert "玩笑" in prompt or "损友" in prompt or "有趣" in prompt

    def test_quiet_style(self):
        prompt = build_system_prompt(personality_type="quiet")
        assert "安静" in prompt or "话不多" in prompt or "简短" in prompt

    def test_custom_style(self):
        prompt = build_system_prompt(
            personality_type="custom",
            personality_desc="你是一个搞笑的人，喜欢讲冷笑话"
        )
        assert "搞笑" in prompt
        assert "冷笑话" in prompt

    def test_custom_without_desc_falls_back(self):
        """custom 但没给 desc，应回退到 warm。"""
        prompt = build_system_prompt(personality_type="custom", personality_desc=None)
        # 应该回退到 warm
        assert "温暖" in prompt or "倾听" in prompt

    def test_unknown_type_falls_back(self):
        """未知类型应回退到 warm。"""
        prompt = build_system_prompt(personality_type="unknown_type")
        assert "温暖" in prompt or "倾听" in prompt

    def test_with_memories(self):
        memories = [
            {"summary": "用户说工作压力大", "mood_keywords": ["压力"]},
            {"summary": "用户养了一只猫", "mood_keywords": ["开心"]},
        ]
        prompt = build_system_prompt(memories=memories)
        assert "工作压力大" in prompt
        assert "猫" in prompt
        assert "记忆" in prompt

    def test_with_user_profile(self):
        profile = {"nickname": "小明", "preferences": {"喜欢": "猫", "职业": "设计师"}}
        prompt = build_system_prompt(user_profile=profile)
        assert "小明" in prompt
        assert "猫" in prompt

    def test_with_user_profile_no_nickname(self):
        """没有昵称时不报错。"""
        profile = {"nickname": None, "preferences": {"喜欢": "咖啡"}}
        prompt = build_system_prompt(user_profile=profile)
        assert "咖啡" in prompt

    def test_full_prompt(self):
        """完整参数组合不报错。"""
        memories = [{"summary": "测试记忆", "mood_keywords": ["测试"]}]
        profile = {"nickname": "小明", "preferences": {"喜欢": "猫"}}
        prompt = build_system_prompt(
            nickname="小夜",
            personality_type="sister",
            memories=memories,
            user_profile=profile,
        )
        assert "小夜" in prompt
        assert "小明" in prompt
        assert "测试记忆" in prompt
        assert len(prompt) > 200
