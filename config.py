import os  
from dotenv import load_dotenv
from pathlib import Path

# C: 加载 .env 文件
# E: Load the .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """
    C: 配置管理类
       LLM_* 变量支持任意 OpenAI 兼容的模型提供商（DeepSeek / OpenAI / 本地模型等）。
       优先级: LLM_* 环境变量 > DEEPSEEK_* 环境变量 > 默认值(DeepSeek)。
       用户只需修改 .env 中的 LLM_* 变量即可切换提供商，无需改动任何代码。
    E: Configuration management class
       LLM_* variables support any OpenAI-compatible model provider (DeepSeek / OpenAI / local models etc.).
       Priority: LLM_* env vars > DEEPSEEK_* env vars > defaults (DeepSeek).
       Users only need to modify LLM_* in .env to switch providers, no code changes needed.
    """
    
    # ---------------------------------------------------------
    # C: 通用 LLM 配置（主要使用这些变量）
    #    设置方法：在 .env 中定义 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
    #    如果不设置，自动回退到 DEEPSEEK_* 变量（向后兼容）
    # E: Generic LLM config (use these primarily)
    #    Set in .env: LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
    #    If not set, auto-fallback to DEEPSEEK_* vars (backward compatible)
    # ---------------------------------------------------------
    LLM_API_KEY = (
        os.getenv('LLM_API_KEY')
        or os.getenv('DEEPSEEK_API_KEY')
    )
    LLM_BASE_URL = (
        os.getenv('LLM_BASE_URL')
        or os.getenv('DEEPSEEK_BASE_URL')
        or 'https://api.deepseek.com'
    )
    LLM_MODEL = (
        os.getenv('LLM_MODEL')
        or os.getenv('DEEPSEEK_MODEL')
        or 'deepseek-chat'
    )
    
    # ---------------------------------------------------------
    # C: DeepSeek 专用变量（向后兼容，指向 LLM_* 同名值）
    #    已废弃：新代码请使用 Config.LLM_API_KEY 等
    #    保留原因：agent.py / test_api.py 仍在使用
    # E: DeepSeek-specific vars (backward compatible, alias to LLM_*)
    #    Deprecated: new code should use Config.LLM_API_KEY etc.
    #    Kept for: agent.py / test_api.py compatibility
    # ---------------------------------------------------------
    DEEPSEEK_API_KEY = LLM_API_KEY
    DEEPSEEK_BASE_URL = LLM_BASE_URL
    DEEPSEEK_MODEL = LLM_MODEL
    
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', 30))
    
    # ---------------------------------------------------------
    # C: 润色专用轻量模型配置（混合审查模式）
    #    设置 POLISH_MODEL 可启用「小模型迭代 + 主模型终审」混合润色。
    #    未配置时自动回退为 LLM_MODEL 直接润色（零额外开销）。
    #    推荐轻量模型: deepseek-lite（云端）, llama3.2 / qwen2.5:0.5b（本地 Ollama）
    # E: Polish-specific lightweight model config (hybrid review mode)
    #    Set POLISH_MODEL to enable "lightweight iteration + main model review".
    #    Falls back to LLM_MODEL direct polish when not configured (zero overhead).
    #    Recommended: deepseek-lite (cloud), llama3.2 / qwen2.5:0.5b (local Ollama)
    # ---------------------------------------------------------
    POLISH_MODEL = (
        os.getenv('POLISH_MODEL')
        or None  # None = 未配置，使用主力模型直润
    )
    POLISH_BASE_URL = (
        os.getenv('POLISH_BASE_URL')
        or LLM_BASE_URL  # 默认与主力模型共用端点
    )
    POLISH_API_KEY = (
        os.getenv('POLISH_API_KEY')
        or LLM_API_KEY  # 默认与主力模型共用 Key
    )
    # C: 轻量模型自迭代最大次数（1~5，默认3）
    # E: Max lightweight self-iteration count (1~5, default 3)
    POLISH_ITERATIONS = int(os.getenv('POLISH_ITERATIONS', '3'))
    
    # ---------------------------------------------------------
    # C: 多模型协作导图生成管线配置（三阶段内部管线）
    #    设置 CONCEPT_MODEL / HIERARCHY_MODEL / DELTA_MODEL 可启用专用模型。
    #    未配置时自动回退为 LLM_MODEL（零额外开销，行为与单模型 ReAct 完全一致）。
    #    推荐：阶段1/2 用轻量模型（deepseek-lite / qwen2.5:1.5b），阶段3 用主力模型。
    # E: Multi-model collaborative map generation pipeline config (3-stage internal pipeline)
    #    Set CONCEPT_MODEL / HIERARCHY_MODEL / DELTA_MODEL to enable specialized models.
    #    Falls back to LLM_MODEL when not configured (zero overhead, identical to single-model ReAct).
    #    Recommended: lightweight models for stages 1/2, main model for stage 3.
    # ---------------------------------------------------------
    # C: 阶段1 — 概念提取模型（轻量，从对话中提取原子化概念）
    # E: Stage 1 — Concept extraction model (lightweight, extract atomic concepts)
    CONCEPT_MODEL = (
        os.getenv('CONCEPT_MODEL')
        or None  # None = 使用 LLM_MODEL
    )
    CONCEPT_BASE_URL = (
        os.getenv('CONCEPT_BASE_URL')
        or LLM_BASE_URL
    )
    CONCEPT_API_KEY = (
        os.getenv('CONCEPT_API_KEY')
        or LLM_API_KEY
    )

    # C: 阶段2 — 层级规划模型（中等，规划父子节点关系）
    #    未设置时回退到 LLM_MODEL，使三阶段管线完整运行。
    #    如需跳过阶段2（两阶段模式），显式设置 HIERARCHY_MODEL="" 或 HIERARCHY_SKIP=true。
    # E: Stage 2 — Hierarchy planning model (medium, plan parent-child relationships)
    #    Falls back to LLM_MODEL when not set, enabling full 3-stage pipeline.
    #    To skip stage 2 (2-stage mode), explicitly set HIERARCHY_MODEL="" or HIERARCHY_SKIP=true.
    HIERARCHY_MODEL = (
        os.getenv('HIERARCHY_MODEL')
        or None  # None = 使用 LLM_MODEL（三阶段模式）
    )
    HIERARCHY_BASE_URL = (
        os.getenv('HIERARCHY_BASE_URL')
        or LLM_BASE_URL
    )
    HIERARCHY_API_KEY = (
        os.getenv('HIERARCHY_API_KEY')
        or LLM_API_KEY
    )

    # C: 阶段3 — Delta 生成模型（主力，输出增删改指令 + 坐标）
    # E: Stage 3 — Delta generation model (main, output CRUD instructions + coordinates)
    DELTA_MODEL = (
        os.getenv('DELTA_MODEL')
        or LLM_MODEL  # 默认复用主力模型
    )
    DELTA_BASE_URL = (
        os.getenv('DELTA_BASE_URL')
        or LLM_BASE_URL
    )
    DELTA_API_KEY = (
        os.getenv('DELTA_API_KEY')
        or LLM_API_KEY
    )

    # ---------------------------------------------------------
    # C: 低参数 LLM 配置（用于低成本批量任务）
    #    用途: get_definition 的 LLM 回退 + lookup_dictionary (IPA + 字面含义)
    #    关闭时（LLM_LIGHT_ENABLED=false）→ 自动回退到 LLM_MODEL
    # E: Low-parameter LLM config (for low-cost batch tasks)
    #    Use: get_definition LLM fallback + lookup_dictionary (IPA + literal meaning)
    #    Disabled (LLM_LIGHT_ENABLED=false) → fallback to LLM_MODEL
    # ---------------------------------------------------------
    LLM_LIGHT_MODEL = (
        os.getenv('LLM_LIGHT_MODEL')
        or None
    )
    LLM_LIGHT_BASE_URL = (
        os.getenv('LLM_LIGHT_BASE_URL')
        or LLM_BASE_URL
    )
    LLM_LIGHT_API_KEY = (
        os.getenv('LLM_LIGHT_API_KEY')
        or LLM_API_KEY
    )
    LLM_LIGHT_ENABLED = (
        os.getenv(
            'LLM_LIGHT_ENABLED',
            'true' if LLM_LIGHT_MODEL else 'false',
        ).lower()
        in ('true', '1', 'yes')
    )

    # C: MCP Server 脚本绝对路径（供 Client spawn 子进程使用）
    # E: MCP Server script absolute path (for Client to spawn subprocess)
    MCP_SERVER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")

    # ---------------------------------------------------------
    # C: 调试输出配置
    #    DEBUG_OUTPUT_ENABLED: 是否启用调试输出（保存每阶段中间结果到文件）
    #    DEBUG_OUTPUT_DIR: 调试文件的根目录
    # E: Debug output configuration
    #    DEBUG_OUTPUT_ENABLED: Whether to enable debug output (save per-stage intermediate results)
    #    DEBUG_OUTPUT_DIR: Root directory for debug files
    # ---------------------------------------------------------
    DEBUG_OUTPUT_ENABLED = (
        os.getenv('DEBUG_OUTPUT_ENABLED', 'true').lower()
        in ('true', '1', 'yes')
    )
    DEBUG_OUTPUT_DIR = (
        os.getenv('DEBUG_OUTPUT_DIR')
        or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug_output')
    )

    # ---------------------------------------------------------
    # C: Details 增强配置
    #    DETAILS_ENRICHMENT_ENABLED: 是否启用节点 details 的层次化增强
    #    开启后，AI 回复中的定义、解释、关键点会被条目化地融入节点 details，
    #    与用户原文、转录上下文一起构成层次化信息。
    #    关闭后恢复原有行为（details 仅含用户直接提及的内容）。
    # E: Details enrichment configuration
    #    DETAILS_ENRICHMENT_ENABLED: Whether to enable hierarchical details enrichment
    #    When enabled, AI reply content (definitions, explanations, key points) is
    #    incorporated into node details alongside user input and transcript context.
    #    When disabled, reverts to original behavior (details only from user input).
    # ---------------------------------------------------------
    DETAILS_ENRICHMENT_ENABLED = (
        os.getenv('DETAILS_ENRICHMENT_ENABLED', 'true').lower()
        in ('true', '1', 'yes')
    )

    # ---------------------------------------------------------
    # C: 深度优先生成策略配置
    #    DEPTH_FIRST_ENABLED: 启用深度优先策略（为已有节点挖掘子节点优先于创建新顶层节点）
    #    MIN_TREE_DEPTH: 目标最小深度（根算第1层，目标 >= 3）
    #    MAX_SIBLINGS_PER_NODE: 每个节点的最大同级子节点数（限制宽度，鼓励深度）
    # E: Depth-first generation strategy config
    #    DEPTH_FIRST_ENABLED: Enable depth-first strategy (dig children before creating new top-level nodes)
    #    MIN_TREE_DEPTH: Target minimum depth (root=level 1, target >= 3)
    #    MAX_SIBLINGS_PER_NODE: Max sibling nodes per parent (limit width, encourage depth)
    # ---------------------------------------------------------
    DEPTH_FIRST_ENABLED = (
        os.getenv('DEPTH_FIRST_ENABLED', 'true').lower()
        in ('true', '1', 'yes')
    )
    MIN_TREE_DEPTH = int(os.getenv('MIN_TREE_DEPTH', '3'))
    MAX_SIBLINGS_PER_NODE = int(os.getenv('MAX_SIBLINGS_PER_NODE', '6'))

    # ---------------------------------------------------------
    # C: 词典术语下划线标注配置
    #    ANNOTATION_ENABLED: 是否启用节点术语下划线标注功能
    #    DICT_UNDERLINE_SERVER_SCRIPT: 词典标注 MCP Server 脚本路径
    #    WIKIPEDIA_LANGUAGE: Wikipedia API 摘要语言（en / zh / ...）
    #    WIKIPEDIA_TIMEOUT: Wikipedia API 超时秒数
    # E: Dictionary term underline annotation configuration
    #    ANNOTATION_ENABLED: Whether to enable term underline annotation
    #    DICT_UNDERLINE_SERVER_SCRIPT: Dictionary underline MCP Server script path
    #    WIKIPEDIA_LANGUAGE: Wikipedia API summary language (en / zh / ...)
    #    WIKIPEDIA_TIMEOUT: Wikipedia API timeout in seconds
    # ---------------------------------------------------------
    ANNOTATION_ENABLED = (
        os.getenv('ANNOTATION_ENABLED', 'true').lower()
        in ('true', '1', 'yes')
    )
    # C: 任务5 — DICT_UNDERLINE_SERVER_SCRIPT 已废弃（原 dict_underline_server.py 被合并到 mcp_server.py）
    # E: Task 5 — DICT_UNDERLINE_SERVER_SCRIPT deprecated (dict_underline_server.py merged into mcp_server.py)
    DICT_UNDERLINE_SERVER_SCRIPT = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "mcp_server.py"
    )
    WIKIPEDIA_LANGUAGE = os.getenv('WIKIPEDIA_LANGUAGE', 'en')
    WIKIPEDIA_TIMEOUT = int(os.getenv('WIKIPEDIA_TIMEOUT', '5'))

    # ---------------------------------------------------------
    # C: Wikipedia-API 官方库配置
    #    WIKIPEDIA_USER_AGENT: User-Agent 标识（Wikipedia 强制要求可识别）
    #    WIKIPEDIA_RATE_LIMIT: 每秒最大请求数（保守 1.0 防 429）
    # E: Wikipedia-API official library config
    #    WIKIPEDIA_USER_AGENT: User-Agent identifier (Wikipedia requires identification)
    #    WIKIPEDIA_RATE_LIMIT: Max requests per second (conservative 1.0 to avoid 429)
    # ---------------------------------------------------------
    WIKIPEDIA_USER_AGENT = (
        os.getenv('WIKIPEDIA_USER_AGENT')
        or 'AI-MindMap-Agent/1.0 (https://github.com/user/ai-mindmap-agent)'
    )
    WIKIPEDIA_RATE_LIMIT = float(os.getenv('WIKIPEDIA_RATE_LIMIT', '1.0'))

    # ---------------------------------------------------------
    # C: Free Dictionary API 超时配置
    # E: Free Dictionary API timeout config
    # ---------------------------------------------------------
    FREE_DICT_TIMEOUT = int(os.getenv('FREE_DICT_TIMEOUT', '5'))

# C: 为了兼容 agent.py，我们在类外部定义这个变量
# E: For compatibility with agent.py, we define this variable outside the class
DEEPSEEK_CONFIG = {
    "api_key": Config.LLM_API_KEY,
    "base_url": Config.LLM_BASE_URL,
    "model": Config.LLM_MODEL
}

if __name__ == "__main__":
    if Config.LLM_API_KEY:
        print(f"C: LLM_CONFIG:")
        print(f"E: LLM_CONFIG:")
        print(f"  Model:     {Config.LLM_MODEL}")
        print(f"  Base URL:  {Config.LLM_BASE_URL}")
        print(f"  API Key:   {'***' + Config.LLM_API_KEY[-4:]}")
        print("C: 配置加载成功！")
        print("E: Configuration loaded successfully!")
    else:
        print("C: 警告: 未设置 LLM_API_KEY 或 DEEPSEEK_API_KEY")
        print("E: Warning: LLM_API_KEY or DEEPSEEK_API_KEY not set")