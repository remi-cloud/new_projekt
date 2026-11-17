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
)

# Official institution feeds (press releases, not commentary).
OFFICIAL_LABELS: tuple[str, ...] = (
    "federal reserve",
    "fed · speeches",
    "european central bank",
    "bank of england",
    "white house",
    "u.s. securities",
)
