"""
C: 第三方 LLM 提供商兼容性测试套件
E: 3rd-party LLM provider compatibility test suite

覆盖 / Covers:
  1. 纯文本 JSON 降级（提供商不支持 function calling）— _BaseAgent._call_llm_tool
  2. 工具参数截断/带围栏 JSON 的修复链
  3. 全链路失败 → ValueError（含降级关闭时行为）
  4. 参数透传断言（tools / tool_choice / temperature / max_tokens / model）
  5. 参数自适应（temperature 被拒移除、max_tokens 超上限减半）
  6. 配置回退链与混用陷阱（Config.validate / LLM_API_KEY_SRC 来源追踪）
  7. 管线降级链（stage1→legacy / stage2→stage3 继续）
  8. mcp_server._call_llm_tool 纯文本降级（annotate_terms 路径）

运行 / Run: ./venv/bin/python test_compat_provider.py
"""
import importlib
import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import openai
import mindmap_agent
from mindmap_agent import _BaseAgent, MindMapPipelineOrchestrator


# =========================================================
# C: 伪 OpenAI 响应构造
# E: Fake OpenAI response builders
# =========================================================
def _msg(tool_calls=None, content=None):
    return SimpleNamespace(tool_calls=tool_calls, content=content)


def _tool_call(arguments):
    return SimpleNamespace(function=SimpleNamespace(arguments=arguments))


