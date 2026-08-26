"""Agent generujący grafiki hero do newsów — zdjęcia ze źródeł + DALL-E + abstrakcyjna grafika."""

from __future__ import annotations

import asyncio
import io
import json
import logging
import math
import random
from pathlib import Path
from typing import Awaitable, Callable

from PIL import Image, ImageDraw

from app.ai.llm import generate_image, image_generation_configured, llm_configured, simple_complete
from app.config import settings
from app.db.paths import BACKEND_ROOT
from app.models.schemas import MacroNewsCategory, MacroNewsItem
from app.news.image_sources import resolve_photo_bytes, stable_seed

logger = logging.getLogger(__name__)

IMAGE_WIDTH = 960
IMAGE_HEIGHT = 540
IMAGE_EXT = ".webp"
PIPELINE_VERSION = 2

_CATEGORY_THEME: dict[MacroNewsCategory, tuple[str, str, str]] = {
    "fed": ("#0a1628", "#2563eb", "#93c5fd"),
    "usa": ("#1a0f0f", "#dc2626", "#fca5a5"),
    "macro": ("#14100a", "#d97706", "#fcd34d"),
    "global": ("#0a1414", "#059669", "#6ee7b7"),
    "musk": ("#120a1a", "#8b5cf6", "#c4b5fd"),
    "crypto": ("#1a1408", "#f59e0b", "#fbbf24"),
}

_inflight: set[str] = set()


def news_images_dir() -> Path:
    path = BACKEND_ROOT / "data" / "news_images"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _meta_path(news_id: str) -> Path:
    safe = news_id.replace("/", "_").replace("..", "")
    return news_images_dir() / f"{safe}.meta.json"


def image_file_path(news_id: str) -> Path:
    safe = news_id.replace("/", "_").replace("..", "")
    return news_images_dir() / f"{safe}{IMAGE_EXT}"


def image_public_url(news_id: str) -> str:
    return f"/api/news/images/{news_id}"


def _read_meta(news_id: str) -> dict | None:
    path = _meta_path(news_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _write_meta(news_id: str, source: str) -> None:
    _meta_path(news_id).write_text(
        json.dumps({"source": source, "pipeline_version": PIPELINE_VERSION}, indent=0)
    )



def has_image(news_id: str) -> bool:
    path = image_file_path(news_id)
    if not path.is_file():
        return False
    meta = _read_meta(news_id)
    if not meta:
        return False
    if meta.get("source") == "text":
        return False
    if meta.get("pipeline_version", 1) < PIPELINE_VERSION:
        return False
    return True


def enrich_item(item: MacroNewsItem) -> MacroNewsItem:
    if has_image(item.id):
        return item.model_copy(update={"image_url": image_public_url(item.id)})
    return item


def enrich_items(items: list[MacroNewsItem]) -> list[MacroNewsItem]:
    return [enrich_item(i) for i in items]


def purge_legacy_images() -> int:
    """Remove outdated images (text cards, missing meta, old pipeline)."""
    removed = 0
    for webp in news_images_dir().glob(f"*{IMAGE_EXT}"):
        news_id = webp.stem
        meta = _read_meta(news_id)
        keep = (
            meta
            and meta.get("pipeline_version", 1) >= PIPELINE_VERSION
            and meta.get("source") not in ("text",)
        )
        if keep:
            continue
        webp.unlink()
        removed += 1
        meta_path = _meta_path(news_id)
        if meta_path.is_file():
            meta_path.unlink()
    if removed:
        logger.info("Purged %d outdated news images (pipeline v%s)", removed, PIPELINE_VERSION)
    return removed


async def _craft_dalle_prompt(item: MacroNewsItem) -> str:
    base = (
        f"Professional editorial news photograph illustration about: {item.title}. "
        f"Topic: {item.category} finance and markets. "
        "Cinematic, photorealistic, Reuters/Bloomberg style, dramatic lighting, "
        "no text, no logos, no watermarks, no readable faces."
    )
    if not llm_configured():
        return base
    try:
        prompt = await simple_complete(
            system=(
                "Write ONE DALL-E prompt for a news hero photo. "
                "Photorealistic editorial style. No text or logos. Max 800 chars."
            ),
            user=f"Headline: {item.title}\nCategory: {item.category}",
            temperature=0.55,
        )
        return (prompt or base)[:800]
    except Exception as exc:
        logger.warning("LLM prompt failed %s: %s", item.id, exc)
        return base


def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _render_abstract_hero(item: MacroNewsItem) -> bytes:
    """Pure visual fallback — gradients + shapes, zero text."""
    bg, accent, glow = _CATEGORY_THEME.get(item.category, _CATEGORY_THEME["macro"])
    rng = random.Random(stable_seed(item.id))
    bg_rgb = _hex_rgb(bg)
    acc_rgb = _hex_rgb(accent)
    glow_rgb = _hex_rgb(glow)

    img = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), bg_rgb)
    draw = ImageDraw.Draw(img)

    for y in range(IMAGE_HEIGHT):
        t = y / IMAGE_HEIGHT
        r = int(bg_rgb[0] * (1 - t * 0.4) + acc_rgb[0] * t * 0.15)
        g = int(bg_rgb[1] * (1 - t * 0.4) + acc_rgb[1] * t * 0.15)
        b = int(bg_rgb[2] * (1 - t * 0.4) + acc_rgb[2] * t * 0.15)
        draw.line([(0, y), (IMAGE_WIDTH, y)], fill=(r, g, b))

    for _ in range(6):
        cx = rng.randint(-100, IMAGE_WIDTH)
        cy = rng.randint(-50, IMAGE_HEIGHT // 2)
        rad = rng.randint(120, 320)
        color = tuple(min(255, int(c * 0.35 + glow_rgb[i] * 0.2)) for i, c in enumerate(acc_rgb))
        draw.ellipse([(cx - rad, cy - rad), (cx + rad, cy + rad)], fill=color)

    if item.category == "macro":
        base_y = int(IMAGE_HEIGHT * 0.62)
        for i in range(24):
            x = 80 + i * 34
            h = rng.randint(40, 180)
            bullish = rng.random() > 0.45
            color = (16, 185, 129) if bullish else (239, 68, 68)
            draw.rectangle([(x, base_y - h), (x + 18, base_y)], fill=color)
            draw.line([(x + 9, base_y - h - 20), (x + 9, base_y + 15)], fill=color, width=2)
    elif item.category == "fed":
        pts = [(480, 80), (720, 420), (240, 420)]
        draw.polygon(pts, fill=tuple(int(c * 0.55) for c in acc_rgb))
        draw.rectangle([(360, 200), (600, 420)], fill=tuple(int(c * 0.35) for c in acc_rgb))
        for i in range(5):
            draw.rectangle([(380 + i * 44, 220), (410 + i * 44, 400)], fill=glow_rgb)
    elif item.category == "usa":
        draw.rectangle([(300, 160), (660, 420)], fill=tuple(int(c * 0.4) for c in acc_rgb))
        for row in range(5):
            for col in range(8):
                if (row + col) % 2 == 0:
                    draw.rectangle(
                        [(320 + col * 42, 180 + row * 38), (354 + col * 42, 210 + row * 38)],
                        fill=(241, 245, 249),
                    )
    else:
        cx, cy = IMAGE_WIDTH // 2, IMAGE_HEIGHT // 2
        for ring in range(4, 0, -1):
            r = ring * 55
            draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=glow_rgb, width=3)
        for i in range(12):
            ang = i * math.pi / 6
            x2 = cx + int(math.cos(ang) * 200)
            y2 = cy + int(math.sin(ang) * 120)
            draw.line([(cx, cy), (x2, y2)], fill=glow_rgb, width=2)

    overlay = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([(0, IMAGE_HEIGHT - 120), (IMAGE_WIDTH, IMAGE_HEIGHT)], fill=(0, 0, 0, 100))
    img.paste(overlay, mask=overlay.split()[3])

    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=88, method=6)
    return buf.getvalue()


