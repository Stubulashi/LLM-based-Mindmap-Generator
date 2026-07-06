# 深度优先思维导图生成策略

## Context

当前导图生成存在**宽而浅问题**：LLM 倾向于创建大量顶层概念（各挂1-2个子节点），而非深度挖掘已有分支。虽然 system prompts 已提及"目标深度 >= 3 层"，但语言较弱——缺反面约束、量化标准和后验校验。本次调整以**提示词增强为主、后验校验为辅**，引导 LLM 优先挖掘深层结构。

---

## 修改清单

### 1. [config.py] 新增深度优先配置项

在 `DETAILS_ENRICHMENT_ENABLED` 块后（~L208）插入：

```python
DEPTH_FIRST_ENABLED = os.getenv('DEPTH_FIRST_ENABLED', 'true').lower() in ('true', '1', 'yes')
MIN_TREE_DEPTH = int(os.getenv('MIN_TREE_DEPTH', '3'))
MAX_SIBLINGS_PER_NODE = int(os.getenv('MAX_SIBLINGS_PER_NODE', '6'))
```

- `DEPTH_FIRST_ENABLED=false` 可恢复旧行为
- `MIN_TREE_DEPTH` 提示词中引用此值替代硬编码3
- `MAX_SIBLINGS_PER_NODE` 限制单父节点子节点数

---

### 2. [mindmap_agent.py] 新增 `compute_depth_stats()` 工具函数

在 `mark_tree_meta` 之后（~L190）插入：

```python
def compute_depth_stats(nodes, links) -> dict:
    """计算 max_depth(根=1), avg_depth, depth_distribution, top_level_count(L2节点数),
    shallow_leaves, min_depth。"""
```

复用 parent_id 映射 + 递归缓存。输出样例：
```json
{"max_depth": 4, "avg_depth": 2.5, "depth_distribution": {1:1, 2:3, 3:2, 4:1},
 "top_level_count": 3, "shallow_leaves": 2, "min_depth": 3}
```

---

### 3. [mindmap_agent.py] 增强 MindMapSpecialistAgent 系统提示词

#### 3a. 核心铁律新增"禁止宽而浅"规则

在原有规则2之后插入（~L711）：

```
C: 3. 【禁止宽而浅的结构】严禁创建大量顶层节点后各自只挂一两个子节点。
   - 不合格：Root → A, B, C, D, E, F (6个顶层，各1子节点)
   - 合格：Root → A(L2) → A1(L3) → A1a(L4)
E: 3. [Ban Wide-Shallow] Strictly prohibit many top-level nodes each with 1-2 children.
```

#### 3b. 增强规则4（深度要求）

替换原有"目标深度 >= 3 层"（~L747-756）：

```
C: 【常规绘图规则 — 深度优先策略（核心）】
4. 【深度优先铁律】优先为已有节点挖掘子节点向下延伸，深度 > 宽度。
   目标深度 ≥ {Config.MIN_TREE_DEPTH} 层（根=L1）。
   每个非叶子节点至少 1 个子节点。
   每个节点直接子节点数 ≤ {Config.MAX_SIBLINGS_PER_NODE} 个。
E: [General Drawing Rules — Depth-First Strategy (Core)]
4. [Depth-First Iron Law] Prioritize digging children for existing nodes.
   Target depth ≥ {Config.MIN_TREE_DEPTH} (root=L1). Each non-leaf ≥1 child.
   Max siblings ≤ {Config.MAX_SIBLINGS_PER_NODE}.
```

---

### 4. [mindmap_agent.py] 增强 HierarchyPlanningAgent 提示词

替换 `_get_system_prompt()` 返回内容（~L1012-1035）：

1. 顶层描述改为 `{Config.MIN_TREE_DEPTH}-5` 层
2. 分组铁律规则1增加反例和深度优先语言
3. 每项目数改为 `2-{Config.MAX_SIBLINGS_PER_NODE}`

关键变化：
- 不写"3-5层"，写 `{Config.MIN_TREE_DEPTH}-5` 层
- 增加"不合格：科学, 艺术, 历史, 技术 → 各自一两个概念（宽而浅）"
- 增加"合格：科学 → 物理学 → 力学, 热学（深）"

---

### 5. [mindmap_agent.py] 增强 DeltaGenerationAgent 分组注入提示

修改 `generate()` 中的分组参考文本（~L1137-1145）：

1. "创建 3-5 级深度树结构" → "创建多级深度树结构"
2. 增加"深度优先铁律"段落
3. 明确禁止宽而浅结构

---

### 6. [mindmap_agent.py] 管线后处理 — 深度校验

在 `MindMapPipelineOrchestrator.generate()` 的闭环验证后（~L1915）插入：

- 调用 `compute_depth_stats(final_map.nodes, final_map.links)`
- 写入 debug 文件（`06_depth_check.txt`）
- 若 max_depth < Config.MIN_TREE_DEPTH → logger.warning
- 将 `_depth_stats` 注入返回结果（信息性，不阻断）

---

### 7. [mindmap_agent.py] 单模型模式深度校验

在 `MindMapSpecialistAgent.generate_map_from_context()` 返回前（~L854）：

- 调用 `compute_depth_stats()`
- 若深度不达标 → logger.warning

---

## 验证方法

1. **深度统计函数测试**：手动构造深/浅两组数据，验证统计值正确
2. **日志验证**：运行请求后搜索 `[Depth Check]` 日志
3. **管线返回**：检查返回结果的 `_depth_stats` 字段
4. **不做强制阻断**：深度校验仅记录 warning，不影响用户体验
