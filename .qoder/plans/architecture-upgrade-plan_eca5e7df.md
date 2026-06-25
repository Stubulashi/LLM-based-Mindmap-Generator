# 架构升级方案 v2：全面迁移至 G6 嵌套树 + 后端输出树格式

## 核心变更（与 v1 的关键差异）

| 方面 | v1 原方案 | v2 最终方案 |
|------|----------|------------|
| 坐标管理 | x/y 改为 Optional，后端 auto_layout 填充 | **彻底移除 x/y**，G6 自动计算所有位置 |
| 数据格式 | 后端返回 flat nodes+links | **后端直接输出 G6 嵌套树**（children/_isVirtual/_depth） |
| 布局引擎 | 后端 BFS 手写布局 | G6 `compactBox` / `mindmap` 内置布局 |
| 前端 | 逐步迁移，保留 SVG 过渡 | **一次性彻底替换**渲染层为 G6 |

---

## 任务一：schema.py / tools.py — 数据模型重构（移除 x/y）

### 改动：`/home/akku/ai-mindmap-agent/schema.py`
- Node: x/y 字段完全移除；id 改为 str；新增 children 字段（用于树结构）
- Link: 移除（树结构中 links 由 children 隐式表达，但保留 flat links 用于增量更新协议）
- 新增 TreeMapData 模型，包含 tree（嵌套树）和 flat（nodes+links 用于增量回传）

### 改动：`/home/akku/ai-mindmap-agent/tools.py`
- `add_nodes`: 将 x 和 y 从 required 移除，也不出现在 properties 中
- `add_links.type`: 枚举扩展为 solid/dashed/dotted/reference/contrast
- LLM system prompt 中移除所有坐标分布规则

---

## 任务二：mindmap_agent.py — 新增 flat→tree 转换 + 移除坐标逻辑

### 改动：`/home/akku/ai-mindmap-agent/mindmap_agent.py`
- 新增 `flatten_to_tree(nodes, links)` 函数：flat list → G6 嵌套树
  - 从 links 构建 children_map
  - 识别根节点（无父节点的节点）
  - 多根节点包裹 `_isVirtual: true` 虚拟根
  - 递归构建 children 数组
- 新增 `mark_tree_meta(root, depth)` 函数：标记 `_isRoot`/`_depth`/`_hasChildren`
- `state_merge()` 返回的 merged map 调用 `flatten_to_tree()` 后同时返回 flat 和 tree
- system prompt 中移除坐标分布规则（"父在上/子在下"等）

---

## 任务三：mcp_server.py — 工具返回值适配树格式

### 改动：`/home/akku/ai-mindmap-agent/mcp_server.py`
- `modify_mind_map_v2`: 返回 `{"tree": [...], "nodes": [...], "links": [...]}`
- `modify_mind_map`: 同上
- 两工具返回同时包含 tree（前端 G6 消费）和 flat（前端 current_map 回传用）

---

## 任务四：index.html — 全面迁移至 AntV G6 v5

### 目标：最大限度简化前端代码

### 移除的代码（约 250 行）
1. `<svg>` 连线层模板（line 249-259）
2. 手动节点 `<div>` 渲染（line 260-267）
3. `computedLinks` 全部逻辑（line 862-1000）— G6 自动绘制连线
4. `resolveOverlaps` 碰撞检测（line 754-775）— G6 布局引擎接管
5. `svgSize` 计算（line 862-870）
6. `NODE_HALF_W`/`NODE_HALF_H` 常量（line 857-858）
7. 所有诊断工具函数 `__testLines`/`__clearTest`/`__diagFull`（line 1006-1121）
8. 节点拖拽中的坐标更新逻辑—改为 G6 `drag-node` 行为

### 新增的代码（约 150 行）
1. G6 CDN 引入
2. G6 图实例创建（`new Graph({...})`）
3. 布局配置（`compactBox` / `mindmap`）
4. 节点/边样式配置函数
5. `collapse-expand` 行为注册
6. `drag-node` 行为注册
7. `node:click` → 打开详情面板 + 子树对话入口
8. `treeRoots` ref 替换 `nodes`/`links` ref，`graph.setData()` 绑定

### 数据流
```
后端返回 {tree, nodes, links}
  → tree 直接传入 graph.setData(tree)
  → nodes/links 保留用于 current_map 回传后端
```

### 保留的代码（约 800 行）
- 全部聊天 UI、设置面板、转录面板
- 录音/播放逻辑
- Vue 响应式状态管理
- `sendMessage`/`processAudioUpload` 等业务流程（`current_map` 改为用 flat nodes+links 构建）

---

## 任务五：main.py — 验证层适配

### 改动：`/home/akku/ai-mindmap-agent/main.py`
- `_validate_map()`: 同时验证 tree 和 nodes/links 字段存在性
- `/chat` 返回增加 tree 字段
- 前端 current_map 回传仍用 flat 格式（nodes+links）

---

## 实施顺序

```
任务一（schema.py + tools.py 移除 x/y）
  → 任务二（mindmap_agent.py flat→tree 转换 + 移除坐标 prompt）
    → 任务三（mcp_server.py 适配返回值）
      → 任务四（index.html G6 迁移）【最大改动】
        → 任务五（main.py 验证适配）
```

## 预期最终效果

- **index.html 减少约 250 行**（移除手动 SVG/坐标/碰撞/诊断代码）
- **LLM 不再输出坐标**，token 消耗降低
- **G6 自动树布局**，层级清晰符合 Evaluation_Schema.md 标准
- **一键展开/折叠**，G6 内置行为
- **自由拖拽**，G6 内置 drag-node
- **多类型连线**，通过 G6 edge.style 区分
- **后端输出 G6 嵌套树**，前端零转换开销
