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

    llm_tools.add_func(
        name="enternode",
        func_args=[
            {
                "type": "string",
                "name": "node_id",
                "description": "必填。要进入并设为当前工作节点的节点 ID。",
            }
        ],
        desc="进入指定 spaceship 节点，后续 executeshell/listdir/readfile/writefile 默认都在该节点执行",
        handler=_make_enternode_handler(runtime, config_getter),
    )

    llm_tools.add_func(
        name="exitnode",
        func_args=[],
        desc="退出当前 spaceship 节点工作区，清除当前选中的节点",
        handler=_make_exitnode_handler(runtime, config_getter),
    )

    # executeshell tool
    llm_tools.add_func(
        name="executeshell",
        func_args=[
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
        desc="在当前已进入的 spaceship 节点上执行 shell 命令；使用前需先调用 enternode",
        handler=_make_executeshell_handler(runtime, config_getter),
    )

    # listdir tool
    llm_tools.add_func(
        name="listdir",
        func_args=[
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
        desc="查看当前已进入的 spaceship 节点上的目录内容；使用前需先调用 enternode",
        handler=_make_listdir_handler(runtime, config_getter),
    )

    # readfile tool
    llm_tools.add_func(
        name="readfile",
        func_args=[
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
        desc="读取当前已进入的 spaceship 节点上的文本文件内容；使用前需先调用 enternode",
        handler=_make_readfile_handler(runtime, config_getter),
    )

    llm_tools.add_func(
        name="writefile",
        func_args=[
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
        desc="向当前已进入的 spaceship 节点上的文件写入文本内容；使用前需先调用 enternode",
        handler=_make_writefile_handler(runtime, config_getter),
    )

    # canceltask tool
    llm_tools.add_func(
        name="canceltask",
        func_args=[
            {
                "type": "string",
                "name": "task_id",
                "description": "必填。要取消的任务 ID。",
            },
            {
                "type": "string",
                "name": "node_id",
                "description": "必填。任务所在节点 ID。",
            },
            {
                "type": "string",
                "name": "reason",
                "description": "可选。取消原因。",
            },
        ],
        desc="取消正在 spaceship 节点上运行的任务",
        handler=_make_canceltask_handler(runtime, config_getter),
    )

    # editfile tool
    llm_tools.add_func(
        name="editfile",
        func_args=[
            {
                "type": "string",
                "name": "path",
                "description": "必填。要编辑的文件路径。",
            },
            {
                "type": "string",
                "name": "edits",
                "description": (
                    '必填。JSON 数组字符串，每个元素为 {"search": "要查找的原文", "replace": "替换后的内容"}。'
                    "每个 search 字符串必须在文件中恰好出现一次。"
                ),
            },
        ],
        desc="使用 search-and-replace 方式编辑当前已进入的 spaceship 节点上的文件；使用前需先调用 enternode",
        handler=_make_editfile_handler(runtime, config_getter),
    )

    # grepfile tool
    llm_tools.add_func(
        name="grepfile",
        func_args=[
            {
                "type": "string",
                "name": "pattern",
                "description": "必填。搜索模式（纯文本或正则表达式）。",
            },
            {
                "type": "string",
                "name": "path",
                "description": "可选。要搜索的文件或目录路径，默认为当前目录。",
            },
            {
                "type": "boolean",
                "name": "is_regex",
                "description": "可选。是否将 pattern 作为正则表达式。",
            },
            {
                "type": "boolean",
                "name": "case_insensitive",
                "description": "可选。是否忽略大小写。",
            },
            {
                "type": "string",
                "name": "include_globs",
                "description": "可选。JSON 数组字符串，只搜索匹配的文件名 glob 模式，例如 '[\"*.go\", \"*.py\"]'。",
            },
            {
                "type": "string",
                "name": "exclude_globs",
                "description": "可选。JSON 数组字符串，排除匹配的文件名 glob 模式，例如 '[\"*.log\"]'。",
            },
            {
                "type": "number",
                "name": "max_matches",
                "description": "可选。最大返回匹配数，默认 100。",
            },
        ],
        desc="在当前已进入的 spaceship 节点上搜索文件内容；支持纯文本和正则，使用前需先调用 enternode",
        handler=_make_grepfile_handler(runtime, config_getter),
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
    """Extract a stable session-scoped identifier from an AstrBot event."""
    unified_msg_origin = getattr(event, "unified_msg_origin", None)
    if unified_msg_origin is not None:
        normalized = str(unified_msg_origin).strip()
        if normalized:
            return normalized

    getter = getattr(event, "get_sender_id", None)
    if callable(getter):
        try:
            sender_id = getter()
            if sender_id is not None:
                normalized = str(sender_id).strip()
                if normalized:
                    return normalized
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


def _make_enternode_handler(
    runtime: SpaceshipRuntime, config_getter: Callable[[], dict]
):
    """Create enternode tool handler."""

    async def enternode_handler(event: object, node_id: str) -> str:
        enabled, err = _check_enabled(config_getter)
        if not enabled:
            return err or "Error: spaceship is disabled."

        try:
            return await runtime.enter_node(
                node_id=node_id,
                requested_by=_requested_by_from_event(event),
            )
        except Exception as exc:
            return f"Error: {exc}"

    return enternode_handler


def _make_exitnode_handler(
    runtime: SpaceshipRuntime, config_getter: Callable[[], dict]
):
    """Create exitnode tool handler."""

    async def exitnode_handler(event: object) -> str:
        enabled, err = _check_enabled(config_getter)
        if not enabled:
            return err or "Error: spaceship is disabled."

        try:
            return await runtime.exit_node(requested_by=_requested_by_from_event(event))
        except Exception as exc:
            return f"Error: {exc}"

    return exitnode_handler


def _make_executeshell_handler(
    runtime: SpaceshipRuntime, config_getter: Callable[[], dict]
):
    """Create executeshell tool handler."""
    from .models import ShellToolRequest

    async def executeshell_handler(
        event: object,
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
        path: str,
        max_bytes: int = 65536,
    ) -> str:
        enabled, err = _check_enabled(config_getter)
        if not enabled:
            return err or "Error: spaceship is disabled."

        try:
            result = await runtime.read_file(
                request=ReadFileToolRequest(
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


def _make_canceltask_handler(
    runtime: SpaceshipRuntime, config_getter: Callable[[], dict]
):
    """Create canceltask tool handler."""

    async def canceltask_handler(
        event: object,
        task_id: str,
        node_id: str,
        reason: str = "",
    ) -> str:
        _ = event
        enabled, err = _check_enabled(config_getter)
        if not enabled:
            return err or "Error: spaceship is disabled."

        try:
            success = await runtime.cancel_task(
                task_id=task_id,
                node_id=node_id,
                reason=reason,
            )
            if success:
                return f"cancel request sent for task '{task_id}' on node '{node_id}'"
            return f"Error: could not cancel task '{task_id}' — node '{node_id}' may be offline"
        except Exception as exc:
            return f"Error: {exc}"

    return canceltask_handler


def _make_editfile_handler(
    runtime: SpaceshipRuntime, config_getter: Callable[[], dict]
):
    """Create editfile tool handler."""
    from .models import EditFileToolRequest

    async def editfile_handler(
        event: object,
        path: str,
        edits: str,
    ) -> str:
        enabled, err = _check_enabled(config_getter)
        if not enabled:
            return err or "Error: spaceship is disabled."

        try:
            parsed_edits = json.loads(edits)
        except (json.JSONDecodeError, TypeError) as exc:
            return f"Error: edits must be a valid JSON array: {exc}"

        if not isinstance(parsed_edits, list) or not parsed_edits:
            return "Error: edits must be a non-empty JSON array"

        for i, edit in enumerate(parsed_edits):
            if not isinstance(edit, dict):
                return f"Error: edits[{i}] must be an object with 'search' and 'replace' keys"
            if "search" not in edit or "replace" not in edit:
                return f"Error: edits[{i}] must have 'search' and 'replace' keys"

        try:
            result = await runtime.edit_file(
                request=EditFileToolRequest(
                    path=path,
                    edits=parsed_edits,
                ),
                requested_by=_requested_by_from_event(event),
            )
            return result
        except Exception as exc:
            return f"Error: {exc}"

    return editfile_handler


def _make_grepfile_handler(
    runtime: SpaceshipRuntime, config_getter: Callable[[], dict]
):
    """Create grepfile tool handler."""
    from .models import GrepToolRequest

    async def grepfile_handler(
        event: object,
        pattern: str,
        path: str = ".",
        is_regex: bool = False,
        case_insensitive: bool = False,
        include_globs: str = "",
        exclude_globs: str = "",
        max_matches: int = 100,
    ) -> str:
        enabled, err = _check_enabled(config_getter)
        if not enabled:
            return err or "Error: spaceship is disabled."

        parsed_include = _parse_globs(include_globs)
        parsed_exclude = _parse_globs(exclude_globs)

        try:
            result = await runtime.grep(
                request=GrepToolRequest(
                    pattern=pattern,
                    path=path,
                    is_regex=is_regex,
                    case_insensitive=case_insensitive,
                    include_globs=parsed_include,
                    exclude_globs=parsed_exclude,
                    max_matches=max_matches,
                ),
                requested_by=_requested_by_from_event(event),
            )
            return result
        except Exception as exc:
            return f"Error: {exc}"

    return grepfile_handler


def _parse_globs(raw: str) -> list[str] | None:
    """Parse a JSON array string of glob patterns, or return None."""
    if not raw or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(parsed, list):
        return [str(g) for g in parsed if g]
    return None
