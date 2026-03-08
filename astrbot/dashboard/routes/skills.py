import asyncio
import ssl
import traceback
import uuid
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
import certifi
from quart import request

from astrbot.api import sp
from astrbot.core import DEMO_MODE, logger
from astrbot.core.skills.skill_manager import SkillManager
from astrbot.core.utils.astrbot_path import get_astrbot_temp_path

from .route import Response, Route, RouteContext

DEFAULT_SKILL_MARKET_URL = "https://skill.astrbot.app"


class SkillsRoute(Route):
    def __init__(self, context: RouteContext, core_lifecycle) -> None:
        super().__init__(context)
        self.core_lifecycle = core_lifecycle
        self.routes = {
            "/skills": ("GET", self.get_skills),
            "/skills/market": ("GET", self.get_market_skills),
            "/skills/source/get": ("GET", self.get_custom_skill_source),
            "/skills/source/save": ("POST", self.save_custom_skill_source),
            "/skills/upload": ("POST", self.upload_skill),
            "/skills/install_from_url": ("POST", self.install_from_url),
            "/skills/update": ("POST", self.update_skill),
            "/skills/delete": ("POST", self.delete_skill),
        }
        self.register_routes()

    async def get_skills(self):
        try:
            provider_settings = self.core_lifecycle.astrbot_config.get(
                "provider_settings", {}
            )
            runtime = provider_settings.get("computer_use_runtime", "local")
            skills = SkillManager().list_skills(
                active_only=False, runtime=runtime, show_sandbox_path=False
            )
            return (
                Response()
                .ok(
                    {
                        "skills": [skill.__dict__ for skill in skills],
                    }
                )
                .__dict__
            )
        except Exception as e:
            logger.error(traceback.format_exc())
            return Response().error(str(e)).__dict__

    async def upload_skill(self):
        if DEMO_MODE:
            return (
                Response()
                .error("You are not permitted to do this operation in demo mode")
                .__dict__
            )

        temp_path: Path | None = None
        try:
            files = await request.files
            file = files.get("file")
            if not file:
                return Response().error("Missing file").__dict__
            filename = Path(file.filename or "skill.zip").name
            if not filename.lower().endswith(".zip"):
                return Response().error("Only .zip files are supported").__dict__

            temp_dir = Path(get_astrbot_temp_path())
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_path = temp_dir / filename
            await file.save(str(temp_path))

            skill_mgr = SkillManager()
            skill_name = skill_mgr.install_skill_from_zip(
                str(temp_path), overwrite=True
            )

            return (
                Response()
                .ok({"name": skill_name}, "Skill uploaded successfully.")
                .__dict__
            )
        except Exception as e:
            logger.error(traceback.format_exc())
            return Response().error(str(e)).__dict__
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    logger.warning(f"Failed to remove temp skill file: {temp_path}")

    async def get_custom_skill_source(self):
        """Get custom skill market sources."""
        sources = await sp.global_get("custom_skill_sources", [])
        return Response().ok(sources).__dict__

    async def save_custom_skill_source(self):
        """Save custom skill market sources."""
        try:
            data = await request.get_json()
            sources = data.get("sources", [])
            if not isinstance(sources, list):
                return Response().error("sources field must be a list").__dict__
            await sp.global_put("custom_skill_sources", sources)
            return Response().ok(None, "保存成功").__dict__
        except Exception as e:
            logger.error(traceback.format_exc())
            return Response().error(str(e)).__dict__

    async def get_market_skills(self):
        # Priority: query param source_url > saved custom sources > legacy config > default
        market_url = request.args.get("source_url", "").strip()
        if not market_url:
            custom_sources = await sp.global_get("custom_skill_sources", [])
            if custom_sources:
                market_url = str(custom_sources[0].get("url", "")).strip()
        if not market_url:
            market_url = str(
                self.core_lifecycle.astrbot_config.get("skill_market_url", "")
            ).strip()
        if not market_url:
            market_url = DEFAULT_SKILL_MARKET_URL

        page = request.args.get("page", "1")
        size = request.args.get("size", "20")
        sort = request.args.get("sort", "downloads")
        target_url = (
            f"{market_url.rstrip('/')}/api/skills?page={page}&size={size}&sort={sort}"
        )

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=15)

        try:
            async with (
                aiohttp.ClientSession(
                    trust_env=True,
                    connector=connector,
                    timeout=timeout,
                ) as session,
                session.get(target_url) as response,
            ):
                if response.status != 200:
                    raise RuntimeError(
                        f"Skill market unavailable, status code: {response.status}"
                    )

                try:
                    payload = await response.json()
                except aiohttp.ContentTypeError:
                    payload = {}

                data = payload.get("data", payload) if isinstance(payload, dict) else {}
                skills = data.get("items") if isinstance(data, dict) else []
                if not isinstance(skills, list):
                    skills = []

                return (
                    Response()
                    .ok(
                        {
                            "skills": skills,
                            "configured": True,
                            "market_url": market_url,
                        }
                    )
                    .__dict__
                )
        except Exception as e:
            logger.warning(f"Failed to fetch skill market list: {e}")
            return Response().error("Skill market unavailable").__dict__

    async def install_from_url(self):
        if DEMO_MODE:
            return (
                Response()
                .error("You are not permitted to do this operation in demo mode")
                .__dict__
            )

        data = await request.get_json(silent=True)
        data = data or {}
        url = str(data.get("url", "")).strip()
        github_url = str(data.get("github_url", "")).strip()

        if not url or not github_url:
            return Response().error("Missing url or github_url").__dict__
        if not self._is_valid_http_url(url):
            return Response().error("Invalid url").__dict__
        if not self._is_valid_http_url(github_url):
            return Response().error("Invalid github_url").__dict__
        if not url.lower().endswith(".zip"):
            return Response().error("url must end with .zip").__dict__

        temp_path: Path | None = None
        try:
            temp_path = await self._download_zip_to_temp(url)
            skill_name = SkillManager().install_skill_from_zip(
                str(temp_path), overwrite=True
            )
            asyncio.create_task(
                self._report_install_to_market(github_url, data.get("market_url", ""))
            )
            return (
                Response()
                .ok({"name": skill_name}, "Skill installed successfully.")
                .__dict__
            )
        except Exception as e:
            logger.error(traceback.format_exc())
            return Response().error(str(e)).__dict__
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    logger.warning(f"Failed to remove temp skill file: {temp_path}")

    async def _download_zip_to_temp(self, url: str) -> Path:
        temp_dir = Path(get_astrbot_temp_path())
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"skill_market_{uuid.uuid4().hex}.zip"

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=45)

        async with (
            aiohttp.ClientSession(
                trust_env=True,
                connector=connector,
                timeout=timeout,
            ) as session,
            session.get(url) as response,
        ):
            if response.status != 200:
                raise RuntimeError(
                    f"Failed to download zip, status code: {response.status}"
                )
            content = await response.read()
            if not content:
                raise RuntimeError("Downloaded zip is empty")
            temp_path.write_bytes(content)

        return temp_path

    async def _report_install_to_market(self, github_url: str, market_url: str = ""):
        market_url = market_url.strip()
        if not market_url:
            market_url = str(
                self.core_lifecycle.astrbot_config.get("skill_market_url", "")
            ).strip()
        if not market_url:
            market_url = DEFAULT_SKILL_MARKET_URL
        if not market_url:
            return

        report_url = f"{market_url.rstrip('/')}/api/skills/report-install"
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=8)

        try:
            async with (
                aiohttp.ClientSession(
                    trust_env=True,
                    connector=connector,
                    timeout=timeout,
                ) as session,
                session.post(report_url, json={"github_url": github_url}) as response,
            ):
                if response.status >= 400:
                    logger.warning(
                        "Skill market report-install failed: %s status=%s",
                        report_url,
                        response.status,
                    )
        except Exception as e:
            logger.warning(f"Skill market report-install failed: {e}")

    def _is_valid_http_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    async def update_skill(self):
        if DEMO_MODE:
            return (
                Response()
                .error("You are not permitted to do this operation in demo mode")
                .__dict__
            )
        try:
            data = await request.get_json()
            name = data.get("name")
            active = data.get("active", True)
            if not name:
                return Response().error("Missing skill name").__dict__
            SkillManager().set_skill_active(name, bool(active))
            return Response().ok({"name": name, "active": bool(active)}).__dict__
        except Exception as e:
            logger.error(traceback.format_exc())
            return Response().error(str(e)).__dict__

    async def delete_skill(self):
        if DEMO_MODE:
            return (
                Response()
                .error("You are not permitted to do this operation in demo mode")
                .__dict__
            )
        try:
            data = await request.get_json()
            name = data.get("name")
            if not name:
                return Response().error("Missing skill name").__dict__
            SkillManager().delete_skill(name)
            return Response().ok({"name": name}).__dict__
        except Exception as e:
            logger.error(traceback.format_exc())
            return Response().error(str(e)).__dict__
