"""
C: Edge/Hierarchy 评估模块回归测试 — 覆盖 2026-08 集中修复的关键缺陷：
   id 类型一致性、空 mu 语义、nTED 树构建（links-only 扁平图）、PC-F1 最优匹配、
   阈值单一语义、多轮平均、报告渲染异常路径。
E: Regression tests for Edge/Hierarchy evaluation fixes — id-type consistency,
   empty-mu semantics, nTED tree building (links-only flat maps), PC-F1 optimal
   matching, single-threshold grading, multi-run averaging, report rendering.
运行: python test_eval_hierarchy.py
"""
import sys
import os
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib.util
_HAS_ZSS = importlib.util.find_spec('zss') is not None

from evaluation.core.aligner import AlignmentResult
from evaluation.core.data_loader import MindMapData
from evaluation.core.thresholds import THRESHOLD_MAP
from evaluation.hierarchy.eval_hierarchy import evaluate_hierarchy_quality


def fake_sim_matrix(gold_labels, gen_labels, model_name="", normalize=True):
    """E: Fake similarity matrix — all 0.99 (every pair matches), avoiding
        embedding-model loading in tests.
    C: 伪相似度矩阵 — 全 0.99（任意配对均匹配），避免测试加载 embedding 模型。"""
    return np.full((len(gold_labels), len(gen_labels)), 0.99)


def make_alignment(gold_nodes, gen_nodes, pairs, model_name="test-model", threshold=0.70):
    """E: Build an AlignmentResult with (gold_id, gen_id, sim) pairs — mimics the
        post-fix aligner output where ids are normalized to str.
    C: 构造 AlignmentResult，配对为 (gold_id, gen_id, sim) — 模拟修复后 aligner
       的输出（id 已统一为 str）。"""
    gold_ids = [str(n['id']) for n in gold_nodes]
    gen_ids = [str(n['id']) for n in gen_nodes]
    gold_labels = [n['label'] for n in gold_nodes]
    gen_labels = [n['label'] for n in gen_nodes]
    raw = []
    for gid, gid_, sim in pairs:
        gi = gen_ids.index(str(gid_))
        si = gold_ids.index(str(gid))
        raw.append((gi, si, sim))
    filtered = [(gi, si, sim) for gi, si, sim in raw if sim >= threshold]
    return AlignmentResult(
        similarity_matrix=None,
        raw_matches=raw,
        filtered_matches=filtered,
        threshold=threshold,
        model_name=model_name,
        gen_labels=gen_labels,
        gold_labels=gold_labels,
        gen_ids=gen_ids,
        gold_ids=gold_ids,
    )


def tree_map(nodes, links):
    """E: Minimal MindMapData helper / C: 构造最小 MindMapData"""
    return MindMapData(nodes=nodes, links=links, tree=[])


