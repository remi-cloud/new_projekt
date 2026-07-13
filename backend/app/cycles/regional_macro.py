"""Regional macro cycles — local events instead of one global US presidential cycle."""

from __future__ import annotations

from datetime import date

from app.cycles.macro_types import MacroCycleResult
from app.cycles.presidential_cycle import analyze_presidential_cycle, presidential_buy_weight
from app.models.schemas import SignalAction

# ── Election / event calendars ──

POLISH_PARLIAMENTARY_ELECTIONS = [
    date(2015, 10, 25),
    date(2019, 10, 13),
    date(2023, 10, 15),
    date(2027, 10, 10),
]

EU_PARLIAMENT_ELECTIONS = [
    date(2019, 5, 26),
    date(2024, 6, 9),
    date(2029, 6, 9),
]

BRAZIL_PRESIDENTIAL_ELECTIONS = [
    date(2018, 10, 28),
    date(2022, 10, 30),
    date(2026, 10, 25),
]

INDIA_BUDGET_MONTH = 2  # Union Budget (February)
JAPAN_FISCAL_START_MONTH = 4
CHINA_NPC_MONTH = 3

REGION_MACRO_WEIGHT: dict[str, float] = {
    "us": 0.55,
    "pl": 0.50,
    "eu": 0.45,
    "asia": 0.42,
    "em": 0.40,
    "global": 0.35,
}


def macro_weight_for_region(region: str) -> float:
    return REGION_MACRO_WEIGHT.get(region, 0.40)


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def _nearest_election(events: list[date], as_of: date) -> tuple[date | None, date | None, int]:
    """Return (last_election, next_election, months_to_next)."""
    past = [d for d in events if d <= as_of]
    future = [d for d in events if d > as_of]
    last_e = max(past) if past else None
    next_e = min(future) if future else None
    months_to = _months_between(as_of, next_e) if next_e else 999
    return last_e, next_e, months_to


def _months_since(last: date | None, as_of: date) -> int:
    if not last:
        return 999
    return _months_between(last, as_of)


def analyze_us_macro(as_of: date | None = None) -> MacroCycleResult:
    pres = analyze_presidential_cycle(as_of)
    weight = presidential_buy_weight(as_of)
    return MacroCycleResult(
        cycle_id="presidential_cycle",
        phase=pres.current_year.value,
        signal=pres.signal,
        buy_weight=weight,
        bias=pres.historical_bias,
        rationale=pres.rationale,
    )


def analyze_polish_cycle(as_of: date | None = None) -> MacroCycleResult:
    as_of = as_of or date.today()
    last_e, next_e, months_to = _nearest_election(POLISH_PARLIAMENTARY_ELECTIONS, as_of)
    months_from = _months_since(last_e, as_of)

    # NBP / budżet: luty = budżet państwa, Q4 = sezon dywidendowy
    month = as_of.month
    budget_note = ""
    if month in (1, 2):
        budget_note = " Sezon projektu budżetu (luty)."
    elif month in (10, 11, 12):
        budget_note = " Sezon dywidendowy GPW."

    if months_from <= 6:
        return MacroCycleResult(
            cycle_id="polish_cycle",
            phase="post_election_rally",
            signal=SignalAction.BUY,
            buy_weight=0.75,
            bias="6 mies. po wyborach parlamentarnych — historycznie odbudowa WIG",
            rationale=(
                f"Polska: {months_from} mies. od wyborów ({last_e}). "
                f"Faza po-wyborcza — sprzyja akcjom.{budget_note}"
            ),
        )
    if months_to <= 3:
        return MacroCycleResult(
            cycle_id="polish_cycle",
            phase="pre_election_volatility",
            signal=SignalAction.WATCH,
            buy_weight=0.30,
            bias="3 mies. przed wyborami — podwyższona niepewność polityczna",
            rationale=(
                f"Polska: {months_to} mies. do wyborów ({next_e}). "
                f"Unikaj agresywnych zakupów.{budget_note}"
            ),
        )
    if months_to <= 12:
        return MacroCycleResult(
            cycle_id="polish_cycle",
            phase="pre_election_caution",
            signal=SignalAction.WATCH,
            buy_weight=0.40,
            bias="Rok przed wyborami — selektywne podejście",
            rationale=(
                f"Polska: {months_to} mies. do wyborów parlamentarnych. "
                f"Obserwuj sektor bankowy i defensywny.{budget_note}"
            ),
        )
    return MacroCycleResult(
        cycle_id="polish_cycle",
        phase="mid_term",
        signal=SignalAction.HOLD,
        buy_weight=0.55,
        bias="Środek kadencji Sejmu — stabilizacja, NBP dominuje krótki horyzont",
        rationale=(
            f"Polska: mid-cycle ({months_from} mies. od wyborów). "
            f"Kombinuj analizę NBP z wynikami spółek WIG20.{budget_note}"
        ),
    )


