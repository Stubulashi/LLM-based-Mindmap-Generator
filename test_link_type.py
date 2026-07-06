"""C: 测试 link_type 在 flatten_to_tree ↔ flatten_from_tree 往返中不丢失
E: Test that link_type is preserved through flatten_to_tree ↔ flatten_from_tree round-trip"""
import json
from mindmap_agent import flatten_to_tree, flatten_from_tree, state_merge_with_tree


# C: 有效的 link_type 集合 / E: Valid link_type set
VALID_LINK_TYPES = {"solid", "dashed", "dotted", "reference", "contrast"}


def test_link_type_roundtrip():
    """C: 创建一个包含多类型连线的导图，执行往返转换，验证 link_type 完整性
    E: Create a map with multi-type links, run round-trip, verify link_type integrity"""

    # C: 输入 flat nodes + links（模拟 LLM 输出的 add_links 含多种 type）
    # E: Input flat nodes + links (simulating LLM add_links with multi-type)
    nodes = [
        {"id": "root", "label": "Root", "color": "var(--node-blue)"},
        {"id": "child1", "label": "Child 1", "color": "var(--node-green)"},
        {"id": "child2", "label": "Child 2", "color": "var(--node-yellow)"},
        {"id": "child3", "label": "Child 3", "color": "var(--node-red)"},
        {"id": "ref1", "label": "Reference", "color": "var(--node-purple)"},
        {"id": "ref2", "label": "Contrast", "color": "var(--node-purple)"},
    ]

    # C: 测试 5 种连线类型（solid/dashed/dotted/reference/contrast）在纯树结构中的完整往返
    # E: Test all 5 link types (solid/dashed/dotted/reference/contrast) in pure tree structure
    links = [
        {"source": "root", "target": "child1", "type": "solid"},
        {"source": "root", "target": "child2", "type": "dashed"},
        {"source": "child1", "target": "child3", "type": "dotted"},
        {"source": "child1", "target": "ref1", "type": "reference"},
        {"source": "child2", "target": "ref2", "link_type": "contrast"},
    ]

    expected_types = {
        ("root", "child1"): "solid",
        ("root", "child2"): "dashed",
        ("child1", "child3"): "dotted",
        ("child1", "ref1"): "reference",
        ("child2", "ref2"): "contrast",
    }

    # Step 1: flatten_to_tree
    tree = flatten_to_tree(nodes, links)
    print(f"[Step 1] Tree roots: {len(tree)}")

    # C: 检查树节点上是否保留了 link_type
    # E: Check link_type preserved on tree nodes
    def check_tree_node(node, depth=0):
        indent = "  " * depth
        lt = node.get('link_type', 'N/A')
        print(f"{indent}Node '{node['id']}' link_type={lt}")
        for child in node.get('children', []):
            check_tree_node(child, depth + 1)

    for root in tree:
        check_tree_node(root)

    # Step 2: flatten_from_tree
    flat_nodes, flat_links = flatten_from_tree(tree)
    print(f"\n[Step 2] Flat nodes: {len(flat_nodes)}, links: {len(flat_links)}")

    # C: 验证 link_type 是否保留
    # E: Verify link_type preserved
    all_pass = True
    for link in flat_links:
        key = (link['source'], link['target'])
        expected = expected_types.get(key)
        actual = link.get('link_type', 'MISSING')
        if expected and actual != expected:
            print(f"  MISMATCH: {key} expected={expected}, actual={actual}")
            all_pass = False
        elif expected:
            print(f"  OK: {key} link_type={actual}")
        else:
            print(f"  UNEXPECTED: {key} link_type={actual}")

    # Step 3: 二次往返（模拟多轮会话后的 state_merge 复用）
    # E: Second round-trip (simulating state_merge reuse across multiple sessions)
    tree2 = flatten_to_tree(flat_nodes, flat_links)
    flat_nodes2, flat_links2 = flatten_from_tree(tree2)
    print(f"\n[Step 3] Second round-trip: nodes={len(flat_nodes2)}, links={len(flat_links2)}")

    for link in flat_links2:
        key = (link['source'], link['target'])
        expected = expected_types.get(key)
        actual = link.get('link_type', 'MISSING')
        if expected and actual != expected:
            print(f"  ROUND2 MISMATCH: {key} expected={expected}, actual={actual}")
            all_pass = False
        elif expected:
            print(f"  ROUND2 OK: {key} link_type={actual}")

    if all_pass:
        print("\n=== ALL TESTS PASSED ===")
    else:
        print("\n=== SOME TESTS FAILED ===")

    assert all_pass, "link_type round-trip failed"
    return all_pass


