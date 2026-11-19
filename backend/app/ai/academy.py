"""Static educational brief for /ai-hacking. No live market figures, no secrets."""

# Prose lines are educational copy, not code.
# pylint: disable=line-too-long

from __future__ import annotations

DISCLAIMER = (
    "Cyclical Academy służy celom edukacyjno-analitycznym i nie stanowi porady inwestycyjnej "
    "ani oferty w rozumieniu przepisów prawa. Inwestowanie wiąże się z ryzykiem utraty kapitału. "
    "Zawsze przeprowadź własną analizę przed podjęciem decyzji finansowych. "
    "Sekcja bezpieczeństwa opisuje wyłącznie obronę. To nie jest instrukcja ataku. "
    "Zgłoszenie scamu składasz sam na oficjalnej stronie — terminal go nie wysyła."
)


def academy_payload() -> dict:
    """Polish education payload: AI research categories and defensive security."""
    return {
        "title": "AI i hacking",
        "eyebrow": "Edukacja · research · obrona",
        "lead": (
            "Dwie rzeczy, które na biurku łatwo pomylić: narzędzia AI skracają research, "
            "a higiena bezpieczeństwa chroni konto i portfel. Poniżej są kategorie, nie obietnice wyniku."
        ),
        "disclaimer": DISCLAIMER,
        "parts": [
            {
                "id": "ai",
                "title": "AI w analizie rynków",
                "lead": (
                    "Modele językowe i narzędzia danych porządkują materiał, który i tak musisz sprawdzić u źródła. "
                    "Nie zastępują modelu ryzyka ani własnej decyzji."
                ),
                "sections": [
                    {
                        "title": "Research i streszczenia",
                        "body": (
                            "Modele językowe nadają się do skracania sprawozdań, transkryptów i wątków newsowych "
                            "oraz do układania pytań, które potem zadajesz danym. Każde twierdzenie o spółce, "
                            "stopie albo regulacji warto zestawić z pierwotnym dokumentem."
                        ),
                    },
                    {
                        "title": "Porządkowanie informacji",
                        "body": (
                            "Klasyfikacja tonu wiadomości, grupowanie tematów i checklisty zdarzeń (wyniki, "
                            "posiedzenia banków, dane makro) pomagają nie zgubić kontekstu. Taki sygnał jest "
                            "pomocniczy: opisuje tekst, nie przyszłą cenę."
                        ),
                    },
                    {
                        "title": "Dane i kod badawczy",
                        "body": (
                            "Asystenci kodu przyspieszają notatniki, zapytania i powtarzalne wykresy. "
                            "Przyspieszenie pracy nie jest przewagą rynkową. Założenia, okno danych i koszty "
                            "transakcji zostają po Twojej stronie."
                        ),
                    },
                    {
                        "title": "Czat na tym biurku",
                        "body": (
                            "Czat idzie na Grok (api.x.ai), gdy właściciel wklei klucz XAI do środowiska i zrestartuje serwer. "
                            "Bez klucza zostaje lokalny skrót z narzędzi, a pasek mówi „Tryb lokalny · narzędzia”. "
                            "OpenAI jest zapasem. llm7 tylko po świadomym włączeniu zewnętrznego czatu. "
                            "Ollama tylko gdy dostawca jest ustawiony na ollama. "
                            "Pełna analiza jest na zalogowanym biurku. Do czatu nie wkleja się kluczy, haseł ani frazy odzyskiwania portfela."
                        ),
                    },
                    {
                        "title": "Granice",
                        "body": (
                            "Modele dopowiadają brakujące fakty, mylą daty i cytują źródła, których nie było. "
                            "Traktuj wynik jak szkic do weryfikacji. Żadne narzędzie z tej listy nie gwarantuje "
                            "zysku ani nie zna Twojej sytuacji."
                        ),
                    },
                ],
            },
            {
                "id": "nauka",
                "title": "Nauka na biurku",
                "lead": "Krótkie ścieżki do stron, które już działają. Każdy link zostaje w terminalu.",
                "sections": [
                    {
                        "title": "Od newsa do decyzji",
                        "body": (
                            "Najpierw wire, potem kalkulator, na końcu agent. Żaden z tych kroków nie wysyła zlecenia "
                            "na giełdę. Broker zostaje papierowy."
                        ),
                    },
                ],
                "links": [
                    {"label": "News", "href": "/news", "note": "Wire z pamięci. Pełne odświeżenie jest ograniczone."},
                    {"label": "Kalkulator", "href": "/kalkulator", "note": "Symulacja bez tokenu biurka."},
                    {"label": "Agent", "href": "/agent", "note": "Czat. Zewnętrzny model jest opt-in."},
                    {"label": "Radar", "href": "/radar", "note": "Mapa edukacyjna, telefon zamaskowany."},
                ],
            },
            {
                "id": "security",
                "title": "Hacking i cyberbezpieczeństwo",
                "lead": (
                    "Etyczny hacking w tym rozdziale znaczy obronę: jak nie oddać konta, poczty i portfela. "
                    "Nie ma tu kroków ataku."
                ),
                "sections": [
                    {
                        "title": "Hasła",
                        "body": (
                            "Każda giełda, poczta i menedżer haseł dostaje inne, długie hasło trzymane w menedżerze. "
                            "Nie zapisuj haseł w notatniku na pulpicie ani w czacie. Osobny adres e-mail tylko do "
                            "konta brokerskiego ogranicza szkody, gdy inna skrzynka wycieknie."
                        ),
                    },
                    {
                        "title": "Drugie składnik logowania",
                        "body": (
                            "Włącz 2FA tam, gdzie trzymasz środki. Aplikacja uwierzytelniająca albo klucz sprzętowy "
                            "jest odporniejszy niż kod SMS, bo SMS da się przekierować. Kody zapasowe trzymaj offline, "
                            "nie na zdjęciu w chmurze."
                        ),
                    },
                    {
                        "title": "Phishing",
                        "body": (
                            "Sprawdzaj domenę znak po znaku, zanim wpiszesz hasło. Nie wchodź w link z niespodziewanej "
                            "wiadomości o „weryfikacji wypłaty”. Giełda, broker i support nie proszą o hasło, kod 2FA "
                            "ani frazę seed. Pilna presja czasu jest typowym znakiem przynęty."
                        ),
                    },
                    {
                        "title": "Konto na giełdzie",
                        "body": (
                            "Włącz białą listę adresów wypłat i kod antyphishingowy w mailach, jeśli giełda to oferuje. "
                            "Nowe urządzenie i nowy adres wypłaty traktuj jako zdarzenie do ręcznego sprawdzenia, "
                            "nie jako coś, co „klikniesz później”."
                        ),
                    },
                    {
                        "title": "Portfel krypto",
                        "body": (
                            "Frazę odzyskiwania zapisujesz offline i nigdy jej nie wpisujesz na stronie, która o nią prosi. "
                            "Portfel sprzętowy oddziela podpis od komputera, na którym czytasz pocztę. "
                            "Przed podpisem transakcji porównaj adres i sieć. Nie podpisuj zgody, której nie umiesz streścić."
                        ),
                    },
                    {
                        "title": "Urządzenie",
                        "body": (
                            "Aktualizuj system i przeglądarkę. Nie instaluj „wsparcia zdalnego” od kogoś, kto pisze "
                            "pierwszy o Twoim portfelu. Osobny profil przeglądarki do giełdy zmniejsza zasięg wtyczki, "
                            "której nie potrzebujesz przy logowaniu."
                        ),
                    },
                    {
                        "title": "Gdzie zgłosić scam",
                        "body": (
                            "Internet Crime Complaint Center (IC3) to oficjalne biuro FBI do zgłoszeń przestępstw w sieci, "
                            "w tym oszustw inwestycyjnych i krypto. IC3 nie współpracuje z kancelariami ani firmami "
                            "„odzyskującymi” środki i nigdy nie prosi o pieniądze ani dane karty. Oszuści podszywają się "
                            "pod IC3 — prawdziwa strona nie napisze pierwsza z żądaniem opłaty. "
                            "W Polsce incydent można zgłosić też do CERT Polska. "
                            "Gdy komuś grozi bezpośrednie niebezpieczeństwo, dzwoń na lokalny numer alarmowy "
                            "(w Polsce 112), zamiast czekać na formularz. "
                            "Przestępstwa wobec dzieci zgłasza się do National Center for Missing & Exploited Children, "
                            "a groźby terrorystyczne na tips.fbi.gov — to inne ścieżki niż skarga inwestora."
                        ),
                    },
                ],
                "links": [
                    {
                        "label": "Zgłoś scam w IC3",
                        "href": "https://www.ic3.gov/",
                        "note": "Oficjalny formularz FBI. Terminal tylko otwiera stronę — zgłoszenie składasz sam.",
                    },
                    {
                        "label": "Zgłoś incydent do CERT Polska",
                        "href": "https://incydent.cert.pl/",
                        "note": "Krajowy zespół reagowania na incydenty komputerowe.",
                    },
                ],
            },
        ],
    }
