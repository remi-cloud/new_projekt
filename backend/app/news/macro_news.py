"""Macro & geopolitical news from public RSS feeds — Fed, USA, global events."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import httpx

from app.config import settings
from app.models.schemas import MacroCalendarMonthResponse, MacroNewsCategory, MacroNewsFeed, MacroNewsItem
from app.news.calendar_ai import enrich_calendar_events
from app.news.google_news_urls import resolve_item_urls
from app.news.ideology_lens import sort_by_alignment
from app.news.image_agent import enrich_items, generate_missing
from app.news.image_sources import extract_image_from_rss_description
from app.news.macro_calendar import get_calendar_month, get_upcoming_calendar

logger = logging.getLogger(__name__)

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CyclicalTrader/1.4; +macro-news)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Cache-Control": "no-cache",
}

# (url, source label, default category)
RSS_SOURCES: list[tuple[str, str, MacroNewsCategory]] = [
    # ── Elon Musk & companies (priority) ───────────────────────────
    ("https://news.google.com/rss/search?q=Elon+Musk+when:1h&hl=en-US&gl=US&ceid=US:en", "Elon Musk", "musk"),
    ("https://news.google.com/rss/search?q=Tesla+stock+OR+Tesla+earnings+when:1h&hl=en-US&gl=US&ceid=US:en", "Tesla", "musk"),
    ("https://news.google.com/rss/search?q=SpaceX+Starship+OR+Starlink+when:1h&hl=en-US&gl=US&ceid=US:en", "SpaceX", "musk"),
    ("https://news.google.com/rss/search?q=xAI+OR+Grok+when:1h&hl=en-US&gl=US&ceid=US:en", "xAI · Grok", "musk"),
    ("https://news.google.com/rss/search?q=Neuralink+when:1h&hl=en-US&gl=US&ceid=US:en", "Neuralink", "musk"),
    ("https://news.google.com/rss/search?q=Elon+Musk+(Robotaxi+OR+Optimus+OR+%22free+speech%22+OR+Starship)+when:1h&hl=en-US&gl=US&ceid=US:en", "Musk · Growth", "musk"),
    ("https://news.google.com/rss/search?q=Musk+DOGE+OR+%22Department+of+Government+Efficiency%22+OR+Trump+Musk+when:1h&hl=en-US&gl=US&ceid=US:en", "Musk · DOGE", "musk"),
    ("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000161", "CNBC · Tesla", "musk"),
    ("https://electrek.co/feed/", "Electrek", "musk"),
    ("https://www.teslarati.com/feed/", "Teslarati", "musk"),
    ("https://www.space.com/feeds/all", "Space.com", "musk"),

    # ── Trump / USA — pro-growth & policy (priority) ───────────────
    ("https://news.google.com/rss/search?q=Donald+Trump+(economy+OR+tariff+OR+deregulation+OR+%22America+First%22)+when:1h&hl=en-US&gl=US&ceid=US:en", "Trump · Economy", "usa"),
    ("https://news.google.com/rss/search?q=Trump+(energy+OR+drill+OR+%22energy+dominance%22+OR+border)+when:1h&hl=en-US&gl=US&ceid=US:en", "Trump · Energy", "usa"),
    ("https://news.google.com/rss/search?q=Trump+White+House+OR+executive+order+when:1h&hl=en-US&gl=US&ceid=US:en", "Trump · WH", "usa"),
    ("https://moxie.foxnews.com/google-publisher/politics.xml", "Fox News · Politics", "usa"),
    ("https://moxie.foxbusiness.com/google-publisher/politics.xml", "Fox Business · Politics", "usa"),
    ("https://nypost.com/politics/feed/", "NY Post · Politics", "usa"),
    ("https://www.washingtonexaminer.com/news/feed/", "Washington Examiner", "usa"),

    # ── Stagflation / Fed / cost-of-living (Trump–Musk macro frame) ─
    ("https://news.google.com/rss/search?q=stagflation+OR+%22sticky+inflation%22+OR+%22cost+of+living%22+Fed+when:1h&hl=en-US&gl=US&ceid=US:en", "Stagflation · Fed", "macro"),
    ("https://news.google.com/rss/search?q=stagflation+(energy+OR+tariff+OR+spending+OR+Trump)+when:1h&hl=en-US&gl=US&ceid=US:en", "Stagflation · Policy", "macro"),
    ("https://news.google.com/rss/search?q=site:zerohedge.com+when:1h&hl=en-US&gl=US&ceid=US:en", "ZeroHedge", "macro"),

    # ── Google News — tylko agregaty bez własnego RSS (when:1h = świeże) ──
    ("https://news.google.com/rss/search?q=site:reuters.com+when:1h&hl=en-US&gl=US&ceid=US:en", "Reuters", "global"),
    ("https://news.google.com/rss/search?q=site:bloomberg.com+when:1h&hl=en-US&gl=US&ceid=US:en", "Bloomberg", "macro"),
    ("https://news.google.com/rss/search?q=Europe+markets+economy+when:1h&hl=en-US&gl=US&ceid=US:en", "Google · Europe", "global"),
    ("https://news.google.com/rss/search?q=China+Japan+Asia+markets+when:1h&hl=en-US&gl=US&ceid=US:en", "Google · Asia", "global"),
    ("https://news.google.com/rss/search?q=OPEC+oil+energy+prices+when:1h&hl=en-US&gl=US&ceid=US:en", "Google · Energy", "global"),
    ("https://news.google.com/rss/search?q=stock+market+breaking+when:1h&hl=en-US&gl=US&ceid=US:en", "Google · Markets", "macro"),
    ("https://news.google.com/rss/search?q=Federal+Reserve+OR+FOMC+when:1h&hl=en-US&gl=US&ceid=US:en", "Google · Fed", "fed"),
    ("https://news.google.com/rss/search?q=Donald+Trump+OR+US+politics+when:1h&hl=en-US&gl=US&ceid=US:en", "Google · USA", "usa"),

    # ── USA — Fed ─────────────────────────────────────────────────
    ("https://www.federalreserve.gov/feeds/press_all.xml", "Federal Reserve", "fed"),
    ("https://www.federalreserve.gov/feeds/speeches.xml", "Fed · Speeches", "fed"),

    # ── USA — markets & politics ────────────────────────────────────
    ("https://finance.yahoo.com/news/rssindex", "Yahoo Finance", "macro"),
    ("https://feeds.marketwatch.com/marketwatch/topstories/", "MarketWatch", "macro"),
    ("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "CNBC", "macro"),
    ("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362", "CNBC · Economy", "macro"),
    ("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000113", "CNBC · Politics", "usa"),
    ("https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "WSJ · Markets", "macro"),
    ("https://feeds.a.dj.com/rss/RSSWorldNews.xml", "WSJ · World", "global"),
    ("https://www.ft.com/markets?format=rss", "FT · Markets", "macro"),
    ("https://www.ft.com/world?format=rss", "FT · World", "global"),
    ("https://www.ft.com/?format=rss", "Financial Times", "macro"),
    ("https://moxie.foxbusiness.com/google-publisher/economy.xml", "Fox Business · Economy", "macro"),
    ("https://moxie.foxbusiness.com/google-publisher/latest.xml", "Fox Business", "macro"),

    # ── Europe ────────────────────────────────────────────────────
    ("https://feeds.bbci.co.uk/news/business/rss.xml", "BBC Business", "global"),
    ("https://www.theguardian.com/business/rss", "Guardian · Business", "global"),
    ("https://www.theguardian.com/world/rss", "Guardian · World", "global"),
    ("https://rss.dw.com/rdf/rss-en-bus", "DW · Business", "global"),
    ("https://rss.dw.com/rdf/rss-en-world", "DW · World", "global"),
    ("https://www.france24.com/en/business/rss", "France 24 · Business", "global"),
    ("https://www.euronews.com/rss?format=mrss&level=theme&name=business", "Euronews · Business", "global"),
    ("https://www.handelsblatt.com/contentexport/feed/top-themen", "Handelsblatt", "global"),
    ("https://www.lemonde.fr/economie/rss_full.xml", "Le Monde · Économie", "global"),
    ("https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada", "El País · Economía", "global"),
    ("https://www.corriere.it/dynamic-feed/rss/section/Economia.xml", "Corriere · Economia", "global"),
    ("https://www.spiegel.de/international/index.rss", "Spiegel International", "global"),

    # ── Asia & Pacific ────────────────────────────────────────────
    ("https://asia.nikkei.com/rss/feed/nar", "Nikkei Asia", "global"),
    ("https://www.japantimes.co.jp/feed/", "Japan Times", "global"),
    ("https://www.scmp.com/rss/91/feed", "SCMP · Business", "global"),
    ("https://www.scmp.com/rss/2/feed", "SCMP", "global"),
    ("https://www.straitstimes.com/news/business/rss.xml", "Straits Times · Business", "global"),
    ("https://economictimes.indiatimes.com/rssfeedsdefault.cms", "Economic Times", "global"),
    ("https://timesofindia.indiatimes.com/rssfeeds/1898055.cms", "Times of India · Business", "global"),

    # ── Crypto / blockchain ───────────────────────────────────────
    ("https://news.bitcoin.com/feed/", "Bitcoin.com", "crypto"),
    ("https://www.coindesk.com/arc/outboundfeeds/rss/", "CoinDesk", "crypto"),
    ("https://cointelegraph.com/rss", "Cointelegraph", "crypto"),
    ("https://decrypt.co/feed", "Decrypt", "crypto"),
    ("https://www.theblock.co/rss.xml", "The Block", "crypto"),
    ("https://blog.blockchain.com/rss/", "Blockchain.com", "crypto"),
    ("https://news.google.com/rss/search?q=site:bitcoinmagazine.com+when:1h&hl=en-US&gl=US&ceid=US:en", "Bitcoin Magazine", "crypto"),
    ("https://news.google.com/rss/search?q=site:cryptoslate.com+when:1h&hl=en-US&gl=US&ceid=US:en", "CryptoSlate", "crypto"),
    ("https://news.google.com/rss/search?q=Bitcoin+OR+BTC+when:1h&hl=en-US&gl=US&ceid=US:en", "Google · Bitcoin", "crypto"),
    ("https://news.google.com/rss/search?q=Ethereum+OR+ETH+when:1h&hl=en-US&gl=US&ceid=US:en", "Google · Ethereum", "crypto"),
    ("https://news.google.com/rss/search?q=(crypto+ETF+OR+Bitcoin+ETF+OR+Ethereum+ETF)+OR+(SEC+crypto)+when:1h&hl=en-US&gl=US&ceid=US:en", "Google · Crypto ETF", "crypto"),
    ("https://news.google.com/rss/search?q=Binance+OR+Coinbase+when:1h&hl=en-US&gl=US&ceid=US:en", "Google · Exchanges", "crypto"),
    ("https://news.google.com/rss/search?q=blockchain+OR+DeFi+OR+stablecoin+when:1h&hl=en-US&gl=US&ceid=US:en", "Google · DeFi", "crypto"),
]

_MUSK_SOURCE_LABELS = frozenset({
    "Elon Musk", "Tesla", "SpaceX", "xAI · Grok", "Neuralink",
    "Musk · Growth", "Musk · DOGE",
    "CNBC · Tesla", "Electrek", "Teslarati", "Space.com",
})

_USA_SOURCE_LABELS = frozenset({
    "Trump · Economy", "Trump · Energy", "Trump · WH", "Google · USA",
    "Fox News · Politics", "Fox Business · Politics",
    "NY Post · Politics", "Washington Examiner", "CNBC · Politics",
})

_CRYPTO_SOURCE_LABELS = frozenset({
    "Bitcoin.com", "CoinDesk", "Cointelegraph", "Decrypt", "The Block",
    "Blockchain.com", "Bitcoin Magazine", "CryptoSlate",
    "Google · Bitcoin", "Google · Ethereum", "Google · Crypto ETF",
    "Google · Exchanges", "Google · DeFi",
})

_PRIORITY_SOURCE_LABELS = _MUSK_SOURCE_LABELS | _USA_SOURCE_LABELS | _CRYPTO_SOURCE_LABELS | frozenset({
    "Stagflation · Fed", "Stagflation · Policy", "ZeroHedge",
    "Desk · Trump · wzrost", "Desk · Musk · podaż", "Desk · Stagflacja",
})

_CATEGORY_RULES: list[tuple[MacroNewsCategory, tuple[str, ...]]] = [
    (
        "musk",
        (
            r"elon musk",
            r"\btesla\b",
            r"\bspacex\b",
            r"\bstarlink\b",
            r"starship",
            r"neuralink",
            r"\bxai\b",
            r"\bgrok\b",
            r"\bx\.com\b",
            r"\brobotaxi\b",
            r"\boptimus\b",
            r"\bdoge\b",
            r"department of government efficiency",
            r"musk",
        ),
    ),
    (
        "crypto",
        (
            r"\bbitcoin\b",
            r"\bbtc\b",
            r"\bethereum\b",
            r"\beth\b",
            r"\bsolana\b",
            r"\bsol\b",
            r"\bcrypto\b",
            r"cryptocurrency",
            r"\bdefi\b",
            r"\bnft\b",
            r"stablecoin",
            r"\busdt\b",
            r"\busdc\b",
            r"bitcoin etf",
            r"ethereum etf",
            r"crypto etf",
            r"\bbinance\b",
            r"\bcoinbase\b",
            r"\bblockchain\b",
            r"\bmining\b",
            r"\bhalving\b",
            r"\bdogecoin\b",
            r"\bxrp\b",
            r"\bripple\b",
            r"\bweb3\b",
            r"\btokeniz",
            r"sec.*(crypto|bitcoin|ethereum)",
            r"(crypto|bitcoin|ethereum).*sec",
        ),
    ),
    (
        "fed",
        (
            r"\bfed\b",
            r"\bfomc\b",
            r"federal reserve",
            r"powell",
            r"interest rate",
            r"rate cut",
            r"rate hike",
            r"basis point",
            r"monetary policy",
            r"fed funds",
            r"treasury yield",
        ),
    ),
    (
        "usa",
        (
            r"\btrump\b",
            r"white house",
            r"tariff",
            r"executive order",
            r"congress",
            r"senate",
            r"u\.s\.",
            r"\busa\b",
            r"america first",
            r"energy dominance",
            r"deregulat",
            r"reciprocal tariff",
        ),
    ),
    (
        "macro",
        (
            r"\bcpi\b",
            r"\bppi\b",
            r"\bgdp\b",
            r"inflation",
            r"stagflation",
            r"stagflacj",
            r"cost.?of.?living",
            r"sticky inflation",
            r"unemployment",
            r"jobs report",
            r"payroll",
            r"nonfarm",
            r"recession",
            r"\becb\b",
            r"european central",
            r"bank of england",
            r"pmi",
            r"consumer confidence",
        ),
    ),
    (
        "global",
        (
            r"\bchina\b",
            r"\brussia\b",
            r"\bukraine\b",
            r"\biran\b",
            r"\bisrael\b",
            r"\bopec\b",
            r"sanction",
            r"geopolit",
            r"\btaiwan\b",
            r"middle east",
            r"trade war",
            r"\bnato\b",
            r"eurozone",
            r"war ",
            r"conflict",
        ),
    ),
]

_IMPACT_HIGH = (
    r"fomc",
    r"rate (cut|hike|decision)",
    r"\bcpi\b",
    r"jobs report",
    r"nonfarm",
    r"payroll",
    r"gdp",
    r"tariff",
    r"\btrump\b",
    r"stagflation",
    r"cost.?of.?living",
    r"\bdoge\b",
    r"sanction",
    r"war ",
    r"emergency",
    r"crisis",
    r"powell",
    r"elon musk",
    r"\btesla\b",
    r"\bspacex\b",
    r"\brobotaxi\b",
    r"\bbitcoin\b",
    r"\bbtc\b",
    r"\bethereum\b",
    r"crypto etf",
    r"bitcoin etf",
    r"\bbinance\b",
    r"\bcoinbase\b",
    r"\bhalving\b",
    r"stablecoin",
)

_cache: MacroNewsFeed | None = None
_pool: list[MacroNewsItem] = []
_cache_lock = asyncio.Lock()


def _stable_id(link: str, title: str) -> str:
    key = (link or title).strip().lower()
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _parse_date(raw: str | None) -> datetime | None:
    """Parse RSS date. Missing/invalid → None (never invent 'now' for stale articles)."""
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


_URL_YMD = re.compile(r"/(20\d{2})/(\d{1,2})/(\d{1,2})(?:/|$)")
_URL_YM = re.compile(r"/(20\d{2})/(\d{1,2})(?:/|$)")


def _article_date_from_url(url: str | None) -> date | None:
    if not url:
        return None
    m = _URL_YMD.search(url)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = _URL_YM.search(url)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), 1)
        except ValueError:
            return None
    return None


def _is_stale_article(
    published: datetime | None,
    url: str | None,
    now: datetime,
) -> bool:
    """Drop old pieces that Google/RSS re-surface with a fresh pubDate."""
    max_days = max(1, settings.news_article_max_age_days)
    if published is None:
        return True
    if now - published > timedelta(hours=settings.news_fresh_hours):
        return True
    url_day = _article_date_from_url(url)
    if url_day is not None and (now.date() - url_day).days > max_days:
        return True
    return False


def _title_fingerprint(title: str) -> str:
    """Normalize title for near-duplicate detection."""
    raw = (title or "").lower()
    raw = re.sub(r"[^a-z0-9\s]", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw[:80]


def _dedupe_by_title(items: list[MacroNewsItem]) -> list[MacroNewsItem]:
    """Keep newest item per title fingerprint."""
    seen: set[str] = set()
    out: list[MacroNewsItem] = []
    for item in sorted(items, key=lambda n: n.published_at, reverse=True):
        fp = _title_fingerprint(item.title)
        if not fp or fp in seen:
            continue
        seen.add(fp)
        out.append(item)
    return out


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _extract_item_image_url(node, description: str, link: str) -> str | None:
    candidates: list[str] = []
    for child in node:
        name = _local_name(child.tag)
        url = child.get("url") or child.get("href") or (child.text or "").strip()
        if name in ("content", "thumbnail") and url.startswith("http"):
            candidates.append(url)
        if name == "enclosure" and url.startswith("http"):
            enc_type = (child.get("type") or "").lower()
            if "image" in enc_type or _is_http_image(url):
                candidates.append(url)
    desc_img = extract_image_from_rss_description(description, link)
    if desc_img:
        candidates.append(desc_img)
    for url in candidates:
        if url.startswith("http"):
            return url
    return None


def _is_http_image(url: str) -> bool:
    lower = url.lower()
    return any(ext in lower for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"))


def _parse_rss_xml(content: bytes, source: str, default_category: MacroNewsCategory) -> list[dict]:
    items: list[dict] = []
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        logger.warning("RSS parse error %s: %s", source, exc)
        return items

    for node in root.iter():
        if _local_name(node.tag) != "item":
            continue
        title = ""
        link = ""
        summary = ""
        published: str | None = None
        raw_description = ""
        for child in node:
            name = _local_name(child.tag)
            text = (child.text or "").strip()
            if name == "title":
                title = text
            elif name == "link":
                link = text or child.get("href", "")
            elif name in ("description", "summary", "content"):
                if not summary:
                    raw_description = text
                    summary = _strip_html(text)
            elif name in ("pubDate", "published", "updated"):
                published = text or child.get("datetime")
        source_image_url = _extract_item_image_url(node, raw_description, link)
        published_at = _parse_date(published)
        if title and published_at is not None:
            items.append(
                {
                    "title": title,
                    "link": link,
                    "summary": summary[:400] if summary else None,
                    "source_image_url": source_image_url,
                    "source": source,
                    "default_category": default_category,
                    "published_at": published_at,
                }
            )
    return items


async def _fetch_one_feed(
    client: httpx.AsyncClient,
    url: str,
    source: str,
    default_category: MacroNewsCategory,
) -> list[dict]:
    try:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        return _parse_rss_xml(resp.content, source, default_category)
    except Exception as exc:
        logger.warning("RSS fetch failed %s (%s): %s", source, url, exc)
        return []


def _classify_item(title: str, summary: str | None, default: MacroNewsCategory) -> MacroNewsCategory:
    blob = f"{title} {summary or ''}".lower()
    for category, patterns in _CATEGORY_RULES:
        for pat in patterns:
            if re.search(pat, blob, re.I):
                return category
    return default


def _impact_level(title: str, summary: str | None) -> str:
    blob = f"{title} {summary or ''}".lower()
    for pat in _IMPACT_HIGH:
        if re.search(pat, blob, re.I):
            return "high"
    return "medium"


def _source_cap(source: str) -> int:
    if source in _MUSK_SOURCE_LABELS:
        return settings.news_musk_max_per_source
    if source in _CRYPTO_SOURCE_LABELS:
        return settings.news_crypto_max_per_source
    if source in _USA_SOURCE_LABELS or source.startswith("Desk ·"):
        return settings.news_usa_max_per_source
    if source in ("Stagflation · Fed", "Stagflation · Policy", "ZeroHedge"):
        return settings.news_usa_max_per_source
    return settings.news_max_per_source


def _age_minutes(item: MacroNewsItem, now: datetime | None = None) -> int:
    if item.age_minutes is not None:
        return item.age_minutes
    ref = now or datetime.now(timezone.utc)
    return int((ref - item.published_at).total_seconds() / 60)


def _display_fresh(pool: list[MacroNewsItem], category: MacroNewsCategory | None = None) -> list[MacroNewsItem]:
    """Only very fresh items — no relaxation to older windows."""
    max_mins = settings.news_display_max_hours * 60
    scoped = pool if category is None else [n for n in pool if n.category == category]
    now = datetime.now(timezone.utc)
    fresh = [
        n
        for n in scoped
        if _age_minutes(n) <= max_mins and not _is_stale_article(n.published_at, n.url, now)
    ]
    return fresh


def _category_counts(pool: list[MacroNewsItem]) -> dict[str, int]:
    counts = {c: 0 for c in ("fed", "usa", "macro", "global", "musk", "crypto")}
    for item in _display_fresh(pool):
        counts[item.category] = counts.get(item.category, 0) + 1
    return counts


def _diversify_by_source(items: list[MacroNewsItem], limit: int) -> list[MacroNewsItem]:
    """Round-robin across sources so one publisher cannot dominate the feed."""
    by_source: dict[str, list[MacroNewsItem]] = {}
    for item in items:
        by_source.setdefault(item.source, []).append(item)
    for bucket in by_source.values():
        bucket.sort(key=lambda n: n.published_at, reverse=True)

    caps = {src: _source_cap(src) for src in by_source}
    picked: list[MacroNewsItem] = []
    sources = sorted(
        by_source.keys(),
        key=lambda s: (
            0 if s in _MUSK_SOURCE_LABELS else 1 if s in _PRIORITY_SOURCE_LABELS else 2,
            s,
        ),
    )

    while len(picked) < limit:
        added = False
        for src in sources:
            if not by_source[src] or caps[src] <= 0:
                continue
            picked.append(by_source[src].pop(0))
            caps[src] -= 1
            added = True
            if len(picked) >= limit:
                break
        if not added:
            break
    return picked


def _build_category_view(
    pool: list[MacroNewsItem],
    category: MacroNewsCategory | None,
    limit: int,
) -> list[MacroNewsItem]:
    """Build a freshness-first feed for one tab (or all), Trump/Musk biased."""
    boost = settings.news_ideology_boost

    if category and category != "all":
        scoped = _display_fresh(pool, category)
        if boost:
            scoped = sort_by_alignment(scoped)
        else:
            scoped.sort(key=lambda n: n.published_at, reverse=True)
        return _diversify_by_source(scoped, limit)

    fresh_pool = _display_fresh(pool)
    musk_slots = settings.news_musk_feed_slots
    usa_slots = settings.news_usa_feed_slots
    crypto_slots = settings.news_crypto_feed_slots

    musk_items = [n for n in fresh_pool if n.category == "musk"]
    usa_items = [n for n in fresh_pool if n.category == "usa"]
    crypto_items = [n for n in fresh_pool if n.category == "crypto"]
    other_items = [n for n in fresh_pool if n.category not in ("musk", "usa", "crypto")]

    if boost:
        musk_items = sort_by_alignment(musk_items)
        usa_items = sort_by_alignment(usa_items)
        crypto_items = sort_by_alignment(crypto_items)
        other_items = sort_by_alignment(other_items)
    else:
        musk_items.sort(key=lambda n: n.published_at, reverse=True)
        usa_items.sort(key=lambda n: n.published_at, reverse=True)
        crypto_items.sort(key=lambda n: n.published_at, reverse=True)
        other_items.sort(key=lambda n: n.published_at, reverse=True)

    musk_part = musk_items[:musk_slots]
    usa_part = usa_items[:usa_slots]
    crypto_part = crypto_items[:crypto_slots]
    reserved = len(musk_part) + len(usa_part) + len(crypto_part)
    remaining = max(0, limit - reserved)
    diverse_rest = _diversify_by_source(other_items, remaining)
    combined = musk_part + usa_part + crypto_part + diverse_rest
    if boost:
        combined = sort_by_alignment(combined)
    else:
        combined.sort(key=lambda n: n.published_at, reverse=True)
    return combined[:limit]


async def _fresh_display(
    pool: list[MacroNewsItem],
    category: MacroNewsCategory | None,
    limit: int,
    now: datetime,
) -> list[MacroNewsItem]:
    """Build tab feed, unwrap Google links, drop resurfaced old URL dates, top up."""
    rejected: set[str] = set()
    picked: list[MacroNewsItem] = []
    # Over-fetch then filter — Google often re-dates old March/April pieces as "now"
    batch_limit = max(limit * 3, limit + 40)

    while len(picked) < limit:
        remaining_pool = [n for n in pool if n.id not in rejected]
        if not remaining_pool:
            break
        batch = _build_category_view(remaining_pool, category, batch_limit)
        if not batch:
            break
        batch = await resolve_item_urls(batch)
        added = 0
        for item in batch:
            if item.id in rejected or any(p.id == item.id for p in picked):
                continue
            if not item.is_curated and _is_stale_article(item.published_at, item.url, now):
                rejected.add(item.id)
                continue
            picked.append(item)
            added += 1
            if len(picked) >= limit:
                break
        if added == 0:
            break
        # Shrink next batch target
        batch_limit = max(limit - len(picked) + 10, 20)

    picked = _dedupe_by_title(picked)
    if settings.news_ideology_boost:
        picked = sort_by_alignment(picked)
    else:
        picked.sort(key=lambda n: n.published_at, reverse=True)
    return picked[:limit]


async def refresh_macro_news() -> tuple[MacroNewsFeed, list[MacroNewsItem]]:
    """Refresh cache; returns (feed, live_items_before_dedup_for_alerts)."""
    global _cache, _pool
    raw_items: list[dict] = []

    async with httpx.AsyncClient(timeout=20, headers=HTTP_HEADERS) as client:
        tasks = [_fetch_one_feed(client, url, source, cat) for url, source, cat in RSS_SOURCES]
        results = await asyncio.gather(*tasks)
        for batch in results:
            raw_items.extend(batch)

    now = datetime.now(timezone.utc)
    max_age = timedelta(hours=settings.news_fresh_hours)
    seen_keys: set[str] = set()
    news: list[MacroNewsItem] = []

    for row in raw_items:
        link = row.get("link") or ""
        dedupe_key = link or row["title"].lower()
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)

        published = row["published_at"]
        if published is None or _is_stale_article(published, link or None, now):
            continue
        if now - published > max_age:
            continue

        category = _classify_item(row["title"], row.get("summary"), row["default_category"])
        if row["default_category"] == "musk" and category != "musk":
            continue
        if row["default_category"] == "crypto":
            category = "crypto"

        impact = _impact_level(row["title"], row.get("summary"))
        age_mins = int((now - published).total_seconds() / 60)
        # Musk / crypto priority sources: even stricter — only within display window
        if age_mins > settings.news_display_max_hours * 60 and row["source"] in (
            _MUSK_SOURCE_LABELS | _CRYPTO_SOURCE_LABELS
        ):
            continue

        news.append(
            MacroNewsItem(
                id=_stable_id(link, row["title"]),
                title=row["title"],
                summary=row.get("summary"),
                url=link or None,
                source_image_url=row.get("source_image_url"),
                source=row["source"],
                category=category,
                impact=impact,
                published_at=published,
                is_curated=False,
                age_minutes=age_mins,
            )
        )

    # Live wire only — curated desk essays stay out of the public feed.
    news = _dedupe_by_title(news)
    news.sort(key=lambda n: n.published_at, reverse=True)
    news = news[: settings.news_pool_limit]
    # Recompute age from refresh time (never trust stale age_minutes)
    for i, item in enumerate(news):
        age = int((now - item.published_at).total_seconds() / 60)
        if item.age_minutes != age:
            news[i] = item.model_copy(update={"age_minutes": max(0, age)})
    news = enrich_items(news)
    news = await resolve_item_urls(news)

    counts = _category_counts(news)
    # Resolve + drop resurfaced old URLs (Google often stamps old March pieces as "now")
    display_items = await _fresh_display(news, None, settings.news_feed_limit, now)
    by_id = {n.id: n for n in display_items}
    news = [by_id.get(n.id, n) for n in news]
    fresh_1h = sum(1 for n in news if _age_minutes(n, now) <= 60)

    # Feed strip: next dozen only (calendar month endpoint assesses the full month)
    upcoming = await enrich_calendar_events(get_upcoming_calendar()[:12], locale="pl")
    feed = MacroNewsFeed(
        items=display_items,
        calendar_events=upcoming,
        fetched_at=now,
        counts=counts,
        sources_count=len(RSS_SOURCES),
        poll_interval_seconds=settings.news_poll_interval_seconds,
        fresh_count_1h=fresh_1h,
    )

    async with _cache_lock:
        _pool = news
        _cache = feed
    logger.info(
        "Macro news: %d pool / %d display (%d last 1h) from %d feeds",
        len(news),
        len(display_items),
        fresh_1h,
        len(RSS_SOURCES),
    )
    return feed, news


async def get_macro_news(category: str | None = None, limit: int = 50, locale: str | None = "pl") -> MacroNewsFeed:
    global _cache, _pool
    async with _cache_lock:
        cached = _cache
        pool = list(_pool)
    if cached is None or not pool:
        cached, _ = await refresh_macro_news()
        async with _cache_lock:
            pool = list(_pool)

    cat: MacroNewsCategory | None = None
    if category and category != "all":
        cat = category  # type: ignore[assignment]

    now = datetime.now(timezone.utc)
    items = await _fresh_display(pool, cat, limit, now)
    counts = _category_counts(pool)

    # Persist resolved urls back into the in-memory pool / cache
    async with _cache_lock:
        if _pool:
            resolved = {n.id: n for n in items}
            _pool = [resolved.get(n.id, n) for n in _pool]
        if _cache is not None and not cat:
            _cache = _cache.model_copy(update={"items": enrich_items(items)})

    upcoming = await enrich_calendar_events(get_upcoming_calendar(locale=locale)[:12], locale=locale)
    return MacroNewsFeed(
        items=enrich_items(items),
        calendar_events=upcoming,
        fetched_at=cached.fetched_at,
        counts=counts,
        sources_count=cached.sources_count,
        poll_interval_seconds=cached.poll_interval_seconds,
        fresh_count_1h=cached.fresh_count_1h,
    )


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


async def get_macro_calendar_month(year: int, month: int, locale: str | None = "pl") -> MacroCalendarMonthResponse:
    global _cache, _pool
    async with _cache_lock:
        cached = _cache
        pool = list(_pool)
    if cached is None or not pool:
        cached, _ = await refresh_macro_news()
        async with _cache_lock:
            pool = list(_pool)

    events = await enrich_calendar_events(
        get_calendar_month(year, month, locale=locale),
        locale=locale,
    )
    start, end = _month_bounds(year, month)
    news = [
        item
        for item in pool
        if start <= item.published_at.date() <= end
    ]
    news = await resolve_item_urls(news)

    return MacroCalendarMonthResponse(
        year=year,
        month=month,
        events=events,
        news=enrich_items(news),
        fetched_at=cached.fetched_at,
        poll_interval_seconds=cached.poll_interval_seconds,
    )


async def get_news_item_by_id(news_id: str) -> MacroNewsItem | None:
    """Lookup a cached news item by stable id."""
    async with _cache_lock:
        pool = list(_pool)
    for item in pool:
        if item.id == news_id:
            return item
    return None


async def patch_cached_image(news_id: str, image_url: str) -> None:
    global _cache, _pool
    async with _cache_lock:
        if _pool:
            _pool = [
                item.model_copy(update={"image_url": image_url}) if item.id == news_id else item
                for item in _pool
            ]
        if _cache is None:
            return
        updated: list[MacroNewsItem] = []
        for item in _cache.items:
            if item.id == news_id:
                updated.append(item.model_copy(update={"image_url": image_url}))
            else:
                updated.append(item)
        _cache = _cache.model_copy(update={"items": updated})


async def schedule_news_images(items: list[MacroNewsItem], on_ready) -> None:
    """Background batch — generate hero images for news missing artwork."""
    try:
        await generate_missing(items, on_ready=on_ready)
    except Exception as exc:
        logger.warning("News image batch failed: %s", exc)
