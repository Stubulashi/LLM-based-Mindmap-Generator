# 定义弹窗溢出修复 + 边类型图例分析计划

## 上下文

### 任务一：定义弹窗（Definition Popup）溢出修复
当前定义弹窗（`.definition-popup`）使用 `position: fixed` 定位，但当弹窗内容过长且触发位置位于屏幕下半部分时，弹窗底部会溢出视口，用户无法滚动查看。根本原因有两个：
1. CSS 中缺少 `max-height` 和 `overflow-y` 控制
2. JS 位置计算中 `showDefinition` 函数使用硬编码 400px，缺乏动态边界约束和向上翻转逻辑

### 任务二：线段类型图例分析
G6 图的边使用 `type: 'cubic-horizontal'` 单一曲线类型，但通过 `link_type` 字段区分了 5 种语义类型，各具不同颜色、虚线样式、箭头和标签。需要分析这些类型并在必要时给出图例方案。

---

## 任务一：定义弹窗溢出修复

### 涉及文件
- **主要修改**：`/home/akku/ai-mindmap-agent/index.html`

### 修改步骤

#### Step 1：CSS 添加 `max-height` 和 `overflow-y`
**位置**：`.definition-popup`（第122-132行）

在 `.definition-popup` 中添加：
```css
max-height: 60vh;
overflow-y: auto;
```
确保弹窗高度不超过视口60%，超出部分可滚动。保留现有 `position: fixed`、`max-width: 380px` 等属性不变。

#### Step 2：优化 `showDefinition` 位置计算
**位置**：第1658-1659行

**当前代码**：
```js
const popupX = Math.min((x || 0) + 12, window.innerWidth - 380);
const popupY = Math.min((y || 0) + 18, window.innerHeight - 400);
```

**问题**：
- `popupY` 使用硬编码 400 作为预估弹窗高度，不准确
- 缺少向上翻转逻辑：当术语位于屏幕下方时，弹窗应在术语**上方**弹出

**修复方案**：
1. 预估弹窗最大高度为 `60vh`（与 CSS 一致），加上 padding 等 ≈ `60vh + 60px`
2. 如果 `y + 18 + estimatedHeight > window.innerHeight`，则将弹窗底部与术语位置对齐（向上弹出）
3. 确保 `popupY` 最小值不低于 10px（防止顶部溢出）
4. 拖拽的 `onDragPopup`（第1779行）已有 `Math.max(0, ...)` 和 `Math.min(..., window.innerHeight - 100)` 保护，无需修改

**新逻辑**：
```js
const popupX = Math.min((x || 0) + 12, window.innerWidth - 380);
const estimatedHeight = window.innerHeight * 0.6 + 60; // 60vh + padding
let popupY = (y || 0) + 18;
if (popupY + estimatedHeight > window.innerHeight) {
    // 向上弹出：弹窗底部对齐术语位置上方
    popupY = Math.max(10, (y || 0) - estimatedHeight + 10);
}
```

#### Step 3：验证不破坏现有功能
- **拖拽功能**（`startDragPopup` / `onDragPopup` / `stopDragPopup`，第1762-1787行）：拖拽使用独立的 `definitionPopup.value.x/y`，与初始定位逻辑解耦，不受影响
- **缓存逻辑**（`annotationCache`，第1663-1741行）：仅修改位置计算，不涉及缓存读写
- **加载动画**（第520行 `v-if="definitionPopup.loading"`）：不受影响
- **Wikipedia 截断**（`truncateWikipediaDefinition`，第681-695行）：不受影响

#### Step 4：验证方法
1. 启动服务，打开画布
2. 点击画布中任意下划线标注术语，观察弹窗位置
3. 特意点击屏幕右下角区域的术语，观察弹窗是否向上弹出
4. 拖拽弹窗确认功能正常
5. 确认弹窗内容超出 60vh 时出现滚动条

---

## 任务二：线段类型图例分析

### 分析结果

#### 1. 当前边配置（`index.html` 第1131-1163行）

G6 的 `edge` 配置使用单一 `type: 'cubic-horizontal'`，但通过 `link_type` 字段区分语义，每种类型有独立的视觉样式：

