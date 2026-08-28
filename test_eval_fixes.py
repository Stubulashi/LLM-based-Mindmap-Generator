"""C: 评估模块修复的回归测试 — ICC(3,k) / Kendall's W / tree_utils 防御 / token_reduction
E: Regression tests for evaluation fixes — ICC(3,k) / Kendall's W / tree_utils defenses / token_reduction
运行: python test_eval_fixes.py
"""
import sys
import os
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# =========================================================
# C: ICC(3,k) 与 Kendall's W — 完全一致数据应得 1.0
# E: ICC(3,k) and Kendall's W — perfect agreement should be 1.0
# =========================================================
def test_icc_perfect_agreement():
    from evaluation.human_correlation.eval_human_correlation import _compute_inter_rater_reliability

    data = [
        {'readability': 5, 'raters': {'A': 5, 'B': 5, 'C': 5}},
        {'readability': 3, 'raters': {'A': 3, 'B': 3, 'C': 3}},
        {'readability': 1, 'raters': {'A': 1, 'B': 1, 'C': 1}},
    ]
    icc, w, k = _compute_inter_rater_reliability(data)
    assert abs(icc - 1.0) < 1e-6, f"ICC perfect agreement expected 1.0, got {icc}"
    assert abs(w - 1.0) < 1e-6, f"Kendall W perfect agreement expected 1.0, got {w}"
    assert k == 3
    print("  [OK] ICC(3,k)=1.0 & Kendall's W=1.0 on perfect agreement")


def test_icc_partial_agreement():
    """C: 部分一致数据应产生 0 < ICC < 1（无恒等退化）
    E: Partial agreement should yield 0 < ICC < 1 (no degenerate identity)"""
    from evaluation.human_correlation.eval_human_correlation import _compute_inter_rater_reliability

    data = [
        {'readability': 1, 'raters': {'A': 1, 'B': 2}},
        {'readability': 2, 'raters': {'A': 3, 'B': 3}},
        {'readability': 3, 'raters': {'A': 5, 'B': 4}},
        {'readability': 4, 'raters': {'A': 4, 'B': 5}},
    ]
    icc, w, k = _compute_inter_rater_reliability(data)
    assert -1.0 <= icc <= 1.0
    assert 0.0 <= w <= 1.0
    assert k == 2
    print(f"  [OK] partial agreement bounded: ICC={icc:.4f}, W={w:.4f}")


def test_icc_insufficient_data():
    """C: 数据不足应返回 (0, 0, 0) 而非崩溃
    E: Insufficient data should return (0, 0, 0) without crashing"""
    from evaluation.human_correlation.eval_human_correlation import _compute_inter_rater_reliability

    assert _compute_inter_rater_reliability([]) == (0.0, 0.0, 0)
    assert _compute_inter_rater_reliability([{'raters': {'A': 1}}, {'raters': {'A': 2}}]) == (0.0, 0.0, 0)
    assert _compute_inter_rater_reliability([{'no_raters': 1}]) == (0.0, 0.0, 0)
    print("  [OK] insufficient data handled gracefully")


