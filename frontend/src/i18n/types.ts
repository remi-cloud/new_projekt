import type { AboutDetailBundle } from './aboutDetail/types'

export type Locale = 'pl' | 'de' | 'en' | 'fil' | 'es' | 'fr' | 'it'

export interface Translations {
  lang: Record<Locale, string>
  nav: Record<'start' | 'panel' | 'markets' | 'opportunities' | 'pearls' | 'cycles' | 'news' | 'alerts' | 'about' | 'portfolio' | 'agent' | 'calculator' | 'live' | 'business' | 'partners' | 'embed' | 'growth' | 'execution', string>
  layout: Record<'scan' | 'scanning' | 'scanDone' | 'scanError' | 'statusScan' | 'statusLive' | 'statusOnline' | 'statusOffline' | 'language' | 'loading' | 'brand' | 'navMain' | 'navMobile' | 'autoRefresh' | 'notFoundTitle' | 'notFoundLead' | 'notFoundHome', string>
  common: Record<'retry' | 'all' | 'world' | 'save' | 'saving' | 'cancel' | 'close' | 'refresh' | 'loading' | 'loadingMarket' | 'seeAll' | 'back' | 'units' | 'pieces' | 'long' | 'short' | 'buy' | 'sell' | 'live' | 'today' | 'tomorrow' | 'inDays', string>
  labels: {
    asset: Record<'crypto' | 'stock' | 'etf' | 'index' | 'bond' | 'commodity' | 'forex', string>
    region: Record<'global' | 'us' | 'eu' | 'asia' | 'em' | 'pl', string>
    signal: Record<'buy' | 'sell' | 'hold' | 'watch', string>
    phase: Record<string, string>
  }
  api: Record<string, string>
  macro: {
    eyebrow: string
    headline: string
    lead: string
    leadHighlight: string
    live: string
    connecting: string
    freshLastHour: string
    refreshEvery: string
    tabNews: string
    tabCalendar: string
    tabs: Record<'all' | 'musk' | 'fed' | 'usa' | 'macro' | 'global', string>
    tabDesc: Record<'all' | 'musk' | 'fed' | 'usa' | 'macro' | 'global', string>
    category: Record<'fed' | 'usa' | 'macro' | 'global' | 'musk', string>
    now: string
    highImpact: string
    refresh: string
    loadingNews: string
    loadingCalendar: string
    noNews: string
    sourcesMeta: string
    disclaimer: string
    timeAgoMin: string
    timeAgoHr: string
    share: {
      button: string
      copied: string
      copyFailed: string
      noUrl: string
      platforms: Record<
        | 'native'
        | 'x'
        | 'facebook'
        | 'linkedin'
        | 'whatsapp'
        | 'telegram'
        | 'reddit'
        | 'bluesky'
        | 'substack'
        | 'email'
        | 'copy',
        string
      >
    }
    cal: {
      weekdays: [string, string, string, string, string, string, string]
      months: [string, string, string, string, string, string, string, string, string, string, string, string]
      today: string
      prevMonth: string
      nextMonth: string
      close: string
      noEvents: string
      eventsTitle: string
      newsTitle: string
      monthMeta: string
      newsMeta: string
      refreshMeta: string
      legendFed: string
      legendUsa: string
      legendMacro: string
      legendGlobal: string
    }
    errors: Record<'fetchNews' | 'fetchCalendar' | 'refresh', string>
  }
  home: Record<string, string>
  investmentShowcase: {
    eyebrow: string
    headline: string
    lead: string
    amountLabel: string
    yearsLabel: string
    strategyLabel: string
    finalValue: string
    profit: string
    roi: string
    vsBuyHold: string
    featured: string
    cta: string
    loading: string
    error: string
    disclaimer: string
  }
  dashboard: Record<string, string>
  cycles: Record<string, string | string[]>
  opportunities: Record<string, string>
  markets: Record<string, string>
  instrument: Record<string, string>
  portfolio: Record<string, string>
  alerts: Record<string, string>
  about: {
    eyebrow: string
    title: string
    principle: string
    principleNote: string
    lead: string
    quote: string
    whoTitle: string
    whoDesc: string
    notTitle: string
    notDesc: string
    methodTitle: string
    methodSteps: string[]
    contactEyebrow: string
    contactTitle: string
    contactBody: string
    chips: string[]
    disclaimer: string
    pillars: { title: string; body: string }[]
    notUs: string[]
  }
  aboutDetail: AboutDetailBundle
  banner: Record<string, string>
  paper: Record<string, string>
  chart: Record<string, string>
  confidence: Record<string, string>
  cyclesCard: Record<string, string>
  table: Record<string, string>
  orders: Record<string, string>
  positions: Record<string, string>
  markers: Record<string, string>
  logo: Record<'tagline', string>
  broker: Record<string, string>
  pearl: Record<string, string>
  execution: Record<string, string>
  agent: {
    eyebrow: string
    title: string
    lead: string
    modeLlm: string
    modeLocal: string
    knowledge: string
    learning: string
    symbol: string
    btnTrend: string
    btnPattern: string
    btnCycles: string
    btnAnalyze: string
    newChat: string
    empty: string
    hintTrend: string
    hintPattern: string
    hintMacro: string
    you: string
    bot: string
    tools: string
    critic: string
    thumbsUp: string
    thumbsDown: string
    thinking: string
    placeholder: string
    send: string
    sending: string
    disclaimer: string
    errorSend: string
    errorAnalyze: string
    quickTrend: string
    quickPattern: string
    quickAnalyze: string
    quickCycles: string
    analyzeOnly: string
  }
  roi: {
    eyebrow: string
    headline: string
    lead: string
    modeForward: string
    modeBacktest: string
    modeForwardDesc: string
    modeBacktestDesc: string
    asset: string
    amount: string
    amountToday: string
    start: string
    horizon: string
    monthly: string
    strategy: string
    strategies: Record<'buy_hold' | 'cycle' | 'dca' | 'cycle_dca', string>
    strategyDesc: Record<'buy_hold' | 'cycle' | 'dca' | 'cycle_dca', string>
    calculate: string
    project: string
    calculating: string
    seeDetails: string
    loading: string
    historyFrom: string
    finalValue: string
    valueInYears: string
    optimistic: string
    pessimistic: string
    roi: string
    cagr: string
    maxDd: string
    years: string
    cycleSource: string
    compareBh: string
    chartEquity: string
    chartBase: string
    chartOpt: string
    chartPes: string
    chartBh: string
    chartPrice: string
    btcAths: string
    btcAthNote: string
    trades: string
    milestones: string
    yearN: string
    nowCycle: string
    nowSentiment: string
    histCagr: string
    histCagrHint: string
    sentimentScore: string
    sentiment: Record<'bullish' | 'constructive' | 'neutral' | 'cautious' | 'bearish', string>
    meta: string
    metaForward: string
    explainWithAgent: string
    errors: Record<'assets' | 'calculate', string>
  }

