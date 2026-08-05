"""
AI trade consultation — synthesizes all available factors into KUP / SPRZEDAJ / CZEKAJ.

Not an external LLM call: a weighted multi-factor advisor that "consults"
cycle model, order book, R:R, liquidation gravity, momentum and prediction.
"""

from __future__ import annotations

import math
from typing import Any


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def consult_trade_signal(
    *,
    action: str,
    cycle_confidence: float,
    cycle_source: str,
    phase: str,
    super_score: float,
    levels: dict,
    spread_pct: float | None,
    prediction: dict | None,
) -> dict[str, Any]:
    """
    Consult every factor and return a trade verdict.

    Returns:
      signal: "kup" | "sprzedaj" | "czekaj"
      confidence: 0–100
      buy_score / sell_score: raw side strengths
      factors: list of {name, side, weight, detail}
      summary: Polish one-liner
    """
    factors: list[dict[str, Any]] = []
    buy = 0.0
    sell = 0.0

    action_l = (action or "").lower()
    side = (levels.get("side") or "neutral").lower()
    rr = float(levels.get("risk_reward") or 0)
    conf = float(cycle_confidence or 0)
    score = float(super_score or 0)
    model = {
        "bitcoin": "Cykl Bitcoin",
        "presidential": "Cykl prezydencki",
        "alpha": "Cykl Bitcoin",
        "beta": "Cykl prezydencki",
    }.get(cycle_source, cycle_source or "cykl")

    # ── 1. Cycle / model bias ───────────────────────────────────────────
    cycle_w = conf * 0.42
    # WATCH in bear = accumulation dial, not a full KUP mandate
    soft_watch = action_l == "watch" and (phase or "").lower() in ("bear", "accumulation")
    if soft_watch:
        cycle_w *= 0.55
        buy += cycle_w
        factors.append(
            {
                "name": "Model cyklu",
                "side": "czekaj",
                "weight": round(cycle_w, 1),
                "detail": (
                    f"{model} → akumulacja (WATCH) w fazie {phase}. "
                    "Wcześniejszy SHORT to poprzednia faza — nie all-in LONG."
                ),
            }
        )
    elif action_l in ("buy", "watch") or side == "long":
        buy += cycle_w
        factors.append(
            {
                "name": "Model cyklu",
                "side": "kup",
                "weight": round(cycle_w, 1),
                "detail": f"{model} → LONG (pewność {conf:.0f}%, faza {phase})",
            }
        )
    elif action_l == "sell" or side == "short":
        sell += cycle_w
        factors.append(
            {
                "name": "Model cyklu",
                "side": "sprzedaj",
                "weight": round(cycle_w, 1),
                "detail": f"{model} → SHORT (pewność {conf:.0f}%, faza {phase})",
            }
        )
    else:
        factors.append(
            {
                "name": "Model cyklu",
                "side": "czekaj",
                "weight": 0.0,
                "detail": f"{model} → NEUTRAL (faza {phase})",
            }
        )

    # ── 2. Super-score quality (amplifies winning side) ─────────────────
    quality = max(0.0, (score - 50.0) / 50.0)  # 0..1 above midpoint
    quality_w = quality * 18.0
    if quality_w > 0.5:
        if buy >= sell:
            buy += quality_w
            q_side = "kup"
        else:
            sell += quality_w
            q_side = "sprzedaj"
        factors.append(
            {
                "name": "Jakość setupu",
                "side": q_side,
                "weight": round(quality_w, 1),
                "detail": f"Super score {score:.0f}/100 wzmacnia stronę dominującą",
            }
        )
    else:
        factors.append(
            {
                "name": "Jakość setupu",
                "side": "czekaj",
                "weight": 0.0,
                "detail": f"Super score {score:.0f}/100 — setup słaby / średni",
            }
        )

    # ── 3. Bid/ask microstructure ───────────────────────────────────────
    if spread_pct is None:
        sell += 1.5
        buy += 1.5
        factors.append(
            {
                "name": "Bid / ask",
                "side": "czekaj",
                "weight": -3.0,
                "detail": "Brak książki zleceń — obniżona pewność fill",
            }
        )
        # Soft penalty both sides later via structure
        structure_mult = 0.88
    else:
        sp = float(spread_pct)
        if sp <= 0.08:
            structure_mult = 1.08
            # Tight spread favors acting on the model side
            boost = 8.0
            if buy >= sell:
                buy += boost
                sp_side = "kup"
            else:
                sell += boost
                sp_side = "sprzedaj"
            factors.append(
                {
                    "name": "Bid / ask",
                    "side": sp_side,
                    "weight": boost,
                    "detail": f"Wąski spread {sp:.3f}% — dobry fill",
                }
            )
        elif sp <= 0.25:
            structure_mult = 1.0
            factors.append(
                {
                    "name": "Bid / ask",
                    "side": "czekaj",
                    "weight": 3.0,
                    "detail": f"Spread OK {sp:.3f}%",
                }
            )
        else:
            structure_mult = 0.82
            factors.append(
                {
                    "name": "Bid / ask",
                    "side": "czekaj",
                    "weight": -6.0,
                    "detail": f"Szeroki spread {sp:.3f}% — ostrożnie z wejściem",
                }
            )

    # ── 4. Risk / reward ─────────────────────────────────────────────────
    if rr >= 2.0:
        rr_w = 12.0
        structure_mult *= 1.05
    elif rr >= 1.4:
        rr_w = 7.0
    elif rr >= 1.0:
        rr_w = 3.0
        structure_mult *= 0.95
    else:
        rr_w = -5.0
        structure_mult *= 0.85

    if rr_w > 0:
        if buy >= sell:
            buy += rr_w
            rr_side = "kup"
        else:
            sell += rr_w
            rr_side = "sprzedaj"
    else:
        rr_side = "czekaj"
    factors.append(
        {
            "name": "Risk / reward",
            "side": rr_side,
            "weight": round(rr_w, 1),
            "detail": f"R:R {rr:.2f} (IN→TP1 vs SL)",
        }
    )

    # ── 5. Liquidation AI prediction ────────────────────────────────────
    pred = prediction or {}
    pred_dir = (pred.get("direction") or "neutral").lower()
    pred_conf = float(pred.get("confidence") or 0)
    pull_up = float(pred.get("pull_up") or 0)
    pull_down = float(pred.get("pull_down") or 0)
    momentum = float(pred.get("momentum") or 0)

    pred_w = pred_conf * 0.38
    if pred_dir == "up":
        buy += pred_w
        factors.append(
            {
                "name": "AI ścieżka liq",
                "side": "kup",
                "weight": round(pred_w, 1),
                "detail": f"Predykcja ↑ do short-liq @ {pred.get('target_price')} ({pred_conf:.0f}%)",
            }
        )
    elif pred_dir == "down":
        sell += pred_w
        factors.append(
            {
                "name": "AI ścieżka liq",
                "side": "sprzedaj",
                "weight": round(pred_w, 1),
                "detail": f"Predykcja ↓ do long-liq @ {pred.get('target_price')} ({pred_conf:.0f}%)",
            }
        )
    else:
        factors.append(
            {
                "name": "AI ścieżka liq",
                "side": "czekaj",
                "weight": 0.0,
                "detail": "Predykcja liq bez wyraźnego kierunku",
            }
        )

    # ── 6. Gravity (pull toward liq magnets) ────────────────────────────
    g_sum = pull_up + pull_down
    if g_sum > 0.01:
        g_up_w = (pull_up / g_sum) * 14.0
        g_dn_w = (pull_down / g_sum) * 14.0
        buy += g_up_w
        sell += g_dn_w
        factors.append(
            {
                "name": "Grawitacja liq",
                "side": "kup" if g_up_w >= g_dn_w else "sprzedaj",
                "weight": round(max(g_up_w, g_dn_w), 1),
                "detail": f"Pull↑ {pull_up:.1f} vs Pull↓ {pull_down:.1f}",
            }
        )

    # ── 7. Momentum from volume/heatmap columns ─────────────────────────
    mom_w = abs(momentum) * 16.0
    if momentum > 0.05:
        buy += mom_w
        factors.append(
            {
                "name": "Momentum",
                "side": "kup",
                "weight": round(mom_w, 1),
                "detail": f"Momentum profilu +{momentum:.2f} (wsparcie LONG)",
            }
        )
    elif momentum < -0.05:
        sell += mom_w
        factors.append(
            {
                "name": "Momentum",
                "side": "sprzedaj",
                "weight": round(mom_w, 1),
                "detail": f"Momentum profilu {momentum:.2f} (wsparcie SHORT)",
            }
        )
    else:
        factors.append(
            {
                "name": "Momentum",
                "side": "czekaj",
                "weight": 0.0,
                "detail": "Momentum płaskie — brak dodatkowego biasu",
            }
        )

    # ── 8. Alignment / conflict between cycle and liq AI ────────────────
    cycle_long = action_l in ("buy", "watch") or side == "long"
    cycle_short = action_l == "sell" or side == "short"
    aligned = (cycle_long and pred_dir == "up") or (cycle_short and pred_dir == "down")
    conflict = (cycle_long and pred_dir == "down") or (cycle_short and pred_dir == "up")

    if aligned:
        align_w = 10.0
        if cycle_long:
            buy += align_w
            a_side = "kup"
        else:
            sell += align_w
            a_side = "sprzedaj"
        factors.append(
            {
                "name": "Spójność czynników",
                "side": a_side,
                "weight": align_w,
                "detail": "Model cyklu i AI liq wskazują ten sam kierunek",
            }
        )
    elif conflict:
        # Conflict → pull both toward wait
        penalty = 12.0
        buy = max(0.0, buy - penalty * 0.5)
        sell = max(0.0, sell - penalty * 0.5)
        structure_mult *= 0.75
        factors.append(
            {
                "name": "Spójność czynników",
                "side": "czekaj",
                "weight": -penalty,
                "detail": "Konflikt: model cyklu vs AI liq — obniżona pewność",
            }
        )
    else:
        factors.append(
            {
                "name": "Spójność czynników",
                "side": "czekaj",
                "weight": 0.0,
                "detail": "Częściowa zgodność — bez bonusu alignment",
            }
        )

    # Apply microstructure multiplier
    buy *= structure_mult
    sell *= structure_mult

    # Softmax-style confidence from score gap
    m = max(buy, sell, 1.0)
    e_b = math.exp((buy - m) / 12.0)
    e_s = math.exp((sell - m) / 12.0)
    p_buy = e_b / (e_b + e_s)
    p_sell = 1.0 - p_buy
    gap = abs(buy - sell)
    strength = max(buy, sell)

    # Decision thresholds
    min_strength = 28.0
    min_gap = 8.0
    # Late-bear / WATCH accumulation must not print aggressive KUP
    if soft_watch and (gap < 22 or conflict or buy < sell + 18):
        signal = "czekaj"
        confidence = _clamp(40.0 + gap * 1.1)
        label = "CZEKAJ"
        verb = "akumulacja DCA / czekaj — nie long przeciw wcześniejszemu SHORT-owi"
    elif strength < min_strength or gap < min_gap or (conflict and gap < 16):
        signal = "czekaj"
        confidence = _clamp(35.0 + gap * 1.2 + strength * 0.15)
        label = "CZEKAJ"
        verb = "brak jasnego KUP/SPRZEDAJ"
    elif buy > sell:
        signal = "kup"
        confidence = _clamp(48.0 + p_buy * 50.0 + min(gap, 40) * 0.35)
        label = "KUP"
        verb = "otwórz / trzymaj LONG"
    else:
        signal = "sprzedaj"
        confidence = _clamp(48.0 + p_sell * 50.0 + min(gap, 40) * 0.35)
        label = "SPRZEDAJ"
        verb = "otwórz SHORT / redukuj LONG"

    # Sort factors by absolute weight for UI
    factors_sorted = sorted(factors, key=lambda f: abs(float(f["weight"])), reverse=True)

    summary = (
        f"Singularity → {label} ({confidence:.0f}%): {verb}. "
        f"Score KUP {buy:.0f} vs SPRZEDAJ {sell:.0f}."
    )

    return {
        "signal": signal,
        "label": label,
        "confidence": round(confidence, 1),
        "buy_score": round(buy, 1),
        "sell_score": round(sell, 1),
        "aligned": aligned,
        "conflict": conflict,
        "summary": summary,
        "factors": factors_sorted,
        "verdict_detail": verb,
    }