class TestEdgeF1(unittest.TestCase):
    def setUp(self):
        # E: Avoid loading the embedding model — PC-F1 calls compute_similarity_matrix
        # C: 避免加载 embedding 模型 — PC-F1 会调用 compute_similarity_matrix
        self._sim_patch = patch('evaluation.hierarchy.eval_hierarchy.compute_similarity_matrix',
                                side_effect=fake_sim_matrix)
        self._sim_patch.start()
        # E: gold R→A, R→B / C: 金标准 R→A、R→B
        self.gold = tree_map(
            [
                {'id': 'R', 'label': 'Root'},
                {'id': 'A', 'label': 'Alpha'},
                {'id': 'B', 'label': 'Beta'},
            ],
            [
                {'source': 'R', 'target': 'A', 'link_type': 'solid'},
                {'source': 'R', 'target': 'B', 'link_type': 'solid'},
            ],
        )

    def test_perfect_mapping_edge_f1_1(self):
        gen = tree_map(
            [
                {'id': 'R2', 'label': 'Root'},
                {'id': 'A2', 'label': 'Alpha'},
                {'id': 'B2', 'label': 'Beta'},
            ],
            [
                {'source': 'R2', 'target': 'A2', 'link_type': 'solid'},
                {'source': 'R2', 'target': 'B2', 'link_type': 'solid'},
            ],
        )
        al = make_alignment(self.gold.nodes, gen.nodes,
                            [('R', 'R2', 0.99), ('A', 'A2', 0.99), ('B', 'B2', 0.99)])
        m = evaluate_hierarchy_quality(self.gold, gen, al)
        self.assertEqual(m.edge_tp, 2)
        self.assertEqual(m.edge_fn, 0)
        self.assertEqual(m.edge_fp, 0)
        self.assertAlmostEqual(m.edge_f1, 1.0, places=4)
        self.assertAlmostEqual(m.edge_precision, 1.0, places=4)
        self.assertAlmostEqual(m.edge_recall, 1.0, places=4)

    def test_extra_gen_edge_penalises_precision(self):
        gen = tree_map(
            [
                {'id': 'R2', 'label': 'Root'},
                {'id': 'A2', 'label': 'Alpha'},
                {'id': 'B2', 'label': 'Beta'},
                {'id': 'C2', 'label': 'Gamma'},
            ],
            [
                {'source': 'R2', 'target': 'A2', 'link_type': 'solid'},
                {'source': 'R2', 'target': 'B2', 'link_type': 'solid'},
                {'source': 'A2', 'target': 'C2', 'link_type': 'solid'},
            ],
        )
        al = make_alignment(self.gold.nodes, gen.nodes,
                            [('R', 'R2', 0.99), ('A', 'A2', 0.99), ('B', 'B2', 0.99)])
        m = evaluate_hierarchy_quality(self.gold, gen, al)
        self.assertEqual(m.edge_tp, 2)
        self.assertEqual(m.edge_fp, 1)   # extra edge A2→C2
        self.assertAlmostEqual(m.edge_precision, 2 / 3, places=4)
        self.assertAlmostEqual(m.edge_recall, 1.0, places=4)

    def test_int_node_ids_no_silent_inflation(self):
        """E: Regression — int ids in the maps must NOT zero Edge-TP nor inflate
            UAS/LAR via None==None (ids are normalized to str by the aligner).
        C: 回归 — 图中 int id 不得使 Edge-TP 归零、也不得借 None==None 虚高 UAS/LAR
            （aligner 已统一 str 化）。"""
        gold = tree_map(
            [
                {'id': 1, 'label': 'Root'},
                {'id': 2, 'label': 'Alpha'},
                {'id': 3, 'label': 'Beta'},
            ],
            [
                {'source': 1, 'target': 2, 'link_type': 'solid'},
                {'source': 1, 'target': 3, 'link_type': 'solid'},
            ],
        )
        gen = tree_map(
            [
                {'id': 10, 'label': 'Root'},
                {'id': 20, 'label': 'Alpha'},
                {'id': 30, 'label': 'Beta'},
            ],
            [
                {'source': 10, 'target': 20, 'link_type': 'solid'},
                {'source': 10, 'target': 30, 'link_type': 'solid'},
            ],
        )
        al = make_alignment(gold.nodes, gen.nodes,
                            [(1, 10, 0.99), (2, 20, 0.99), (3, 30, 0.99)])
        m = evaluate_hierarchy_quality(gold, gen, al)
        self.assertEqual(m.edge_tp, 2, "int ids must not zero Edge-TP")
        self.assertAlmostEqual(m.uas, 1.0, places=4, msg="UAS must not collapse via None==None")
        self.assertAlmostEqual(m.lar, 1.0, places=4, msg="LAR must not collapse via None==None")
        self.assertEqual(m.aligned_count, 3)

    def tearDown(self):
        self._sim_patch.stop()

    def test_empty_mu_returns_zero(self):
        """E: Empty alignment — UAS/LAR must be explicit 0.0, not 1.0.
        C: 空对齐 — UAS/LAR 必须显式 0.0，而非 1.0。"""
        gen = tree_map(
            [
                {'id': 'X', 'label': 'Totally unrelated'},
            ],
            [],
        )
        al = make_alignment(self.gold.nodes, gen.nodes, [])  # no matches
        m = evaluate_hierarchy_quality(self.gold, gen, al)
        self.assertEqual(m.aligned_count, 0)
        self.assertEqual(m.uas, 0.0)
        self.assertEqual(m.lar, 0.0)


