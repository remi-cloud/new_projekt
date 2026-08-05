"""AI-style liquidation direction predictor + path from position levels to liq magnets."""

from __future__ import annotations

import math
from typing import Any


def _nearest_cluster(
    bins: list[dict],
    price: float,
    side: str,
    min_intensity: float = 0.35,
) -> dict | None:
    """Nearest strong liq cluster above (short) or below (long) price."""
    if side == "short":
        cands = [
            b
            for b in bins
            if b["price"] > price and b.get("short_intensity", 0) >= min_intensity
        ]
        key = "short_intensity"
    else:
        cands = [
            b
            for b in bins
            if b["price"] < price and b.get("long_intensity", 0) >= min_intensity
        ]
        key = "long_intensity"
    if not cands:
        return None
    # Prefer strong + close (gravity ~ intensity / distance)
    def score(b: dict) -> float:
        dist = abs(b["price"] - price) / max(price, 1e-9)
        return b.get(key, 0) / max(dist, 0.002)

    return max(cands, key=score)


def _gravity(bins: list[dict], price: float) -> tuple[float, float]:
    """Return (pull_up, pull_down) from short-above / long-below clusters."""
    up = 0.0
    down = 0.0
    for b in bins:
        dist = abs(b["price"] - price) / max(price, 1e-9)
        w = 1.0 / max(dist, 0.002)
        if b["price"] > price:
            up += b.get("short_intensity", 0) * w
        elif b["price"] < price:
            down += b.get("long_intensity", 0) * w
    return up, down


def _column_momentum(columns: list[list[dict]]) -> float:
    """Crude trend from early→late mid intensity skew (-1..+1)."""
    if not columns or len(columns) < 4:
        return 0.0
    early = columns[len(columns) // 4]
    late = columns[-1]
    if not early or not late:
        return 0.0

    def center_of_mass(col: list[dict]) -> float:
        num = sum(c["price"] * max(c["long_intensity"], c["short_intensity"]) for c in col)
        den = sum(max(c["long_intensity"], c["short_intensity"]) for c in col) or 1.0
        return num / den

    e = center_of_mass(early)
    l = center_of_mass(late)
    return max(-1.0, min(1.0, (l - e) / max(abs(e), 1e-9) * 40))


def predict_liq_path(
    heatmap: dict,
    levels: dict,
    action: str,
) -> dict[str, Any]:
    """
    Predict price direction toward liquidation magnets and build a path
    connecting position levels (IN/SL/TP) to the primary liq target.
    """
    bins: list[dict] = heatmap.get("bins") or []
    columns: list[list[dict]] = heatmap.get("columns") or []
    price = float(heatmap.get("price") or levels.get("entry") or 0)
    entry = float(levels.get("entry") or price)
    stop = float(levels.get("stop_loss") or price)
    tp1 = float(levels.get("take_profit_1") or price)
    tp2 = float(levels.get("take_profit_2") or price)
    side = levels.get("side") or "neutral"

    pull_up, pull_down = _gravity(bins, price)
    momentum = _column_momentum(columns)

    # Softmax-style direction score (AI feature blend)
    features = {
        "pull_up": pull_up,
        "pull_down": pull_down,
        "momentum": momentum,
        "side_long": 1.0 if side == "long" else 0.0,
        "side_short": 1.0 if side == "short" else 0.0,
        "action_buy": 1.0 if action in ("buy", "watch") else 0.0,
        "action_sell": 1.0 if action == "sell" else 0.0,
    }
    # Weighted logits
    logit_up = (
        1.15 * math.log1p(pull_up)
        + 0.55 * max(0, momentum)
        + 0.7 * features["side_long"]
        + 0.5 * features["action_buy"]
    )
    logit_down = (
        1.15 * math.log1p(pull_down)
        + 0.55 * max(0, -momentum)
        + 0.7 * features["side_short"]
        + 0.5 * features["action_sell"]
    )
    # Numerical stability
    m = max(logit_up, logit_down)
    e_up = math.exp(logit_up - m)
    e_down = math.exp(logit_down - m)
    p_up = e_up / (e_up + e_down)
    p_down = 1.0 - p_up

    if abs(p_up - p_down) < 0.08:
        direction = "neutral"
        confidence = 45.0 + abs(p_up - 0.5) * 40
    elif p_up > p_down:
        direction = "up"
        confidence = 50.0 + p_up * 48
    else:
        direction = "down"
        confidence = 50.0 + p_down * 48

    # Primary liq target in predicted direction
    if direction == "up":
        target_bin = _nearest_cluster(bins, price, "short", 0.3)
        target_side = "short"
        fallback = tp1 if tp1 > entry else price * 1.02
    elif direction == "down":
        target_bin = _nearest_cluster(bins, price, "long", 0.3)
        target_side = "long"
        fallback = tp1 if tp1 < entry else price * 0.98
    else:
        # Prefer the stronger magnet either side
        up_b = _nearest_cluster(bins, price, "short", 0.25)
        dn_b = _nearest_cluster(bins, price, "long", 0.25)
        if up_b and (not dn_b or up_b["short_intensity"] >= dn_b["long_intensity"]):
            target_bin, target_side, direction = up_b, "short", "up"
        elif dn_b:
            target_bin, target_side, direction = dn_b, "long", "down"
        else:
            target_bin, target_side = None, "short"
        fallback = tp1

    target_price = float(target_bin["price"]) if target_bin else float(fallback)
    target_intensity = float(
        (target_bin or {}).get("short_intensity" if target_side == "short" else "long_intensity", 0.5)
    )

    # Path: IN → (via TP1) → LIQ magnet, with time progressing left→right
    n = 18
    path: list[dict] = []
    for i in range(n):
        t = i / (n - 1)
        # Quadratic Bezier: entry → tp1 → liq
        u = 1 - t
        px = u * u * entry + 2 * u * t * tp1 + t * t * target_price
        role = "entry" if i == 0 else "liq_target" if i == n - 1 else "path"
        path.append(
            {
                "t": round(t, 4),
                "price": round(px, 6),
                "role": role,
                "intensity": round(target_intensity * (0.35 + 0.65 * t), 4),
            }
        )

    # Also pin stop as a side anchor (not on main path)
    anchors = [
        {"price": round(entry, 6), "role": "entry", "label": "IN", "t": 0.08},
        {"price": round(stop, 6), "role": "stop", "label": "SL", "t": 0.12},
        {"price": round(tp1, 6), "role": "tp1", "label": "TP1", "t": 0.55},
        {"price": round(tp2, 6), "role": "tp2", "label": "TP2", "t": 0.78},
        {
            "price": round(target_price, 6),
            "role": "liq",
            "label": "LIQ",
            "t": 0.97,
            "liq_side": target_side,
        },
    ]

    arrow = "↑" if direction == "up" else "↓" if direction == "down" else "↔"
    liq_name = "short-liq" if target_side == "short" else "long-liq"
    summary = (
        f"AI {arrow} kierunek do {liq_name} @ {target_price:.4g} "
        f"(pewność {confidence:.0f}%)"
    )

    return {
        "direction": direction,
        "confidence": round(min(98.0, confidence), 1),
        "summary": summary,
        "target_price": round(target_price, 6),
        "target_side": target_side,
        "target_intensity": round(target_intensity, 4),
        "pull_up": round(pull_up, 4),
        "pull_down": round(pull_down, 4),
        "momentum": round(momentum, 4),
        "path": path,
        "anchors": anchors,
        "features": {k: round(float(v), 4) for k, v in features.items()},
    }
