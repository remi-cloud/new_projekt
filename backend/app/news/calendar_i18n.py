"""Localized titles for macro calendar events."""

from __future__ import annotations

SUPPORTED_LOCALES = frozenset({"pl", "de", "en", "fil", "es", "fr", "it"})

MONTHS: dict[str, list[str]] = {
    "pl": ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"],
    "de": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    "fil": ["Enero", "Pebrero", "Marso", "Abril", "Mayo", "Hunyo", "Hulyo", "Agosto", "Setyembre", "Oktubre", "Nobyembre", "Disyembre"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    "it": ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"],
}

TEMPLATES: dict[str, dict[str, str]] = {
    "fomc": {
        "pl": "FOMC — decyzja o stopach ({period})",
        "de": "FOMC — Zinsentscheid ({period})",
        "en": "FOMC — rate decision ({period})",
        "fil": "FOMC — desisyon sa rate ({period})",
        "es": "FOMC — decisión de tipos ({period})",
        "fr": "FOMC — décision sur les taux ({period})",
        "it": "FOMC — decisione sui tassi ({period})",
    },
    "cpi": {
        "pl": "CPI USA — inflacja konsumencka ({period})",
        "de": "US-CPI — Verbraucherpreise ({period})",
        "en": "US CPI — consumer inflation ({period})",
        "fil": "US CPI — inflation ng consumer ({period})",
        "es": "CPI EE.UU. — inflación al consumidor ({period})",
        "fr": "IPC USA — inflation des ménages ({period})",
        "it": "CPI USA — inflazione al consumo ({period})",
    },
    "nfp": {
        "pl": "NFP / Payrolls USA — rynek pracy ({period})",
        "de": "NFP / US-Arbeitsmarkt ({period})",
        "en": "NFP / US payrolls — jobs report ({period})",
        "fil": "NFP / US payrolls — ulat sa trabaho ({period})",
        "es": "NFP / nóminas EE.UU. — empleo ({period})",
        "fr": "NFP / emplois US — marché du travail ({period})",
        "it": "NFP / payroll USA — mercato del lavoro ({period})",
    },
    "ecb": {
        "pl": "ECB — decyzja o stopach ({period})",
        "de": "EZB — Zinsentscheid ({period})",
        "en": "ECB — rate decision ({period})",
        "fil": "ECB — desisyon sa rate ({period})",
        "es": "BCE — decisión de tipos ({period})",
        "fr": "BCE — décision sur les taux ({period})",
        "it": "BCE — decisione sui tassi ({period})",
    },
    "boe": {
        "pl": "BoE — decyzja o stopach ({period})",
        "de": "BoE — Zinsentscheid ({period})",
        "en": "BoE — rate decision ({period})",
        "fil": "BoE — desisyon sa rate ({period})",
        "es": "BoE — decisión de tipos ({period})",
        "fr": "BoE — décision sur les taux ({period})",
        "it": "BoE — decisione sui tassi ({period})",
    },
    "boj": {
        "pl": "BoJ — decyzja o stopach ({period})",
        "de": "BoJ — Zinsentscheid ({period})",
        "en": "BoJ — rate decision ({period})",
        "fil": "BoJ — desisyon sa rate ({period})",
        "es": "BoJ — decisión de tipos ({period})",
        "fr": "BoJ — décision sur les taux ({period})",
        "it": "BoJ — decisione sui tassi ({period})",
    },
    "opec": {
        "pl": "OPEC+ — przegląd produkcji ropy",
        "de": "OPEC+ — Ölproduktionsüberprüfung",
        "en": "OPEC+ — oil production review",
        "fil": "OPEC+ — review ng produksyon ng langis",
        "es": "OPEP+ — revisión de producción de petróleo",
        "fr": "OPEP+ — revue de la production pétrolière",
        "it": "OPEC+ — revisione produzione petrolio",
    },
    "g7_finance": {
        "pl": "G7 — spotkanie ministrów finansów",
        "de": "G7 — Finanzministertreffen",
        "en": "G7 — finance ministers meeting",
        "fil": "G7 — pagpupulong ng mga finance minister",
        "es": "G7 — reunión de ministros de finanzas",
        "fr": "G7 — réunion des ministres des finances",
        "it": "G7 — riunione dei ministri delle finanze",
    },
    "g7_summit": {
        "pl": "G7 — szczyt przywódców",
        "de": "G7 — Gipfel der Staats- und Regierungschefs",
        "en": "G7 — leaders summit",
        "fil": "G7 — summit ng mga lider",
        "es": "G7 — cumbre de líderes",
        "fr": "G7 — sommet des dirigeants",
        "it": "G7 — vertice dei leader",
    },
    "g20_summit": {
        "pl": "G20 — szczyt przywódców",
        "de": "G20 — Gipfel der Staats- und Regierungschefs",
        "en": "G20 — leaders summit",
        "fil": "G20 — summit ng mga lider",
        "es": "G20 — cumbre de líderes",
        "fr": "G20 — sommet des dirigeants",
        "it": "G20 — vertice dei leader",
    },
    "davos": {
        "pl": "Davos — Światowe Forum Ekonomiczne",
        "de": "Davos — Weltwirtschaftsforum",
        "en": "Davos — World Economic Forum",
        "fil": "Davos — World Economic Forum",
        "es": "Davos — Foro Económico Mundial",
        "fr": "Davos — Forum économique mondial",
        "it": "Davos — World Economic Forum",
    },
    "china_gdp": {
        "pl": "Chiny — PKB Q2 (szac.)",
        "de": "China — BIP Q2 (Schätzung)",
        "en": "China — GDP Q2 (est.)",
        "fil": "Tsina — GDP Q2 (tantiya)",
        "es": "China — PIB Q2 (est.)",
        "fr": "Chine — PIB T2 (est.)",
        "it": "Cina — PIL Q2 (stima)",
    },
}


def normalize_locale(locale: str | None) -> str:
    if not locale:
        return "pl"
    code = locale.lower().split("-")[0]
    if code == "tl":
        return "fil"
    return code if code in SUPPORTED_LOCALES else "pl"


def month_period(locale: str, month: int, year: int) -> str:
    loc = normalize_locale(locale)
    names = MONTHS.get(loc, MONTHS["en"])
    return f"{names[month - 1]} {year}"


def event_title(locale: str | None, kind: str, month: int | None = None, year: int | None = None) -> str:
    loc = normalize_locale(locale)
    tpl_map = TEMPLATES.get(kind, {})
    tpl = tpl_map.get(loc) or tpl_map.get("en") or kind
    if "{period}" in tpl and month and year:
        return tpl.format(period=month_period(loc, month, year))
    return tpl
