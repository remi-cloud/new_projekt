import type { AboutDetailBundle } from './types'

export const aboutDetailFr: AboutDetailBundle = {
  back: '← Retour à À propos',
  learnMore: 'Comment ça marche →',
  notFound: 'Page méthodologie introuvable.',
  howItWorks: 'Comment ça marche',
  topics: {
    'cycles-not-headlines': {
      eyebrow: 'Méthodologie · Cycles',
      title: 'Les cycles, pas les titres',
      intro:
        'Les signaux de Cyclical Academy ne naissent pas d’une réaction à une seule actualité. Ils s’appuient sur des phases de marché répétables, historiquement observées à des échelles de temps similaires.',
      sections: [
        {
          title: 'Cycle Bitcoin (364 / 1064 jours)',
          body:
            'Après l’ATH, le BTC entre souvent en phase baissière (~364 jours), puis en accumulation et vague haussière (~1064 jours). Le scanner suit les jours depuis l’ATH, la phase (bear / accumulation / bull / distribution) et le % d’avancement — filtre de contexte pour la crypto et les actifs corrélés.',
        },
        {
          title: 'Cycle présidentiel américain',
          body:
            'Statistiquement, la 3e année de mandat tend à être la plus forte pour le S&P 500, la 2e (midterms) la plus faible. La plateforme cartographie l’année de mandat en cours et les biais historiques — non comme garantie, mais comme contexte macro pour les actifs US.',
        },
        {
          title: 'Momentum RSI et cartes régionales',
          body:
            'Le RSI sur 14 périodes signale survente (<30) et surachat (>70) dans le contexte du cycle. Notations séparées pour USA, Europe, Asie, Pologne, EM — pour que le signal d’un instrument n’ignore pas son environnement macro.',
        },
      ],
      inAppTitle: 'Où le voir',
      inAppBody: 'Onglet Cycles (cartes BTC et présidentielles), Dashboard global, notations sur Marchés et Opportunités.',
    },
    'own-schemas': {
      eyebrow: 'Méthodologie · Modèles',
      title: 'Frameworks propriétaires',
      intro:
        'Les modèles KAR Digital combinent des couches habituellement analysées séparément : prix, cycle, momentum et macro régionale en une notation d’instrument.',
      sections: [
        {
          title: 'Couches d’évaluation',
          body:
            'Chaque instrument passe par le contexte prix 52 semaines, l’alignement cycle BTC (crypto) ou cycle présidentiel (US), le momentum RSI et la carte régionale. Résultat : Acheter, Vendre, Conserver ou Observer.',
        },
        {
          title: 'Confiance du signal (%)',
          body:
            'Le pourcentage sur l’étiquette (ex. 80,5 %) mesure l’accord entre couches — plus il est élevé, plus l’alignement cycle/prix/momentum est fort. 80 %+ est une opportunité forte dans notre cadre ; sous 60 %, prudence.',
        },
        {
          title: 'Calibration pluriannuelle',
          body:
            'Les modèles ne sont pas calibrés sur « la tendance de la semaine ». Paramètres de phase BTC, seuils RSI et pondérations régionales issus d’années d’observation — le paper trading valide la discipline d’exécution, pas la course au graphique.',
        },
      ],
      inAppTitle: 'Où le voir',
      inAppBody: 'Opportunités (cartes avec %), détail instrument, guide de confiance sur le Dashboard, analyse Agent IA.',
    },
    'long-term-horizon': {
      eyebrow: 'Méthodologie · Horizon',
      title: 'Horizon long terme',
      intro:
        'La construction de capital se mesure en années, pas en minutes. La plateforme favorise l’allocation et la patience — pas le sur-trading.',
      sections: [
        {
          title: 'Marqueurs entrée / sortie (WEJ / WYJ)',
          body:
            'Les marqueurs sur le graphique indiquent les zones d’entrée (WEJ) et de sortie (WYJ) issues des phases de cycle et du momentum — cadres pédagogiques pour votre propre jugement, pas des ordres automatiques.',
        },
        {
          title: 'Paper trading sans pression',
          body:
            'Portefeuille virtuel de 1 000 000 PLN, ordres limit/stop/TP et archive des positions clôturées permettent de s’entraîner sans risque de capital réel.',
        },
        {
          title: 'Mentalité d’allocation',
          body:
            '« Observer » ou « Conserver » compte autant qu’« Acheter » — souvent la meilleure décision est d’attendre une meilleure phase de cycle. L’horizon long réduit les réactions émotionnelles aux titres.',
        },
      ],
      inAppTitle: 'Où le voir',
      inAppBody: 'Portefeuille (paper), graphique instrument avec marqueurs WEJ/WYJ, Opportunités filtrées par force du signal.',
    },
    'terminal-not-tabloid': {
      eyebrow: 'Méthodologie · Philosophie',
      title: 'Terminal, pas tabloïd',
      intro:
        'Cyclical Academy est un outil analytique type mission control — graphiques, données, cycles et notations. Pas de clickbait ni de promesses de gains rapides.',
      sections: [
        {
          title: 'Graphiques et données live',
          body:
            'TradingView, presets 1M–5Y, RSI, prix live et historique de bougies par instrument. Les news macro sont une couche de contexte séparée, pas le cœur du signal.',
        },
        {
          title: 'Méthodologie transparente',
          body:
            'Chaque carte cycle ou opportunité affiche la justification — d’où vient le signal. Pas de boîte noire ; l’utilisateur peut vérifier phase et paramètres.',
        },
        {
          title: 'Éducation, pas conseil',
          body:
            'Le contenu vise l’apprentissage et l’auto-analyse. L’Agent IA répond uniquement aux questions financières et conclut par un disclaimer éducatif.',
        },
      ],
      inAppTitle: 'Où le voir',
      inAppBody: 'Marchés → instrument, Dashboard, Agent IA (/agent), sous-pages À propos.',
    },
    'not-breaking-news': {
      eyebrow: 'Philosophie · Limites',
      title: 'Nous ne sommes pas une plateforme de breaking news',
      intro:
        'Les news macro (Fed, CPI, géopolitique) sont un contexte important — mais ne génèrent pas automatiquement des signaux achat/vente chaque minute.',
      sections: [
        {
          title: 'Économie des événements vs cycles',
          body:
            'La plupart des médias financiers vivent d’événements ponctuels. Nous les traitons comme contexte (onglet News, calendrier macro) tandis que le cœur de la notation repose sur la répétabilité des phases et la structure du marché.',
        },
        {
          title: 'RSS et calendrier comme contexte',
          body:
            'Les news se rafraîchissent toutes les 2 minutes ; le calendrier affiche FOMC, CPI, NFP — les alertes push ciblent les événements macro significatifs, pas chaque titre. Les signaux de trading viennent toujours du scanner cyclique.',
        },
      ],
      inAppTitle: 'Où le voir',
      inAppBody: 'Onglet News (contexte) vs Opportunités / Cycles (signaux structurels).',
    },
    'not-headline-trading': {
      eyebrow: 'Philosophie · Limites',
      title: 'Nous ne tradons pas sur les titres',
      intro:
        'Les décisions dans notre cadre suivent des schémas que nous construisons et testons sur données historiques et paper trading.',
      sections: [
        {
          title: 'Schéma avant impulsion',
          body:
            'Les réactions aux titres sont souvent tardives et émotionnelles. Le schéma cyclique demande : quelle phase, le momentum confirme-t-il, la macro régionale soutient-elle — avant de cliquer sur Acheter.',
        },
        {
          title: 'Tests en paper',
          body:
            'Les changements de logique doivent passer par le portefeuille simulé : limit, stop, take profit et archive P/L réalisé — sans vérification sur compte live.',
        },
      ],
      inAppTitle: 'Où le voir',
      inAppBody: 'Portefeuille paper, historique par instrument, justification sur chaque opportunité.',
    },
    'not-minute-signals': {
      eyebrow: 'Philosophie · Limites',
      title: 'Nous ne promettons pas de signaux chaque minute',
      intro:
        'Les scans complets tournent toutes les quelques minutes, mais la qualité prime sur la quantité. Nous offrons un cadre plus serein pour investisseurs long terme.',
      sections: [
        {
          title: 'Fréquence des scans',
          body:
            'Analyse complète (52 sem., signaux, cycles) — toutes les 5 min en arrière-plan. Rafraîchissement des prix — chaque minute. Ce n’est pas un terminal de scalping ; les signaux concernent des phases de semaines et mois.',
        },
        {
          title: 'Qualité > quantité',
          body:
            'Opportunités liste les instruments avec le plus fort accord entre couches. Un filtre vide est une information — parfois le meilleur signal est de ne pas trader.',
        },
      ],
      inAppTitle: 'Où le voir',
      inAppBody: 'Opportunités, statut du scanner sur le Dashboard, bouton « Scanner les marchés ».',
    },
    'method-map-cycles': {
      eyebrow: 'Méthode · Étape 1',
      title: 'Nous cartographions les cycles',
      intro:
        'Première étape : comprendre la phase de cycle globale et régionale — du BTC au rythme présidentiel US et aux cartes macro.',
      sections: [
        {
          title: 'Bitcoin comme horloge crypto',
          body:
            'Jours depuis ATH, phase bear/bull, jours restants — sur la carte Cycle Bitcoin. Biaise les signaux pour BTC, ETH et ETF crypto.',
        },
        {
          title: 'Mandat US et régions',
          body:
            'Cycle présidentiel pour actifs US ; snapshots régionaux (UE, Asie, PL, EM) avec notation macro et instruments représentatifs.',
        },
        {
          title: 'Le scanner combine tout',
          body:
            'Lors du scan complet, chaque actif suivi reçoit une notation avec le cycle adapté à sa classe d’actif et sa région.',
        },
      ],
      inAppTitle: 'Où le voir',
      inAppBody: 'Cycles, Dashboard (résumé BTC + régional), cartes page d’accueil.',
    },
    'method-layers': {
      eyebrow: 'Méthode · Étape 2',
      title: 'Nous combinons les couches',
      intro:
        'Un seul indicateur suffit rarement. Nous fusionnons prix, momentum, macro et WEJ/WYJ en une notation avec confiance %.',
      sections: [
        {
          title: 'Couche prix',
          body:
            'Position vs range 52 semaines, phase (bear, accumulation, bull, distribution) et tendance structurelle sur le graphique.',
        },
        {
          title: 'Couche momentum',
          body:
            'RSI 14 — zones survente/surachat interprétées dans le contexte de phase de cycle, pas comme achat/vente automatique.',
        },
        {
          title: 'Synthèse du scanner',
          body:
            'L’analyseur d’actifs agrège les couches en SignalAction + confiance + justification sur cartes opportunités et tableaux marchés.',
        },
      ],
      inAppTitle: 'Où le voir',
      inAppBody: 'Opportunités, Marchés, détail instrument, Agent IA → « Analyse complète ».',
    },
    'method-discipline': {
      eyebrow: 'Méthode · Étape 3',
      title: 'Nous testons la discipline',
      intro:
        'Le paper trading avec limit, stop et take profit est un terrain d’entraînement — sans risquer le capital réel dès le départ.',
      sections: [
        {
          title: 'Portefeuille 1 000 000 PLN',
          body:
            'Cash initial en PLN, conversions USD/EUR, prix live et P/L ouvert/réalisé. La réinitialisation permet de recommencer les tests.',
        },
        {
          title: 'Ordres avancés',
          body:
            'Market, limit, stop et TP — annulation d’un ordre ou de tous par symbole. Clôture partielle (ex. 50 %).',
        },
        {
          title: 'Archive et apprentissage',
          body:
            'Positions clôturées avec date et P/L montrent si l’exécution correspondait au signal cyclique — sans pression du compte broker.',
        },
      ],
      inAppTitle: 'Où le voir',
      inAppBody: 'Portefeuille, trading sur la page instrument, positions ouvertes et clôturées.',
    },
    'method-years': {
      eyebrow: 'Méthode · Étape 4',
      title: 'Nous pensons en années',
      intro:
        'Les signaux servent l’allocation de capital sur de nombreuses années — les cycles BTC et présidentiels durent plus qu’une session de trading.',
      sections: [
        {
          title: 'La patience comme avantage',
          body:
            'L’accumulation post-bear peut durer des mois. Un signal « Observer » en distribution protège des entrées tardives en bulle.',
        },
        {
          title: 'Rééquilibrer, ne pas paniquer',
          body:
            'L’évaluation globale (combien d’instruments en Acheter/Vendre) montre la vue d’ensemble — risk-on vs risk-off — au lieu de réagir à une bougie.',
        },
      ],
      inAppTitle: 'Où le voir',
      inAppBody: 'Dashboard (notation globale), Cycles (avancement de phase %), presets graphique longs 1A/5A.',
    },
  },
}
