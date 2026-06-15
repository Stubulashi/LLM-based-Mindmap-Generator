# /home/akku/ai-mindmap-agent/mcp_client.py
# C: MCP Client 封装层 — 管理 MCP Server 子进程生命周期，提供统一的 call_tool 接口
# E: MCP Client wrapper — manages MCP Server subprocess lifecycle, provides unified call_tool interface
import json
import logging
import os
import sys
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

logger = logging.getLogger("mcp-client")


class MCPMindMapClient:
    """C: MCP 思维导图客户端 — 封装 stdio 通信与工具调用
    E: MCP Mind Map Client — encapsulates stdio communication and tool invocation"""

    def __init__(self, server_script: str):
        self.server_script = server_script
        self._exit_stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def start(self):
        """C: 启动 MCP Server 子进程并建立 stdio 会话
        E: Start MCP Server subprocess and establish stdio session"""
        logger.info("C: 正在启动 MCP Client...")
        logger.info("E: Starting MCP Client...")

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[self.server_script],
            env={**os.environ},  # C: 显式传递所有环境变量 / E: Explicitly pass all env vars
        )

        self._exit_stack = AsyncExitStack()

        # C: 通过 stdio_client 建立读写流
        # E: Establish read/write streams via stdio_client
        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )

        # C: 创建 MCP 会话并初始化
        # E: Create MCP session and initialize
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()

        logger.info("C: MCP Client 启动完成，会话已建立")
        logger.info("E: MCP Client started, session established")

        # C: 列出可用工具（调试用）
        # E: List available tools (for debugging)
        tools_result = await self._session.list_tools()
        tool_names = [t.name for t in tools_result.tools]
        logger.info(f"C: 可用 MCP 工具: {tool_names}")
        logger.info(f"E: Available MCP tools: {tool_names}")

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
        """C: 关闭 MCP 会话和子进程
        E: Close MCP session and subprocess"""
        if self._exit_stack:
            logger.info("C: 正在关闭 MCP Client...")
            logger.info("E: Closing MCP Client...")
            await self._exit_stack.aclose()
            self._session = None
            self._exit_stack = None
            logger.info("C: MCP Client 已关闭")
            logger.info("E: MCP Client closed")
