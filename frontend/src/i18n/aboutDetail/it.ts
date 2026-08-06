import type { AboutDetailBundle } from './types'

export const aboutDetailIt: AboutDetailBundle = {
  back: '← Torna a Chi siamo',
  learnMore: 'Come funziona →',
  notFound: 'Pagina metodologia non trovata.',
  howItWorks: 'Come funziona',
  topics: {
    'cycles-not-headlines': {
      eyebrow: 'Metodologia · Cicli',
      title: 'Cicli, non titoli',
      intro:
        'I segnali in Cyclical Academy non nascono dalla reazione a una singola notizia. Si basano su fasi di mercato ripetibili, storicamente osservate su scale temporali simili.',
      sections: [
        {
          title: 'Ciclo Bitcoin (364 / 1064 giorni)',
          body:
            'Dopo l’ATH, BTC entra spesso in fase ribassista (~364 giorni), poi accumulazione e onda rialzista (~1064 giorni). Lo scanner traccia giorni dall’ATH, fase (bear / accumulation / bull / distribution) e avanzamento fase % — filtro di contesto per crypto e asset correlati.',
        },
        {
          title: 'Ciclo presidenziale USA',
          body:
            'Statisticamente, il 3° anno di mandato tende a essere il più forte per l’S&P 500, il 2° (midterms) il più debole. La piattaforma mappa l’anno di mandato corrente e i bias storici — non come garanzia, ma come contesto macro per asset US.',
        },
        {
          title: 'Momentum RSI e mappe regionali',
          body:
            'RSI a 14 periodi segnala ipervenduto (<30) e ipercomprato (>70) nel contesto del ciclo. Valutazioni separate per USA, Europa, Asia, Polonia, EM — così il segnale di uno strumento non ignora il macro ambiente.',
        },
      ],
      inAppTitle: 'Dove vederlo',
      inAppBody: 'Scheda Cicli (card BTC e presidenziale), Dashboard globale, valutazioni su Mercati e Opportunità.',
    },
    'own-schemas': {
      eyebrow: 'Metodologia · Modelli',
      title: 'Framework proprietari',
      intro:
        'I modelli KAR Digital combinano layer di solito analizzati separatamente: prezzo, ciclo, momentum e macro regionale in un’unica valutazione dello strumento.',
      sections: [
        {
          title: 'Layer di valutazione',
          body:
            'Ogni strumento passa per contesto prezzo 52 settimane, allineamento ciclo BTC (crypto) o ciclo presidenziale (US), momentum RSI e mappa regionale. Output: Compra, Vendi, Mantieni o Osserva.',
        },
        {
          title: 'Confidenza del segnale (%)',
          body:
            'La percentuale sul tag (es. 80,5 %) è l’accordo tra layer — più alta significa maggiore allineamento ciclo/prezzo/momentum. 80 %+ è opportunità forte nel nostro framework; sotto 60 % richiede cautela.',
        },
        {
          title: 'Calibrazione pluriennale',
          body:
            'I modelli non sono tarati sul «trend della settimana». Parametri fase BTC, soglie RSI e pesi regionali derivano da anni di osservazione — il paper trading verifica la disciplina di esecuzione, non l’inseguimento del grafico.',
        },
      ],
      inAppTitle: 'Dove vederlo',
      inAppBody: 'Opportunità (card con %), dettaglio strumento, guida confidenza su Dashboard, analisi Agente IA.',
    },
    'long-term-horizon': {
      eyebrow: 'Metodologia · Orizzonte',
      title: 'Orizzonte a lungo termine',
      intro:
        'La costruzione del capitale si misura in anni, non in minuti. La piattaforma supporta allocazione e pazienza — non overtrading.',
      sections: [
        {
          title: 'Marker entrata / uscita (WEJ / WYJ)',
          body:
            'I marker sul grafico mostrano zone suggerite di entrata (WEJ) e uscita (WYJ) da fasi di ciclo e momentum — cornici educative per la propria valutazione, non ordini automatici.',
        },
        {
          title: 'Paper trading senza pressione',
          body:
            'Portafoglio virtuale da 1.000.000 PLN, ordini limit/stop/TP e archivio posizioni chiuse permettono di esercitarsi senza rischio di capitale reale.',
        },
        {
          title: 'Mentalità di allocazione',
          body:
            '«Osserva» o «Mantieni» è importante quanto «Compra» — spesso la mossa migliore è attendere una fase di ciclo migliore. L’orizzonte lungo riduce reazioni emotive ai titoli.',
        },
      ],
      inAppTitle: 'Dove vederlo',
      inAppBody: 'Portafoglio (paper), grafico strumento con marker WEJ/WYJ, Opportunità filtrate per forza del segnale.',
    },
    'terminal-not-tabloid': {
      eyebrow: 'Metodologia · Filosofia',
      title: 'Terminal, non tabloid',
      intro:
        'Cyclical Academy è uno strumento analitico stile mission control — grafici, dati, cicli e valutazioni. Niente clickbait o promesse di guadagni rapidi.',
      sections: [
        {
          title: 'Grafici e dati live',
          body:
            'TradingView, preset 1M–5Y, RSI, prezzi live e storico candele per strumento. Le news macro sono un layer di contesto separato, non il nucleo del segnale.',
        },
        {
          title: 'Metodologia trasparente',
          body:
            'Ogni card ciclo o opportunità mostra la rationale — da dove proviene il segnale. Niente black box; l’utente può verificare fase e parametri.',
        },
        {
          title: 'Educazione, non consulenza',
          body:
            'I contenuti servono apprendimento e auto-analisi. L’Agente IA risponde solo a domande finanziarie e chiude con disclaimer educativo.',
        },
      ],
      inAppTitle: 'Dove vederlo',
      inAppBody: 'Mercati → strumento, Dashboard, Agente IA (/agent), sottopagine Chi siamo.',
    },
    'not-breaking-news': {
      eyebrow: 'Filosofia · Confini',
      title: 'Non siamo una piattaforma di breaking news',
      intro:
        'Le news macro (Fed, CPI, geopolitica) sono contesto importante — ma non generano segnali buy/sell automatici ogni minuto.',
      sections: [
        {
          title: 'Economia degli eventi vs cicli',
          body:
            'La maggior parte dei media finanziari vive di eventi puntuali. Li trattiamo come contesto (scheda News, calendario macro) mentre il nucleo della valutazione è la ripetibilità delle fasi e la struttura di mercato.',
        },
        {
          title: 'RSS e calendario come contesto',
          body:
            'Le news si aggiornano ogni 2 minuti; il calendario mostra FOMC, CPI, NFP — gli alert push si concentrano su eventi macro significativi, non ogni titolo. I segnali di trading provengono ancora dallo scanner ciclico.',
        },
      ],
      inAppTitle: 'Dove vederlo',
      inAppBody: 'Scheda News (contesto) vs Opportunità / Cicli (segnali strutturali).',
    },
    'not-headline-trading': {
      eyebrow: 'Filosofia · Confini',
      title: 'Non operiamo sui titoli',
      intro:
        'Le decisioni nel nostro framework seguono pattern che costruiamo e testiamo su dati storici e paper trading.',
      sections: [
        {
          title: 'Pattern prima dell’impulso',
          body:
            'Le reazioni ai titoli sono spesso tardive ed emotive. Lo schema ciclico chiede: in quale fase siamo, il momentum conferma, il macro regionale supporta — prima di cliccare Compra.',
        },
        {
          title: 'Test in paper',
          body:
            'I cambi di logica devono passare dal portafoglio simulato: limit, stop, take profit e archivio P/L realizzato — senza verifica su conto live.',
        },
      ],
      inAppTitle: 'Dove vederlo',
      inAppBody: 'Portafoglio paper, storico per strumento, rationale su ogni opportunità.',
    },
    'not-minute-signals': {
      eyebrow: 'Filosofia · Confini',
      title: 'Non promettiamo segnali ogni minuto',
      intro:
        'Scan completi ogni pochi minuti, ma la qualità del segnale batte la quantità. Offriamo un framework più calmo per investitori a lungo termine.',
      sections: [
        {
          title: 'Frequenza degli scan',
          body:
            'Analisi completa (52 sett., segnali, cicli) — ogni 5 min in background. Refresh prezzi — ogni minuto. Non è un terminal da scalping; i segnali riguardano fasi di settimane e mesi.',
        },
        {
          title: 'Qualità > quantità',
          body:
            'Opportunità elenca strumenti con maggiore accordo tra layer. Un filtro vuoto è informazione — a volte il miglior segnale è non operare.',
        },
      ],
      inAppTitle: 'Dove vederlo',
      inAppBody: 'Opportunità, stato scanner su Dashboard, pulsante «Scansiona mercati».',
    },
    'method-map-cycles': {
      eyebrow: 'Metodo · Passo 1',
      title: 'Mappiamo i cicli',
      intro:
        'Primo passo: capire la fase di ciclo globale e regionale — da BTC al ritmo presidenziale US e mappe macro.',
      sections: [
        {
          title: 'Bitcoin come orologio crypto',
          body:
            'Giorni dall’ATH, fase bear/bull, giorni rimanenti — sulla card Ciclo Bitcoin. Influenza segnali per BTC, ETH e ETF crypto.',
        },
        {
          title: 'Mandato US e regioni',
          body:
            'Ciclo presidenziale per asset US; snapshot regionali (UE, Asia, PL, EM) con valutazione macro e strumenti rappresentativi.',
        },
        {
          title: 'Lo scanner combina tutto',
          body:
            'Allo scan completo, ogni asset monitorato riceve valutazione con il ciclo adatto a classe di asset e regione.',
        },
      ],
      inAppTitle: 'Dove vederlo',
      inAppBody: 'Cicli, Dashboard (riepilogo BTC + regionale), card homepage.',
    },
    'method-layers': {
      eyebrow: 'Metodo · Passo 2',
      title: 'Combiniamo i layer',
      intro:
        'Un indicatore raramente basta. Uniamo prezzo, momentum, macro e WEJ/WYJ in una valutazione con confidenza %.',
      sections: [
        {
          title: 'Layer prezzo',
          body:
            'Posizione vs range 52 settimane, fase (bear, accumulation, bull, distribution) e trend strutturale sul grafico.',
        },
        {
          title: 'Layer momentum',
          body:
            'RSI 14 — zone ipervenduto/ipercomprato interpretate nel contesto di fase di ciclo, non come buy/sell automatico.',
        },
        {
          title: 'Sintesi dello scanner',
          body:
            'L’asset analyzer aggrega i layer in SignalAction + confidenza + rationale su card opportunità e tabelle mercati.',
        },
      ],
      inAppTitle: 'Dove vederlo',
      inAppBody: 'Opportunità, Mercati, dettaglio strumento, Agente IA → «Analisi completa».',
    },
    'method-discipline': {
      eyebrow: 'Metodo · Passo 3',
      title: 'Testiamo la disciplina',
      intro:
        'Paper trading con limit, stop e take profit è campo di addestramento — senza rischiare capitale reale all’inizio.',
      sections: [
        {
          title: 'Portafoglio 1.000.000 PLN',
          body:
            'Cash iniziale in PLN, conversioni USD/EUR, prezzi live e P/L aperto/realizzato. Reset portafoglio permette di ripartire con i test.',
        },
        {
          title: 'Ordini avanzati',
          body:
            'Market, limit, stop e TP — cancellazione singola o di tutti gli ordini per simbolo. Chiusura parziale (es. 50 %).',
        },
        {
          title: 'Archivio e apprendimento',
          body:
            'Posizioni chiuse con data e P/L insegnano se l’esecuzione corrispondeva al segnale ciclico — senza pressione del conto broker.',
        },
      ],
      inAppTitle: 'Dove vederlo',
      inAppBody: 'Portafoglio, trading su pagina strumento, posizioni aperte e chiuse.',
    },
    'method-years': {
      eyebrow: 'Metodo · Passo 4',
      title: 'Pensiamo in anni',
      intro:
        'I segnali servono l’allocazione del capitale su molti anni — i cicli BTC e presidenziali durano più di una sessione di trading.',
      sections: [
        {
          title: 'La pazienza come vantaggio',
          body:
            'L’accumulazione post-bear può durare mesi. Un segnale «Osserva» in distribuzione protegge da ingressi tardivi in bolla.',
        },
        {
          title: 'Ribilanciare, non panico',
          body:
            'La valutazione globale (quanti strumenti in Compra/Vendi) mostra il quadro generale — risk-on vs risk-off — invece di reagire a una candela.',
        },
      ],
      inAppTitle: 'Dove vederlo',
      inAppBody: 'Dashboard (valutazione globale), Cicli (avanzamento fase %), preset grafico lunghi 1A/5A.',
    },
  },
}
