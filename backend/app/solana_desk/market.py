"""Read-only public market data. No wallet, no trade broadcast."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone

import httpx

from app.solana_desk.models import MarketSnapshot, TokenView, finite

log = logging.getLogger("app.solana_desk.market")

SOL_MINT = "So11111111111111111111111111111111111111112"
_EMPTY_AUTHORITY = {"", "none", "null", "11111111111111111111111111111111"}
_POOL_WORDS = ("raydium", "pumpswap", "pump.fun", "bonding", "amm", "liquidity", "pool", "meteora", "orca")
_UA = {"User-Agent": "Mozilla/5.0 CyklicznyTrader/solana-desk", "Accept": "application/json"}
_REPORT_TTL = 600.0
_REPORT_FAIL_TTL = 120.0
_REPORT_CACHE: dict[str, tuple[float, dict | None]] = {}
_MISS = object()


def clear_report_cache() -> None:
    _REPORT_CACHE.clear()


async def _pause(seconds: float) -> None:
    await asyncio.sleep(seconds)


def _pct(value: object) -> float:
    if isinstance(value, str):
        value = value.strip().rstrip("%")
    return finite(value)


def screen_tokens(tokens: list[TokenView], settings: dict) -> list[TokenView]:
    """Cheap DexScreener gate. Highest volume, then liquidity, then 5m rise."""
    min_liq = finite(settings.get("min_liquidity_usd"), 1500)
    min_vol = finite(settings.get("min_volume_usd"), 400)
    min_age = finite(settings.get("min_age_minutes"), 2)
    max_age = finite(settings.get("max_age_hours"), 72) * 60
    picked: list[TokenView] = []
    seen: set[str] = set()
    for token in tokens:
        mint = (token.mint or "").strip()
        if not mint or mint in seen:
            continue
        if token.venue not in {"pump", "pump_fun", "pumpswap", "raydium"} and not mint.endswith("pump"):
            continue
        if finite(token.price_usd) <= 0:
            continue
        if finite(token.liquidity_usd) < min_liq or finite(token.volume_usd) < min_vol:
            continue
        age = finite(token.age_minutes)
        if age < min_age or (max_age > 0 and age > max_age):
            continue
        seen.add(mint)
        picked.append(token)
    picked.sort(
        key=lambda item: (
            finite(item.volume_usd),
            finite(item.liquidity_usd),
            max(finite(item.change_5m_pct), 0.0),
        ),
        reverse=True,
    )
    return picked


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        stamp = float(value)
        if stamp > 10_000_000_000:
            stamp /= 1000
        try:
            return datetime.fromtimestamp(stamp, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip().replace("Z", "+00:00")
    if "." in text:
        head, tail = text.split(".", 1)
        frac = "".join(ch for ch in tail if ch.isdigit())[:6]
        zone = ""
        rest = tail[len("".join(ch for ch in tail if ch.isdigit())) :]
        if "+" in rest or "-" in rest[1:]:
            zone = rest[rest.find("+") if "+" in rest else rest.find("-") :]
        text = f"{head}.{frac}{zone}" if frac else f"{head}{zone}"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _age_minutes(moment: datetime | None, now: datetime) -> float:
    if moment is None:
        return 0.0
    return max(0.0, (now - moment).total_seconds() / 60)


def _authority_active(value: object, present: bool) -> bool | None:
    if not present:
        return None
    if value is None:
        return False
    text = str(value).strip()
    if text.lower() in _EMPTY_AUTHORITY:
        return False
    return True


def _venue(dex_id: str, market_type: str, mint: str) -> str:
    blob = f"{dex_id} {market_type}".lower()
    if "raydium" in blob:
        return "raydium"
    if "pump" in blob or mint.endswith("pump"):
        return "pumpswap" if "swap" in blob else "pump_fun"
    if mint.endswith("pump"):
        return "pump_fun"
    return dex_id or "solana"


def parse_dex_pair(raw: dict, now: datetime | None = None) -> TokenView | None:
    if not isinstance(raw, dict):
        return None
    if str(raw.get("chainId") or "") not in {"", "solana"}:
        return None
    base = raw.get("baseToken") or {}
    mint = str(base.get("address") or "")
    if not mint or mint == SOL_MINT:
        return None
    moment = now or _now()
    volume = raw.get("volume") or {}
    change = raw.get("priceChange") or {}
    liquidity = raw.get("liquidity") or {}
    vol_m5 = finite(volume.get("m5"))
    vol_h1 = finite(volume.get("h1"))
    vol = vol_h1 or vol_m5 * 12 or finite(volume.get("h24")) / 24
    avg_5m = vol_h1 / 12 if vol_h1 > 0 else 0.0
    spike = (vol_m5 / avg_5m) if avg_5m > 0 and vol_m5 > 0 else None
    txns = raw.get("txns") if isinstance(raw.get("txns"), dict) else {}
    m5 = txns.get("m5") if isinstance(txns.get("m5"), dict) else {}
    buys = finite(m5.get("buys"))
    sells = finite(m5.get("sells"))
    buys_pct = (buys / (buys + sells) * 100.0) if (buys + sells) > 0 else None
    return TokenView(
        mint=mint,
        symbol=str(base.get("symbol") or mint[:6]),
        name=str(base.get("name") or ""),
        price_usd=finite(raw.get("priceUsd")),
        liquidity_usd=finite(liquidity.get("usd")),
        volume_usd=vol,
        age_minutes=_age_minutes(_parse_time(raw.get("pairCreatedAt")), moment),
        venue=_venue(str(raw.get("dexId") or ""), "", mint),
        change_5m_pct=finite(change.get("m5")) if change.get("m5") is not None else None,
        spike=spike,
        buys_pct=buys_pct,
        volume_5m_usd=vol_m5 or None,
    )


def parse_new_token(raw: dict, now: datetime | None = None) -> TokenView | None:
    if not isinstance(raw, dict):
        return None
    mint = str(raw.get("mint") or "")
    if len(mint) < 20:
        return None
    moment = now or _now()
    keys = set(raw)
    return TokenView(
        mint=mint,
        symbol=str(raw.get("symbol") or mint[:6]),
        age_minutes=_age_minutes(_parse_time(raw.get("createAt") or raw.get("createdAt")), moment),
        venue="pump_fun" if mint.endswith("pump") else "solana",
        mint_authority_active=_authority_active(raw.get("mintAuthority"), "mintAuthority" in keys),
        freeze_authority_active=_authority_active(raw.get("freezeAuthority"), "freezeAuthority" in keys),
    )


def _pool_ids(report: dict) -> set[str]:
    found: set[str] = set()
    for market in report.get("markets") or []:
        if not isinstance(market, dict):
            continue
        for key in ("pubkey", "mintLP", "liquidityA", "liquidityB"):
            value = str(market.get(key) or "")
            if value:
                found.add(value)
    return found


def _holder_pcts(report: dict) -> tuple[float | None, float | None, float | None]:
    holders = report.get("topHolders")
    if not isinstance(holders, list):
        return None, None, None
    pools = _pool_ids(report)
    creator = str(report.get("creator") or "")
    ranked: list[float] = []
    dev = 0.0
    dev_known = False
    for holder in holders:
        if not isinstance(holder, dict):
            continue
        address = str(holder.get("address") or "")
        owner = str(holder.get("owner") or "")
        label = f"{address} {owner} {holder.get('name') or ''}".lower()
        if address in pools or owner in pools or any(word in label for word in _POOL_WORDS):
            continue
        pct = _pct(holder.get("pct"))
        ranked.append(pct)
        if creator and (owner == creator or address == creator or holder.get("insider") is True):
            dev = max(dev, pct)
            dev_known = True
    if creator and not dev_known:
        dev_known = True
        supply = finite((report.get("token") or {}).get("supply")) if isinstance(report.get("token"), dict) else 0.0
        held = finite(report.get("creatorBalance"))
        dev = (held / supply * 100.0) if supply > 0 and held > 0 else 0.0
    if not ranked and not holders:
        return None, None, None
    ranked.sort(reverse=True)
    top = ranked[0] if ranked else 0.0
    top10 = sum(ranked[:10])
    return top, top10, dev if dev_known or creator else None


def lp_locked_pct(report: dict) -> float | None:
    """Highest Rugcheck LP locked/burned percent across markets."""
    found: list[float] = []
    for market in report.get("markets") or []:
        if not isinstance(market, dict):
            continue
        lp = market.get("lp") if isinstance(market.get("lp"), dict) else {}
        if lp.get("lpLockedPct") is None:
            continue
        found.append(_pct(lp.get("lpLockedPct")))
    if not found:
        return None
    return max(found)


def apply_rugcheck(token: TokenView, report: dict) -> TokenView:
    if not isinstance(report, dict):
        return token
    keys = set(report)
    token_block = report.get("token") if isinstance(report.get("token"), dict) else {}
    mint_active = _authority_active(report.get("mintAuthority"), "mintAuthority" in keys)
    if mint_active is None and "mintAuthority" in token_block:
        mint_active = _authority_active(token_block.get("mintAuthority"), True)
    freeze_active = _authority_active(report.get("freezeAuthority"), "freezeAuthority" in keys)
    if freeze_active is None and "freezeAuthority" in token_block:
        freeze_active = _authority_active(token_block.get("freezeAuthority"), True)
    top, top10, dev = _holder_pcts(report)
    meta = report.get("tokenMeta") if isinstance(report.get("tokenMeta"), dict) else {}
    fee = report.get("transferFee") if isinstance(report.get("transferFee"), dict) else {}
    tax = finite(fee.get("pct")) if fee else 0.0
    extensions = report.get("token_extensions") if isinstance(report.get("token_extensions"), dict) else {}
    risks = report.get("risks") if isinstance(report.get("risks"), list) else []
    names = " ".join(str(item.get("name") or "") for item in risks if isinstance(item, dict)).lower()
    can_sell = True
    if extensions.get("nonTransferable") or "honeypot" in names:
        can_sell = False
    rugged = bool(report.get("rugged")) or "creator history of rugged" in names
    venue = token.venue
    for market in report.get("markets") or []:
        if isinstance(market, dict) and market.get("marketType"):
            venue = _venue("", str(market.get("marketType")), token.mint)
            break
    liquidity = finite(report.get("totalMarketLiquidity")) or token.liquidity_usd
    price = finite(report.get("price")) or token.price_usd
    return TokenView(
        mint=token.mint,
        symbol=str(meta.get("symbol") or token.symbol),
        name=str(meta.get("name") or token.name),
        price_usd=price,
        liquidity_usd=liquidity,
        volume_usd=token.volume_usd,
        age_minutes=token.age_minutes,
        venue=venue,
        mint_authority_active=mint_active,
        freeze_authority_active=freeze_active,
        top_holder_pct=top,
        top10_holder_pct=top10,
        dev_holder_pct=dev,
        buy_tax_pct=tax,
        sell_tax_pct=tax,
        can_sell=can_sell,
        change_5m_pct=token.change_5m_pct,
        rugged=rugged,
        risk_ready=True,
        spike=token.spike,
        buys_pct=token.buys_pct,
        lp_locked_pct=lp_locked_pct(report) if lp_locked_pct(report) is not None else token.lp_locked_pct,
        volume_5m_usd=token.volume_5m_usd,
        creator=str(report.get("creator") or token.creator),
    )


def _merge(left: TokenView, right: TokenView) -> TokenView:
    """Prefer the side that actually has a price, then copy risk fields."""
    base, extra = (left, right) if left.price_usd > 0 or right.price_usd <= 0 else (right, left)
    if extra.risk_ready and not base.risk_ready:
        return TokenView(
            mint=base.mint,
            symbol=base.symbol or extra.symbol,
            name=base.name or extra.name,
            price_usd=base.price_usd or extra.price_usd,
            liquidity_usd=base.liquidity_usd or extra.liquidity_usd,
            volume_usd=base.volume_usd or extra.volume_usd,
            age_minutes=base.age_minutes or extra.age_minutes,
            venue=base.venue if base.venue != "solana" else extra.venue,
            mint_authority_active=extra.mint_authority_active,
            freeze_authority_active=extra.freeze_authority_active,
            top_holder_pct=extra.top_holder_pct,
            top10_holder_pct=extra.top10_holder_pct,
            dev_holder_pct=extra.dev_holder_pct,
            buy_tax_pct=extra.buy_tax_pct,
            sell_tax_pct=extra.sell_tax_pct,
            can_sell=extra.can_sell,
            change_5m_pct=base.change_5m_pct if base.change_5m_pct is not None else extra.change_5m_pct,
            rugged=extra.rugged,
            risk_ready=True,
            spike=base.spike if base.spike is not None else extra.spike,
            buys_pct=base.buys_pct if base.buys_pct is not None else extra.buys_pct,
            lp_locked_pct=extra.lp_locked_pct if extra.lp_locked_pct is not None else base.lp_locked_pct,
            volume_5m_usd=base.volume_5m_usd or extra.volume_5m_usd,
            creator=extra.creator or base.creator,
        )
    if base.price_usd <= 0 and extra.price_usd > 0:
        return extra
    return base


class MarketClient:
    """Public reads only. Birdeye is used when BIRDEYE_API_KEY is set and is never logged."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def snapshot(self, held_mints: list[str], screen: dict | None = None) -> MarketSnapshot:
        errors: list[str] = []
        pending = 0
        async with httpx.AsyncClient(timeout=12.0, headers=_UA, follow_redirects=False) as client:
            http = self._client or client
            sol_usd = await self._sol_usd(http, errors)
            discovered, pending = await self._discover(http, errors, screen or {})
            quotes = await self._quotes(http, held_mints, errors)
        return MarketSnapshot(
            sol_usd=sol_usd,
            discovered=list(discovered.values()),
            quotes=quotes,
            error="; ".join(errors[:3]),
            risk_pending=pending,
        )

    async def _sol_usd(self, client: httpx.AsyncClient, errors: list[str]) -> float:
        try:
            response = await client.get(f"https://api.dexscreener.com/tokens/v1/solana/{SOL_MINT}")
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            errors.append(f"kurs SOL: {exc.__class__.__name__}")
            return 0.0
        pairs = body if isinstance(body, list) else []
        best_liq = -1.0
        chosen = 0.0
        for pair in pairs:
            if not isinstance(pair, dict):
                continue
            price = finite(pair.get("priceUsd"))
            liq = finite((pair.get("liquidity") or {}).get("usd"))
            if price > 0 and liq >= best_liq:
                best_liq = liq
                chosen = price
        return chosen

    async def _discover(
        self,
        client: httpx.AsyncClient,
        errors: list[str],
        screen: dict,
    ) -> tuple[dict[str, TokenView], int]:
        found: dict[str, TokenView] = {}
        now = _now()
        await self._load_new(client, found, now, errors)
        await self._load_search(client, found, now, errors)
        await self._load_profiles(client, found, errors)
        mints = list(found)
        for offset in range(0, len(mints), 25):
            await self._attach_pairs(client, found, mints[offset : offset + 25], now, errors)
        ranked = screen_tokens(list(found.values()), screen)
        top_n = max(1, min(int(finite(screen.get("rugcheck_top_n"), 15)), 30))
        chosen = ranked[:top_n]
        pending = max(0, len(ranked) - len(chosen))
        reports = await self._rugcheck_many(client, [token.mint for token in chosen], errors)
        ready: dict[str, TokenView] = {}
        for token in chosen:
            report = reports.get(token.mint)
            if not report:
                pending += 1
                continue
            ready[token.mint] = apply_rugcheck(token, report)
        return ready, pending

    async def _load_new(self, client, found, now, errors) -> None:
        try:
            response = await client.get("https://api.rugcheck.xyz/v1/stats/new_tokens")
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            errors.append(f"nowe tokeny: {exc.__class__.__name__}")
            return
        if not isinstance(body, list):
            return
        for raw in body[:20]:
            token = parse_new_token(raw, now)
            if token:
                found[token.mint] = token

    async def _load_search(self, client, found, now, errors) -> None:
        for query in ("pumpswap", "raydium sol"):
            try:
                response = await client.get(
                    "https://api.dexscreener.com/latest/dex/search",
                    params={"q": query},
                )
                response.raise_for_status()
                body = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                errors.append(f"dex {query}: {exc.__class__.__name__}")
                continue
            for raw in (body.get("pairs") or [])[:30]:
                token = parse_dex_pair(raw, now)
                if token and token.venue in {"pumpswap", "pump_fun", "raydium"}:
                    found[token.mint] = _merge(found.get(token.mint, token), token) if token.mint in found else token

    async def _load_profiles(self, client, found, errors) -> None:
        try:
            response = await client.get("https://api.dexscreener.com/token-profiles/latest/v1")
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            errors.append(f"profile: {exc.__class__.__name__}")
            return
        if not isinstance(body, list):
            return
        for raw in body:
            if not isinstance(raw, dict) or raw.get("chainId") != "solana":
                continue
            mint = str(raw.get("tokenAddress") or "")
            if not mint.endswith("pump") and mint in found:
                continue
            if mint and mint not in found and (mint.endswith("pump") or "pump" in str(raw.get("url") or "")):
                found[mint] = TokenView(mint=mint, symbol=mint[:4], venue="pump_fun")

    async def _attach_pairs(self, client, found, mints, now, errors) -> None:
        if not mints:
            return
        url = "https://api.dexscreener.com/tokens/v1/solana/" + ",".join(mints)
        try:
            response = await client.get(url)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            errors.append(f"ceny: {exc.__class__.__name__}")
            return
        if not isinstance(body, list):
            return
        for raw in body:
            token = parse_dex_pair(raw, now)
            if not token or token.mint not in found and token.venue not in {"pumpswap", "pump_fun", "raydium"}:
                continue
            current = found.get(token.mint)
            found[token.mint] = _merge(current, token) if current else token

    async def _quotes(self, client, mints: list[str], errors: list[str]) -> dict[str, TokenView]:
        unique = [mint for mint in dict.fromkeys(mints) if mint]
        if not unique:
            return {}
        url = "https://api.dexscreener.com/tokens/v1/solana/" + ",".join(unique[:20])
        try:
            response = await client.get(url)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            errors.append(f"wycena pozycji: {exc.__class__.__name__}")
            return {}
        quotes: dict[str, TokenView] = {}
        if not isinstance(body, list):
            return quotes
        for raw in body:
            token = parse_dex_pair(raw, _now())
            if not token:
                continue
            current = quotes.get(token.mint)
            if current is None or token.liquidity_usd > current.liquidity_usd:
                quotes[token.mint] = token
        missing = [mint for mint in unique if mint not in quotes]
        key = os.environ.get("BIRDEYE_API_KEY", "").strip()
        if key and missing:
            await self._birdeye(client, missing[:5], quotes, key, errors)
        return quotes

    async def _birdeye(self, client, mints, quotes, key: str, errors: list[str]) -> None:
        for mint in mints:
            try:
                response = await client.get(
                    "https://public-api.birdeye.so/defi/price",
                    params={"address": mint},
                    headers={"X-API-KEY": key, "x-chain": "solana"},
                )
                response.raise_for_status()
                body = response.json()
            except (httpx.HTTPError, ValueError):
                errors.append("Birdeye niedostępny")
                return
            price = finite(((body.get("data") or {}) if isinstance(body, dict) else {}).get("value"))
            if price > 0:
                quotes[mint] = TokenView(mint=mint, symbol=mint[:4], price_usd=price, venue="birdeye")

    async def _rugcheck_many(
        self,
        client: httpx.AsyncClient,
        mints: list[str],
        errors: list[str],
    ) -> dict[str, dict | None]:
        sem = asyncio.Semaphore(4)

        async def one(mint: str) -> tuple[str, dict | None]:
            cached = _cache_get(mint)
            if cached is not _MISS:
                return mint, cached  # type: ignore[return-value]
            async with sem:
                again = _cache_get(mint)
                if again is not _MISS:
                    return mint, again  # type: ignore[return-value]
                report = await self._rugcheck(client, mint, errors)
                _cache_put(mint, report)
                return mint, report

        pairs = await asyncio.gather(*(one(mint) for mint in mints))
        return dict(pairs)

    async def _rugcheck(self, client, mint: str, errors: list[str]) -> dict | None:
        delay = 0.5
        last_error = ""
        for _attempt in range(4):
            try:
                response = await client.get(f"https://api.rugcheck.xyz/v1/tokens/{mint}/report")
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc.__class__.__name__
                break
            status = getattr(response, "status_code", 200)
            if status == 429:
                last_error = "429"
                await _pause(delay)
                delay *= 2
                continue
            if status >= 400:
                last_error = str(status)
                break
            try:
                body = response.json()
            except ValueError:
                last_error = "ValueError"
                break
            return body if isinstance(body, dict) else None
        if last_error:
            errors.append(f"rugcheck: {last_error}")
        return None


