# AI MindMap Agent — 五项重构/修复统一实施计划

> 任务范围: 弹窗 Bug 修复 · 本地术语缓存 · Wikipedia-API 官方库 · 低参数 LLM · MCP Server 合并
> 推荐执行顺序: **3 → 4 → 1 → 2 → 5**（先做无依赖的基础设施,再做集成）
> 关键决策(已与用户确认): ① 直接删除旧 dict_underline_server.py / dictionary_server.py;② 缓存预取在 annotate_terms Tool 内部串行执行;③ 弹窗修复采用 document capture 委托。

---

## Context

AI MindMap Agent 项目通过多 MCP Server + 前端 Vue 3 + AntV G6 v5 构建对话式思维导图生成工具。当前的 `dict_underline_server.py` 与 `dictionary_server.py` 各自独立启动为子进程,`/define` 路由每次点击术语都会重新调用 Wikipedia + LLM + Free Dictionary,既慢又贵;术语下划线点击事件偶尔无法弹窗;Wikipedia 调用走裸 `httpx` 而非官方 `wikipediaapi` 库;标注/定义类 LLM 调用一律使用主模型,token 浪费严重。本计划一次性解决这五项问题,合并两个独立 Server 到主 `mcp_server.py` 简化进程模型,同时把 wikipediaapi、light LLM、缓存预取全部集成进 mcp_server。

---

## 任务 3 — 接入 wikipediaapi 官方库（先做,无依赖）

### 修改文件

| 文件 | 改动 |
|---|---|
| `/home/akku/ai-mindmap-agent/requirements.txt` | 追加 `wikipedia-api>=0.7.0` |
| `/home/akku/ai-mindmap-agent/config.py` | line 198 后新增 `WIKIPEDIA_USER_AGENT` / `WIKIPEDIA_RATE_LIMIT` |
| `/home/akku/ai-mindmap-agent/.env` | 末尾新增 Wikipedia 配置段 |
| `/home/akku/ai-mindmap-agent/dict_underline_server.py` | line 11 import + line 44-55 全局变量 + line 464-527 `_fetch_wikipedia_summary` |

### 关键代码改动

**config.py**（line 198 后追加）:
```python
WIKIPEDIA_USER_AGENT = os.getenv('WIKIPEDIA_USER_AGENT') or 'AI-MindMap-Agent/1.0 (contact@example.com)'
WIKIPEDIA_RATE_LIMIT = float(os.getenv('WIKIPEDIA_RATE_LIMIT', '1.0'))
```

**dict_underline_server.py** — 替换 `_fetch_wikipedia_summary` (line 464-527):
- 初始化 `wikipediaapi.Wikipedia(user_agent=Config.WIKIPEDIA_USER_AGENT, language=...)` 全局实例
- `page = _wiki_wiki.page(term)` → `page.exists()` 判断 → `page.summary` 提取
- 异常处理 `wikipediaapi.DisambiguationError`(取 `e.options[0]` 降级)与 `PageError`
- 简单 rate limiter:`threading.Lock` + `time.sleep(max(0, 1.0/RATE_LIMIT - elapsed))`
- 新增 `_fetch_wikipedia_page(term, language)` 返回 `WikipediaPage`,供 `get_definition` 取 `page.fullurl`

**验证**: 启动 `python dict_underline_server.py` 后 `call_tool('get_definition', {'term': 'Python'})` 应返回 `wikipedia_definition` 非空且 `wikipedia_url = 'https://en.wikipedia.org/wiki/Python_(programming_language)'`;测 `PageError`(不存在的词)与 `DisambiguationError`(`'Mercury'`)路径。

---

## 任务 4 — 新增低参数 LLM 接口（独立,先做）

### 修改文件

| 文件 | 改动 |
|---|---|
| `/home/akku/ai-mindmap-agent/.env` | 末尾新增 `LLM_LIGHT_*` 段(API_KEY/BASE_URL/MODEL/ENABLED) |
| `/home/akku/ai-mindmap-agent/config.py` | line 138 后追加 LLM_LIGHT 配置块 |
| `/home/akku/ai-mindmap-agent/dict_underline_server.py` | line 44-55 全局变量 + line 602-655 `_generate_llm_definition` + line 743-746 `_lookup_dictionary_impl` 调用 |
| `/home/akku/ai-mindmap-agent/dictionary_server.py` | line 99-189 `_lookup_dictionary_impl` 函数签名增加 `model` 参数 |

### 关键改动

