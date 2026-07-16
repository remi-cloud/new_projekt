import type { AboutDetailBundle } from './types'

export const aboutDetailEn: AboutDetailBundle = {
  back: '← Back to About',
  learnMore: 'How it works →',
  notFound: 'Methodology page not found.',
  howItWorks: 'How it works',
  topics: {
    'cycles-not-headlines': {
      eyebrow: 'Methodology · Cycles',
      title: 'Cycles, not headlines',
      intro:
        'Signals in Cyclical Academy are not built from reacting to a single news item. They rely on repeatable market phases that have historically returned on similar time scales.',
      sections: [
        {
          title: 'Bitcoin cycle (364 / 1064 days)',
          body:
            'After ATH, BTC often enters a bear phase (~364 days), then accumulation and a bull wave (~1064 days). The scanner tracks days since ATH, phase (bear / accumulation / bull / distribution) and phase progress % — a context filter for crypto and correlated assets.',
        },
        {
          title: 'US presidential cycle',
          body:
            'Statistically, year 3 of a term tends to be strongest for the S&P 500, year 2 (midterms) weakest. The platform maps the current term year and historical bias — not as a guarantee, but as macro context for US-region assets.',
        },
        {
          title: 'RSI momentum & regional maps',
          body:
            '14-period RSI flags oversold (<30) and overbought (>70) in cycle context. Separate ratings for USA, Europe, Asia, Poland, EM — so an instrument signal does not ignore its macro environment.',
        },
      ],
      inAppTitle: 'Where to see it',
      inAppBody: 'Cycles tab (BTC & presidential cards), global Dashboard, and ratings on Markets and Opportunities.',
    },
    'own-schemas': {
      eyebrow: 'Methodology · Models',
      title: 'Proprietary frameworks',
      intro:
        'KAR Digital models combine layers usually analysed separately: price, cycle, momentum and regional macro into one instrument rating.',
      sections: [
        {
          title: 'Assessment layers',
          body:
            'Each instrument goes through 52-week price context, BTC cycle alignment (crypto) or presidential cycle (US), RSI momentum and regional map. Output: Buy, Sell, Hold or Watch.',
        },
        {
          title: 'Signal confidence (%)',
          body:
            'The percentage on the tag (e.g. 80.5%) is layer agreement — higher means stronger cycle/price/momentum alignment. 80%+ is a strong opportunity in our framework; below 60% is weaker and needs caution.',
        },
        {
          title: 'Multi-year calibration',
          body:
            'Models are not tuned for “this week’s trend”. BTC phase parameters, RSI thresholds and regional weights come from years of observation — paper trading verifies execution discipline, not chart chasing.',
        },
      ],
      inAppTitle: 'Where to see it',
      inAppBody: 'Opportunities (cards with %), instrument detail, confidence guide on Dashboard, AI Agent analysis.',
    },
    'long-term-horizon': {
      eyebrow: 'Methodology · Horizon',
      title: 'Long-term horizon',
      intro:
        'Capital building is measured in years, not minutes. The platform supports allocation and patience — not overtrading.',
      sections: [
        {
          title: 'Entry / exit markers (WEJ / WYJ)',
          body:
            'Chart markers show suggested entry (WEJ) and exit (WYJ) zones from cycle phases and momentum — educational frames for your own assessment, not auto-orders.',
        },
        {
          title: 'Pressure-free paper trading',
          body:
            'Virtual 1,000,000 PLN portfolio, limit/stop/TP orders and closed-position archive let you practice plans without real capital risk.',
        },
        {
          title: 'Allocation mindset',
          body:
            '“Watch” or “Hold” is as important as “Buy” — often the best move is waiting for a better cycle phase. Long horizon reduces emotional reactions to headlines.',
        },
      ],
      inAppTitle: 'Where to see it',
      inAppBody: 'Portfolio (paper), instrument chart with WEJ/WYJ markers, Opportunities filtered by signal strength.',
    },
    'terminal-not-tabloid': {
      eyebrow: 'Methodology · Philosophy',
      title: 'Terminal, not tabloid',
      intro:
        'Cyclical Academy is a mission-control-style analytics tool — charts, data, cycles and ratings. No clickbait or quick-profit promises.',
      sections: [
        {
          title: 'Charts & live data',
          body:
            'TradingView, 1M–5Y presets, RSI, live prices and candle history per instrument. Macro news is a separate context layer, not the signal core.',
        },
        {
          title: 'Transparent methodology',
          body:
            'Every cycle and opportunity card shows rationale — where the signal came from. No black box; users can verify phase and parameters.',
        },
        {
          title: 'Education, not advice',
          body:
            'Content is for learning and self-analysis. The AI Agent answers finance questions only and ends with an educational disclaimer.',
        },
      ],
      inAppTitle: 'Where to see it',
      inAppBody: 'Markets → instrument, Dashboard, AI Agent (/agent), About subpages.',
    },
    'not-breaking-news': {
      eyebrow: 'Philosophy · Boundaries',
      title: 'We are not a breaking news platform',
      intro:
        'Macro news (Fed, CPI, geopolitics) is important context — but does not auto-generate buy/sell signals every minute.',
      sections: [
        {
          title: 'Event economics vs cycles',
          body:
            'Most financial media lives on point events. We treat them as context (News tab, macro calendar) while the rating core is phase repeatability and market structure.',
        },
        {
          title: 'RSS & calendar as context',
          body:
            'News refreshes every 2 minutes; calendar shows FOMC, CPI, NFP — push alerts focus on meaningful macro events, not every headline. Trade signals still come from the cyclical scanner.',
        },
      ],
      inAppTitle: 'Where to see it',
      inAppBody: 'News tab (context) vs Opportunities / Cycles (structural signals).',
    },
    'not-headline-trading': {
      eyebrow: 'Philosophy · Boundaries',
      title: 'We do not trade on headlines',
      intro:
        'Decisions in our framework come from patterns we built and test on historical data and paper trading.',
      sections: [
        {
          title: 'Pattern before impulse',
          body:
            'Headline reactions are often late and emotional. The cyclical schema asks: what phase are we in, does momentum confirm, does regional macro support — before you click Buy.',
        },
        {
          title: 'Testing on paper',
          body:
            'Logic changes should pass through the simulated portfolio: limit, stop, take profit and closed P/L archive — without live account verification.',
        },
      ],
      inAppTitle: 'Where to see it',
      inAppBody: 'Paper portfolio, per-instrument trade history, rationale on each opportunity.',
    },
    'not-minute-signals': {
      eyebrow: 'Philosophy · Boundaries',
      title: 'We do not promise signals every minute',
      intro:
        'Full scans run every few minutes, but signal quality beats quantity. We provide a calmer framework for long-term investors.',
      sections: [
        {
          title: 'Scan frequency',
          body:
            'Full analysis (52w, signals, cycles) — every 5 min in background. Price refresh — every minute. Not a scalping terminal; signals relate to phases lasting weeks and months.',
        },
        {
          title: 'Quality > quantity',
          body:
            'Opportunities lists instruments with highest layer agreement. An empty filter result is information — sometimes the best signal is no trade.',
        },
      ],
      inAppTitle: 'Where to see it',
      inAppBody: 'Opportunities, scanner status on Dashboard, “Scan markets” button.',
    },
    'method-map-cycles': {
      eyebrow: 'Method · Step 1',
      title: 'We map cycles',
      intro:
        'Step one: understand global and regional cycle phase — from BTC to the US presidential cadence and macro maps.',
      sections: [
        {
          title: 'Bitcoin as crypto clock',
          body:
            'Days since ATH, bear/bull phase, days remaining — on the Bitcoin Cycle card. Biases signals for BTC, ETH and crypto ETFs.',
        },
        {
          title: 'US term & regions',
          body:
            'Presidential cycle for US assets; regional snapshots (EU, Asia, PL, EM) with macro rating and representative instruments.',
        },
        {
          title: 'Scanner combines all',
          body:
            'On full scan, each monitored asset gets a rating using the right cycle for its asset class and region.',
        },
      ],
      inAppTitle: 'Where to see it',
      inAppBody: 'Cycles, Dashboard (BTC + regional summary), home page cards.',
    },
    'method-layers': {
      eyebrow: 'Method · Step 2',
      title: 'We combine layers',
      intro:
        'One indicator is rarely enough. We merge price, momentum, macro and WEJ/WYJ into one rating with confidence %.',
      sections: [
        {
          title: 'Price layer',
          body:
            'Position vs 52-week range, phase (bear, accumulation, bull, distribution) and structural trend on chart.',
        },
        {
          title: 'Momentum layer',
          body:
            'RSI 14 — oversold/overbought zones interpreted in cycle phase context, not as automatic buy/sell.',
        },
        {
          title: 'Scanner synthesis',
          body:
            'Asset analyzer aggregates layers into SignalAction + confidence + rationale on opportunity cards and market tables.',
        },
      ],
      inAppTitle: 'Where to see it',
      inAppBody: 'Opportunities, Markets, instrument detail, AI Agent → “Full analysis”.',
    },
    'method-discipline': {
      eyebrow: 'Method · Step 3',
      title: 'We test discipline',
      intro:
        'Paper trading with limit, stop and take profit is a training ground — without risking real capital upfront.',
      sections: [
        {
          title: '1,000,000 PLN portfolio',
          body:
            'Starting cash in PLN, USD/EUR conversions, live prices and open/realized P/L. Portfolio reset lets you restart tests.',
        },
        {
          title: 'Advanced orders',
          body:
            'Market, limit, stop and TP — cancel single or all orders per symbol. Partial close (e.g. 50%).',
        },
        {
          title: 'Archive & learning',
          body:
            'Closed positions with date and P/L teach whether execution matched the cyclical signal — without broker account pressure.',
        },
      ],
      inAppTitle: 'Where to see it',
      inAppBody: 'Portfolio, trading on instrument page, open and closed positions.',
    },
    'method-years': {
      eyebrow: 'Method · Step 4',
      title: 'We think in years',
      intro:
        'Signals serve capital allocation over many years — BTC and presidential cycles last longer than one trading session.',
      sections: [
        {
          title: 'Patience as edge',
          body:
            'Post-bear accumulation can last months. A “Watch” signal in distribution protects against late bubble entries.',
        },
        {
          title: 'Rebalance, not panic',
          body:
            'Global assessment (how many instruments in Buy/Sell) shows the big picture — risk-on vs risk-off — instead of reacting to one candle.',
        },
      ],
      inAppTitle: 'Where to see it',
      inAppBody: 'Dashboard (global rating), Cycles (phase progress %), long chart presets 1Y/5Y.',
    },
  },
}