def analyze_europe_cycle(as_of: date | None = None) -> MacroCycleResult:
    as_of = as_of or date.today()
    last_eu, next_eu, months_to_eu = _nearest_election(EU_PARLIAMENT_ELECTIONS, as_of)
    months_from_eu = _months_since(last_eu, as_of)

    # ECB: większa aktywność marzec/czerwiec/wrzesień/grudzień
    ecb_active = as_of.month in (3, 6, 9, 12)
    ecb_note = " Miesiąc decyzji ECB — podwyższona zmienność." if ecb_active else ""

    us_spill = presidential_buy_weight(as_of) * 0.35

    if months_from_eu <= 12:
        buy_w = 0.45 + us_spill * 0.3
        return MacroCycleResult(
            cycle_id="europe_cycle",
            phase="post_eu_election",
            signal=SignalAction.WATCH,
            buy_weight=min(0.65, buy_w),
            bias="Rok po wyborach do PE — konsolidacja polityki UE",
            rationale=(
                f"Europa: {months_from_eu} mies. od wyborów do PE ({last_eu}). "
                f"Reformy instytucjonalne, umiarkowany bias.{ecb_note}"
            ),
        )
    if months_to_eu <= 12:
        return MacroCycleResult(
            cycle_id="europe_cycle",
            phase="pre_eu_election",
            signal=SignalAction.WATCH,
            buy_weight=0.40 + us_spill * 0.2,
            bias="Przed wyborami do PE — niepewność polityczna w strefie euro",
            rationale=(
                f"Europa: {months_to_eu} mies. do wyborów PE ({next_eu}). "
                f"Ostrożność na DAX/CAC.{ecb_note}"
            ),
        )

    buy_w = 0.60 + us_spill * 0.25
    return MacroCycleResult(
        cycle_id="europe_cycle",
        phase="expansion_midcycle",
        signal=SignalAction.BUY if buy_w >= 0.55 else SignalAction.HOLD,
        buy_weight=min(0.72, buy_w),
        bias="Środek cyklu UE — wsparcie ECB + stabilny eksport",
        rationale=(
            f"Europa: mid-cycle między wyborami PE. "
            f"Spillover z USA: {us_spill:.0%} wagi.{ecb_note}"
        ),
    )


def _asia_market_hint(symbol: str) -> str | None:
    if symbol.endswith(".T") or symbol.endswith(".HK") or symbol in ("EWJ", "SONY", "TM"):
        return "japan"
    if symbol.endswith(".NS") or symbol.endswith(".BO") or symbol in ("INDA", "IBN", "INFY"):
        return "india"
    if symbol.endswith(".KS") or symbol in ("EWY", "005930.KS"):
        return "korea"
    if symbol.endswith(".TW") or symbol in ("EWT", "TSM", "2330.TW"):
        return "taiwan"
    if symbol.endswith(".SS") or symbol.endswith(".HK") or "9988" in symbol or symbol in ("FXI", "MCHI", "BABA"):
        return "china"
    if symbol.endswith(".AX") or symbol in ("EWA", "BHP.AX", "CBA.AX"):
        return "australia"
    return None


