"""Finance-only topic guard."""

from __future__ import annotations

import re

FINANCE_KEYWORDS = (
    r"\b(stock|akcj|etf|crypto|bitcoin|btc|eth|forex|fx|bond|obligac|commodit|surowc|"
    r"market|rynek|trade|inwest|invest|portfolio|portfel|cycle|cykl|fed|fomc|cpi|inflac|"
    r"gdp|recession|recesj|yield|stop|limit|rsi|trend|wzrost|spad|bull|bear|makro|macro|"
    r"dividend|dywidend|option|opcj|future|kontrakt|nasdaq|s&p|sp500|dax|wig|"
    r"support|resist|opór|wsparc|pattern|wzor|chart|wykres|sygna|signal|momentum|"
    r"paper|pozycj|position|zlecen|order|volatil|volat|liquidity|płynno|"
    r"ecb|boe|boj|trump|tariff|cło|geopolit|opec|payroll|nfp|rate|stop[a]|"
    r"technical|technicz|fundamental|valuation|wycen|pe ratio|p/e|kapitał|capital)\b"
)

OFF_TOPIC = (
    r"\b(przepis|recipe|sport|football|piłk|film|movie|serial|gra video|game|"
    r"randk|dating|medycyn|doctor|chorob|weather|pogod|polityk lokal|gossip|plotk)\b"
)

FINANCE_RE = re.compile(FINANCE_KEYWORDS, re.I)
OFF_RE = re.compile(OFF_TOPIC, re.I)


def is_finance_related(text: str) -> bool:
    low = text.lower().strip()
    if len(low) < 3:
        return False
    if OFF_RE.search(low) and not FINANCE_RE.search(low):
        return False
    if FINANCE_RE.search(low):
        return True
    # Short follow-ups in chat context
    followups = ("dlaczego", "why", "wyjaśnij", "explain", "a co z", "what about", "tak", "nie", "ok", "thanks", "dzięki")
    if any(low.startswith(f) or low == f for f in followups) and len(low) < 80:
        return True
    # Symbol-like tickers
    if re.search(r"\b[A-Z]{2,5}(?:/USD|/PLN)?\b", text):
        return True
    if re.search(r"\b[A-Z]{2,5}-USD\b", text):
        return True
    return False


def finance_only_message(locale: str = "pl") -> str:
    messages = {
        "pl": "Odpowiadam wyłącznie na pytania związane z finansami, rynkami, cyklami i tradingiem. "
        "Zapytaj np. o trend BTC, wzorzec na wykresie, cykl Fed lub sygnał z naszego skanera.",
        "en": "I only answer questions related to finance, markets, cycles, and trading. "
        "Try asking about BTC trend, chart patterns, the Fed cycle, or a signal from our scanner.",
        "de": "Ich beantworte nur Fragen zu Finanzen, Märkten, Zyklen und Trading.",
        "es": "Solo respondo preguntas sobre finanzas, mercados, ciclos y trading.",
        "fr": "Je réponds uniquement aux questions liées à la finance, aux marchés, aux cycles et au trading.",
        "it": "Rispondo solo a domande su finanza, mercati, cicli e trading.",
        "fil": "Sumasagot lang ako sa mga tanong tungkol sa pananalapi, merkado, siklo, at trading.",
    }
    return messages.get(locale, messages["en"])