def _resp(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _fake_http_response():
    """C: 满足 openai 异常构造所需的 response.request / status_code 访问
    E: Satisfy the response.request / status_code access in openai exception constructors"""
    return SimpleNamespace(request=SimpleNamespace(), status_code=400, headers={})


class FakeCompletions:
    """C: 按脚本顺序返回响应并记录每次调用参数
    E: Returns scripted responses in order and records call kwargs"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self.responses:
            raise RuntimeError("no more scripted responses")
        return self.responses.pop(0)


def _make_agent(fake):
    """C: 绕过 __init__ 构造最小 _BaseAgent 实例
    E: Build a minimal _BaseAgent instance bypassing __init__"""
    agent = _BaseAgent.__new__(_BaseAgent)
    agent.client = SimpleNamespace(chat=SimpleNamespace(completions=fake))
    agent.model = "test-model"
    return agent


TOOLS = [{
    "type": "function",
    "function": {"name": "extract_concepts", "parameters": {"type": "object"}},
}]


# =========================================================
# C: 1/4. 纯文本 JSON 降级 + 参数透传
# E: 1/4. Plain-text JSON fallback + parameter passthrough
# =========================================================
class TestTextJsonFallback(unittest.TestCase):
    """C: 纯文本 JSON 降级 — 提供商不支持 function calling
    E: Plain-text JSON fallback — provider without function calling"""

    def setUp(self):
        self._patcher = patch.object(mindmap_agent.Config, "LLM_JSON_FALLBACK", True)
        self._patcher.start()
        self.addCleanup(self._patcher.stop)

    def test_fallback_parses_text_json(self):
        fake = FakeCompletions([
            _resp(_msg(tool_calls=None, content="I cannot call tools.")),
            _resp(_msg(tool_calls=None, content="I still cannot call tools.")),
            _resp(_msg(tool_calls=None, content=json.dumps(
                {"concepts": [{"id": "c1", "label": "Deep Learning",
                               "color": "var(--node-blue)"}]}
            ))),
        ])
        agent = _make_agent(fake)
        result = agent._call_llm_tool("sys", "user", TOOLS, "extract_concepts")
        self.assertEqual(result["concepts"][0]["id"], "c1")
        # C: 前两次带 tools，第三次降级调用不带 tools
        # E: First two calls carry tools, the fallback call omits them
        self.assertIn("tools", fake.calls[0])
        self.assertIn("tools", fake.calls[1])
        self.assertNotIn("tools", fake.calls[2])
        self.assertNotIn("tool_choice", fake.calls[2])
        self.assertEqual(len(fake.calls), 3)

    def test_parameter_passthrough(self):
        fake = FakeCompletions([
            _resp(_msg(tool_calls=[_tool_call('{"concepts": []}')], content=None)),
        ])
        agent = _make_agent(fake)
        with patch.object(mindmap_agent.Config, "LLM_MAX_TOKENS", 4096):
            result = agent._call_llm_tool("sys", "user", TOOLS, "extract_concepts")
        self.assertEqual(result, {"concepts": []})
        call = fake.calls[0]
        self.assertEqual(call["tools"], TOOLS)
        self.assertEqual(call["tool_choice"], {
            "type": "function", "function": {"name": "extract_concepts"}
        })
        self.assertEqual(call["temperature"], 0.0)
        self.assertEqual(call["max_tokens"], 4096)
        self.assertEqual(call["model"], "test-model")

    def test_fallback_disabled_raises(self):
        fake = FakeCompletions([
            _resp(_msg(tool_calls=None, content="cannot")),
            _resp(_msg(tool_calls=None, content="cannot again")),
        ])
        agent = _make_agent(fake)
        with patch.object(mindmap_agent.Config, "LLM_JSON_FALLBACK", False):
            with self.assertRaises(ValueError):
                agent._call_llm_tool("sys", "user", TOOLS, "extract_concepts")
        self.assertEqual(len(fake.calls), 2)

    def test_fallback_unparseable_raises(self):
        fake = FakeCompletions([
            _resp(_msg(tool_calls=None, content="cannot")),
            _resp(_msg(tool_calls=None, content="cannot again")),
            _resp(_msg(tool_calls=None, content="Sorry, I cannot output JSON.")),
        ])
        agent = _make_agent(fake)
        with self.assertRaises(ValueError):
            agent._call_llm_tool("sys", "user", TOOLS, "extract_concepts")


# =========================================================
# C: 2. 工具参数 JSON 容错修复链
# E: 2. Tool-arguments JSON repair chain
# =========================================================
class TestArgumentsRepair(unittest.TestCase):
    def test_truncated_json_repaired(self):
        fake = FakeCompletions([
            _resp(_msg(tool_calls=[_tool_call(
                '{"concepts": [{"id": "c1", "label": "Deep Learning"'
            )], content=None)),
        ])
        agent = _make_agent(fake)
        result = agent._call_llm_tool("sys", "user", TOOLS, "extract_concepts")
        self.assertEqual(result["concepts"][0]["id"], "c1")
        self.assertEqual(len(fake.calls), 1)

    def test_markdown_fenced_arguments_repaired(self):
        fake = FakeCompletions([
            _resp(_msg(tool_calls=[_tool_call('```json\n{"concepts": []}\n```')], content=None)),
        ])
        agent = _make_agent(fake)
        result = agent._call_llm_tool("sys", "user", TOOLS, "extract_concepts")
        self.assertEqual(result, {"concepts": []})


# =========================================================
# C: 5. 参数自适应 — 推理模型拒绝 temperature / max_tokens
# E: 5. Param adaptation — reasoning models rejecting temperature / max_tokens
# =========================================================
class TestParamAdaptation(unittest.TestCase):
    def test_temperature_removed_and_retried(self):
        class ThrowingCompletions:
            def __init__(self):
                self.calls = []

            def create(self, **kwargs):
                self.calls.append(kwargs)
                if "temperature" in kwargs:
                    raise openai.BadRequestError(
                        "Unknown parameter: 'temperature'",
                        response=_fake_http_response(), body=None,
                    )
                return _resp(_msg(tool_calls=[_tool_call('{"concepts": []}')], content=None))

        fake = ThrowingCompletions()
        agent = _make_agent(fake)
        result = agent._call_llm_tool("sys", "user", TOOLS, "extract_concepts")
        self.assertEqual(result, {"concepts": []})
        self.assertEqual(len(fake.calls), 2)
        self.assertNotIn("temperature", fake.calls[1])

    def test_max_tokens_halved_and_retried(self):
        class ThrowingCompletions:
            def __init__(self):
                self.calls = []

            def create(self, **kwargs):
                self.calls.append(kwargs)
                if kwargs.get("max_tokens", 0) > 4096:
                    raise openai.BadRequestError(
                        "max_tokens is too large",
                        response=_fake_http_response(), body=None,
                    )
                return _resp(_msg(tool_calls=[_tool_call('{"concepts": []}')], content=None))

        fake = ThrowingCompletions()
        agent = _make_agent(fake)
        with patch.object(mindmap_agent.Config, "LLM_MAX_TOKENS", 8192):
            result = agent._call_llm_tool("sys", "user", TOOLS, "extract_concepts")
        self.assertEqual(result, {"concepts": []})
        self.assertEqual(len(fake.calls), 2)
        self.assertLessEqual(fake.calls[1]["max_tokens"], 4096)


# =========================================================
# C: 6. 配置回退链与混用陷阱（validate）
# E: 6. Config fallback chain and mixing trap (validate)
# =========================================================
class TestConfigFallbackChain(unittest.TestCase):
    def _reload_config(self, env):
        """C: 在受控环境中重载 config 模块（屏蔽 .env 加载）
        E: Reload the config module under a controlled env (block .env loading)"""
        with patch.dict(os.environ, env, clear=True), \
             patch("dotenv.load_dotenv"):
            import config as config_mod
            return importlib.reload(config_mod)

    def test_openai_key_mixing_warning(self):
        config_mod = self._reload_config({"OPENAI_API_KEY": "sk-xxx"})
        self.assertEqual(config_mod.Config.LLM_API_KEY, "sk-xxx")
        self.assertEqual(config_mod.Config.LLM_API_KEY_SRC, "OPENAI_API_KEY")
        self.assertIsNone(config_mod.Config.LLM_BASE_URL_SRC)
        self.assertEqual(config_mod.Config.LLM_BASE_URL, "https://api.deepseek.com")
        self.assertTrue(
            any("OPENAI_API_KEY" in w for w in config_mod.Config.validate()),
            "混用陷阱应产生警告 / mixing trap should warn",
        )

    def test_trio_no_mixing_warning(self):
        config_mod = self._reload_config({
            "OPENAI_API_KEY": "sk-xxx",
            "LLM_BASE_URL": "https://api.openai.com/v1",
            "LLM_MODEL": "gpt-4o",
        })
        self.assertEqual(config_mod.Config.LLM_API_KEY_SRC, "OPENAI_API_KEY")
        self.assertEqual(config_mod.Config.LLM_BASE_URL_SRC, "LLM_BASE_URL")
        self.assertFalse(any("OPENAI_API_KEY" in w for w in config_mod.Config.validate()))

    def test_missing_key_warning(self):
        config_mod = self._reload_config({})
        self.assertIsNone(config_mod.Config.LLM_API_KEY)
        self.assertTrue(config_mod.Config.validate())

    def test_llm_trio_priority(self):
        config_mod = self._reload_config({
            "LLM_API_KEY": "k-llm",
            "LLM_BASE_URL": "https://custom.example/v1",
            "LLM_MODEL": "custom-model",
            "DEEPSEEK_API_KEY": "k-ds",
        })
        self.assertEqual(config_mod.Config.LLM_API_KEY, "k-llm")
        self.assertEqual(config_mod.Config.LLM_API_KEY_SRC, "LLM_API_KEY")
        self.assertEqual(config_mod.Config.LLM_BASE_URL, "https://custom.example/v1")
        self.assertEqual(config_mod.Config.LLM_MODEL, "custom-model")

    def test_json_fallback_default_on(self):
        config_mod = self._reload_config({"LLM_API_KEY": "k"})
        self.assertTrue(config_mod.Config.LLM_JSON_FALLBACK)


# =========================================================
# C: 7. 管线降级链 — stage1→legacy / stage2→stage3 继续
# E: 7. Pipeline degradation chain — stage1→legacy / stage2→stage3 continues
# =========================================================
class TestPipelineDegradation(unittest.TestCase):
    def _no_debug(self):
        return patch.object(mindmap_agent.Config, "DEBUG_OUTPUT_ENABLED", False)

    def test_stage1_failure_degrades_to_legacy(self):
        class BoomConcept:
            def extract(self, *a, **k):
                raise RuntimeError("stage1 boom")

        class FakeLegacy:
            def __init__(self):
                self.called = False

            def generate_map_from_context(self, chat_history, current_map):
                self.called = True
                return {"nodes": [
                    {"id": "x", "label": "X", "color": "var(--node-blue)"}
                ], "links": []}

        legacy = FakeLegacy()
        pipeline = MindMapPipelineOrchestrator(
            concept_agent=BoomConcept(),
            hierarchy_agent=None,
            delta_agent=None,
            legacy_agent=legacy,
        )
        with self._no_debug():
            result = pipeline.generate("hello", {"nodes": [], "links": []})
        self.assertTrue(legacy.called)
        self.assertTrue(result["_degradation"]["stage1_failed"])
        self.assertTrue(result["_degradation"]["degraded_to_legacy"])
        self.assertEqual(len(result["nodes"]), 1)

    def test_stage2_failure_continues_stage3(self):
        class FakeConcept:
            def extract(self, chat_history, current_map):
                return [{"id": "c1", "label": "Concept", "color": "var(--node-blue)"}]

        class BoomHierarchy:
            def plan(self, *a, **k):
                raise RuntimeError("stage2 boom")

        class FakeDelta:
            def __init__(self):
                self.received_hierarchy = "unset"

            def generate(self, chat_history, concepts, hierarchy, current_map):
                self.received_hierarchy = hierarchy
                return {
                    "delta": {"add_nodes": [
                        {"id": "c1", "label": "Concept", "color": "var(--node-blue)"}
                    ]},
                    "merged_map": {"nodes": [
                        {"id": "c1", "label": "Concept", "color": "var(--node-blue)",
                         "parent_id": None}
                    ], "links": []},
                }

        delta = FakeDelta()
        pipeline = MindMapPipelineOrchestrator(
            concept_agent=FakeConcept(),
            hierarchy_agent=BoomHierarchy(),
            delta_agent=delta,
            legacy_agent=None,
        )
        with self._no_debug():
            result = pipeline.generate("hello", {"nodes": [], "links": []})
        self.assertIsNone(delta.received_hierarchy)
        self.assertTrue(result["_degradation"]["stage2_failed"])
        self.assertFalse(result["_degradation"]["stage3_failed"])
        self.assertEqual(len(result["nodes"]), 1)


# =========================================================
# C: 8. mcp_server._call_llm_tool 纯文本降级（annotate_terms 路径）
# E: 8. mcp_server._call_llm_tool plain-text fallback (annotate_terms path)
# =========================================================
class TestMcpServerFallback(unittest.TestCase):
    def test_text_fallback(self):
        import mcp_server
        fake = FakeCompletions([
            _resp(_msg(tool_calls=None, content="cannot")),
            _resp(_msg(tool_calls=None, content="cannot again")),
            _resp(_msg(tool_calls=None, content=json.dumps(
                {"annotations": {"n1": [{"term": "AI", "source": "label",
                                          "char_start": 0, "char_end": 2}]}}
            ))),
        ])
        client = SimpleNamespace(chat=SimpleNamespace(completions=fake))
        with patch.object(mcp_server.Config, "LLM_JSON_FALLBACK", True):
            result = mcp_server._call_llm_tool(
                "sys", "user",
                [{"type": "function", "function": {"name": "annotate_terms"}}],
                "annotate_terms",
                client=client,
                model="m",
            )
        self.assertEqual(result["annotations"]["n1"][0]["term"], "AI")
        self.assertNotIn("tools", fake.calls[2])


if __name__ == "__main__":
    unittest.main(verbosity=2)
