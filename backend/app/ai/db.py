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


async def _seed_knowledge_if_empty() -> None:
    async with db_session() as db:
        cur = await db.execute("SELECT COUNT(*) FROM ai_knowledge")
        row = await cur.fetchone()
        if row and row[0] > 0:
            return

    seeds = [
        ("cycles", "Cykl Bitcoina 364/1064", "Po ATH Bitcoin często przechodzi fazę spadkową (~364 dni), potem falę wzrostową (~1064 dni), następnie dystrybucję. Sygnały krypto powinny uwzględniać fazę cyklu BTC.", "bitcoin,crypto,cycle"),
        ("cycles", "Cykl prezydencki USA", "Historycznie rok 3 kadencji bywa najsilniejszy dla S&P 500, rok 2 najsłabszy (midterms). Dotyczy aktywów z regionem US.", "usa,presidential,cycle"),
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


async def add_learning_note(topic: str, lesson: str, source: str = "self_critique", confidence: float = 0.75) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with db_session() as db:
        await db.execute(
            "INSERT INTO ai_learning_notes (topic, lesson, source, confidence, use_count, created_at) VALUES (?, ?, ?, ?, 0, ?)",
            (topic[:80], lesson[:2000], source, confidence, now),
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