  growth: {
    newsletterTitle: string
    newsletterLead: string
    newsletterEmail: string
    newsletterCta: string
    newsletterOk: string
    newsletterErr: string
    liveEyebrow: string
    liveHeadline: string
    liveLead: string
    ctaCalc: string
    ctaBiz: string
    ctaLive: string
    ctaEmbed: string
    btcNow: string
    usaNow: string
    topOpps: string
    liveNews: string
    watchlist: string
    watchlistLead: string
    scanWait: string
    bizEyebrow: string
    bizHeadline: string
    bizLead: string
    channelsTitle: string
    channelsHint: string
    partnersLink: string
    contactTitle: string
    contactLead: string
    contactName: string
    contactEmail: string
    contactCompany: string
    contactPackage: string
    contactMessage: string
    contactCta: string
    contactOk: string
    contactErr: string
    partnersEyebrow: string
    partnersHeadline: string
    partnersLead: string
    wlTitle: string
    wlBody: string
    wl1: string
    wl2: string
    wl3: string
    mediaTitle: string
    mediaBody: string
    media1: string
    media2: string
    media3: string
    eduTitle: string
    eduBody: string
    edu1: string
    edu2: string
    edu3: string
    embedEyebrow: string
    embedHeadline: string
    embedLead: string
    embedCode: string
    copyEmbed: string
    copied: string
    apiSandbox: string
    embedJsonDocs: string
    embedDay: string
    embedLiveLink: string
    compliance: string
    homeStripTitle: string
    homeStripLead: string
    errors: Record<'live' | 'packages', string>
  }

  tagTips: {
    meaning: string
    suggestion: string
    clickHint: string
    layerCycle: { body: string; hint: string }
    layerPrice: { body: string; hint: string }
    layerMomentum: { body: string; hint: string }
    layerOther: { body: string; hint: string }
    asset: Record<'crypto' | 'stock' | 'etf' | 'index' | 'bond' | 'commodity' | 'forex', { body: string; hint: string }>
    region: Record<'global' | 'us' | 'eu' | 'asia' | 'em' | 'pl', { body: string; hint: string }>
    phase: Record<
      | 'bear'
      | 'accumulation'
      | 'bull'
      | 'distribution'
      | 'neutral'
      | 'year_1'
      | 'year_2'
      | 'year_3'
      | 'year_4'
      | 'silne_wzrost'
      | 'wzrost'
      | 'silne_spadk'
      | 'spadek'
      | 'neutralne',
      { body: string; hint: string }
    >
    momScore: { body: string; hint: string }
    momPick: { body: string; hint: string }
    confidence: Record<'high' | 'mid' | 'low', { body: string; hint: string }>
  }
}