**config.py**:
```python
LLM_LIGHT_MODEL = os.getenv('LLM_LIGHT_MODEL') or None
LLM_LIGHT_BASE_URL = os.getenv('LLM_LIGHT_BASE_URL') or LLM_BASE_URL
LLM_LIGHT_API_KEY = os.getenv('LLM_LIGHT_API_KEY') or LLM_API_KEY
LLM_LIGHT_ENABLED = os.getenv('LLM_LIGHT_ENABLED', 'true' if LLM_LIGHT_MODEL else 'false').lower() in ('true','1','yes')
```

**dict_underline_server.py**:
- 新增 `light_llm_client` 全局变量,`_init_models()` 中按 `Config.LLM_LIGHT_ENABLED` 初始化
- `_generate_llm_definition` 改为: `client, model = (light_llm_client, LLM_LIGHT_MODEL) if light_llm_client else (llm_client, LLM_MODEL)`;失败时自动 fallback 到主模型
- `_lookup_dictionary_impl` 调用改为传入 `(light_llm_client if light_llm_client else llm_client)`

**dictionary_server.py**:
- `_lookup_dictionary_impl` 签名增加 `model: str | None = None`,调用方未传时内部按 `Config.LLM_LIGHT_*` 选择

**验证**: 设置 `LLM_LIGHT_MODEL=deepseek-v4-flash`,启动后 stderr 应有 "轻量 LLM 客户端就绪";调用 `get_definition` 触发 LLM fallback 时日志应含 `mode=light`;关闭 `LLM_LIGHT_MODEL` 后回退主模型且日志无 `mode=light`。

---

## 任务 1 — 修复弹窗 Bug

### 修改文件

`/home/akku/ai-mindmap-agent/index.html`

### 根因

G6 v5 的 HTML 节点把 HTML 渲染到 G6 内部管理的 `<foreignObject>` 中,**不在 `#g6-container` 子树内**(P0);`graph.on('node:click', ...)` 内部 stopPropagation 影响 capture 之外的外层监听(P1);`activeNode` 详情面板 z-30 + `position: absolute` 形成 stacking context 可能遮挡 z-50 popup(P2);`.g6-node-label` 容器 `white-space: nowrap; overflow: hidden` 截断术语命中区域(P3)。

### 关键改动

**替换 line 1693-1727** 内的 `onMountedWithG6` 事件委托为 document 级 capture:
```javascript
const handleAnnoTermClick = (e) => {
    const annoEl = e.target?.closest?.('.anno-term');
    if (!annoEl) return;
    e.stopPropagation();
    e.preventDefault();
    const term = annoEl.dataset.term;
    if (!term) return;
    showDefinition(term, e.clientX, e.clientY);
};
document.addEventListener('click', handleAnnoTermClick, true);
document.addEventListener('pointerdown', (e) => {
    if (e.target?.closest?.('.anno-term')) e.stopPropagation();
}, true);
```

**showDefinition (line 1521-1560)** 增加坐标偏移 `x + 12, y + 18`,并在文件顶部加 `annotationCache` ref;缓存命中时直接填充 `definitionPopup.value` 并标记 `from_cache: true`,**不**调用 `/define`。

**line 128 CSS** `.definition-popup` 的 `z-index` 改为 `60`,确保盖住 z-30 的 activeNode 面板。

**验证**: 浏览器点击 G6 节点 label 与 activeNode 详情面板中的下划线术语,均能弹出 popup;Console 显示 `[Popup Debug]` 一次性 z-index 日志;Network 面板 `/define` 仅在 cache miss 时被调用。

---

## 任务 2 — 本地缓存二级菜单展开内容

### 修改文件

| 文件 | 改动 |
|---|---|
| `/home/akku/ai-mindmap-agent/dict_underline_server.py` | `annotate_terms` (line 288-457) 末尾追加预取逻辑 |
| `/home/akku/ai-mindmap-agent/main.py` | `/annotate` 路由 (line 506-531) 入口创建缓存目录 |
| `/home/akku/ai-mindmap-agent/index.html` | line 1487-1517 `triggerAnnotation` 接收 `prefetched_cache`;`showDefinition` 优先读缓存 |

### 关键改动

