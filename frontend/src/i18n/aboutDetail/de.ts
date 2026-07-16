import type { AboutDetailBundle } from './types'

export const aboutDetailDe: AboutDetailBundle = {
  back: '← Zurück zu Über uns',
  learnMore: 'So funktioniert es →',
  notFound: 'Methodologie-Seite nicht gefunden.',
  howItWorks: 'So funktioniert es',
  topics: {
    'cycles-not-headlines': {
      eyebrow: 'Methodologie · Zyklen',
      title: 'Zyklen, nicht Schlagzeilen',
      intro:
        'Signale in Cyclical Academy entstehen nicht aus der Reaktion auf eine einzelne Nachricht. Sie basieren auf wiederkehrenden Marktphasen, die historisch in ähnlichen Zeiträumen zurückkehrten.',
      sections: [
        {
          title: 'Bitcoin-Zyklus (364 / 1064 Tage)',
          body:
            'Nach dem ATH durchläuft BTC oft eine Bärenphase (~364 Tage), dann Akkumulation und eine Bullenwelle (~1064 Tage). Der Scanner verfolgt Tage seit ATH, Phase (bear / accumulation / bull / distribution) und Phasenfortschritt in % — ein Kontextfilter für Krypto und korrelierte Assets.',
        },
        {
          title: 'US-Präsidentschaftszyklus',
          body:
            'Statistisch ist Jahr 3 einer Amtszeit für den S&P 500 am stärksten, Jahr 2 (Midterms) am schwächsten. Die Plattform bildet das aktuelle Amtsjahr und historische Tendenzen ab — nicht als Garantie, sondern als Makrokontext für US-Region-Assets.',
        },
        {
          title: 'RSI-Momentum & regionale Karten',
          body:
            'RSI über 14 Perioden markiert überverkauft (<30) und überkauft (>70) im Zykluskontext. Separate Bewertungen für USA, Europa, Asien, Polen, EM — damit ein Instrumentssignal sein Makroumfeld nicht ignoriert.',
        },
      ],
      inAppTitle: 'Wo Sie es sehen',
      inAppBody: 'Reiter Zyklen (BTC- & Präsidentschaftskarten), globales Dashboard sowie Bewertungen unter Märkte und Chancen.',
    },
    'own-schemas': {
      eyebrow: 'Methodologie · Modelle',
      title: 'Proprietäre Frameworks',
      intro:
        'KAR-Digital-Modelle verbinden Ebenen, die üblicherweise getrennt analysiert werden: Preis, Zyklus, Momentum und regionales Makro in einer Instrumentbewertung.',
      sections: [
        {
          title: 'Bewertungsebenen',
          body:
            'Jedes Instrument durchläuft 52-Wochen-Preiskontext, BTC-Zyklus-Ausrichtung (Krypto) oder Präsidentschaftszyklus (US), RSI-Momentum und regionale Karte. Ergebnis: Kaufen, Verkaufen, Halten oder Beobachten.',
        },
        {
          title: 'Signal-Konfidenz (%)',
          body:
            'Der Prozentsatz am Tag (z. B. 80,5 %) ist die Übereinstimmung der Ebenen — höher bedeutet stärkere Ausrichtung von Zyklus, Preis und Momentum. 80 %+ ist in unserem Framework eine starke Chance; unter 60 % schwächer und mit Vorsicht zu behandeln.',
        },
        {
          title: 'Mehrjährige Kalibrierung',
          body:
            'Modelle sind nicht auf den „Trend der Woche“ optimiert. BTC-Phasenparameter, RSI-Schwellen und regionale Gewichte stammen aus jahrelanger Beobachtung — Paper Trading prüft Ausführungsdisziplin, nicht Chart-Jagd.',
        },
      ],
      inAppTitle: 'Wo Sie es sehen',
      inAppBody: 'Chancen (Karten mit %), Instrumentendetails, Konfidenz-Leitfaden im Dashboard, KI-Agent-Analyse.',
    },
    'long-term-horizon': {
      eyebrow: 'Methodologie · Horizont',
      title: 'Langfristiger Horizont',
      intro:
        'Kapitalaufbau wird in Jahren gemessen, nicht in Minuten. Die Plattform unterstützt Allokation und Geduld — nicht Overtrading.',
      sections: [
        {
          title: 'Ein-/Ausstiegsmarker (WEJ / WYJ)',
          body:
            'Chart-Marker zeigen vorgeschlagene Einstiegs- (WEJ) und Ausstiegszonen (WYJ) aus Zyklusphasen und Momentum — Bildungsrahmen für die eigene Bewertung, keine Auto-Orders.',
        },
        {
          title: 'Druckfreies Paper Trading',
          body:
            'Virtuelles Portfolio mit 1.000.000 PLN, Limit/Stop/TP-Orders und Archiv geschlossener Positionen ermöglichen Übung ohne reales Kapitalrisiko.',
        },
        {
          title: 'Allokationsdenken',
          body:
            '„Beobachten“ oder „Halten“ ist genauso wichtig wie „Kaufen“ — oft ist die beste Entscheidung, auf eine bessere Zyklusphase zu warten. Langer Horizont reduziert emotionale Reaktionen auf Schlagzeilen.',
        },
      ],
      inAppTitle: 'Wo Sie es sehen',
      inAppBody: 'Portfolio (Paper), Instrumentenchart mit WEJ/WYJ-Markern, Chancen gefiltert nach Signalstärke.',
    },
    'terminal-not-tabloid': {
      eyebrow: 'Methodologie · Philosophie',
      title: 'Terminal, kein Boulevard',
      intro:
        'Cyclical Academy ist ein Mission-Control-Analysetool — Charts, Daten, Zyklen und Bewertungen. Kein Clickbait, keine Schnellgewinn-Versprechen.',
      sections: [
        {
          title: 'Charts & Live-Daten',
          body:
            'TradingView, Presets 1M–5Y, RSI, Live-Preise und Kerzenhistorie pro Instrument. Makro-News sind eine separate Kontextebene, nicht der Signal-Kern.',
        },
        {
          title: 'Transparente Methodologie',
          body:
            'Jede Zyklus- und Chancenkarte zeigt die Begründung — woher das Signal kommt. Keine Black Box; Nutzer können Phase und Parameter prüfen.',
        },
        {
          title: 'Bildung, keine Beratung',
          body:
            'Inhalte dienen Lernen und Selbstanalyse. Der KI-Agent beantwortet nur Finanzfragen und schließt mit einem Bildungs-Disclaimer.',
        },
      ],
      inAppTitle: 'Wo Sie es sehen',
      inAppBody: 'Märkte → Instrument, Dashboard, KI-Agent (/agent), Über-uns-Unterseiten.',
    },
    'not-breaking-news': {
      eyebrow: 'Philosophie · Grenzen',
      title: 'Wir sind keine Breaking-News-Plattform',
      intro:
        'Makro-News (Fed, CPI, Geopolitik) sind wichtiger Kontext — generieren aber nicht jede Minute automatisch Kauf-/Verkaufssignale.',
      sections: [
        {
          title: 'Ereignisökonomie vs. Zyklen',
          body:
            'Die meisten Finanzmedien leben von Punkt-Ereignissen. Wir behandeln sie als Kontext (News-Reiter, Makro-Kalender), während der Bewertungskern Phasenwiederholbarkeit und Marktstruktur ist.',
        },
        {
          title: 'RSS & Kalender als Kontext',
          body:
            'News aktualisieren sich alle 2 Minuten; der Kalender zeigt FOMC, CPI, NFP — Push-Alerts fokussieren bedeutsame Makro-Ereignisse, nicht jede Schlagzeile. Handelssignale kommen weiterhin vom zyklischen Scanner.',
        },
      ],
      inAppTitle: 'Wo Sie es sehen',
      inAppBody: 'News-Reiter (Kontext) vs. Chancen / Zyklen (strukturelle Signale).',
    },
    'not-headline-trading': {
      eyebrow: 'Philosophie · Grenzen',
      title: 'Wir handeln nicht nach Schlagzeilen',
      intro:
        'Entscheidungen in unserem Framework folgen Mustern, die wir auf historischen Daten und Paper Trading entwickeln und testen.',
      sections: [
        {
          title: 'Muster vor Impuls',
          body:
            'Schlagzeilen-Reaktionen sind oft spät und emotional. Das zyklische Schema fragt: In welcher Phase sind wir, bestätigt Momentum, unterstützt regionales Makro — bevor Sie auf Kaufen klicken.',
        },
        {
          title: 'Testen auf Paper',
          body:
            'Logikänderungen sollten durch das simulierte Portfolio gehen: Limit, Stop, Take Profit und Archiv realisierten P/L — ohne Live-Konto-Verifikation.',
        },
      ],
      inAppTitle: 'Wo Sie es sehen',
      inAppBody: 'Paper-Portfolio, Handelshistorie pro Instrument, Begründung bei jeder Chance.',
    },
    'not-minute-signals': {
      eyebrow: 'Philosophie · Grenzen',
      title: 'Wir versprechen keine Signale jede Minute',
      intro:
        'Vollscans laufen alle paar Minuten, aber Signalqualität schlägt Quantität. Wir bieten einen ruhigeren Rahmen für langfristige Anleger.',
      sections: [
        {
          title: 'Scan-Frequenz',
          body:
            'Vollanalyse (52W, Signale, Zyklen) — alle 5 Min. im Hintergrund. Preis-Refresh — jede Minute. Kein Scalping-Terminal; Signale beziehen sich auf Phasen von Wochen und Monaten.',
        },
        {
          title: 'Qualität > Quantität',
          body:
            'Chancen listen Instrumente mit höchster Ebenenübereinstimmung. Ein leeres Filterergebnis ist Information — manchmal ist das beste Signal: kein Trade.',
        },
      ],
      inAppTitle: 'Wo Sie es sehen',
      inAppBody: 'Chancen, Scanner-Status im Dashboard, Schaltfläche „Märkte scannen“.',
    },
    'method-map-cycles': {
      eyebrow: 'Methode · Schritt 1',
      title: 'Wir kartieren Zyklen',
      intro:
        'Schritt eins: globale und regionale Zyklusphase verstehen — von BTC bis US-Präsidentschaftsrythmus und Makro-Karten.',
      sections: [
        {
          title: 'Bitcoin als Krypto-Uhr',
          body:
            'Tage seit ATH, Bären-/Bullenphase, verbleibende Tage — auf der Bitcoin-Zyklus-Karte. Beeinflusst Signale für BTC, ETH und Krypto-ETFs.',
        },
        {
          title: 'US-Amtszeit & Regionen',
          body:
            'Präsidentschaftszyklus für US-Assets; regionale Snapshots (EU, Asien, PL, EM) mit Makrobewertung und repräsentativen Instrumenten.',
        },
        {
          title: 'Scanner verbindet alles',
          body:
            'Beim Vollscan erhält jedes überwachte Asset eine Bewertung mit dem passenden Zyklus für Anlageklasse und Region.',
        },
      ],
      inAppTitle: 'Wo Sie es sehen',
      inAppBody: 'Zyklen, Dashboard (BTC + regionale Zusammenfassung), Startseiten-Karten.',
    },
    'method-layers': {
      eyebrow: 'Methode · Schritt 2',
      title: 'Wir kombinieren Ebenen',
      intro:
        'Ein Indikator reicht selten. Wir führen Preis, Momentum, Makro und WEJ/WYJ in eine Bewertung mit Konfidenz-% zusammen.',
      sections: [
        {
          title: 'Preisebene',
          body:
            'Position vs. 52-Wochen-Range, Phase (bear, accumulation, bull, distribution) und struktureller Trend im Chart.',
        },
        {
          title: 'Momentum-Ebene',
          body:
            'RSI 14 — überverkaufte/überkaufte Zonen im Zyklusphasen-Kontext interpretiert, nicht als automatisches Kaufen/Verkaufen.',
        },
        {
          title: 'Scanner-Synthese',
          body:
            'Der Asset Analyzer aggregiert Ebenen zu SignalAction + Konfidenz + Begründung auf Chancen- und Markttabellen.',
        },
      ],
      inAppTitle: 'Wo Sie es sehen',
      inAppBody: 'Chancen, Märkte, Instrumentendetails, KI-Agent → „Vollanalyse“.',
    },
    'method-discipline': {
      eyebrow: 'Methode · Schritt 3',
      title: 'Wir testen Disziplin',
      intro:
        'Paper Trading mit Limit, Stop und Take Profit ist Trainingsgelände — ohne reales Kapital von Anfang an zu riskieren.',
      sections: [
        {
          title: 'Portfolio 1.000.000 PLN',
          body:
            'Start-Cash in PLN, USD/EUR-Umrechnungen, Live-Preise und offener/realisierter P/L. Portfolio-Reset ermöglicht Neustart der Tests.',
        },
        {
          title: 'Erweiterte Orders',
          body:
            'Market, Limit, Stop und TP — einzelne oder alle Orders pro Symbol stornieren. Teilweise Schließung (z. B. 50 %).',
        },
        {
          title: 'Archiv & Lernen',
          body:
            'Geschlossene Positionen mit Datum und P/L zeigen, ob die Ausführung zum zyklischen Signal passte — ohne Broker-Kontodruck.',
        },
      ],
      inAppTitle: 'Wo Sie es sehen',
      inAppBody: 'Portfolio, Handel auf der Instrumentenseite, offene und geschlossene Positionen.',
    },
    'method-years': {
      eyebrow: 'Methode · Schritt 4',
      title: 'Wir denken in Jahren',
      intro:
        'Signale dienen der Kapitalallokation über viele Jahre — BTC- und Präsidentschaftszyklen dauern länger als eine Handelssitzung.',
      sections: [
        {
          title: 'Geduld als Vorteil',
          body:
            'Akkumulation nach Bärenmarkt kann Monate dauern. Ein „Beobachten“-Signal in der Distribution schützt vor späten Blaseneinstiegen.',
        },
        {
          title: 'Rebalancing, nicht Panik',
          body:
            'Globale Bewertung (wie viele Instrumente in Kaufen/Verkaufen) zeigt das Gesamtbild — Risk-on vs. Risk-off — statt auf eine Kerze zu reagieren.',
        },
      ],
      inAppTitle: 'Wo Sie es sehen',
      inAppBody: 'Dashboard (globale Bewertung), Zyklen (Phasenfortschritt %), lange Chart-Presets 1J/5J.',
    },
  },
}