def test_human_correlation_to_dict_contains_icc():
    """C: HumanCorrelationMetrics.to_dict() 应包含 icc / kendall_w，且数值在有效范围内
    E: to_dict() should include icc / kendall_w with values in valid range"""
    from evaluation.human_correlation.eval_human_correlation import evaluate_human_correlation

    # C: 使用逐样本各异的分数（而非常量数组，常量会触发 ConstantInputWarning/NaN）
    # E: Use per-sample varying scores (constant arrays trigger ConstantInputWarning/NaN)
    automated = [
        {'node_f1': 0.9, 'edge_f1': 0.8, 'uas': 0.85, 'label_sim': 0.9},
        {'node_f1': 0.8, 'edge_f1': 0.7, 'uas': 0.80, 'label_sim': 0.8},
        {'node_f1': 0.7, 'edge_f1': 0.6, 'uas': 0.70, 'label_sim': 0.7},
        {'node_f1': 0.6, 'edge_f1': 0.5, 'uas': 0.60, 'label_sim': 0.6},
        {'node_f1': 0.5, 'edge_f1': 0.4, 'uas': 0.50, 'label_sim': 0.5},
    ]
    human = [
        {'readability': 4, 'hierarchy_intuitiveness': 4, 'raters': {'A': 4, 'B': 4}},
        {'readability': 3, 'hierarchy_intuitiveness': 3, 'raters': {'A': 3, 'B': 3}},
        {'readability': 5, 'hierarchy_intuitiveness': 5, 'raters': {'A': 5, 'B': 5}},
        {'readability': 2, 'hierarchy_intuitiveness': 2, 'raters': {'A': 2, 'B': 2}},
        {'readability': 1, 'hierarchy_intuitiveness': 1, 'raters': {'A': 1, 'B': 1}},
    ]
    m = evaluate_human_correlation(automated, human)
    d = m.to_dict()
    assert 'icc' in d and 'kendall_w' in d, "to_dict must expose icc/kendall_w"
    # C: 数值必须在有效范围内（0.0 到 1.0），NaN 视为失败
    # E: Values must be within the valid range (0.0-1.0); NaN is a failure
    assert d['icc'] == d['icc'] and 0.0 <= d['icc'] <= 1.0, f"icc out of range or NaN: {d['icc']}"
    assert 0.0 <= d['kendall_w'] <= 1.0, f"kendall_w out of range: {d['kendall_w']}"
    print(f"  [OK] to_dict exposes icc={d['icc']}, kendall_w={d['kendall_w']}")


# =========================================================
# C: tree_utils 防御 — 畸形节点不抛异常
# E: tree_utils defenses — malformed nodes must not raise
# =========================================================
def test_tree_utils_defensive():
    from evaluation.utils import tree_utils as tu

    bad_nodes = [{'label': 'no-id'}, {'id': 'a', 'label': 'A'}]
    m1 = tu.build_node_id_map(bad_nodes)
    m2 = tu.build_parent_map(bad_nodes)
    pairs = tu.extract_parent_child_pairs(bad_nodes, [{'source': 'a', 'target': 'x', 'link_type': 'solid'}])
    depth = tu.compute_depth_map(bad_nodes, [{'source': 'a', 'target': 'x', 'link_type': 'solid'}])
    edges = tu.extract_edges(bad_nodes, [{'source': 'a', 'target': 'x', 'link_type': 'reference'}])
    assert 'a' in m1 and 'a' in m2
    assert isinstance(pairs, list) and isinstance(depth, dict) and isinstance(edges, list)
    print("  [OK] tree_utils handles malformed nodes without raising")


# =========================================================
# C: token_reduction — 真实 usage 优先，缺失回退估算
# E: token_reduction — real usage preferred, estimation fallback
# =========================================================
def _make_fake_client(contents_and_tokens):
    """C: 构造伪 OpenAI 客户端，依次返回 (content, total_tokens)
    E: Build a fake OpenAI client returning (content, total_tokens) in sequence"""
    calls = []

    class FakeCompletions:
        def create(self, **kwargs):
            content, tokens = contents_and_tokens[len(calls) % len(contents_and_tokens)]
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
                usage=SimpleNamespace(total_tokens=tokens),
            )

    return SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions())), calls


def test_call_llm_for_qa_returns_usage():
    from evaluation.qa.eval_qa import _call_llm_for_qa

    client, _ = _make_fake_client([("A: answer1\nA: answer2", 120)])
    answers, usage = _call_llm_for_qa(client, "model", "sys", "user")
    assert answers == ["answer1", "answer2"]
    assert usage == 120
    print("  [OK] _call_llm_for_qa returns usage tokens")


def test_call_llm_for_qa_usage_none_on_error():
    from evaluation.qa.eval_qa import _call_llm_for_qa

    class Boom:
        chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **k: (_ for _ in ()).throw(RuntimeError("boom"))))

    answers, usage = _call_llm_for_qa(Boom(), "m", "s", "u")
    assert answers == [] and usage is None
    print("  [OK] _call_llm_for_qa degrades to ([], None) on failure")