def analyze_asia_cycle(as_of: date | None = None, symbol: str = "") -> MacroCycleResult:
    as_of = as_of or date.today()
    month = as_of.month
    market = _asia_market_hint(symbol)

    us_spill = presidential_buy_weight(as_of) * 0.25
    phase = "asia_general"
    signal = SignalAction.HOLD
    buy_w = 0.50 + us_spill
    bias = "Azja — sezonowość lokalna + spillover z Fed"
    rationale_parts = []

    if market == "japan" or (not market and month == JAPAN_FISCAL_START_MONTH):
        if month in (4, 5, 6):
            phase = "japan_fiscal_start"
            buy_w = 0.68 + us_spill
            signal = SignalAction.BUY
            rationale_parts.append("Japonia: początek roku fiskalnego (kwiecień) — historycznie mocny Nikkei")
        elif month in (1, 2, 3):
            phase = "japan_fiscal_end"
            buy_w = 0.42 + us_spill
            signal = SignalAction.WATCH
            rationale_parts.append("Japonia: koniec roku fiskalnego — realizacja zysków")
    elif market == "china" or month == CHINA_NPC_MONTH:
        if month in (3, 4):
            phase = "china_npc"
            buy_w = 0.58 + us_spill
            signal = SignalAction.HOLD
            rationale_parts.append("Chiny: NPC/Two Sessions — ogłoszenia polityki gospodarczej")
        elif month in (7, 8):
            phase = "china_summer_lull"
            buy_w = 0.38 + us_spill
            signal = SignalAction.WATCH
            rationale_parts.append("Chiny: letnia słaba płynność")
    elif market == "india" or month == INDIA_BUDGET_MONTH:
        if month in (2, 3):
            phase = "india_budget"
            buy_w = 0.65 + us_spill
            signal = SignalAction.BUY
            rationale_parts.append("Indie: Union Budget (luty) — historycznie pozytywny dla Nifty")
    elif month == 1:
        phase = "lunar_new_year"
        buy_w = 0.35 + us_spill
        signal = SignalAction.WATCH
        rationale_parts.append("Nowy Rok księżycowy — niższe wolumeny w Azji")

    if not rationale_parts:
        if month in (9, 10, 11):
            buy_w = 0.55 + us_spill
            signal = SignalAction.HOLD
            rationale_parts.append("Azja: Q4 eksportowy — sezon wysyłek")
        else:
            rationale_parts.append(f"Azja: ogólna sezonowość (miesiąc {month})")

    return MacroCycleResult(
        cycle_id="asia_cycle",
        phase=phase,
        signal=signal,
        buy_weight=min(0.75, buy_w),
        bias=bias,
        rationale=" ".join(rationale_parts) + f" Spillover Fed: {us_spill:.0%}.",
    )


def analyze_em_cycle(as_of: date | None = None, symbol: str = "") -> MacroCycleResult:
    as_of = as_of or date.today()
    us_spill = presidential_buy_weight(as_of)

    # Brazylia — wybory co 4 lata (październik)
    last_br, next_br, months_to_br = _nearest_election(BRAZIL_PRESIDENTIAL_ELECTIONS, as_of)
    months_from_br = _months_since(last_br, as_of)

    latam = symbol in ("PBR", "VALE", "ITUB", "BBD", "NU", "EWZ", "ECH") or symbol.endswith(".SA")

    if latam:
        if months_from_br <= 6:
            return MacroCycleResult(
                cycle_id="em_cycle",
                phase="brazil_post_election",
                signal=SignalAction.BUY,
                buy_weight=0.55 + us_spill * 0.25,
                bias="Brazylia: 6 mies. po wyborach — stabilizacja polityki",
                rationale=f"EM/LATAM: {months_from_br} mies. od wyborów BR ({last_br}). Fed spillover: {us_spill:.0%}.",
            )
        if months_to_br <= 6:
            return MacroCycleResult(
                cycle_id="em_cycle",
                phase="brazil_pre_election",
                signal=SignalAction.WATCH,
                buy_weight=0.35 + us_spill * 0.20,
                bias="Brazylia: przed wyborami — zmienność Bovespa",
                rationale=f"EM/LATAM: {months_to_br} mies. do wyborów ({next_br}). Ostrożność.",
            )

    buy_w = 0.45 + us_spill * 0.40
    return MacroCycleResult(
        cycle_id="em_cycle",
        phase="em_fed_spillover",
        signal=SignalAction.BUY if buy_w >= 0.52 else SignalAction.WATCH,
        buy_weight=min(0.70, buy_w),
        bias="EM: kapitał zależny od Fed i USD — 40% wagi cyklu USA",
        rationale=(
            f"Rynki wschodzące: spillover cyklu Fed/USA ({us_spill:.0%}) + lokalne wybory/stopy. "
            f"Surowce i waluty EM reagują na DXY."
        ),
    )