**dict_underline_server.py** — `annotate_terms` 在 `_validate_annotations` 之后、`return output` 之前:
```python
all_terms: set[str] = set()
for ann_list in cleaned.values():
    for ann in ann_list:
        if ann.get('term'):
            all_terms.add(ann['term'])

cache_index: dict[str, dict] = {}
for term in sorted(all_terms):
    defn = get_definition(term=term, detail_level=detail_level,
                          language=user_language, session_ts=session_ts)
    cache_index[term] = {
        "wikipedia_definition": defn.get("wikipedia_definition"),
        "wikipedia_url": defn.get("wikipedia_url"),
        "llm_definition": defn.get("llm_definition"),
        "ipa": defn.get("ipa"),
        "literal_meaning": defn.get("literal_meaning"),
        "source": defn.get("source"),
    }

if session_ts:
    cache_dir = os.path.join(Config.DEBUG_OUTPUT_DIR, session_ts, "underline_cache")
    os.makedirs(cache_dir, exist_ok=True)
    with open(os.path.join(cache_dir, "underline_cache.json"), 'w', encoding='utf-8') as f:
        json.dump({
            "session_ts": session_ts,
            "user_language": user_language,
            "detail_level": detail_level,
            "node_count": len(cleaned),
            "term_count": len(cache_index),
            "by_term": cache_index,
            "by_node": {nid: [a["term"] for a in anns if a.get("term")]
                       for nid, anns in cleaned.items()},
        }, f, ensure_ascii=False, indent=2)

write_debug_file(filename="06_underline_cache.json",
                 content={"session_ts": session_ts, "term_count": len(cache_index),
                          "by_term": cache_index}, session_ts=session_ts, is_json=True)

output["prefetched_cache"] = cache_index
```

**main.py /annotate 路由**:
```python
session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
cache_dir = os.path.join(Config.DEBUG_OUTPUT_DIR, session_ts, "underline_cache")
os.makedirs(cache_dir, exist_ok=True)
```

**index.html triggerAnnotation**:
```javascript
const data = await response.json();
if (data.annotations) annotations.value = data.annotations;
if (data.prefetched_cache) annotationCache.value = data.prefetched_cache;
nextTick(() => updateG6Data());
```

**index.html showDefinition** (line 1521 替换):
- 顶部 `const annotationCache = ref({})`
- 命中缓存时直接 `definitionPopup.value = { ..., from_cache: true }` 并 return
- 未命中时调用 `/define` 并把响应写入 `annotationCache.value[term]`

**验证**: 调用 `/annotate` 后 `debug_output/<session_ts>/underline_cache/underline_cache.json` 与 `06_underline_cache.json` 存在;`term_count` 等于标注去重后的术语数;浏览器点击已缓存术语,Network **无** `/define` 请求,popup 标注 `(cache hit)`。

---

## 任务 5 — 合并两个 MCP Server 到 mcp_server.py

### 修改文件

| 文件 | 改动 |
|---|---|
| `/home/akku/ai-mindmap-agent/mcp_server.py` | 末尾追加章节 7: light_llm_client 全局 + wikipediaapi 初始化 + 三个 Tool |
| `/home/akku/ai-mindmap-agent/dict_underline_server.py` | **删除** |
| `/home/akku/ai-mindmap-agent/dictionary_server.py` | **删除** |
| `/home/akku/ai-mindmap-agent/main.py` | 移除 `dict_underline_client` 全局与 lifespan 启动逻辑;`/annotate` `/define` 改用 `mcp_client` |
| `/home/akku/ai-mindmap-agent/config.py` | 注释 line 194-196 `DICT_UNDERLINE_SERVER_SCRIPT`(已废弃) |
| `/home/akku/ai-mindmap-agent/MCP_Architecture_Deep_Dive.md` | 更新架构图、lifespan 说明、端到端流程图 |
| `/home/akku/ai-mindmap-agent/README.md` | 标注 MCP Server 数量从 2 变 1,启动命令无需变化 |

### mcp_server.py 末尾新增结构

**全局变量**:
```python
light_llm_client = None  # 任务 4
_wiki_wiki: wikipediaapi.Wikipedia | None = None  # 任务 3
_wiki_rate_lock = None
```

**`_init_models` 末尾追加**:
```python
# 轻量 LLM (任务 4)
if Config.LLM_LIGHT_ENABLED and Config.LLM_LIGHT_MODEL:
    light_llm_client = OpenAI(api_key=Config.LLM_LIGHT_API_KEY,
                              base_url=Config.LLM_LIGHT_BASE_URL)
else:
    light_llm_client = None

# Wikipedia (任务 3)
import threading, time
_wiki_rate_lock = threading.Lock()
_wiki_wiki = wikipediaapi.Wikipedia(user_agent=Config.WIKIPEDIA_USER_AGENT,
                                    language=Config.WIKIPEDIA_LANGUAGE)
```

**Helper 函数**(全部从 dict_underline_server.py 移植,带 light 客户端优先逻辑):
- `_safe_json_parse(text)` — line 62-104
- `_call_llm_tool(...)` — line 111-178
- `_validate_annotations(raw, current_map)` — line 185-281
- `_fetch_wikipedia_summary(term, language)` — §3 改造版
- `_fetch_wikipedia_page(term, language)` — 返回 WikipediaPage
- `_fetch_free_dictionary(term)` — line 534-595
- `_generate_llm_definition(term, detail_level, language)` — §4 改造版(light 优先)
- `_lookup_dictionary_impl(term, llm_client_override=None, model_override=None, session_ts=None)` — dictionary_server.py 移植 + light 优先