async def _save_image(news_id: str, raw: bytes, source: str) -> Path:
    path = image_file_path(news_id)
    try:
        img = Image.open(io.BytesIO(raw))
        if img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (10, 14, 23))
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img = img.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=88, method=6)
        path.write_bytes(buf.getvalue())
    except Exception:
        path.write_bytes(raw)
    _write_meta(news_id, source)
    return path


async def generate_for_item(item: MacroNewsItem) -> str | None:
    if not settings.news_images_enabled:
        return None
    if has_image(item.id):
        return image_public_url(item.id)
    if item.id in _inflight:
        return None

    _inflight.add(item.id)
    try:
        raw: bytes | None = None
        source = "abstract"

        photo, photo_src = await resolve_photo_bytes(item)
        if photo:
            raw, source = photo, photo_src

        if raw is None and settings.news_images_use_dalle and image_generation_configured():
            try:
                raw = await generate_image(await _craft_dalle_prompt(item))
                source = "dalle"
            except Exception as exc:
                logger.warning("DALL-E failed %s: %s", item.id, exc)

        if raw is None:
            raw = _render_abstract_hero(item)
            source = "abstract"

        await _save_image(item.id, raw, source)
        logger.info("News image [%s]: %s", source, item.id)
        return image_public_url(item.id)
    except Exception as exc:
        logger.error("News image failed %s: %s", item.id, exc)
        return None
    finally:
        _inflight.discard(item.id)


def _priority_key(item: MacroNewsItem) -> tuple[float, int]:
    age = float(item.age_minutes if item.age_minutes is not None else 9999)
    impact_rank = 0 if item.impact == "high" else 1
    return (age, impact_rank)


async def generate_missing(
    items: list[MacroNewsItem],
    *,
    on_ready: Callable[[str, str], Awaitable[None]] | None = None,
) -> int:
    if not settings.news_images_enabled:
        return 0

    pending = [i for i in items if not has_image(i.id)]
    pending.sort(key=_priority_key)
    batch = pending[: settings.news_images_max_per_refresh]
    if not batch:
        return 0

    sem = asyncio.Semaphore(3)

    async def _one(item: MacroNewsItem) -> None:
        async with sem:
            url = await generate_for_item(item)
            if url and on_ready:
                await on_ready(item.id, url)

    await asyncio.gather(*[_one(i) for i in batch])
    return len(batch)
