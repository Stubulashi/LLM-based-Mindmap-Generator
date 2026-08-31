"""
C: 核心管线单元测试
   覆盖 state_merge、flatten_to_tree/flatten_from_tree、
   compute_depth_stats、_safe_json_parse 等关键纯函数。
E: Core pipeline unit tests
   Covers state_merge, flatten_to_tree/flatten_from_tree,
   compute_depth_stats, _safe_json_parse and other critical pure functions.
"""
import json
import sys
import os
import unittest

# C: 确保项目根目录在 sys.path 中
# E: Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mindmap_agent import (
    state_merge,
    flatten_to_tree,
    flatten_from_tree,
    compute_depth_stats,
)


class TestStateMerge(unittest.TestCase):
    """C: state_merge() — 增量合并测试"""

    def setUp(self):
        self.empty_map = {"nodes": [], "links": []}
        self.base_map = {
            "nodes": [
                {"id": "A", "label": "Root", "details": ["existing detail"]},
                {"id": "B", "label": "Child", "details": []},
            ],
            "links": [
                {"source": "A", "target": "B", "link_type": "solid"},
            ],
        }

    def test_add_nodes(self):
        delta = {"add_nodes": [{"id": "C", "label": "New Node"}]}
        result = state_merge(delta, self.empty_map)
        self.assertEqual(len(result["nodes"]), 1)
        self.assertEqual(result["nodes"][0]["id"], "C")

    def test_update_nodes_append_details(self):
        delta = {
            "update_nodes": [
                {"id": "A", "append_details": ["new detail"]}
            ]
        }
        result = state_merge(delta, self.base_map)
        node_a = next(n for n in result["nodes"] if n["id"] == "A")
        self.assertIn("new detail", node_a["details"])
        self.assertIn("existing detail", node_a["details"])

    def test_update_nodes_dedup_details(self):
        """C: 重复的 detail 不应被追加两次 / E: Duplicate details should not be appended twice"""
        delta = {
            "update_nodes": [
                {"id": "A", "append_details": ["existing detail"]}
            ]
        }
        result = state_merge(delta, self.base_map)
        node_a = next(n for n in result["nodes"] if n["id"] == "A")
        self.assertEqual(node_a["details"].count("existing detail"), 1)

    def test_add_links_dedup(self):
        """C: 重复连线不应被添加 / E: Duplicate links should not be added"""
        delta = {
            "add_links": [
                {"source": "A", "target": "B", "type": "solid"}
            ]
        }
        result = state_merge(delta, self.base_map)
        self.assertEqual(len(result["links"]), 1)

    def test_link_type_normalization(self):
        """C: LLM 输出的 type 字段应归一化为 link_type（非破坏性，不移除原始 type）
        E: LLM type field should normalize to link_type (non-mutating, original type not removed)"""
        delta = {
            "add_links": [
                {"source": "A", "target": "C", "type": "dashed"}
            ]
        }
        result = state_merge(delta, {"nodes": [{"id": "A"}, {"id": "C"}], "links": []})
        link = result["links"][0]
        self.assertEqual(link["link_type"], "dashed")

    def test_link_type_fallback(self):
        """C: 非法 link_type 应回退为 solid / E: Invalid link_type should fallback to solid"""
        delta = {
            "add_links": [
                {"source": "A", "target": "C", "type": "INVALID"}
            ]
        }
        result = state_merge(delta, {"nodes": [{"id": "A"}, {"id": "C"}], "links": []})
        self.assertEqual(result["links"][0]["link_type"], "solid")

    def test_delete_nodes(self):
        delta = {"delete_nodes": ["B"]}
        result = state_merge(delta, self.base_map)
        self.assertEqual(len(result["nodes"]), 1)
        self.assertEqual(result["nodes"][0]["id"], "A")
        self.assertEqual(len(result["links"]), 0)

    def test_non_mutating_input(self):
        """C: state_merge 不应修改输入的 delta dict / E: state_merge should not mutate input delta"""
        original_type_value = "dashed"
        delta = {
            "add_links": [
                {"source": "A", "target": "C", "type": original_type_value}
            ]
        }
        delta_copy = json.loads(json.dumps(delta))
        state_merge(delta, {"nodes": [{"id": "A"}, {"id": "C"}], "links": []})
        # delta 中的原始 link 对象不应被修改
        self.assertEqual(delta_copy["add_links"][0].get("type"), "dashed")