**三个 Tool**:
- `@mcp.tool() annotate_terms(...)` — 完整移植 line 288-457 + 任务 2 预取逻辑
- `@mcp.tool() get_definition(...)` — 完整移植 line 662-797,使用 `page.fullurl` 取 wikipedia_url
- `@mcp.tool() lookup_dictionary(term, session_ts=None)` — 委托到 `_lookup_dictionary_impl`

**mcp_server.py 启动入口** (`__main__` 段 line 701-773) 需同步处理 `SKIP_HEAVY_INIT` 模式下的 light_llm_client 与 _wiki_wiki 初始化(参照 line 716-768 现有 Inspector 模式分支)。

### main.py 改动

**全局变量** (line 23):
```diff
- dict_underline_client: MCPMindMapClient | None = None
+ # 任务 5: dict_underline_client 已删除,统一使用 mcp_client
```

**lifespan** (line 198-269) 删除 `if Config.ANNOTATION_ENABLED` 整个分支及对应 `dict_underline_client` 关闭逻辑。

**/annotate 与 /define 路由** (line 506-531, 543-567):
- 删除 `client=dict_underline_client` 参数
- `if dict_underline_client is None` 改为 `if mcp_client is None`
- 在 `/annotate` 路由入口创建 `os.path.join(Config.DEBUG_OUTPUT_DIR, session_ts, "underline_cache")`

### 删除文件

`rm /home/akku/ai-mindmap-agent/dict_underline_server.py`
`rm /home/akku/ai-mindmap-agent/dictionary_server.py`

### 验证

1. **进程数**: `ps aux | grep mcp_server.py | grep -v grep | wc -l` → 应为 1(从原来的 2 减为 1)
2. **Tool 列表**: `echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python mcp_server.py` → 8 个 Tool(原 5 + 新 3)
3. **路由兼容**: `curl` 依次调用 `/chat /annotate /define /upload_audio` 全部 200,响应结构与改造前一致
4. **缓存**: 调 `/annotate` 后 `debug_output/<session_ts>/underline_cache/underline_cache.json` 存在
5. **回归**: 聊天、绘图、音频、标注、定义全部功能正常

---

## 端到端验证矩阵

| 任务 | 验证手段 | 通过标准 |
|---|---|---|
| 任务 3 | `python -c "from dict_underline_server import _fetch_wikipedia_summary; print(_fetch_wikipedia_summary('Python','en')[:50])"` | 返回英文摘要字符串 |
| 任务 4 | 启动后 stderr 含 "轻量 LLM 客户端就绪",`get_definition` 触发 LLM 时日志含 `mode=light` | 命中 |
| 任务 1 | 浏览器点击 G6 节点 label 与详情面板中的 `.anno-term` | 均弹 popup,Network `/define` 被调用 |
| 任务 2 | 调 `/annotate` 后 `underline_cache.json` 存在,`term_count > 0`;前端 popup 显示 `(cache hit)` | 命中 |
| 任务 5 | `ps aux | grep mcp_server | wc -l` = 1;8 个 Tool 全部可调 | 命中 |

## 关键文件路径总览

```
/home/akku/ai-mindmap-agent/
├── mcp_server.py                  # 任务 5 合并目标,任务 3/4 集成点
├── dict_underline_server.py       # 任务 5 删除
├── dictionary_server.py           # 任务 5 删除
├── main.py                        # 任务 5 lifespan + 路由改造
├── config.py                      # 任务 3/4 新增配置
├── .env                           # 任务 3/4 新增环境变量
├── requirements.txt               # 任务 3 追加 wikipedia-api
├── index.html                     # 任务 1 修复 + 任务 2 前端缓存
├── MCP_Architecture_Deep_Dive.md  # 任务 5 文档更新
└── README.md                      # 任务 5 文档更新
```

## 实施检查清单

- [ ] 备份:`cp -r ai-mindmap-agent ai-mindmap-agent.bak-$(date +%Y%m%d)`
- [ ] `pip install wikipedia-api` 装到 venv
- [ ] `python -c "import wikipediaapi; print(wikipediaapi.__version__)"` ≥ 0.7.0
- [ ] 确认 `.env` 中 `LLM_API_KEY` 有效
- [ ] 每个任务完成后立即进行对应的端到端验证
- [ ] 任务 5 前先确认任务 3/4 已稳定(避免合并时多个差异叠加)
- [ ] 任务 5 完成后,`/annotate` 和 `/define` 路由行为需与改造前完全一致