def analyze_global_macro(
    as_of: date | None = None,
    asset_class: str = "commodity",
) -> MacroCycleResult:
    as_of = as_of or date.today()
    us_spill = presidential_buy_weight(as_of) * 0.40
    month = as_of.month

    if asset_class == "commodity":
        # Złoto: Q4/Q1 silniejsze sezonowo; ropa: lato popyt
        if month in (11, 12, 1, 2):
            phase = "commodity_strong_season"
            buy_w = 0.55 + us_spill * 0.3
            note = "Surowce: sezon popytu zimowego / fizyczne złoto"
        elif month in (6, 7, 8):
            phase = "commodity_summer"
            buy_w = 0.42 + us_spill * 0.2
            note = "Surowce: lato — spadek popytu energetycznego"
        else:
            phase = "commodity_neutral"
            buy_w = 0.48 + us_spill * 0.25
            note = "Surowce: neutralna sezonowość"
        return MacroCycleResult(
            cycle_id="global_commodity_cycle",
            phase=phase,
            signal=SignalAction.BUY if buy_w >= 0.52 else SignalAction.WATCH,
            buy_weight=min(0.68, buy_w),
            bias="Surowce: sezonowość + USD/Fed (nie cykl prezydencki w pełni)",
            rationale=f"{note}. Wpływ Fed: {us_spill:.0%}.",
        )

    if asset_class == "forex":
        pres = analyze_presidential_cycle(as_of)
        # Rok 1-2 USD często silniejszy; rok 3-4 słabszy — uproszczone
        if pres.year_number in (1, 2):
            phase = "usd_strong_bias"
            buy_w = 0.45
            signal = SignalAction.WATCH
            note = "Forex: wczesna faza kadencji USA — tendencja silniejszego USD"
        else:
            phase = "usd_neutral_bias"
            buy_w = 0.50
            signal = SignalAction.HOLD
            note = "Forex: późna kadencja — rotacja z USD"
        return MacroCycleResult(
            cycle_id="global_forex_cycle",
            phase=phase,
            signal=signal,
            buy_weight=buy_w,
            bias="Forex: wpływ Fed/USD, nie pełny cykl prezydencki",
            rationale=f"{note} ({pres.president}, rok {pres.year_number}).",
        )

    # bonds with region global (BNDX etc.)
    buy_w = 0.48 + us_spill * 0.35
    return MacroCycleResult(
        cycle_id="global_macro_cycle",
        phase="fed_spillover",
        signal=SignalAction.HOLD,
        buy_weight=min(0.65, buy_w),
        bias="Global: ograniczony spillover z polityki USA",
        rationale=f"Aktywa globalne: {us_spill:.0%} wagi cyklu Fed/USA.",
    )


def analyze_regional_macro(
    region: str,
    asset_class: str,
    symbol: str = "",
    as_of: date | None = None,
) -> MacroCycleResult:
    """Pick the correct macro cycle for a region / asset."""
    if region == "us":
        return analyze_us_macro(as_of)
    if region == "pl":
        return analyze_polish_cycle(as_of)
    if region == "eu":
        return analyze_europe_cycle(as_of)
    if region == "asia":
        return analyze_asia_cycle(as_of, symbol=symbol)
    if region == "em":
        return analyze_em_cycle(as_of, symbol=symbol)
    return analyze_global_macro(as_of, asset_class=asset_class)


REGION_LABELS: dict[str, str] = {
    "us": "USA",
    "pl": "Polska",
    "eu": "Europa",
    "asia": "Azja",
    "em": "Rynki wschodzące",
    "global": "Globalne",
}


def build_regional_cycles_snapshot(as_of: date | None = None) -> dict[str, MacroCycleResult]:
    """Dashboard snapshot of macro cycles per region."""
    return {
        "us": analyze_us_macro(as_of),
        "pl": analyze_polish_cycle(as_of),
        "eu": analyze_europe_cycle(as_of),
        "asia": analyze_asia_cycle(as_of),
        "em": analyze_em_cycle(as_of),
        "global": analyze_global_macro(as_of, asset_class="commodity"),
    }
