"""Whitelist for automatic posts on X.

Edit this file to add or remove a publisher. Automatic posts require the
article host to be in URL_HOSTS. A Google News label such as "Reuters" is not
enough while the link is still a news.google.com wrapper. Manual Publish is separate.
"""

from __future__ import annotations

# Case-insensitive substrings of the feed label (the `source` field).
SOURCE_LABELS: tuple[str, ...] = (
    "reuters",
    "associated press",
    "ap news",
    "agence france",
    "afp",
    "bloomberg",
    "bbc",
    "financial times",
    "ft ·",
    "ft ",
    "polska agencja prasowa",
    " pap",
    "pap ",
)

# Article URL host suffixes. Google News wrappers do not count.
URL_HOSTS: tuple[str, ...] = (
    "reuters.com",
    "apnews.com",
    "afp.com",
    "bloomberg.com",
    "bbc.com",
    "bbc.co.uk",
    "bbci.co.uk",
    "ft.com",
    "pap.pl",
    "federalreserve.gov",
    "ecb.europa.eu",
    "bankofengland.co.uk",
    "whitehouse.gov",
    "sec.gov",
    "imf.org",
    "bis.org",
    "worldbank.org",
    "aljazeera.com",
    "nhk.or.jp",
    "kyodonews.net",
    "yna.co.kr",
    "en.yna.co.kr",
    "abc.net.au",
    "cbc.ca",
    "dw.com",
    "france24.com",
    "euronews.com",
    "nikkei.com",
    "asia.nikkei.com",
    "lemonde.fr",
    "efe.com",
    "ansa.it",
    "dpa-international.com",
    "europa.eu",
    "un.org",
    "nato.int",
    "who.int",
)

# Canonical name printed in the post. The feed label is not trusted.
PUBLISHER_NAMES: dict[str, str] = {
    "reuters.com": "Reuters",
    "apnews.com": "Associated Press",
    "afp.com": "AFP",
    "bloomberg.com": "Bloomberg",
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
    "bbci.co.uk": "BBC",
    "ft.com": "Financial Times",
    "pap.pl": "PAP",
    "federalreserve.gov": "Federal Reserve",
    "ecb.europa.eu": "European Central Bank",
    "bankofengland.co.uk": "Bank of England",
    "whitehouse.gov": "White House",
    "sec.gov": "U.S. Securities and Exchange Commission",
    "imf.org": "IMF",
    "bis.org": "BIS",
    "worldbank.org": "World Bank",
    "aljazeera.com": "Al Jazeera",
    "nhk.or.jp": "NHK",
    "kyodonews.net": "Kyodo",
    "yna.co.kr": "Yonhap",
    "en.yna.co.kr": "Yonhap",
    "abc.net.au": "ABC",
    "cbc.ca": "CBC",
    "dw.com": "DW",
    "france24.com": "France 24",
    "euronews.com": "Euronews",
    "nikkei.com": "Nikkei",
    "asia.nikkei.com": "Nikkei",
    "lemonde.fr": "Le Monde",
    "efe.com": "EFE",
    "ansa.it": "ANSA",
    "dpa-international.com": "dpa",
    "europa.eu": "European Commission",
    "un.org": "United Nations",
    "nato.int": "NATO",
    "who.int": "WHO",
}

# Official institution feeds (press releases, not commentary).
OFFICIAL_LABELS: tuple[str, ...] = (
    "federal reserve",
    "fed · speeches",
    "european central bank",
    "bank of england",
    "white house",
    "u.s. securities",
)
