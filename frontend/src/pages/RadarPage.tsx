import { Link } from 'react-router-dom'
import {
  RADAR_EDGES,
  RADAR_KIND_COLOR,
  RADAR_NODES,
  RADAR_PUBLISHED,
  RADAR_SOURCE,
} from '../data/radarPublic'

const byId = Object.fromEntries(RADAR_NODES.map((node) => [node.id, node]))

export function RadarPage() {
  return (
    <div className="radar-page institutional-page">
      <header className="page-intro">
        <span className="page-eyebrow">Radar · arch-clean · tylko obrona</span>
        <h2 className="page-headline">Radar oszustw</h2>
        <p className="page-lead">
          Publiczna mapa z lokalnego radaru (C++17 i moduł straż, gałąź arch-clean). Program stoi na
          własnej maszynie z Arch Linuksa i nie działa w przeglądarce. Tutaj widać tylko ostrzeżenie,
          które sam opublikował: identyfikatory podane przez te konta, połączone w siatki. To nie jest
          wyrok. Nie otwieraj ich profili i nie pisz do nich.
        </p>
        <div className="astra-math-links">
          <a className="btn tap-target" href="https://www.ic3.gov/" target="_blank" rel="noopener noreferrer">
            Zgłoś w IC3
          </a>
          <a className="btn btn-ghost tap-target" href="https://incydent.cert.pl/" target="_blank" rel="noopener noreferrer">
            CERT Polska
          </a>
          <a className="btn btn-ghost tap-target" href={RADAR_SOURCE} target="_blank" rel="noopener noreferrer">
            Kod na GitHubie
          </a>
          <Link className="btn btn-ghost tap-target" to="/ai-hacking">
            AI i hacking
          </Link>
        </div>
      </header>

      <section className="radar-map" aria-label="Mapa siatek">
        <svg viewBox="0 0 720 280" role="img">
          <title>Dwie siatki ostrzeżeń S1 i S2</title>
          {RADAR_EDGES.map(([a, b]) => {
            const from = byId[a]
            const to = byId[b]
            return (
              <line
                key={`${a}-${b}`}
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                className="radar-edge"
              />
            )
          })}
          {RADAR_NODES.map((node) => (
            <g key={node.id}>
              <circle cx={node.x} cy={node.y} r="8" fill={RADAR_KIND_COLOR[node.kind] || '#ccc'}>
                <title>
                  {node.net} {node.kind}: {node.label} · ryzyko {node.score}/100
                </title>
              </circle>
              <text x={node.x + 12} y={node.y + 4}>
                {node.label}
              </text>
            </g>
          ))}
        </svg>
        <p className="radar-note">Opublikowano {RADAR_PUBLISHED}. Kolor oznacza rodzaj identyfikatora, nie pewność prawną.</p>
      </section>

      <div className="ai-hack-grid">
        <article className="ai-hack-card">
          <h4>S1 · 100/100</h4>
          <p>
            Automatyczna ocena: podszywanie się, brak weryfikacji, zmiana nazwy, wyprowadzenie na
            Telegram, WhatsApp i Zangi, obietnica zysku, numer telefonu, presja i wcześniejsze
            zgłoszenie. Identyfikatory: konto @E___m2677, nick Elon101020, Telegram XXXXX029ELON.
            Cytaty z tych kont mówią o „bezpośredniej rozmowie z Elonem” i o „100% guaranteed profit”.
          </p>
        </article>
        <article className="ai-hack-card">
          <h4>S2 · 85/100</h4>
          <p>
            Automatyczna ocena: podszywanie, wyprowadzenie na Telegram i nachalna promocja memecoina
            oraz adresu portfela. Identyfikatory: @VitoNakamoto, @GTAmemesSOL, ticker $GTA, Telegram
            GTAbagwork. Adres Solana jest w bazie radaru jako tekst, nie jako link do kupna.
          </p>
        </article>
        <article className="ai-hack-card">
          <h4>Skąd bierze się liczba</h4>
          <p>
            Ocena 0–100 sumuje reguły z kodu (R1–R12): podszywanie, młode lub niezweryfikowane konto,
            zmiana nazwy, wyjście poza platformę, gwarantowany zysk, pump memecoina, numer, portfel,
            dziwny nick, presja i status „już zgłoszony”. Od 85 program opisuje poziom jako wysoki:
            zablokuj i zgłoś. Próg jest heurystyką autora, nie skalą policyjną.
          </p>
        </article>
        <article className="ai-hack-card">
          <h4>Co zostaje na Archu</h4>
          <p>
            Pełny radar w katalogu cpp/ trzyma dowody lokalnie (~/radar-data). Każdy wpis dziennika ma
            czas UTC i skrót SHA-512 spięty z poprzednim wpisem. Moduł straż pilnuje integralności
            własnych plików (HMAC-SHA-512 i podpisy SLH-DSA) i nasłuchujących portów. Globus tylko
            obserwuje połączenia tej maszyny. Program nie skanuje cudzych adresów i niczego nie wysyła.
          </p>
        </article>
      </div>

      <footer className="about-disclaimer">
        <p>
          Ostrzeżenie edukacyjne na podstawie publicznej strony radaru. Identyfikatory zostały podane
          przez te konta; ocena jest automatyczna i nie stanowi ustalenia winy ani porady inwestycyjnej.
          Cyclical Academy nie składa za Ciebie skargi. Zgłoszenie składasz sam w IC3 albo CERT Polska.
          Inwestowanie wiąże się z ryzykiem utraty kapitału.
        </p>
      </footer>
    </div>
  )
}