def test_link_type_field_name_compatibility():
    """C: 验证 `type` 和 `link_type` 两种字段名都兼容
    E: Verify both `type` and `link_type` field names are compatible"""
    nodes = [
        {"id": "a", "label": "A", "color": "var(--node-blue)"},
        {"id": "b", "label": "B", "color": "var(--node-green)"},
    ]

    # C: tools.py 的输出用 type，前端 G6 用 link_type
    # E: tools.py output uses type, frontend G6 uses link_type
    links_type_field = [{"source": "a", "target": "b", "type": "dashed"}]
    links_link_type_field = [{"source": "a", "target": "b", "link_type": "reference"}]

    for i, links in enumerate([links_type_field, links_link_type_field]):
        tree = flatten_to_tree(nodes, links)
        fn, fl = flatten_from_tree(tree)
        lt = fl[0].get('link_type', 'MISSING')
        print(f"  Test {i+1}: input={'type' if i==0 else 'link_type'}, output=link_type='{lt}'")
        expected = "dashed" if i == 0 else "reference"
        assert lt == expected, f"Test {i+1} failed: expected {expected}, got {lt}"

    print("  Field name compatibility: PASSED")


def test_state_merge_field_normalization():
    """C: 验证 state_merge_with_tree 正确将 LLM 输出的 type 归一化为 link_type
    E: Verify state_merge_with_tree correctly normalizes LLM type field to link_type"""
    print("\n--- Test 3: state_merge field normalization ---")

    # C: 模拟 LLM 输出的 delta（使用 type 字段）
    # E: Simulate LLM delta output (using type field)
    delta = {
        "add_nodes": [
            {"id": "root", "label": "Root", "color": "var(--node-blue)"},
            {"id": "child1", "label": "Child 1", "color": "var(--node-green)"},
            {"id": "child2", "label": "Child 2", "color": "var(--node-yellow)"},
        ],
        "add_links": [
            {"source": "root", "target": "child1", "type": "solid"},
            {"source": "root", "target": "child2", "type": "dashed"},
        ]
    }
    current_map = {"nodes": [], "links": []}

    result = state_merge_with_tree(delta, current_map)
    links = result.get("links", [])

    # C: 验证 type 已被归一化为 link_type
    # E: Verify type has been normalized to link_type
    assert len(links) == 2, f"Expected 2 links, got {len(links)}"
    for link in links:
        assert "link_type" in link, f"Missing link_type in {link}"
        assert "type" not in link, f"Stale type field in {link}"
        assert link["link_type"] in VALID_LINK_TYPES, f"Invalid link_type '{link['link_type']}' in {link}"
    assert links[0]["link_type"] == "solid"
    assert links[1]["link_type"] == "dashed"

    # C: 验证幂等性 — 再次 merge 不会出错
    # E: Verify idempotency — re-merging does not error
    result2 = state_merge_with_tree(delta, result)
    links2 = result2.get("links", [])
    for link in links2:
        assert "link_type" in link
        assert "type" not in link

    # C: 验证缺失 type/link_type 时默认使用 solid
    # E: Verify default to solid when type/link_type missing
    delta_no_type = {
        "add_links": [{"source": "root", "target": "child1"}]
    }
    result3 = state_merge_with_tree(delta_no_type, {"nodes": delta["add_nodes"], "links": []})
    assert result3["links"][0]["link_type"] == "solid", "Expected default solid"

    print("  state_merge field normalization: PASSED")


def test_validate_map_link_type():
    """C: 验证 _validate_map 对 link_type 的合法性检查（回退到 solid）
    E: Verify _validate_map link_type validation (fallback to solid)"""
    from main import _validate_map
    print("\n--- Test 4: _validate_map link_type validation ---")

    # C: 合法 link_type 应通过
    # E: Valid link_type should pass
    valid_links = [
        {"source": "a", "target": "b", "link_type": "solid"},
        {"source": "b", "target": "c", "link_type": "reference"},
    ]
    passed, result = _validate_map({"nodes": [], "links": valid_links})
    assert passed, "Valid link types should pass"
    assert result["links"][0]["link_type"] == "solid"
    assert result["links"][1]["link_type"] == "reference"

    # C: 非法 link_type 应回退到 solid
    # E: Invalid link_type should fall back to solid
    invalid_links = [
        {"source": "a", "target": "b", "link_type": "invalid_type"},
        {"source": "c", "target": "d", "link_type": "unknown"},
    ]
    passed, result = _validate_map({"nodes": [], "links": invalid_links})
    assert passed, "Invalid link types should still pass (silent fallback)"
    for link in result["links"]:
        assert link["link_type"] == "solid", f"Expected solid fallback, got '{link['link_type']}'"

    # C: 缺失 link_type 应保持原样
    # E: Missing link_type should remain unchanged
    no_type_links = [{"source": "a", "target": "b"}]
    passed, result = _validate_map({"nodes": [], "links": no_type_links})
    assert passed
    assert result["links"][0].get("link_type", "solid") == "solid"

    print("  _validate_map link_type validation: PASSED")


if __name__ == "__main__":
    print("=" * 50)
    print("Test 1: Multi-type link round-trip")
    print("=" * 50)
    test_link_type_roundtrip()

    print("\n" + "=" * 50)
    print("Test 2: Field name compatibility")
    print("=" * 50)
    test_link_type_field_name_compatibility()

    print("\n" + "=" * 50)
    print("Test 3: state_merge type→link_type normalization")
    print("=" * 50)
    test_state_merge_field_normalization()

    print("\n" + "=" * 50)
    print("Test 4: _validate_map link_type validation")
    print("=" * 50)
    test_validate_map_link_type()

    print("\n=== ALL TESTS COMPLETE ===")
