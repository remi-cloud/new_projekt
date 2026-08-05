"""AI agent persistence — conversations, feedback, learning notes, knowledge."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from app.db.sqlite import db_session

logger = logging.getLogger(__name__)


async def init_ai_db() -> None:
    async with db_session() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                meta_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES ai_sessions(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message_id INTEGER,
                rating INTEGER NOT NULL,
                correction TEXT,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_learning_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                lesson TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'self_critique',
                confidence REAL NOT NULL DEFAULT 0.7,
                use_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_ai_messages_session ON ai_messages(session_id, created_at)"
        )
        await db.commit()
    await _seed_knowledge_if_empty()
    await _ensure_seasonality_knowledge()
    await _ensure_btc_seasonality_knowledge()
    await _upsert_knowledge_entries(INTRAMONTH_KNOWLEDGE, "intramonth")
    await _upsert_knowledge_entries(GLOBAL_BOOK_KNOWLEDGE, "global_cycle_book")
    await _upsert_knowledge_entries(CALENDAR_PUMP_KNOWLEDGE, "calendar_pumps")


SEASONALITY_KNOWLEDGE = [
    (
        "cycles",
        "Cykl prezydencki USA",
        (
            "Lata kadencji (S&P Almanac): rok 3 zwykle najsilniejszy, rok 2 najsłabszy (midterms), "
            "rok 1/4 umiarkowane. Dotyczy aktywów region=us. "
            "Sygnał wejścia łączy rok kadencji z sezonowością miesiąca."
        ),
        "usa,presidential,cycle",
    ),
    (
        "cycles",
        "Sezonowość miesięczna USA (kadencja × miesiąc)",
        (
            "Model liczy equal-weight średnie zwroty miesięczne po uniwersum USA (akcje/ETF/indeksy/obligacje) "
            "w latach 1–4 kadencji (inauguracja 20 stycznia). "
            "get_macro_cycles.month_matrices ma WSZYSTKIE lata Y1–Y4 bieżącej kadencji (nie tylko rok bieżący). "
            "next_term_outlook nakłada ten sam wzorzec na 2029–2033 po Trump II — kontynuacja cyklu, "
            "nie prognoza wyborów 2028. "
            "Średnie miesięczne są monitorowane (seasonality_health); przy dryfcie overlay_scale spada — "
            "nie traktuj % jako pewnych. "
            "Agent ma brać current_month_bias + strongest/weakest_months + all_years — nie zmyślać tabel."
        ),
        "usa,seasonality,presidential,month",
    ),
    (
        "cycles",
        "Best Six Months (XI–IV)",
        (
            "Klasyczna sezonowość kalendarzowa USA: listopad–kwiecień historycznie silniejsze dla risk-on; "
            "maj–październik słabsze. W desk: calendar_season=best_six lub worst_six. "
            "Poza sezonem: wymagaj potwierdzenia MTF/price, mniejszy size — nie automatyczny SELL."
        ),
        "usa,seasonality,best_six,almanac",
    ),
]


INTRAMONTH_KNOWLEDGE = [
    (
        "cycles",
        "Sezonowość wewnątrz miesiąca (dzień / tydzień)",
        (
            "Pod każdym miesiącem w macierzy USA (equal-weight katalog) i BTC jest cykl dzienny 1–31 "
            "oraz 4 tygodnie (1–7, 8–14, 15–21, 22–31). Tool/API: GET /api/cycles/intramonth?month=&universe=us|btc. "
            "Wzorzec tygodniowy często steruje krótkoterminowym biasem — cytuj weeks + strongest/weakest days, "
            "nie zmyślaj tabel."
        ),
        "usa,bitcoin,intramonth,week,day,seasonality",
    ),
]


GLOBAL_BOOK_KNOWLEDGE = [
    (
        "cycles",
        "Globalny order book cykli (field scouts)",
        (
            "Te same reguły sezonowości (miesiąc kalendarzowy, tydzień w miesiącu W1–W4, Best Six Nov–Apr vs Sell-May) "
            "liczone equal-weight na rynkach: us, eu, asia, em, pl, crypto. "
            "Gdy wzorzec ma ten sam znak i wystarczającą magitudę na ≥4 rynkach → status adopted (bid↑ / ask↓). "
            "API: GET /api/cycles/global-book?status=adopted|watch|all. "
            "Cytuj adopted slots + reproduction_score + rynki; nie zmyślaj korelacji między regionami."
        ),
        "global,orderbook,seasonality,adoption,eu,asia,em,pl,crypto",
    ),
]


CALENDAR_PUMP_KNOWLEDGE = [
    (
        "cycles",
        "Kalendarzowe pompowanie instrumentów (miesiąc)",
        (
            "Dla każdego miesiąca 1–12 cały katalog (stock/etf/bond/commodity/crypto/forex/index, w tym XLU utility "
            "i ETF sektorowe/commodity) ma historyczny średni zwrot. "
            "API: GET /api/cycles/month-pumps?month= & GET /api/cycles/instrument-calendar?symbol=. "
            "get_macro_cycles → calendar_pumps: top pumped/drained bieżącego miesiąca. "
            "Cytuj symbole + avg_pct + win_rate; nie zmyślaj rankingu."
        ),
        "calendar,pump,seasonality,commodity,utility,etf,month",
    ),
]


BTC_SEASONALITY_KNOWLEDGE = [
    (
        "cycles",
        "Cykl Bitcoina 364/1064",
        (
            "Po ATH: ~364 dni bear/akumulacja, potem ~1064 dni bull, na końcu dystrybucja. "
            "To primary clock dla crypto. Sezonowość miesięczna jest additive — nie nadpisuje SELL "
            "z late-cycle samym silnym miesiącem kalendarzowym."
        ),
        "bitcoin,crypto,cycle,ath",
    ),
    (
        "cycles",
        "Sezonowość miesięczna BTC",
        (
            "Macierz z historii BTC-USD: średnie zwroty per miesiąc + faza ATH×miesiąc (min_n). "
            "Tool get_macro_cycles → bitcoin.seasonality / month_returns: current_month_bias, "
            "strongest/weakest_months, sample_count. Nie zmyślać tabel."
        ),
        "bitcoin,seasonality,month,crypto",
    ),
    (
        "cycles",
        "BTC vs S&P sezonowość",
        (
            "Porównanie kalendarza BTC z ^GSPC: corr miesięczna, Best Six delta, sign agreement, "
            "verdict (similar_to_spx|partially|idiosyncratic) i regime (equity_beta|mixed|crypto_idiosyncratic). "
            "Best Six USA nie kopiować 1:1 na BTC — u BTC best/worst six bywają podobne wielkością. "
            "Gdy regime=equity_beta, BTC zachowuje się bliżej equity; inaczej podkreśl idiosyncrasy."
        ),
        "bitcoin,spx,seasonality,regime,correlation",
    ),
]


async def _upsert_knowledge_entries(entries: list[tuple[str, str, str, str]], label: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        for cat, title, content, tags in entries:
            cur = await db.execute("SELECT id FROM ai_knowledge WHERE title = ?", (title,))
            row = await cur.fetchone()
            if row:
                await db.execute(
                    "UPDATE ai_knowledge SET category = ?, content = ?, tags = ? WHERE id = ?",
                    (cat, content, tags, row[0]),
                )
            else:
                await db.execute(
                    "INSERT INTO ai_knowledge (category, title, content, tags, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (cat, title, content, tags, now),
                )
        await db.commit()
    logger.info("Ensured %d %s knowledge entries", len(entries), label)


async def _ensure_seasonality_knowledge() -> None:
    """Upsert US seasonality knowledge even if older seeds already filled the table."""
    await _upsert_knowledge_entries(SEASONALITY_KNOWLEDGE, "seasonality")


async def _ensure_btc_seasonality_knowledge() -> None:
    await _upsert_knowledge_entries(BTC_SEASONALITY_KNOWLEDGE, "btc_seasonality")


async def _seed_knowledge_if_empty() -> None:
    async with db_session() as db:
        cur = await db.execute("SELECT COUNT(*) FROM ai_knowledge")
        row = await cur.fetchone()
        if row and row[0] > 0:
            return

    seeds = [
        ("cycles", "Cykl Bitcoina 364/1064", "Po ATH Bitcoin często przechodzi fazę spadkową (~364 dni), potem falę wzrostową (~1064 dni), następnie dystrybucję. Sygnały krypto powinny uwzględniać fazę cyklu BTC.", "bitcoin,crypto,cycle"),
        ("cycles", "Cykl prezydencki USA", "Lata kadencji (S&P Almanac): rok 3 zwykle najsilniejszy, rok 2 najsłabszy (midterms). Łącz z sezonowością miesięczną USA z get_macro_cycles.", "usa,presidential,cycle"),
        ("macro", "Fed i stopy procentowe", "Decyzje FOMC wpływają na koszt kapitału, dolara i wyceny aktywów ryzykownych. Rynek często dyskontuje oczekiwania przed samym komunikatem.", "fed,rates,macro"),
        ("macro", "CPI i inflacja", "CPI powyżej oczekiwań może wspierać hossę na obligacjach krótkoterminowych i osłabiać growth/tech w krótkim horyzoncie. Kontekst cyklu ma znaczenie.", "cpi,inflation,macro"),
        ("technical", "Trend vs korekta", "Trend wzrostowy: wyższe dołki i szczyty (HH/HL). Trend spadkowy: niższe szczyty i dołki (LH/LL). Korekta w trendzie ≠ zmiana trendu.", "trend,technical"),
        ("technical", "RSI i momentum", "RSI < 30 — strefa wyprzedania (możliwe odbicie, nie automatyczny buy). RSI > 70 — wykupienie. Łącz z fazą cyklu i makro.", "rsi,momentum"),
        ("patterns", "Double top / bottom", "Double top: dwa zbliżone szczyty + przełamanie szyi — sygnał kontynuacji spadków. Double bottom — odwrotnie. Potwierdzenie wolumenem zwiększa wiarygodność.", "pattern,double"),
        ("patterns", "Support / resistance", "Poziomy gdzie cena wielokrotnie odbijała się lub zatrzymywała. Przebicie oporu z wolumenem może otworzyć drogę wyżej.", "support,resistance,pattern"),
        ("risk", "Paper trading", "Cyclical Academy oferuje paper trading — test dyscypliny bez ryzyka kapitału. Limit, stop loss i take profit pomagają ćwiczyć plan.", "paper,risk"),
        ("risk", "Disclaimer", "Analiza edukacyjna — nie stanowi porady inwestycyjnej. Zawsze własna ocena ryzyka i horyzontu.", "disclaimer,risk"),
    ]
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        for cat, title, content, tags in seeds:
            await db.execute(
                "INSERT INTO ai_knowledge (category, title, content, tags, created_at) VALUES (?, ?, ?, ?, ?)",
                (cat, title, content, tags, now),
            )
        await db.commit()
    logger.info("Seeded %d AI knowledge entries", len(seeds))


def new_session_id() -> str:
    return str(uuid.uuid4())


async def create_session(title: str = "") -> str:
    sid = new_session_id()
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        await db.execute(
            "INSERT INTO ai_sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (sid, title[:120], now, now),
        )
        await db.commit()
    return sid


async def touch_session(session_id: str, title: str | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        if title:
            await db.execute(
                "UPDATE ai_sessions SET updated_at = ?, title = ? WHERE id = ?",
                (now, title[:120], session_id),
            )
        else:
            await db.execute("UPDATE ai_sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        await db.commit()


async def add_message(session_id: str, role: str, content: str, meta: dict | None = None) -> int:
    now = datetime.now(timezone.utc).isoformat()
    meta_json = json.dumps(meta) if meta else None
    async with db_session() as db:
        cur = await db.execute(
            "INSERT INTO ai_messages (session_id, role, content, meta_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, meta_json, now),
        )
        await db.commit()
        return cur.lastrowid or 0


async def get_messages(session_id: str, limit: int = 40) -> list[dict]:
    async with db_session() as db:
        cur = await db.execute(
            """SELECT id, role, content, meta_json, created_at FROM ai_messages
               WHERE session_id = ? ORDER BY id DESC LIMIT ?""",
            (session_id, limit),
        )
        rows = await cur.fetchall()
    out = []
    for row in reversed(rows):
        meta = json.loads(row[3]) if row[3] else None
        out.append({"id": row[0], "role": row[1], "content": row[2], "meta": meta, "created_at": row[4]})
    return out


async def search_knowledge(query: str, limit: int = 5) -> list[dict]:
    terms = [t.lower() for t in query.split() if len(t) > 2][:8]
    if not terms:
        return []
    async with db_session() as db:
        cur = await db.execute("SELECT id, category, title, content, tags FROM ai_knowledge")
        rows = await cur.fetchall()
    scored: list[tuple[int, dict]] = []
    for row in rows:
        blob = f"{row[2]} {row[3]} {row[4]}".lower()
        score = sum(1 for t in terms if t in blob)
        if score:
            scored.append((score, {"id": row[0], "category": row[1], "title": row[2], "content": row[3], "tags": row[4]}))
    scored.sort(key=lambda x: -x[0])
    return [item for _, item in scored[:limit]]


async def get_learning_notes(limit: int = 8) -> list[dict]:
    async with db_session() as db:
        cur = await db.execute(
            """SELECT id, topic, lesson, source, confidence, use_count FROM ai_learning_notes
               ORDER BY confidence DESC, use_count DESC, id DESC LIMIT ?""",
            (limit,),
        )
        rows = await cur.fetchall()
    return [
        {"id": r[0], "topic": r[1], "lesson": r[2], "source": r[3], "confidence": r[4], "use_count": r[5]}
        for r in rows
    ]


async def add_learning_note(topic: str, lesson: str, source: str = "self_critique", confidence: float = 0.75) -> bool:
    """Insert a learning note; skip near-duplicates. Returns True if inserted."""
    text = (lesson or "").strip()
    if len(text) < 12:
        return False
    now = datetime.now(timezone.utc).isoformat()
    needle = text[:80].lower()
    async with db_session() as db:
        cur = await db.execute(
            "SELECT id, lesson FROM ai_learning_notes ORDER BY id DESC LIMIT 80"
        )
        rows = await cur.fetchall()
        for _id, existing in rows:
            ex = (existing or "").lower()
            if needle in ex or ex[:80] in text.lower():
                # Reinforce existing lesson instead of duplicating
                await db.execute(
                    "UPDATE ai_learning_notes SET use_count = use_count + 1, confidence = MIN(0.95, confidence + 0.02) WHERE id = ?",
                    (_id,),
                )
                await db.commit()
                return False
        await db.execute(
            "INSERT INTO ai_learning_notes (topic, lesson, source, confidence, use_count, created_at) VALUES (?, ?, ?, ?, 0, ?)",
            (topic[:80], text[:2000], source, confidence, now),
        )
        await db.commit()
    return True


async def upsert_learning_note(
    topic: str,
    lesson: str,
    source: str = "portfolio_session",
    confidence: float = 0.9,
) -> None:
    """Replace the latest note for (topic, source) — used for live session state (portfolio)."""
    text = (lesson or "").strip()
    if len(text) < 12:
        return
    now = datetime.now(timezone.utc).isoformat()
    topic_key = topic[:80]
    async with db_session() as db:
        cur = await db.execute(
            "SELECT id FROM ai_learning_notes WHERE topic = ? AND source = ? ORDER BY id DESC LIMIT 1",
            (topic_key, source),
        )
        row = await cur.fetchone()
        if row:
            await db.execute(
                """UPDATE ai_learning_notes
                   SET lesson = ?, confidence = ?, created_at = ?, use_count = use_count + 1
                   WHERE id = ?""",
                (text[:2000], confidence, now, row[0]),
            )
        else:
            await db.execute(
                "INSERT INTO ai_learning_notes (topic, lesson, source, confidence, use_count, created_at) VALUES (?, ?, ?, ?, 0, ?)",
                (topic_key, text[:2000], source, confidence, now),
            )
        await db.commit()


async def add_feedback(session_id: str, message_id: int | None, rating: int, correction: str | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        await db.execute(
            "INSERT INTO ai_feedback (session_id, message_id, rating, correction, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, message_id, rating, correction, now),
        )
        await db.commit()


async def bump_learning_use(note_id: int) -> None:
    async with db_session() as db:
        await db.execute("UPDATE ai_learning_notes SET use_count = use_count + 1 WHERE id = ?", (note_id,))
        await db.commit()


async def get_stats() -> dict[str, int]:
    async with db_session() as db:
        k = await (await db.execute("SELECT COUNT(*) FROM ai_knowledge")).fetchone()
        l = await (await db.execute("SELECT COUNT(*) FROM ai_learning_notes")).fetchone()
    return {"knowledge_entries": k[0] if k else 0, "learning_notes": l[0] if l else 0}
