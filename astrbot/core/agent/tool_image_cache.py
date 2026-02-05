"""Tool image cache module for storing and retrieving images returned by tools.

This module allows LLM to review images before deciding whether to send them to users.
"""

import base64
import os
import time
from dataclasses import dataclass, field
from typing import ClassVar

from astrbot import logger
from astrbot.core.utils.astrbot_path import get_astrbot_temp_path


@dataclass
class CachedImage:
    """Represents a cached image from a tool call."""

    image_ref: str
    """Unique reference ID for the image (format: {tool_call_id}_{index})."""
    tool_call_id: str
    """The tool call ID that produced this image."""
    tool_name: str
    """The name of the tool that produced this image."""
    file_path: str
    """The file path where the image is stored."""
    mime_type: str
    """The MIME type of the image."""
    created_at: float = field(default_factory=time.time)
    """Timestamp when the image was cached."""


class ToolImageCache:
    """Manages cached images from tool calls.

    Images are stored in data/temp/tool_images/ and can be retrieved by image_ref.
    """

    _instance: ClassVar["ToolImageCache | None"] = None
    CACHE_DIR_NAME: ClassVar[str] = "tool_images"
    # Cache expiry time in seconds (1 hour)
    CACHE_EXPIRY: ClassVar[int] = 3600

    def __new__(cls) -> "ToolImageCache":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._cache: dict[str, CachedImage] = {}
        self._cache_dir = os.path.join(get_astrbot_temp_path(), self.CACHE_DIR_NAME)
        os.makedirs(self._cache_dir, exist_ok=True)
        logger.debug(f"ToolImageCache initialized, cache dir: {self._cache_dir}")

    def _get_file_extension(self, mime_type: str) -> str:
        """Get file extension from MIME type."""
        mime_to_ext = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/bmp": ".bmp",
            "image/svg+xml": ".svg",
        }
        return mime_to_ext.get(mime_type.lower(), ".png")

    def save_image(
        self,
        base64_data: str,
        tool_call_id: str,
        tool_name: str,
        index: int = 0,
        mime_type: str = "image/png",
    ) -> CachedImage:
        """Save an image to cache and return the cached image info.

        Args:
            base64_data: Base64 encoded image data.
            tool_call_id: The tool call ID that produced this image.
            tool_name: The name of the tool that produced this image.
            index: The index of the image (for multiple images from same tool call).
            mime_type: The MIME type of the image.

        Returns:
            CachedImage object with image reference and file path.
        """
        image_ref = f"{tool_call_id}_{index}"
        ext = self._get_file_extension(mime_type)
        file_name = f"{image_ref}{ext}"
        file_path = os.path.join(self._cache_dir, file_name)

        # Decode and save the image
        try:
            image_bytes = base64.b64decode(base64_data)
            with open(file_path, "wb") as f:
                f.write(image_bytes)
            logger.debug(f"Saved tool image to: {file_path}")
        except Exception as e:
            logger.error(f"Failed to save tool image: {e}")
            raise

        cached_image = CachedImage(
            image_ref=image_ref,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            file_path=file_path,
            mime_type=mime_type,
        )
        self._cache[image_ref] = cached_image
        return cached_image

    def get_image(self, image_ref: str) -> CachedImage | None:
        """Get a cached image by its reference ID.

        Args:
            image_ref: The unique reference ID of the image.

        Returns:
            CachedImage object if found, None otherwise.
        """
        cached = self._cache.get(image_ref)
        if cached and os.path.exists(cached.file_path):
            return cached

        # Try to find the file directly if not in memory cache
        for ext in [".png", ".jpg", ".gif", ".webp", ".bmp"]:
            file_path = os.path.join(self._cache_dir, f"{image_ref}{ext}")
            if os.path.exists(file_path):
                # Reconstruct cache entry
                parts = image_ref.rsplit("_", 1)
                tool_call_id = parts[0] if len(parts) > 1 else image_ref
                cached_image = CachedImage(
                    image_ref=image_ref,
                    tool_call_id=tool_call_id,
                    tool_name="unknown",
                    file_path=file_path,
                    mime_type=f"image/{ext[1:]}",
                )
                self._cache[image_ref] = cached_image
                return cached_image

        return None

    def get_image_base64(self, image_ref: str) -> tuple[str, str] | None:
        """Get the base64 encoded data of a cached image.

        Args:
            image_ref: The unique reference ID of the image.

        Returns:
            Tuple of (base64_data, mime_type) if found, None otherwise.
        """
        cached = self.get_image(image_ref)
        if not cached:
            return None

        try:
            with open(cached.file_path, "rb") as f:
                image_bytes = f.read()
            base64_data = base64.b64encode(image_bytes).decode("utf-8")
            return base64_data, cached.mime_type
        except Exception as e:
            logger.error(f"Failed to read cached image {image_ref}: {e}")
            return None

    def delete_image(self, image_ref: str) -> bool:
        """Delete a cached image.

        Args:
            image_ref: The unique reference ID of the image.

        Returns:
            True if deleted successfully, False otherwise.
        """
        cached = self._cache.pop(image_ref, None)
        if cached and os.path.exists(cached.file_path):
            try:
                os.remove(cached.file_path)
                logger.debug(f"Deleted cached image: {cached.file_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete cached image: {e}")
                return False
        return False

    def cleanup_expired(self) -> int:
        """Clean up expired cached images.

        Returns:
            Number of images cleaned up.
        """
        now = time.time()
        expired_refs = []

        for image_ref, cached in self._cache.items():
            if now - cached.created_at > self.CACHE_EXPIRY:
                expired_refs.append(image_ref)

        for image_ref in expired_refs:
            self.delete_image(image_ref)

        # Also clean up orphan files
        try:
            for file_name in os.listdir(self._cache_dir):
                file_path = os.path.join(self._cache_dir, file_name)
                if os.path.isfile(file_path):
                    file_age = now - os.path.getmtime(file_path)
                    if file_age > self.CACHE_EXPIRY:
                        os.remove(file_path)
                        expired_refs.append(file_name)
        except Exception as e:
            logger.warning(f"Error during orphan file cleanup: {e}")

        if expired_refs:
            logger.info(f"Cleaned up {len(expired_refs)} expired cached images")

        return len(expired_refs)

    def list_images_by_tool_call(self, tool_call_id: str) -> list[CachedImage]:
        """List all cached images from a specific tool call.

        Args:
            tool_call_id: The tool call ID.

        Returns:
            List of CachedImage objects.
        """
        return [
            cached
            for cached in self._cache.values()
            if cached.tool_call_id == tool_call_id
        ]


# Global singleton instance
tool_image_cache = ToolImageCache()
