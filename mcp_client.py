# /home/akku/ai-mindmap-agent/mcp_client.py
# C: MCP Client 封装层 — 管理 MCP Server 子进程生命周期，提供统一的 call_tool 接口
# E: MCP Client wrapper — manages MCP Server subprocess lifecycle, provides unified call_tool interface
import json
import logging
import os
import sys
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

logger = logging.getLogger("mcp-client")


class MCPMindMapClient:
    """C: MCP 思维导图客户端 — 封装 stdio 通信与工具调用

    设计要点（修复 cancel scope 跨 task 报错）:
    1. 不再使用 AsyncExitStack 管理 stdio_client / ClientSession，
       改为显式保存内部 CM 对象，在 close() 中按相反顺序手动 __aexit__，
       保证 enter / exit 严格发生在同一个 asyncio task 中。
    2. 实现 __aenter__ / __aexit__，可在 lifespan 中通过
       `async with MCPMindMapClient(...) as client:` 使用，
       进一步保证 start / close 配对且在同一个 task 中。
    3. start() 失败时按相反顺序清理已成功 enter 的 CM，避免资源泄漏。
    4. close() 幂等：多次调用不会抛错，也不会触发 cancel scope 异常。

    E: MCP Mind Map Client — encapsulates stdio communication and tool invocation
    Design notes (fixes "exit cancel scope in a different task" error):
    1. Drop AsyncExitStack; track CMs explicitly and exit manually in LIFO
       order so enter/exit always run in the same asyncio task.
    2. Implements __aenter__ / __aexit__ for use via
       `async with MCPMindMapClient(...) as client:` in FastAPI lifespan.
    3. start() rolls back already-entered CMs in reverse order on failure.
    4. close() is idempotent and never propagates cancel-scope errors.
    """

    def __init__(self, server_script: str):
        self.server_script = server_script
        self._session: ClientSession | None = None
        # C: 显式持有内部 CM 对象，避免使用 AsyncExitStack
        # E: Explicitly hold inner CM objects to avoid AsyncExitStack pitfalls
        self._stdio_cm = None
        self._session_cm = None
        self._closed = False

    # ---------------------------------------------------------
    # C: async context manager 协议 — 推荐在 lifespan 中使用
    # E: async context manager protocol — recommended usage in lifespan
    # ---------------------------------------------------------
    async def __aenter__(self) -> "MCPMindMapClient":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        await self.close()
        return False

    async def start(self):
        """C: 启动 MCP Server 子进程并建立 stdio 会话
        E: Start MCP Server subprocess and establish stdio session"""
        if self._session is not None:
            logger.warning(
                "C: MCP Client 已经启动，跳过重复 start()\n"
                "E: MCP Client already started, skipping duplicate start()"
            )
            return

        logger.info("C: 正在启动 MCP Client...")
        logger.info("E: Starting MCP Client...")

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[self.server_script],
            env={**os.environ},  # C: 显式传递所有环境变量 / E: Explicitly pass all env vars
        )

        # C: 按顺序 enter，每一步失败都回滚已 enter 的 CM
        # E: Enter in order; on failure, roll back any CMs already entered
        try:
            self._stdio_cm = stdio_client(server_params)
            read_stream, write_stream = await self._stdio_cm.__aenter__()
        except Exception as e:
            logger.error(f"C: [MCP Client] stdio_client 启动失败: {e}")
            logger.error(f"E: [MCP Client] stdio_client startup failed: {e}")
            self._stdio_cm = None
            raise

        try:
            self._session_cm = ClientSession(read_stream, write_stream)
            self._session = await self._session_cm.__aenter__()
        except Exception as e:
            logger.error(f"C: [MCP Client] ClientSession 创建失败: {e}")
            logger.error(f"E: [MCP Client] ClientSession creation failed: {e}")
            self._session = None
            self._session_cm = None
            # C: 回滚 stdio_client / E: Roll back stdio_client
            if self._stdio_cm is not None:
                try:
                    await self._stdio_cm.__aexit__(None, None, None)
                except Exception:
                    # C: 静默吞掉回滚异常，避免覆盖原始错误
                    # E: Silently swallow rollback errors to not mask original
                    pass
                self._stdio_cm = None
            raise

        try:
            await self._session.initialize()
        except Exception as e:
            logger.error(f"C: [MCP Client] initialize 失败: {e}")
            logger.error(f"E: [MCP Client] initialize failed: {e}")
            # C: 整体回滚 — 必须按相反顺序退出
            # E: Roll back everything — must exit in reverse order
            await self.close()
            raise

        logger.info("C: MCP Client 启动完成，会话已建立")
        logger.info("E: MCP Client started, session established")

        # C: 列出可用工具（调试用） / E: List available tools (for debugging)
        try:
            tools_result = await self._session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            logger.info(f"C: 可用 MCP 工具: {tool_names}")
            logger.info(f"E: Available MCP tools: {tool_names}")
        except Exception as e:
            # C: 列出工具失败不影响主流程 / E: list_tools failure is non-fatal
            logger.warning(f"C: 列出工具失败（非致命）: {e}")
            logger.warning(f"E: list_tools failed (non-fatal): {e}")

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """C: 调用 MCP 工具并解析返回的 JSON 数据
        E: Call MCP tool and parse returned JSON data

        Args:
            tool_name: 工具名称 / Tool name
            arguments: 工具参数字典 / Tool arguments dict

        Returns:
            C: 解析后的 Python 对象（dict / list / str）
            E: Parsed Python object (dict / list / str)
        """
        if self._session is None:
            raise RuntimeError(
                "C: MCP Client 未启动，请先调用 start()\nE: MCP Client not started, call start() first"
            )

        logger.info(f"C: 调用工具 '{tool_name}'...")
        logger.info(f"E: Calling tool '{tool_name}'...")

        result = await self._session.call_tool(tool_name, arguments)

        # C: 解析返回的 CallToolResult
        # E: Parse returned CallToolResult
        if result.content:
            text_content = result.content[0].text
            try:
                parsed = json.loads(text_content)
                logger.info(f"C: 工具 '{tool_name}' 返回成功")
                logger.info(f"E: Tool '{tool_name}' returned successfully")
                return parsed
            except (json.JSONDecodeError, TypeError):
                # C: 如果不是 JSON，直接返回文本
                # E: If not JSON, return text directly
                return text_content

        return {}

    async def close(self):
        """C: 关闭 MCP 会话和子进程（幂等，不会抛出 cancel scope 异常）
        E: Close MCP session and subprocess (idempotent, never propagates cancel-scope errors)

        必须保证 enter / exit 在同一个 asyncio task 中。
        请通过 lifespan 中的 `async with` 触发调用。
        Must ensure enter/exit run in the same asyncio task.
        Recommended to invoke via `async with` in FastAPI lifespan.
        """
        if self._closed:
            return
        self._closed = True

        # C: 按 enter 的相反顺序退出，捕获所有异常防止级联
        # E: Exit in reverse order of entry, catch all errors to prevent cascade
        if self._session_cm is not None:
            try:
                await self._session_cm.__aexit__(None, None, None)
            except Exception as e:
                # C: 静默吞掉，避免遮蔽上层异常 / E: Swallow to not mask upper errors
                logger.error(f"C: 关闭 ClientSession 异常（已吞掉）: {e}")
                logger.error(f"E: Error closing ClientSession (swallowed): {e}")
            finally:
                self._session_cm = None
                self._session = None

        if self._stdio_cm is not None:
            try:
                await self._stdio_cm.__aexit__(None, None, None)
            except Exception as e:
                # C: cancel scope 跨 task 错误在此处最常见 — 仅记录，绝不重新抛出
                # E: cancel-scope cross-task errors are most common here — log only, never re-raise
                logger.error(f"C: 关闭 stdio_client 异常（已吞掉）: {e}")
                logger.error(f"E: Error closing stdio_client (swallowed): {e}")
            finally:
                self._stdio_cm = None

        logger.info("C: MCP Client 已关闭")
        logger.info("E: MCP Client closed")
