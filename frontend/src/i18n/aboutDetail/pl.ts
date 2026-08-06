import type { AboutDetailBundle } from './types'

export const aboutDetailPl: AboutDetailBundle = {
  back: '← Wróć do O nas',
  learnMore: 'Jak to działa →',
  notFound: 'Nie znaleziono tej strony metodologii.',
  howItWorks: 'Jak to działa',
  topics: {
    'cycles-not-headlines': {
      eyebrow: 'Metodologia · Cykle',
      title: 'Cykle, nie nagłówki',
      intro:
        'Sygnały w Cyclical Academy nie powstają z reakcji na pojedynczy news. Bazują na powtarzalnych fazach rynku, które historycznie wracały w podobnych odstępach czasu.',
      sections: [
        {
          title: 'Cykl Bitcoina (364 / 1064 dni)',
          body:
            'Po szczytach (ATH) BTC często wchodzi w fazę spadkową (~364 dni), potem akumulację i falę wzrostową (~1064 dni). Skaner śledzi dni od ATH, fazę (bear / accumulation / bull / distribution) i procent postępu w fazie — to filtr kontekstu dla całego rynku krypto i aktywów skorelowanych.',
        },
        {
          title: 'Cykl prezydencki USA',
          body:
            'Statystycznie rok 3 kadencji bywa najsilniejszy dla S&P 500, rok 2 (midterms) najsłabszy. Platforma mapuje aktualny rok kadencji i historyczny bias — nie jako gwarancję, lecz jako tło makro dla aktywów z regionem US.',
        },
        {
          title: 'Momentum RSI i mapy regionalne',
          body:
            'RSI 14 okresów wskazuje wyprzedanie (<30) i wykupienie (>70) w kontekście fazy cyklu. Osobno liczymy oceny dla regionów: USA, Europa, Azja, Polska, EM — aby sygnał na instrumencie nie ignorował makro otoczenia.',
        },
      ],
      inAppTitle: 'Gdzie to zobaczyć',
      inAppBody: 'Zakładka Cykle (karty BTC i kadencja), Panel globalny oraz ocena przy każdym instrumencie na Rynkach i w Okazjach.',
    },
    'own-schemas': {
      eyebrow: 'Metodologia · Modele',
      title: 'Własne schematy',
      intro:
        'Autorskie modele KAR Digital łączą warstwy, które zwykle analizuje się osobno: cenę, cykl, momentum i makro regionalne w jedną ocenę instrumentu.',
      sections: [
        {
          title: 'Warstwy oceny',
          body:
            'Każdy instrument przechodzi przez analizę fazy cenowej (52-tygodniowy kontekst), zgodność z cyklem BTC (dla krypto) lub cyklem prezydenckim (dla US), momentum RSI oraz mapę regionalną. Wynik to sygnał: Kupuj, Sprzedaj, Trzymaj lub Obserwuj.',
        },
        {
          title: 'Pewność sygnału (%)',
          body:
            'Procent przy tagu (np. 80,5%) to zgodność warstw — im wyższy, tym silniejsza spójność cyklu, ceny i momentum. 80%+ oznacza silną okazję w naszym frameworku; poniżej 60% to słabszy sygnał wymagający ostrożności.',
        },
        {
          title: 'Kalibracja wieloletnia',
          body:
            'Modele nie są dostrajane pod „modę tygodnia”. Parametry faz BTC, progów RSI i wag regionalnych wynikają z wieloletnich obserwacji — a paper trading służy weryfikacji dyscypliny egzekucji, nie chase’owaniu wykresu.',
        },
      ],
      inAppTitle: 'Gdzie to zobaczyć',
      inAppBody: 'Okazje (karty z % pewności), szczegóły instrumentu, przewodnik pewności na Panelu oraz Agent AI (analiza w kontekście schematów).',
    },
    'long-term-horizon': {
      eyebrow: 'Metodologia · Horyzont',
      title: 'Horyzont długoterminowy',
      intro:
        'Budowa kapitału to proces mierzony latami, nie minutami. Platforma wspiera decyzje alokacyjne i cierpliwość — nie zachęca do overtradingu.',
      sections: [
        {
          title: 'Sygnały WEJ / WYJ',
          body:
            'Markery na wykresie oznaczają proponowane strefy wejścia (WEJ) i wyjścia (WYJ) wynikające z faz cyklu i momentum — nie są to zlecenia automatyczne, lecz ramy edukacyjne do własnej oceny.',
        },
        {
          title: 'Paper trading bez presji',
          body:
            'Wirtualny portfel 1 000 000 PLN, zlecenia limit/stop/TP i archiwum pozycji pozwalają ćwiczyć plan wejścia i wyjścia bez ryzyka realnego kapitału. To laboratorium dyscypliny, nie wyścig na ticki.',
        },
        {
          title: 'Myślenie alokacyjne',
          body:
            'Sygnał „Obserwuj” lub „Trzymaj” jest równie ważny jak „Kupuj” — często najlepsza decyzja to czekanie na lepszą fazę cyklu. Długi horyzont redukuje koszt emocjonalnych reakcji na nagłówki.',
        },
      ],
      inAppTitle: 'Gdzie to zobaczyć',
      inAppBody: 'Portfel (paper), wykres instrumentu z markerami WEJ/WYJ, zakładka Okazje filtrowana po sile sygnału.',
    },
    'terminal-not-tabloid': {
      eyebrow: 'Metodologia · Filozofia',
      title: 'Terminal, nie tabloid',
      intro:
        'Cyclical Academy to narzędzie analityczne w stylu mission control — wykresy, dane, cykle i oceny. Bez clickbaitu i obietnic szybkiego zysku.',
      sections: [
        {
          title: 'Wykresy i dane live',
          body:
            'TradingView, presety 1M–5Y, RSI, ceny live i historia świec — wszystko w jednym miejscu przy każdym instrumencie. News makro jest osobną warstwą kontekstu, nie rdzeniem sygnału.',
        },
        {
          title: 'Transparentna metodologia',
          body:
            'Każda karta cyklu i okazji pokazuje uzasadnienie (rationale) — skąd wziął się sygnał. Nie ukrywamy logiki za „czarną skrzynką”; użytkownik może zweryfikować fazę i parametry.',
        },
        {
          title: 'Edukacja, nie porada',
          body:
            'Treści służą nauce i analizie własnej. Agent AI odpowiada tylko na pytania finansowe i kończy odpowiedzi disclaimerem edukacyjnym — zgodnie z regulacyjnym charakterem platformy.',
        },
      ],
      inAppTitle: 'Gdzie to zobaczyć',
      inAppBody: 'Rynki → instrument, Panel, Agent AI (/agent), sekcja O nas (te podstrony).',
    },
    'not-breaking-news': {
      eyebrow: 'Filozofia · Granice',
      title: 'Nie jesteśmy platformą „breaking news”',
      intro:
        'Newsy makro (Fed, CPI, Trump, geopolityka) są ważnym tłem — ale nie generują u nas automatycznych sygnałów kupna/sprzedaży co minutę.',
      sections: [
        {
          title: 'Ekonomia wydarzeń vs cykle',
          body:
            'Większość mediów finansowych żyje od wydarzeń punktowych. My traktujemy je jako kontekst (zakładka News, kalendarz makro), podczas gdy rdzeń oceny to fazy i powtarzalność struktury rynku.',
        },
        {
          title: 'RSS i kalendarz jako kontekst',
          body:
            'Strumień newsów odświeża się co 2 minuty, kalendarz pokazuje FOMC, CPI, NFP — ale alert push dotyczy istotnych wydarzeń makro, nie każdego nagłówka. Sygnał handlowy nadal pochodzi ze skanera cyklicznego.',
        },
      ],
      inAppTitle: 'Gdzie to zobaczyć',
      inAppBody: 'Zakładka News (kontekst) vs Okazje / Cykle (sygnały strukturalne).',
    },
    'not-headline-trading': {
      eyebrow: 'Filozofia · Granice',
      title: 'Nie handlujemy pod wpływem nagłówków',
      intro:
        'Decyzje w naszym frameworku wynikają ze schematów, które sami zbudowaliśmy i testujemy na danych historycznych oraz paper tradingu.',
      sections: [
        {
          title: 'Schemat przed impulsem',
          body:
            'Reakcja na nagłówek często jest spóźniona i emocjonalna. Schemat cykliczny mówi: w jakiej fazie jesteśmy, czy momentum potwierdza, czy makro regionalne wspiera — zanim klikniesz „Kupuj”.',
        },
        {
          title: 'Testowanie na paper',
          body:
            'Każda zmiana w logice sygnałów powinna przejść przez portfel symulacyjny: limit, stop, take profit i archiwum zamkniętych pozycji z P/L — bez weryfikacji na koncie live.',
        },
      ],
      inAppTitle: 'Gdzie to zobaczyć',
      inAppBody: 'Portfel paper, historia transakcji per instrument, rationale przy każdej okazji.',
    },
    'not-minute-signals': {
      eyebrow: 'Filozofia · Granice',
      title: 'Nie obiecujemy sygnałów co minutę',
      intro:
        'Skaner pełny uruchamia się co kilka minut, ale jakość sygnału ważniejsza niż ich liczba. Dajemy ramę do spokojniejszego myślenia długoterminowego inwestora.',
      sections: [
        {
          title: 'Częstotliwość skanów',
          body:
            'Pełna analiza (52 tyg., sygnały, cykle) — co 5 min w tle. Odświeżenie cen — co minutę. To nie jest scalping terminal; sygnały dotyczą faz trwających tygodniami i miesiącami.',
        },
        {
          title: 'Jakość > ilość',
          body:
            'Lista Okazji filtruje instrumenty z najwyższą zgodnością warstw. Pusty wynik po filtrze to informacja — czasem najlepszy sygnał to brak transakcji.',
        },
      ],
      inAppTitle: 'Gdzie to zobaczyć',
      inAppBody: 'Okazje, status skanera na Panelu, przycisk „Skanuj rynki”.',
    },
    'method-map-cycles': {
      eyebrow: 'Metoda · Krok 1',
      title: 'Mapujemy cykle',
      intro:
        'Pierwszy krok to zorientowanie się, w jakiej fazie globalnego i regionalnego cyklu znajduje się rynek — od BTC po kadencję prezydencką i mapy makro.',
      sections: [
        {
          title: 'Bitcoin jako zegar krypto',
          body:
            'Dni od ATH, faza bear/bull, pozostałe dni w fazie — wyświetlane na karcie Cykl Bitcoina. Wpływa na bias sygnałów dla BTC, ETH i krypto ETF.',
        },
        {
          title: 'Kadencja USA i regiony',
          body:
            'Cykl prezydencki dla aktywów US; osobne snapshoty regionalne (EU, Azja, PL, EM) z oceną makro i listą reprezentatywnych instrumentów.',
        },
        {
          title: 'Skaner łączy wszystko',
          body:
            'Przy pełnym skanie każdy z ~dziesiątek monitorowanych aktywów dostaje ocenę z uwzględnieniem właściwego cyklu dla klasy aktywa i regionu.',
        },
      ],
      inAppTitle: 'Gdzie to zobaczyć',
      inAppBody: 'Cykle, Panel (podsumowanie BTC + regionalne), karty na stronie głównej.',
    },
    'method-layers': {
      eyebrow: 'Metoda · Krok 2',
      title: 'Łączymy warstwy',
      intro:
        'Pojedynczy wskaźnik rzadko wystarcza. Łączymy cenę, momentum, makro i sygnały WEJ/WYJ w jedną ocenę z procentem pewności.',
      sections: [
        {
          title: 'Warstwa cenowa',
          body:
            'Pozycja względem zakresu 52-tygodniowego, faza (spadkowa, akumulacja, wzrostowa, dystrybucja) i trend strukturalny na wykresie.',
        },
        {
          title: 'Warstwa momentum',
          body:
            'RSI 14 — strefy wyprzedania i wykupienia interpretowane w kontekście fazy cyklu, nie jako automatyczny buy/sell.',
        },
        {
          title: 'Synteza w skanerze',
          body:
            'Asset analyzer agreguje warstwy w SignalAction + confidence + rationale widoczne na karcie okazji i w tabeli rynków.',
        },
      ],
      inAppTitle: 'Gdzie to zobaczyć',
      inAppBody: 'Okazje, Rynki, szczegóły instrumentu, Agent AI → „Pełna analiza”.',
    },
    'method-discipline': {
      eyebrow: 'Metoda · Krok 3',
      title: 'Testujemy dyscyplinę',
      intro:
        'Paper trading z limitem, stopem i take profit to poligon do ćwiczenia planu — bez ryzyka utraty realnego kapitału na starcie.',
      sections: [
        {
          title: 'Portfel 1 000 000 PLN',
          body:
            'Startowy cash w PLN, przeliczenia USD/EUR, live ceny i P/L otwarty/zrealizowany. Reset portfela pozwala zacząć test od nowa.',
        },
        {
          title: 'Zlecenia zaawansowane',
          body:
            'Market, limit, stop i TP — anulowanie pojedynczych zleceń lub wszystkich na symbol. Zamknięcie pozycji częściowe (np. 50%).',
        },
        {
          title: 'Archiwum i nauka',
          body:
            'Zamknięte pozycje z datą i P/L uczą, czy dyscyplina egzekucji była zgodna z sygnałem cyklicznym — bez presji wyniku na koncie brokerskim.',
        },
      ],
      inAppTitle: 'Gdzie to zobaczyć',
      inAppBody: 'Portfel, handel na stronie instrumentu, otwarte i zamknięte pozycje.',
    },
    'method-years': {
      eyebrow: 'Metoda · Krok 4',
      title: 'Myślimy w latach',
      intro:
        'Sygnały służą alokacji kapitału w horyzoncie wielu lat — cykle BTC i kadencja prezydencka trwają dłużej niż jedna sesja giełdowa.',
      sections: [
        {
          title: 'Cierpliwość jako edge',
          body:
            'Faza akumulacji po bear market może trwać miesiące. Sygnał „Obserwuj” w dystrybucji chroni przed późnym wejściem w bańkę.',
        },
        {
          title: 'Rebalans, nie panic',
          body:
            'Ocena globalna (ile instrumentów w Kupuj/Sprzedaj) pomaga widzieć szeroki obraz — czy rynek jest w fazie ryzyka on czy off, zamiast reagować na pojedynczą świecę.',
        },
      ],
      inAppTitle: 'Gdzie to zobaczyć',
      inAppBody: 'Panel (ocena globalna), Cykle (postęp fazy w %), długie presety wykresu 1Y/5Y.',
    },
  },
}
