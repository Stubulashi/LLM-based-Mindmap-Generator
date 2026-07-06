# 关系类型自动推断功能实现计划

## Context

当前系统虽在 `tools.py` 的 `add_links` Schema 中定义了 `type` 枚举字段（solid/dashed/dotted/reference/contrast），且前端 index.html 已完整支持全部 5 种连线样式渲染，但缺失两个关键环节：

1. **LLM 未被引导**：`_get_system_prompt()`、`_build_react_prompt()` 和 `DeltaGenerationAgent.generate()` 中均无任何关于连线类型选择的指令，导致 LLM 始终使用默认 `type` 或无值
2. **字段名未归一化**：LLM function calling 输出使用 `type` 字段名（因 tools.py Schema 如此定义），但系统内部使用 `link_type` 字段名，`state_merge()` 入口处缺少归一化

本计划通过 6 步修改实现全链路支持：LLM 推理 → 字段归一化 → 合法性校验 → 自动化测试。

## 改动清单

### 1. `state_merge()` — 添加 `type` → `link_type` 归一化

**文件**: `/home/akku/ai-mindmap-agent/mindmap_agent.py`, 行 48-53

在 `add_links` 循环中，追加 link 到 `links_list` 之前添加归一化：

- `type` 存在时 `pop()` 取出，赋值给 `link_type`（幂等：后续调用不存在 `type` 键）
- `type` 和 `link_type` 均缺失时默认 `"solid"`

```python
for l in delta.get('add_links', []):
    lt = l.pop('type', None) or l.get('link_type') or 'solid'
    l['link_type'] = lt
    if not any(...):
        links_list.append(l)
```

### 2. `_get_system_prompt()` — 新增规则 5b（连线类型选择）

**文件**: `/home/akku/ai-mindmap-agent/mindmap_agent.py`, 行 845-846 之间

在规则 5（"使用 add_links 连接父子节点"）之后、规则 6（"不要重复创建"）之前，插入约 20 行的中英双语规则 5b，详细说明 5 种 `type` 的语义和使用场景。

### 3. `_build_react_prompt()` — ReAct 步骤补充连线类型指导

**文件**: `/home/akku/ai-mindmap-agent/mindmap_agent.py`, 行 881-890

在步骤 2 的 `step2_cn`/`step2_en` 末尾追加连线类型选择指导（v1 单模型 + v2 管线各 2 处）：

- 行 882(v2_cn): `" ...并为需要建立的关系选择正确的连线 type（solid/dashed/dotted/reference/contrast）"`
- 行 883(v2_en): 对应英文
- 行 888(v1_cn): 同上
- 行 890(v1_en): 同上

### 4. `DeltaGenerationAgent.generate()` — 分组参考中追加连线类型指导

**文件**: `/home/akku/ai-mindmap-agent/mindmap_agent.py`, 行 1262-1265 之间

在 `extra_parts` 的分组参考块末尾（深度优先铁律之后、`group_summary` 之前），追加约 6 行的连线类型选择指导。

### 5. `main.py` — `_validate_map()` 添加 link_type 合法性校验

**文件**: `/home/akku/ai-mindmap-agent/main.py`, 行 68-69 之间

在现有 nodes/links 存在性检查之后，新增 link_type 校验循环：仅允许 `solid/dashed/dotted/reference/contrast` 之一，非法值回退到 `"solid"` 并记录 `logger.warning`。

### 6. `test_link_type.py` — 新增 2 个测试函数

**文件**: `/home/akku/ai-mindmap-agent/test_link_type.py`, 文件末尾

- **`test_state_merge_field_normalization()`**: 验证 `type` → `link_type` 归一化、幂等性、缺失默认值
- **`test_validate_map_link_type()`**: 验证合法值通过、非法值回退到 solid

## 无需修改

- `ConceptExtractionAgent`（阶段1）：只提取概念，不生成连线
- `HierarchyPlanningAgent`（阶段2）：只规划分组，不生成连线
- `index.html`（前端）：已完整支持全部 5 种连线样式
- `tools.py`：Schema 定义正确，无需修改
- `schema.py`：定义正确，无需修改

## 验证方式

1. **单元测试**：运行 `python test_link_type.py` 验证 4 个测试全部通过
2. **端到端验证**：启动服务，发送请求触发 `modify_mind_map_v2`，检查返回的 `links` 中 `link_type` 字段值正确
3. **降级验证**：强制设置非法 `link_type`，确认后端回退到 `solid` 并记录 warning 日志
