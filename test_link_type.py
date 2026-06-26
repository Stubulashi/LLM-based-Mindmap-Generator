"""C: 测试 link_type 在 flatten_to_tree ↔ flatten_from_tree 往返中不丢失
E: Test that link_type is preserved through flatten_to_tree ↔ flatten_from_tree round-trip"""
import json
from mindmap_agent import flatten_to_tree, flatten_from_tree


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


if __name__ == "__main__":
    print("=" * 50)
    print("Test 1: Multi-type link round-trip")
    print("=" * 50)
    test_link_type_roundtrip()

    print("\n" + "=" * 50)
    print("Test 2: Field name compatibility")
    print("=" * 50)
    test_link_type_field_name_compatibility()

    print("\n=== ALL TESTS COMPLETE ===")