class TestLinksOnlyFlatMaps(unittest.TestCase):
    """E: Flat maps without parent_id (structure in links) must be handled by
        extract_edges fallback for Edge metrics and nTED tree building.
    C: 无 parent_id 的扁平图（结构在 links 中）必须经 extract_edges 兜底，
        Edge 指标与 nTED 树构建均应正常。"""

    def setUp(self):
        # E: Avoid loading the embedding model (PC-F1 similarity matrices)
        # C: 避免加载 embedding 模型（PC-F1 相似度矩阵）
        self._sim_patch = patch('evaluation.hierarchy.eval_hierarchy.compute_similarity_matrix',
                                side_effect=fake_sim_matrix)
        self._sim_patch.start()

    def tearDown(self):
        self._sim_patch.stop()

    def test_edge_metrics_from_links_only(self):
        gold = tree_map(
            [{'id': 'R', 'label': 'Root'}, {'id': 'A', 'label': 'Alpha'}],
            [{'source': 'R', 'target': 'A', 'link_type': 'solid'}],
        )
        gen = tree_map(
            [{'id': 'R2', 'label': 'Root'}, {'id': 'A2', 'label': 'Alpha'}],
            [{'source': 'R2', 'target': 'A2', 'link_type': 'solid'}],
        )
        al = make_alignment(gold.nodes, gen.nodes, [('R', 'R2', 0.99), ('A', 'A2', 0.99)])
        m = evaluate_hierarchy_quality(gold, gen, al)
        self.assertEqual(m.edge_tp, 1)
        self.assertAlmostEqual(m.edge_f1, 1.0, places=4)

    @unittest.skipUnless(_HAS_ZSS, "zss not installed")
    def test_nted_links_only_identical_trees(self):
        """E: Identical links-only trees must yield nTED ≈ 0 (regression: the old
            parent_id-only builder collapsed them to single-node trees).
        C: 同构 links-only 树 nTED 应 ≈ 0（回归：旧版仅按 parent_id 建树会把
            它们退化为单节点树）。"""
        nodes = [
            {'id': 'R', 'label': 'root'},
            {'id': 'A', 'label': 'a'},
            {'id': 'B', 'label': 'b'},
        ]
        links = [
            {'source': 'R', 'target': 'A', 'link_type': 'solid'},
            {'source': 'R', 'target': 'B', 'link_type': 'solid'},
        ]
        gold = tree_map(nodes, links)
        gen = tree_map(nodes, links)
        al = make_alignment(gold.nodes, gen.nodes, [('R', 'R', 0.99), ('A', 'A', 0.99), ('B', 'B', 0.99)])
        m = evaluate_hierarchy_quality(gold, gen, al)
        self.assertIsNotNone(m.nted)
        self.assertLessEqual(m.nted, 0.05, f"identical trees should have nTED≈0, got {m.nted}")

    @unittest.skipUnless(_HAS_ZSS, "zss not installed")
    def test_nted_links_only_different_trees(self):
        """E: Structurally different links-only trees must score high nTED (old
            single-node collapse made even unrelated maps score ≈0).
        C: 结构不同的 links-only 树 nTED 应偏高（旧版单节点退化会让完全无关的
            图也得分 ≈0）。"""
        gold = tree_map(
            [{'id': 'R', 'label': 'root'}, {'id': 'A', 'label': 'a'}, {'id': 'B', 'label': 'b'}],
            [
                {'source': 'R', 'target': 'A', 'link_type': 'solid'},
                {'source': 'R', 'target': 'B', 'link_type': 'solid'},
            ],
        )
        gen = tree_map(
            [
                {'id': 'X', 'label': 'x'},
                {'id': 'Y', 'label': 'y'},
                {'id': 'Z', 'label': 'z'},
                {'id': 'W', 'label': 'w'},
            ],
            [
                {'source': 'X', 'target': 'Y', 'link_type': 'solid'},
                {'source': 'Y', 'target': 'Z', 'link_type': 'solid'},
                {'source': 'Z', 'target': 'W', 'link_type': 'solid'},
            ],
        )
        al = make_alignment(gold.nodes, gen.nodes, [])
        m = evaluate_hierarchy_quality(gold, gen, al)
        self.assertIsNotNone(m.nted)
        self.assertGreater(m.nted, 0.4, f"different trees should score high nTED, got {m.nted}")


