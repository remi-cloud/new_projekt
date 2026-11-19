"""Fail closed. Rugcheck report plus on-chain mint account, holders, and a sell quote."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.solana_desk.agents.scanner import features
from app.solana_desk.learning.apply import effects_for, reason_for
from app.solana_desk.models import TokenView, finite
from app.solana_desk.quotes import SOL_MINT, NoRoute, QuoteRouter, QuoteUnavailable
from app.solana_desk.risk import assess_risk


@dataclass
class RugResult:
    ok: bool
    reason: str
    degraded: bool = False
    checks: list[dict] = field(default_factory=list)


def parse_mint_account(payload: dict | None) -> dict:
    """jsonParsed getAccountInfo result → authorities and Token-2022 flags."""
    value = ((payload or {}).get("result") or {}).get("value")
    if not isinstance(value, dict):
        return {"missing": True}
    data = value.get("data")
    parsed = data.get("parsed") if isinstance(data, dict) else None
    info = (parsed or {}).get("info") if isinstance(parsed, dict) else None
    if not isinstance(info, dict):
        return {"missing": True}
    extensions = info.get("extensions") if isinstance(info.get("extensions"), list) else []
    names = {str(item.get("extension") or "") for item in extensions if isinstance(item, dict)}
    fee = 0.0
    for item in extensions:
        if isinstance(item, dict) and item.get("extension") == "transferFeeConfig":
            state = item.get("state") or {}
            newer = (state.get("newerTransferFee") or {}) if isinstance(state, dict) else {}
            fee = finite(newer.get("transferFeeBasisPoints"))
    return {
        "missing": False,
        "mint_authority_active": info.get("mintAuthority") not in (None, "", "none"),
        "freeze_authority_active": info.get("freezeAuthority") not in (None, "", "none"),
        "transfer_fee_bps": fee,
        "permanent_delegate": "permanentDelegate" in names,
        "non_transferable": "nonTransferable" in names,
    }


def parse_largest(payload: dict | None, pool_ids: set[str] | None = None) -> tuple[float | None, float | None]:
    value = ((payload or {}).get("result") or {}).get("value")
    if not isinstance(value, list) or not value:
        return None, None
    pools = pool_ids or set()
    ranked: list[float] = []
    supply = 0.0
    for item in value:
        if not isinstance(item, dict):
            continue
        amount = finite((item.get("uiAmount") if item.get("uiAmount") is not None else item.get("amount")))
        address = str(item.get("address") or "")
        supply += amount
        if address and address in pools:
            continue
        ranked.append(amount)
    if supply <= 0 or not ranked:
        return None, None
    ranked.sort(reverse=True)
    top1 = ranked[0] / supply * 100
    top10 = sum(ranked[:10]) / supply * 100
    return top1, top10


async def evaluate(
    token: TokenView,
    settings: dict,
    router: QuoteRouter,
    *,
    onchain: dict | None = None,
    holders: tuple[float | None, float | None] | None = None,
    rugcheck_ok: bool | None = None,
    probe_sol: float = 0.01,
    sol_usd: float = 0.0,
) -> RugResult:
    checks: list[dict] = []
    chain = onchain or {}
    chain_ok = bool(chain) and not chain.get("missing")
    checks.append({"name": "onchain", "ok": chain_ok, "detail": "mint account" if chain_ok else "no data: mint account"})
    checks.append(
        {
            "name": "rugcheck",
            "ok": bool(rugcheck_ok if rugcheck_ok is not None else token.risk_ready),
            "detail": "report" if (rugcheck_ok if rugcheck_ok is not None else token.risk_ready) else "rugcheck down",
        }
    )
    merged = _merge_token(token, chain, holders)
    verdict = assess_risk(merged, settings)
    reason = ""
    if chain.get("transfer_fee_bps") and finite(chain.get("transfer_fee_bps")) > 0:
        reason = "token-2022 transfer fee"
    elif chain.get("permanent_delegate"):
        reason = "token-2022 permanent delegate"
    elif chain.get("non_transferable"):
        reason = "token-2022 nonTransferable"
    elif merged.mint_authority_active:
        reason = "mint authority active"
    elif merged.freeze_authority_active:
        reason = "freeze authority active"
    elif not chain_ok and merged.mint_authority_active is None:
        reason = "no data: mint authority"
    elif not chain_ok and merged.freeze_authority_active is None:
        reason = "no data: freeze authority"
    elif merged.top_holder_pct is None:
        reason = "no data: top holder"
    elif finite(merged.top_holder_pct) > finite(settings.get("max_top_holder_pct"), 30):
        reason = f"top holder {finite(merged.top_holder_pct):.1f}%"
    elif merged.top10_holder_pct is not None and finite(merged.top10_holder_pct) > finite(settings.get("max_top10_pct"), 70):
        reason = f"top 10 holds {finite(merged.top10_holder_pct):.1f}%"
    elif merged.dev_holder_pct is None:
        reason = "no data: dev wallet"
    elif finite(merged.dev_holder_pct) > finite(settings.get("max_dev_pct"), 10):
        reason = f"dev wallet {finite(merged.dev_holder_pct):.1f}%"
    elif merged.lp_locked_pct is not None and finite(merged.lp_locked_pct) < finite(settings.get("min_lp_locked_pct"), 0):
        reason = f"LP lock {finite(merged.lp_locked_pct):.0f}%"
    elif verdict.reasons:
        reason = _english(verdict.reasons[0], merged)
    if not reason:
        feats = features(merged)
        effects = await effects_for("rug_check", feats)
        blocks = [item for item in effects if item.type == "block"]
        if blocks:
            reason = reason_for(blocks, "filtered")
        else:
            tightened = [item for item in effects if item.type == "tighten_param"]
            for item in tightened:
                if _tightened_fail(item, merged):
                    reason = reason_for([item], "filtered")
                    break
    if not reason:
        sell_reason = await _sell_route(router, merged, settings, probe_sol, sol_usd)
        if sell_reason:
            reason = sell_reason
    degraded = checks[1]["ok"] is False and checks[0]["ok"] is True
    if reason:
        return RugResult(False, reason, degraded, checks)
    return RugResult(True, f"passed ${merged.symbol}", degraded, checks)


def _merge_token(token: TokenView, chain: dict, holders: tuple[float | None, float | None] | None) -> TokenView:
    top1, top10 = holders if holders is not None else (token.top_holder_pct, token.top10_holder_pct)
    if chain.get("missing"):
        chain = {}
    return TokenView(
        mint=token.mint,
        symbol=token.symbol,
        name=token.name,
        price_usd=token.price_usd,
        liquidity_usd=token.liquidity_usd,
        volume_usd=token.volume_usd,
        age_minutes=token.age_minutes,
        venue=token.venue,
        mint_authority_active=chain.get("mint_authority_active", token.mint_authority_active),
        freeze_authority_active=chain.get("freeze_authority_active", token.freeze_authority_active),
        top_holder_pct=top1,
        top10_holder_pct=top10,
        dev_holder_pct=token.dev_holder_pct,
        buy_tax_pct=token.buy_tax_pct,
        sell_tax_pct=token.sell_tax_pct,
        can_sell=False if chain.get("non_transferable") else token.can_sell,
        change_5m_pct=token.change_5m_pct,
        rugged=token.rugged,
        risk_ready=token.risk_ready or bool(chain),
        spike=token.spike,
        buys_pct=token.buys_pct,
        lp_locked_pct=token.lp_locked_pct,
        volume_5m_usd=token.volume_5m_usd,
        creator=token.creator,
        transfer_fee_bps=chain.get("transfer_fee_bps", token.transfer_fee_bps),
        permanent_delegate=chain.get("permanent_delegate", token.permanent_delegate),
        non_transferable=chain.get("non_transferable", token.non_transferable),
        onchain_ready=bool(chain) and not chain.get("missing"),
    )


def _english(reason: str, token: TokenView) -> str:
    if "mint" in reason and "uprawnienie" in reason:
        return "mint authority active" if "nieznane" not in reason else "no data: mint authority"
    if "freeze" in reason:
        return "freeze authority active" if "nieznane" not in reason else "no data: freeze authority"
    if "dev" in reason:
        return f"dev wallet {finite(token.dev_holder_pct):.1f}%"
    if "płynność" in reason:
        return "liquidity too low"
    if "młody" in reason:
        return "token too young"
    if "wolumen" in reason:
        return "volume too low"
    if "honeypot" in reason:
        return "honeypot: sell sim failed"
    if "rug" in reason:
        return "rug flag"
    if "cena" in reason:
        return "no data: price"
    if "holder" in reason or "koncentr" in reason:
        return f"top holder {finite(token.top_holder_pct):.1f}%"
    return reason


def _tightened_fail(effect, token: TokenView) -> bool:
    value = finite(effect.value)
    if effect.param == "max_dev_pct" and token.dev_holder_pct is not None:
        return finite(token.dev_holder_pct) > value
    if effect.param == "max_top10_pct" and token.top10_holder_pct is not None:
        return finite(token.top10_holder_pct) > value
    if effect.param == "min_liquidity_usd":
        return finite(token.liquidity_usd) < value
    if effect.param == "min_lp_locked_pct" and token.lp_locked_pct is not None:
        return finite(token.lp_locked_pct) < value
    if effect.param == "min_age_minutes":
        return finite(token.age_minutes) < value
    return False


async def _sell_route(router: QuoteRouter, token: TokenView, settings: dict, probe_sol: float, sol_usd: float) -> str:
    cap = min(3.0, finite(settings.get("max_slippage_pct"), 2.0))
    bps = int(round(cap * 100))
    lamports = max(1, int(probe_sol * 1_000_000_000))
    try:
        buy = await router.quote(input_mint=SOL_MINT, output_mint=token.mint, amount=lamports, slippage_bps=bps)
    except NoRoute:
        return "honeypot: sell sim failed"
    except QuoteUnavailable:
        return "no data: sell route"
    try:
        sell = await router.quote(input_mint=token.mint, output_mint=SOL_MINT, amount=buy.out_amount, slippage_bps=bps)
    except NoRoute:
        return "honeypot: sell sim failed"
    except QuoteUnavailable:
        return "no data: sell route"
    if sell.impact_pct > cap:
        return f"honeypot: sell sim failed"
    if sol_usd < 0:
        return "no data: sol price"
    return ""