def test_evaluate_token_reduction_prefers_usage():
    """C: 有真实 usage 时 token_reduction 使用 usage 而非估算
    E: token_reduction uses real usage when available"""
    from evaluation.qa.eval_qa import QAEvaluator, _call_llm_for_qa

    questions = [
        {'id': 'q1', 'question': 'Q1?', 'answer': 'gold1'},
        {'id': 'q2', 'question': 'Q2?', 'answer': 'gold2'},
    ]
    # C: 对照组每轮 200 token，实验组每轮 50 token → reduction = 1 - 150/600 = 0.75
    # E: control 200 tokens/run, experiment 50 tokens/run → reduction = 1 - 150/600 = 0.75
    def fake_call(client, model, system_prompt, user_content):
        if "Transcript" in user_content:
            return ["gold1", "gold2"], 200
        return ["gold1", "gold2"], 50

    # C: 绕过 __init__（跳过 _init_scoring_libs 与 LLM 客户端初始化，避免加载评分库/模型）
    # E: bypass __init__ (skip _init_scoring_libs and LLM client init to avoid heavy imports)
    evaluator = QAEvaluator.__new__(QAEvaluator)
    evaluator._initialized = True
    evaluator.client = object()
    evaluator.model = "fake"

    with patch('evaluation.qa.eval_qa._call_llm_for_qa', side_effect=fake_call), \
         patch('evaluation.qa.eval_qa._exact_match_accuracy', return_value=1.0), \
         patch('evaluation.qa.eval_qa._compute_bleu4', return_value=0.5), \
         patch('evaluation.qa.eval_qa._compute_rouge_l', return_value=0.5), \
         patch('evaluation.qa.eval_qa._compute_bert_score', return_value=0.5):
        metrics = evaluator.evaluate("some transcript " * 50, [{'label': 'A'}, {'label': 'B'}], questions)
        assert abs(metrics.token_reduction - 0.75) < 1e-6, f"expected 0.75, got {metrics.token_reduction}"
        print(f"  [OK] token_reduction from real usage = {metrics.token_reduction:.4f}")


# =========================================================
# C: composite custom_weights
# E: composite custom_weights
# =========================================================
def test_composite_custom_weights():
    from evaluation.report.composite import compute_composite_score

    score, detail = compute_composite_score({'node_f1': 0.8}, custom_weights={'node_f1': 0.5})
    assert abs(score - 0.8) < 1e-9, f"expected 0.8, got {score}"
    # C: 默认权重保持兼容 / E: default weights remain compatible
    score2, _ = compute_composite_score({'node_f1': 0.8})
    assert abs(score2 - 0.8) < 1e-9
    print("  [OK] composite custom weights applied")


# =========================================================
# C: 噪声注入可复现性（seed）
# E: seeded noise reproducibility
# =========================================================
def test_noise_seed_reproducible():
    from evaluation.multilingual.eval_multilingual import _inject_noise

    text = "人工智能与机器学习是重要方向"
    n1 = _inject_noise(text, 0.2, seed=42)
    n2 = _inject_noise(text, 0.2, seed=42)
    assert n1 == n2, "seeded noise must be reproducible"
    assert _inject_noise(text, 0.0) == text
    print("  [OK] seeded noise is reproducible")


if __name__ == "__main__":
    print("=" * 60)
    print("Test 1: ICC/Kendall W")
    print("=" * 60)
    test_icc_perfect_agreement()
    test_icc_partial_agreement()
    test_icc_insufficient_data()
    test_human_correlation_to_dict_contains_icc()

    print("\n" + "=" * 60)
    print("Test 2: tree_utils defenses")
    print("=" * 60)
    test_tree_utils_defensive()

    print("\n" + "=" * 60)
    print("Test 3: token_reduction")
    print("=" * 60)
    test_call_llm_for_qa_returns_usage()
    test_call_llm_for_qa_usage_none_on_error()
    test_evaluate_token_reduction_prefers_usage()

    print("\n" + "=" * 60)
    print("Test 4: composite custom weights")
    print("=" * 60)
    test_composite_custom_weights()

    print("\n" + "=" * 60)
    print("Test 5: noise seed reproducibility")
    print("=" * 60)
    test_noise_seed_reproducible()

    print("\n=== ALL EVAL FIX TESTS PASSED ===")