class TestPCF1OptimalMatching(unittest.TestCase):
    """E: PC-F1 must use global optimal one-to-one matching — result independent
        of pair ordering (regression for the order-sensitive greedy loop).
    C: PC-F1 必须使用全局最优一对一指派 — 结果与配对顺序无关
        （回归：此前顺序敏感的贪心循环会低估命中数）。"""

    def test_optimal_matching_finds_both_hits(self):
        # E: gold A matches gen 1 AND 2; gold B matches only gen 1.
        #    Greedy first-fit would take A→1 then leave B unmatched (1 hit);
        #    optimal assignment A→2, B→1 gives 2 hits.
        # C: gold A 可匹配 gen 1、2；gold B 仅可匹配 gen 1。
        #    贪心 first-fit 会取 A→1 使 B 落空（1 次命中）；最优指派 A→2、B→1 得 2 次命中。
        parent_S = [[0.9, 0.9],
                    [0.9, 0.1]]
        child_S = [[0.9, 0.9],
                   [0.9, 0.1]]
        gold_nodes = [
            {'id': 'g1', 'label': 'gA', 'parent_id': None},
            {'id': 'g2', 'label': 'gB', 'parent_id': 'g1'},
            {'id': 'g3', 'label': 'gC', 'parent_id': 'g1'},
        ]
        gen_nodes = [
            {'id': 'p1', 'label': 'pA', 'parent_id': None},
            {'id': 'p2', 'label': 'pB', 'parent_id': 'p1'},
            {'id': 'p3', 'label': 'pC', 'parent_id': 'p1'},
        ]
        gold = tree_map(gold_nodes, [])
        gen = tree_map(gen_nodes, [])
        al = make_alignment(gold.nodes, gen.nodes, [])
        # E: gold pairs (gA,gB),(gA,gC) vs gen pairs (pA,pB),(pA,pC); the two
        #    similarity-matrix calls (parent, child) are served in order.
        # C: gold 对 (gA,gB)、(gA,gC) 对比 gen 对 (pA,pB)、(pA,pC)；两次相似度矩阵
        #    调用（父、子）按序返回。
        with patch('evaluation.hierarchy.eval_hierarchy.compute_similarity_matrix',
                   side_effect=[np.array(parent_S), np.array(child_S)]):
            m = evaluate_hierarchy_quality(gold, gen, al)
        self.assertEqual(m.pc_tp, 2, "optimal one-to-one matching should find 2 hits")
        self.assertAlmostEqual(m.pc_f1, 1.0, places=4)


