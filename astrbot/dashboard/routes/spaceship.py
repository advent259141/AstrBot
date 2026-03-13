import os
import traceback
from typing import Any

from quart import jsonify, request, send_file, websocket

from astrbot.core import logger
from astrbot.core.core_lifecycle import AstrBotCoreLifecycle

from .route import Response, Route, RouteContext


class SpaceshipRoute(Route):
    def __init__(
        self,
        context: RouteContext,
        core_lifecycle: AstrBotCoreLifecycle,
    ) -> None:
        super().__init__(context)
        self.core_lifecycle = core_lifecycle
        self.routes = [
            ("/spaceship/config", ("GET", self.get_config)),
            ("/spaceship/config", ("POST", self.update_config)),
            ("/spaceship/nodes", ("GET", self.list_nodes)),
            ("/spaceship/nodes/<node_id>", ("GET", self.get_node)),
            ("/spaceship/nodes/<node_id>/alias", ("POST", self.update_node_alias)),
        ]
        self.register_routes()
        self.app.websocket("/api/spaceship/ws")(self.spaceship_ws)
        # HTTP file transfer endpoints (token-authenticated, no JWT)
        self.app.route(
            "/api/spaceship/files/<token>", methods=["GET"]
        )(self.file_download)
        self.app.route(
            "/api/spaceship/files/upload", methods=["POST"]
        )(self.file_upload)

    async def get_config(self):
        try:
            cfg = self.core_lifecycle.astrbot_config
            data = cfg.get("spaceship")
            if not isinstance(data, dict):
                data = {
                    "enable": False,
                    "websocket_path": "/api/spaceship/ws",
                    "heartbeat_timeout_sec": 60,
                    "allow_auto_register": False,
                    "bootstrap_token": "",
                    "require_admin": True,
                    "default_granted_scopes": ["exec", "list_dir", "read_file"],
                }
            data.setdefault("enable", False)
            data.setdefault("websocket_path", "/api/spaceship/ws")
            data.setdefault("heartbeat_timeout_sec", 60)
            data.setdefault("allow_auto_register", False)
            data.setdefault("bootstrap_token", "")
            data.setdefault("require_admin", True)
            data.setdefault("default_granted_scopes", ["exec", "list_dir", "read_file"])
            data.setdefault("node_aliases", {})
            data.setdefault("node_descriptions", {})
            return jsonify(Response().ok(data=data).__dict__)
        except Exception as e:
            logger.error(traceback.format_exc())
            return jsonify(Response().error(f"获取 spaceship 配置失败: {e!s}").__dict__)

    async def update_config(self):
        try:
            data = await request.json
            if not isinstance(data, dict):
                return jsonify(Response().error("配置必须为 JSON 对象").__dict__)
            cfg = self.core_lifecycle.astrbot_config
            cfg["spaceship"] = data
            cfg.save_config()
            return jsonify(Response().ok(message="保存成功").__dict__)
        except Exception as e:
            logger.error(traceback.format_exc())
            return jsonify(Response().error(f"保存 spaceship 配置失败: {e!s}").__dict__)

    async def list_nodes(self):
        try:
            runtime = self.core_lifecycle.spaceship_runtime
            if runtime is None:
                return jsonify(Response().ok(data=[]).__dict__)
            return jsonify(Response().ok(data=runtime.list_nodes()).__dict__)
        except Exception as e:
            logger.error(traceback.format_exc())
            return jsonify(Response().error(f"获取节点列表失败: {e!s}").__dict__)

    async def get_node(self, node_id: str):
        try:
            runtime = self.core_lifecycle.spaceship_runtime
            if runtime is None:
                return jsonify(Response().error("spaceship runtime 未初始化").__dict__)
            node = runtime.get_node_info(node_id)
            if node is None:
                return jsonify(Response().error("节点不存在").__dict__)
            return jsonify(Response().ok(data=node).__dict__)
        except Exception as e:
            logger.error(traceback.format_exc())
            return jsonify(Response().error(f"获取节点详情失败: {e!s}").__dict__)

    async def update_node_alias(self, node_id: str):
        try:
            data = await request.json
            if not isinstance(data, dict) or "alias" not in data:
                return jsonify(Response().error("请求体必须包含 alias 字段").__dict__)
            alias = str(data["alias"]).strip()
            runtime = self.core_lifecycle.spaceship_runtime
            if runtime is None:
                return jsonify(Response().error("spaceship runtime 未初始化").__dict__)
            ok = runtime.set_node_alias(node_id, alias)
            if not ok:
                return jsonify(Response().error("节点不存在").__dict__)
            return jsonify(Response().ok(message="别名已保存").__dict__)
        except Exception as e:
            logger.error(traceback.format_exc())
            return jsonify(Response().error(f"更新节点别名失败: {e!s}").__dict__)

    async def file_download(self, token: str):
        """Serve a file to a node using a one-time download token."""
        try:
            runtime = self.core_lifecycle.spaceship_runtime
            if runtime is None:
                return jsonify({"error": "runtime not initialized"}), 503
            file_path = runtime.file_transfer.consume_download_ticket(token)
            if file_path is None:
                return jsonify({"error": "invalid or expired token"}), 403
            if not os.path.isfile(file_path):
                return jsonify({"error": "file not found"}), 404
            return await send_file(
                file_path,
                as_attachment=True,
                attachment_filename=os.path.basename(file_path),
            )
        except Exception as e:
            logger.error(f"file_download error: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    async def file_upload(self):
        """Receive a file upload from a node using a one-time upload token."""
        try:
            runtime = self.core_lifecycle.spaceship_runtime
            if runtime is None:
                return jsonify({"error": "runtime not initialized"}), 503

            files = await request.files
            form = await request.form
            token = form.get("token", "")
            if not token:
                return jsonify({"error": "token is required"}), 400

            save_path = runtime.file_transfer.consume_upload_ticket(token)
            if save_path is None:
                return jsonify({"error": "invalid or expired token"}), 403

            uploaded = files.get("file")
            if uploaded is None:
                return jsonify({"error": "no file in request"}), 400

            parent = os.path.dirname(save_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            await uploaded.save(save_path)
            return jsonify({"ok": True, "path": save_path})
        except Exception as e:
            logger.error(f"file_upload error: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    async def spaceship_ws(self) -> None:
        runtime = self.core_lifecycle.spaceship_runtime
        if runtime is None:
            await websocket.close(1011, "spaceship runtime not initialized")
            return

        cfg = self.core_lifecycle.astrbot_config.get("spaceship", {})
        if not cfg.get("enable", False):
            await websocket.close(1008, "spaceship gateway disabled")
            return

        connection = _QuartWebSocketConnection(websocket._get_current_object())
        bound_node_id: str | None = None

        try:
            while True:
                envelope = await websocket.receive_json()
                if not isinstance(envelope, dict):
                    await websocket.close(1003, "invalid payload")
                    return

                event_type = str(envelope.get("type", ""))
                node_id = str(envelope.get("node_id", ""))
                payload = envelope.get("payload") or {}
                if not isinstance(payload, dict):
                    await websocket.close(1003, "payload must be object")
                    return

                if event_type == "node.hello":
                    expected_token = str(cfg.get("bootstrap_token", "")).strip()
                    received_token = str(payload.get("token", "")).strip()
                    if expected_token and received_token != expected_token:
                        await websocket.close(1008, "invalid bootstrap token")
                        return
                    if not cfg.get("allow_auto_register", False):
                        await websocket.close(1008, "auto registration disabled")
                        return

                response = await runtime.handle_incoming_event(
                    envelope=envelope, connection=connection
                )
                if node_id:
                    bound_node_id = node_id
                if response is not None:
                    await websocket.send_json(response)
        except Exception as e:
            logger.error(f"Spaceship WebSocket error: {e}", exc_info=True)
        finally:
            if bound_node_id:
                runtime.disconnect(bound_node_id)


class _QuartWebSocketConnection:
    def __init__(self, ws: Any) -> None:
        self._ws = ws

    async def send_json(self, payload: dict[str, Any]) -> None:
        await self._ws.send_json(payload)