def _cache_get(mint: str) -> dict | None | object:
    hit = _REPORT_CACHE.get(mint)
    if not hit:
        return _MISS
    stored_at, report = hit
    ttl = _REPORT_TTL if report else _REPORT_FAIL_TTL
    if time.monotonic() - stored_at > ttl:
        return _MISS
    return report


def _cache_put(mint: str, report: dict | None) -> None:
    _REPORT_CACHE[mint] = (time.monotonic(), report)


async def fetch_prices(mints: list[str]) -> dict[str, dict]:
    """DexScreener batch, then Jupiter Price API. Empty when both are down."""
    wanted = [mint for mint in mints if mint][:30]
    if not wanted:
        return {}
    found: dict[str, dict] = {}
    joined = ",".join(wanted)
    try:
        async with httpx.AsyncClient(timeout=8.0, headers=_UA) as client:
            response = await client.get(f"https://api.dexscreener.com/tokens/v1/solana/{joined}")
            if response.status_code == 200:
                payload = response.json()
                rows = payload if isinstance(payload, list) else payload.get("pairs") or []
                for raw in rows:
                    parsed = parse_dex_pair(raw) if isinstance(raw, dict) else None
                    if parsed and parsed.price_usd > 0 and parsed.mint not in found:
                        found[parsed.mint] = {"price": parsed.price_usd, "liq": parsed.liquidity_usd}
    except Exception:
        found = {}
    missing = [mint for mint in wanted if mint not in found]
    if not missing:
        return found
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get("https://lite-api.jup.ag/price/v3", params={"ids": ",".join(missing)})
            if response.status_code == 200 and isinstance(response.json(), dict):
                for mint, item in response.json().items():
                    if isinstance(item, dict) and item.get("usdPrice"):
                        found[mint] = {"price": finite(item.get("usdPrice")), "liq": None}
    except Exception:
        return found
    return found