class TestFlatTreeConversion(unittest.TestCase):
    """C: flatten_to_tree / flatten_from_tree — 格式互转测试"""

    def test_single_root(self):
        nodes = [
            {"id": "R", "label": "Root", "details": [], "parent_id": None},
            {"id": "C1", "label": "Child 1", "details": [], "parent_id": "R"},
            {"id": "C2", "label": "Child 2", "details": [], "parent_id": "R"},
        ]
        links = [
            {"source": "R", "target": "C1", "link_type": "solid"},
            {"source": "R", "target": "C2", "link_type": "solid"},
        ]
        tree = flatten_to_tree(nodes, links)
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0]["id"], "R")
        self.assertEqual(len(tree[0]["children"]), 2)

    def test_multi_root_virtual_wrap(self):
        """C: 多根节点应被虚拟根包裹 / E: Multiple roots should be wrapped by virtual root"""
        nodes = [
            {"id": "R1", "label": "Root 1", "details": [], "parent_id": None},
            {"id": "R2", "label": "Root 2", "details": [], "parent_id": None},
        ]
        links = []
        tree = flatten_to_tree(nodes, links)
        self.assertEqual(len(tree), 1)
        self.assertTrue(tree[0].get("_isVirtual"))

    def test_roundtrip(self):
        """C: flat → tree → flat 应保持一致性 / E: flat → tree → flat should be consistent"""
        nodes = [
            {"id": "R", "label": "Root", "details": ["d1"], "parent_id": None},
            {"id": "C1", "label": "Child", "details": [], "parent_id": "R",
             "x": 100, "y": 200, "userPositioned": True},
        ]
        links = [{"source": "R", "target": "C1", "link_type": "dashed"}]
        tree = flatten_to_tree(nodes, links)
        r_nodes, r_links = flatten_from_tree(tree)
        self.assertEqual(len(r_nodes), len(nodes))
        self.assertEqual(len(r_links), len(links))
        # 验证坐标保留
        c1 = next(n for n in r_nodes if n["id"] == "C1")
        self.assertEqual(c1["x"], 100)
        self.assertEqual(c1["y"], 200)
        self.assertTrue(c1["userPositioned"])
        # 验证连线类型保留
        self.assertEqual(r_links[0]["link_type"], "dashed")

    def test_empty_nodes(self):
        self.assertEqual(flatten_to_tree([], []), [])
        fn, fl = flatten_from_tree([])
        self.assertEqual(fn, [])
        self.assertEqual(fl, [])


class TestComputeDepthStats(unittest.TestCase):
    """C: compute_depth_stats() — 深度统计测试"""

    def test_simple_tree(self):
        nodes = [
            {"id": "R", "parent_id": None},
            {"id": "C1", "parent_id": "R"},
            {"id": "C2", "parent_id": "R"},
            {"id": "GC1", "parent_id": "C1"},
        ]
        links = [
            {"source": "R", "target": "C1", "link_type": "solid"},
            {"source": "R", "target": "C2", "link_type": "solid"},
            {"source": "C1", "target": "GC1", "link_type": "solid"},
        ]
        stats = compute_depth_stats(nodes, links)
        self.assertEqual(stats["max_depth"], 3)
        self.assertEqual(stats["top_level_count"], 2)  # C1, C2 at depth 2

    def test_empty_nodes(self):
        stats = compute_depth_stats([], [])
        self.assertEqual(stats["max_depth"], 0)
        self.assertEqual(stats["top_level_count"], 0)

    def test_single_root(self):
        nodes = [{"id": "R", "parent_id": None}]
        stats = compute_depth_stats(nodes, [])
        self.assertEqual(stats["max_depth"], 1)
        self.assertEqual(stats["top_level_count"], 0)

    def test_shallow_nodes_count(self):
        """C: 深度不达标的节点数应正确计算 / E: Shallow node count should be accurate"""
        nodes = [
            {"id": "R", "parent_id": None},
            {"id": "C1", "parent_id": "R"},
        ]
        links = [{"source": "R", "target": "C1", "link_type": "solid"}]
        stats = compute_depth_stats(nodes, links)
        # C1 深度为 2，MIN_TREE_DEPTH 默认为 3，所以 C1 算 shallow
        self.assertEqual(stats["shallow_nodes"], 1)


class TestSafeJsonParse(unittest.TestCase):
    """C: _safe_json_parse() — JSON 修复测试"""

    @classmethod
    def setUpClass(cls):
        from mindmap_agent import _BaseAgent
        from unittest.mock import MagicMock
        # C: 创建最小化 Agent 实例（绕过 __init__）
        # E: Create minimal Agent instance (bypass __init__)
        cls.agent = _BaseAgent.__new__(_BaseAgent)
        cls.agent.client = MagicMock()

    def test_valid_json(self):
        result = self.agent._safe_json_parse('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

    def test_trailing_comma(self):
        """C: JSON 尾部逗号修复 / E: Trailing comma repair"""
        result = self.agent._safe_json_parse('{"key": "value",}')
        self.assertEqual(result, {"key": "value"})

    def test_truncated_bracket_repair(self):
        """C: 截断 JSON 的括号补全 / E: Truncated JSON bracket completion"""
        result = self.agent._safe_json_parse('{"key": [1, 2')
        self.assertEqual(result, {"key": [1, 2]})

    def test_markdown_json_block(self):
        """C: Markdown JSON 代码块提取 / E: Markdown JSON code block extraction"""
        result = self.agent._safe_json_parse('```json\n{"key": "value"}\n```')
        self.assertEqual(result, {"key": "value"})

    def test_text_before_json(self):
        """C: 文本前缀后的 JSON 提取 / E: JSON extraction after text prefix"""
        result = self.agent._safe_json_parse(
            'Here is the result: {"key": "value"}'
        )
        self.assertEqual(result, {"key": "value"})

    def test_nested_json(self):
        result = self.agent._safe_json_parse(
            '{"outer": {"inner": [1, 2, 3]}}'
        )
        self.assertEqual(result, {"outer": {"inner": [1, 2, 3]}})

    def test_missing_closing_brace(self):
        """C: 缺失闭合括号修复 / E: Missing closing brace repair"""
        result = self.agent._safe_json_parse('{"key": "value"')
        self.assertEqual(result, {"key": "value"})

    def test_truncated_nested_repair(self):
        """C: 截断嵌套 JSON 的 LIFO 补全 / E: Truncated nested JSON LIFO completion"""
        result = self.agent._safe_json_parse('{"outer": {"inner": "val"')
        self.assertEqual(result, {"outer": {"inner": "val"}})


if __name__ == "__main__":
    # C: 运行所有测试
    # E: Run all tests
    unittest.main(verbosity=2)