class TestThresholdSingleBand(unittest.TestCase):
    """E: Spec §2.3-§2.5 single thresholds — PASS only at/above the excellent
        boundary (regression: self-invented good bands showed PASS below spec).
    C: 规范 §2.3-§2.5 单一阈值 — 只有达到优秀边界才 PASS
        （回归：自造 good 带曾让低于规范阈值的值显示 PASS）。"""

    def test_nted_boundary(self):
        band = THRESHOLD_MAP['nted']
        self.assertIn('✅ PASS', band.pass_fail(0.25))
        self.assertIn('❌ FAIL', band.pass_fail(0.26))
        self.assertIn('❌ FAIL', band.pass_fail(0.40))  # old good band would PASS

    def test_pc_f1_boundary(self):
        band = THRESHOLD_MAP['pc_f1']
        self.assertIn('✅ PASS', band.pass_fail(0.75))
        self.assertIn('❌ FAIL', band.pass_fail(0.74))
        self.assertIn('❌ FAIL', band.pass_fail(0.60))  # old good band would PASS

    def test_lar_boundary(self):
        band = THRESHOLD_MAP['lar']
        self.assertIn('✅ PASS', band.pass_fail(0.70))
        self.assertIn('❌ FAIL', band.pass_fail(0.69))
        self.assertIn('❌ FAIL', band.pass_fail(0.50))  # old good band would PASS

    def test_edge_f1_dual_band_unchanged(self):
        band = THRESHOLD_MAP['edge_f1']
        self.assertIn('✅ PASS', band.pass_fail(0.65))
        self.assertIn('✅ PASS', band.pass_fail(0.80))
        self.assertIn('❌ FAIL', band.pass_fail(0.64))


class TestAverageEvalResults(unittest.TestCase):
    """E: Multi-run averaging — counts rounded to int, partial nTED → None.
    C: 多轮平均 — 计数取整，nTED 部分缺失置 None。"""

    def test_counts_averaged_as_integers(self):
        from evaluation.run_evaluation import _average_eval_results
        runs = [
            {'label': {'tp': 2, 'node_f1': 0.8}},
            {'label': {'tp': 3, 'node_f1': 0.9}},
        ]
        avg = _average_eval_results(runs)
        self.assertEqual(avg['label']['tp'], 2)  # round(2.5)
        self.assertIsInstance(avg['label']['tp'], int)
        self.assertAlmostEqual(avg['label']['node_f1'], 0.85, places=4)

    def test_partial_nted_marks_unavailable(self):
        from evaluation.run_evaluation import _average_eval_results
        runs = [
            {'hierarchy': {'nted': 0.2, 'edge_f1': 0.9}},
            {'hierarchy': {'nted': None, 'edge_f1': 0.8}},
        ]
        avg = _average_eval_results(runs)
        self.assertIsNone(avg['hierarchy']['nted'])
        self.assertTrue(avg['hierarchy'].get('nted_partial'))
        self.assertAlmostEqual(avg['hierarchy']['edge_f1'], 0.85, places=4)


class TestRendererPaths(unittest.TestCase):
    """E: Renderer regression paths — error dict → Anomaly block, missing WER → N/A,
        label metrics expose node_p/node_r rows.
    C: 渲染器回归路径 — 异常字典输出 Anomaly 块、WER 缺失输出 N/A、
        label 指标暴露 node_p/node_r 行。"""

    def test_hierarchy_error_renders_anomaly(self):
        from evaluation.report.markdown_renderer import MarkdownReportRenderer
        r = MarkdownReportRenderer(embedding_model='test', threshold=0.70)
        out = r._render_hierarchy_section({'error': 'boom'})
        self.assertIn('Anomaly', out)
        self.assertIn('boom', out)
        self.assertNotIn('Gold edges', out)  # no misleading all-zero details

    def test_wer_none_renders_na(self):
        from evaluation.report.markdown_renderer import MarkdownReportRenderer
        r = MarkdownReportRenderer(embedding_model='test', threshold=0.70)
        out = r._render_efficiency_section({'wer': None, 'wer_method': 'ground truth required / 待提供标准文本'})
        self.assertIn('N/A', out)
        self.assertNotIn('0.0000', out)

    def test_label_section_renders_node_p_r(self):
        from evaluation.report.markdown_renderer import MarkdownReportRenderer
        r = MarkdownReportRenderer(embedding_model='test', threshold=0.70)
        metrics = {'node_f1': 0.85, 'node_p': 0.80, 'node_r': 0.90,
                   'label_sim': 0.80, 'entity_recall': 0.90,
                   'tp': 5, 'fp': 1, 'fn': 0}
        out = r._render_label_section(metrics)
        self.assertIn('Node-P', out)
        self.assertIn('Node-R', out)
        self.assertIn('0.800', out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
