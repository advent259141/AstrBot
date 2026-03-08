"""Spaceship LLM tool registration and handlers."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from astrbot.core.provider.func_tool_manager import FunctionToolManager

    from .runtime import SpaceshipRuntime


def register_spaceship_tools(
    runtime: SpaceshipRuntime,
    llm_tools: FunctionToolManager,
    config_getter: Callable[[], dict],
) -> None:
    """Register all spaceship LLM tools to FunctionToolManager.

    Args:
        runtime: SpaceshipRuntime instance
        llm_tools: FunctionToolManager to register tools to
        config_getter: Callable that returns spaceship config dict
    """
    # listnode tool
    llm_tools.add_func(
        name="listnode",
        func_args=[
            {
                "type": "string",
                "name": "status",
                "description": "可选。按状态过滤节点，例如 active 或 offline。",
            }
        ],
        desc="列出所有 spaceship 远程节点的基本信息",
        handler=_make_listnode_handler(runtime, config_getter),
    )

    # getnodeinfo tool
    llm_tools.add_func(
        name="getnodeinfo",
        func_args=[
            {
                "type": "string",
                "name": "node_id",
                "description": "必填。要查看的节点 ID。",
            }
        ],
        desc="查看指定 spaceship 节点的详细信息",
        handler=_make_getnodeinfo_handler(runtime, config_getter),
    )

    # executeshell tool
    llm_tools.add_func(
        name="executeshell",
        func_args=[
            {
                "type": "string",
                "name": "node_id",
                "description": "必填。目标节点 ID。",
            },
            {
                "type": "string",
                "name": "command",
                "description": "必填。要执行的命令。",
            },
            {
                "type": "string",
                "name": "cwd",
                "description": "可选。工作目录。",
            },
            {
                "type": "number",
                "name": "timeout_sec",
                "description": "可选。超时秒数。",
            },
        ],
        desc="在指定 spaceship 节点上执行 shell 命令",
        handler=_make_executeshell_handler(runtime, config_getter),
    )

    # listdir tool
    llm_tools.add_func(
        name="listdir",
        func_args=[
            {
                "type": "string",
                "name": "node_id",
                "description": "必填。目标节点 ID。",
            },
            {
                "type": "string",
                "name": "path",
                "description": "可选。目标目录路径。",
            },
            {
                "type": "boolean",
                "name": "recursive",
                "description": "可选。是否递归列出子目录。",
            },
            {
                "type": "boolean",
                "name": "show_hidden",
                "description": "可选。是否显示隐藏文件。",
            },
            {
                "type": "number",
                "name": "limit",
                "description": "可选。最大返回条目数。",
            },
        ],
        desc="查看指定 spaceship 节点上的目录内容",
        handler=_make_listdir_handler(runtime, config_getter),
    )

    # readfile tool
    llm_tools.add_func(
        name="readfile",
        func_args=[
            {
                "type": "string",
                "name": "node_id",
                "description": "必填。目标节点 ID。",
            },
            {
                "type": "string",
                "name": "path",
                "description": "必填。文件路径。",
            },
            {
                "type": "number",
                "name": "max_bytes",
                "description": "可选。最大读取字节数。",
            },
        ],
        desc="读取指定 spaceship 节点上的文本文件内容",
        handler=_make_readfile_handler(runtime, config_getter),
    )

    llm_tools.add_func(
        name="writefile",
        func_args=[
            {
                "type": "string",
                "name": "node_id",
                "description": "必填。目标节点 ID。",
            },
            {
                "type": "string",
                "name": "path",
                "description": "必填。目标文件路径。",
            },
            {
                "type": "string",
                "name": "content",
                "description": "必填。要写入的文本内容。",
            },
            {
                "type": "boolean",
                "name": "append",
                "description": "可选。是否以追加方式写入。",
            },
            {
                "type": "boolean",
                "name": "create_dirs",
                "description": "可选。是否自动创建父目录。",
            },
        ],
        desc="向指定 spaceship 节点上的文件写入文本内容",
        handler=_make_writefile_handler(runtime, config_getter),
    )


def _check_enabled(config_getter: Callable[[], dict]) -> tuple[bool, str | None]:
    """Check if spaceship is enabled in config.

    Returns:
        (is_enabled, error_message): error_message is None if enabled
    """
    spaceship_cfg = config_getter()
    if not spaceship_cfg.get("enable", False):
        return False, "Error: spaceship gateway is disabled."
    return True, None


def _requested_by_from_event(event: object) -> str:
    """Extract a stable requested_by identifier from an AstrBot event."""
    getter = getattr(event, "get_sender_id", None)
    if callable(getter):
        try:
            sender_id = getter()
            if sender_id is not None:
                return str(sender_id)
        except Exception:
            pass
    return "system"


def _make_listnode_handler(
    runtime: SpaceshipRuntime, config_getter: Callable[[], dict]
):
    """Create listnode tool handler."""

    async def listnode_handler(event: object, status: str | None = None) -> str:
        _ = event
        enabled, err = _check_enabled(config_getter)
        if not enabled:
            return err or "Error: spaceship is disabled."

        nodes = list(runtime.nodes.values())
        if status:
            nodes = [n for n in nodes if n.status == status]
        result = [
            {
                "node_id": n.node_id,
                "alias": n.alias,
                "hostname": n.hostname,
                "platform": n.platform,
                "arch": n.arch,
                "status": n.status,
            }
            for n in nodes
        ]
        return json.dumps(result, ensure_ascii=False)

    return listnode_handler


def _make_getnodeinfo_handler(
    runtime: SpaceshipRuntime, config_getter: Callable[[], dict]
):
    """Create getnodeinfo tool handler."""

    async def getnodeinfo_handler(event: object, node_id: str) -> str:
        _ = event
        enabled, err = _check_enabled(config_getter)
        if not enabled:
            return err or "Error: spaceship is disabled."

        node = runtime.get_node_info(node_id)
        if node is None:
            return f"Error: node '{node_id}' not found."
        return json.dumps(node, ensure_ascii=False)

    return getnodeinfo_handler


def _make_executeshell_handler(
    runtime: SpaceshipRuntime, config_getter: Callable[[], dict]
):
    """Create executeshell tool handler."""
    from .models import ShellToolRequest

    async def executeshell_handler(
        event: object,
        node_id: str,
        command: str,
        cwd: str = "",
        timeout_sec: int = 30,
    ) -> str:
        enabled, err = _check_enabled(config_getter)
        if not enabled:
            return err or "Error: spaceship is disabled."

        try:
            result = await runtime.execute_shell(
                request=ShellToolRequest(
                    node_id=node_id,
                    command=command,
                    cwd=cwd or None,
                    timeout_sec=timeout_sec,
                ),
                requested_by=_requested_by_from_event(event),
            )
            return result
        except Exception as exc:
            return f"Error: {exc}"

    return executeshell_handler


def _make_listdir_handler(runtime: SpaceshipRuntime, config_getter: Callable[[], dict]):
    """Create listdir tool handler."""
    from .models import ListDirToolRequest

    async def listdir_handler(
        event: object,
        node_id: str,
        path: str = ".",
        recursive: bool = False,
        show_hidden: bool = False,
        limit: int = 200,
    ) -> str:
        enabled, err = _check_enabled(config_getter)
        if not enabled:
            return err or "Error: spaceship is disabled."

        try:
            result = await runtime.list_dir(
                request=ListDirToolRequest(
                    node_id=node_id,
                    path=path,
                    recursive=recursive,
                    show_hidden=show_hidden,
                    limit=limit,
                ),
                requested_by=_requested_by_from_event(event),
            )
            return result
        except Exception as exc:
            return f"Error: {exc}"

    return listdir_handler


def _make_readfile_handler(
    runtime: SpaceshipRuntime, config_getter: Callable[[], dict]
):
    """Create readfile tool handler."""
    from .models import ReadFileToolRequest

    async def readfile_handler(
        event: object,
        node_id: str,
        path: str,
        max_bytes: int = 65536,
    ) -> str:
        enabled, err = _check_enabled(config_getter)
        if not enabled:
            return err or "Error: spaceship is disabled."

        try:
            result = await runtime.read_file(
                request=ReadFileToolRequest(
                    node_id=node_id,
                    path=path,
                    max_bytes=max_bytes,
                ),
                requested_by=_requested_by_from_event(event),
            )
            return result
        except Exception as exc:
            return f"Error: {exc}"

    return readfile_handler


def _make_writefile_handler(
    runtime: SpaceshipRuntime, config_getter: Callable[[], dict]
):
    """Create writefile tool handler."""
    from .models import WriteFileToolRequest

    async def writefile_handler(
        event: object,
        node_id: str,
        path: str,
        content: str,
        append: bool = False,
        create_dirs: bool = True,
    ) -> str:
        enabled, err = _check_enabled(config_getter)
        if not enabled:
            return err or "Error: spaceship is disabled."

        try:
            result = await runtime.write_file(
                request=WriteFileToolRequest(
                    node_id=node_id,
                    path=path,
                    content=content,
                    append=append,
                    create_dirs=create_dirs,
                ),
                requested_by=_requested_by_from_event(event),
            )
            return result
        except Exception as exc:
            return f"Error: {exc}"

    return writefile_handler