| link_type | 颜色 | 虚线样式 | 末端箭头 | 标签 | 含义 |
|-----------|------|----------|----------|------|------|
| `solid` (默认) | `#3b82f6` (蓝) | 无 | 无 | (空) | 默认连线 |
| `dashed` | `#94a3b8` (灰) | `[6, 4]` | 无 | 关联 | 关联关系 |
| `dotted` | `#a78bfa` (紫) | `[2, 4]` | 无 | 弱关联 | 弱关联 |
| `reference` | `#10b981` (绿) | 无 | 有箭头 | 引用 | 引用关系 |
| `contrast` | `#f59e0b` (琥珀) | 无 | 有箭头 | 对比 | 对比关系 |

#### 2. 实际使用的类型数量
项目中共有 **5 种语义类型**，通过 `link_type` 字段区分。后端 `schema.py`（第42行）也定义了相同的默认值。`test_link_type.py` 验证了所有类型在 `flatten_to_tree` / `flatten_from_tree` 往返中的完整性。

#### 3. 图例必要性评估
**结论：有必要添加图例。** 理由：
- 5 种不同类型的视觉差异明显（颜色、虚线、箭头、标签），但用户需要主动悬停或点击才能识别含义
- 当前边标签（"关联"、"弱关联"等）仅在虚线/引用/对比边上显示，而 `solid` 类型没有标签——用户无法直观知道蓝色实线是"默认连线"
- 画布上可以同时出现多种边类型，图例能帮助用户快速理解导图结构
- `reference` 和 `contrast` 带有末端箭头，与视觉流向相关，值得解释

#### 4. 图例实现方案（简短）

在 `index.html` 中添加一个固定位置的图例组件：

**位置建议**：画布右下角（避开弹窗和工具栏），使用 `position: fixed`

**技术实现**：
1. 在 Vue 模板中添加一个条件渲染的图例容器（`.edge-legend`）
2. 用 `v-show` 或 `v-if` 控制显示/隐藏（默认显示，可关闭）
3. 图例内容为 5 行，每行包含：
   - 一个小色块 + 对应线型示例（用 SVG 或 CSS 模拟）
   - 类型中文名称
   - 简短含义说明

**CSS 要点**：
- `position: fixed; bottom: 20px; right: 20px; z-index: 50;`
- 半透明背景、圆角、小字号
- 不影响画布交互（`pointer-events: auto`）

**数据结构**（静态配置，无需后端）：
```js
const EDGE_LEGEND_ITEMS = [
    { type: 'solid', color: '#3b82f6', label: '默认连线', dash: [], arrow: false },
    { type: 'dashed', color: '#94a3b8', label: '关联', dash: [6, 4], arrow: false },
    { type: 'dotted', color: '#a78bfa', label: '弱关联', dash: [2, 4], arrow: false },
    { type: 'reference', color: '#10b981', label: '引用', dash: [], arrow: true },
    { type: 'contrast', color: '#f59e0b', label: '对比', dash: [], arrow: true },
];
```

---

## 文件修改清单

| 文件 | 修改内容 |
|------|----------|
| `index.html` | 1. `.definition-popup` 添加 `max-height: 60vh; overflow-y: auto`（第122-132行） |
| `index.html` | 2. `showDefinition` 函数优化位置计算（第1658-1659行） |
| `index.html` | 3. 添加图例 HTML 模板和样式（新代码） |

仅修改 `index.html` 一个文件，涉及 3 处改动。

---

## 验证方法

### 任务一验证
1. 运行 `python main.py` 启动服务
2. 在浏览器中打开画布
3. 选择一个位于画布右下方的下划线术语，点击触发定义弹窗
4. **预期**：弹窗向上弹出，不溢出视口底部
5. 拖拽弹窗确认功能正常
6. 验证滚动条在内容超长时出现

### 任务二验证
1. 在浏览器中打开画布
2. 观察画布右下角是否显示图例组件
3. 确认 5 种边类型的颜色、样式示例与画布中实际边一致
4. 确认图例可关闭/重新显示
