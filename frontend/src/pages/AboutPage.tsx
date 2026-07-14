import { KarDigitalLogo } from '../components/KarDigitalLogo'

const PILLARS = [
  {
    title: 'Cykle, nie nagłówki',
    body:
      'Nasze sygnały wynikają z powtarzalnych faz rynku — cykl Bitcoina, rytm kadencji prezydenckiej, momentum RSI i własne mapy regionalne. Nie reagujemy na każdy tweet ani raport makro.',
  },
  {
    title: 'Własne schematy',
    body:
      'Opracowaliśmy autorskie modele łączenia cykli cenowych, makro regionalnego i momentum. To nasz wewnętrzny język rynku — kalibrowany pod perspektywę wieloletnią, nie pod chwilową modę inwestycyjną.',
  },
  {
    title: 'Horyzont długoterminowy',
    body:
      'Projektujemy decyzje pod budowę kapitału w czasie. Paper trading, sygnały WEJ/WYJ i portfel symulacyjny służą ćwiczeniu dyscypliny — nie zachęcamy do gonienia każdego ruchu wykresu.',
  },
  {
    title: 'Terminal, nie tabloid',
    body:
      'Cyclical Trader to narzędzie analityczne: wykresy, cykle, ocena instrumentów i wirtualne konto. Bez szumu newsowego, bez obietnic szybkiego zysku — z pełną transparentnością metodologii.',
  },
] as const

const NOT_US = [
  'Nie jesteśmy platformą „breaking news” ani kalendarzem wydarzeń makro.',
  'Nie handlujemy pod wpływem nagłówków — handlujemy według schematów, które sami zbudowaliśmy i testujemy.',
  'Nie obiecujemy sygnałów co minutę. Dajemy ramę, w której długoterminowy inwestor może myśleć spokojniej.',
] as const

export function AboutPage() {
  return (
    <div className="about-page institutional-page">
      <header className="page-intro about-hero">
        <div className="about-hero-brand">
          <KarDigitalLogo size={72} variant="hero" />
        </div>
        <span className="page-eyebrow">Long-Term Investment Corp · KAR Digital</span>
        <h2 className="page-headline">O nas</h2>
        <p className="about-principle">
          Nasza zasada: skoro nie da się walczyć z falą rynku —{' '}
          <strong>trzeba nią się stać</strong>.
        </p>
        <p className="about-principle-note">
          Autorskie sformułowanie KAR Digital · w duchu surfera na trendzie, nie wojownika z falą
        </p>
        <p className="page-lead about-lead">
          Jesteśmy zespołem analityków i inżynierów rynku, którzy wierzą, że kapitał buduje się
          przez <strong>zrozumienie rytmu</strong>, a nie przez reakcję na każdy impuls informacyjny.
          Cyclical Trader to nasz autorski terminal — odzwierciedlenie wieloletniej pracy nad
          schematami finansowymi, które wykraczają poza typową ekonomię wydarzeń.
        </p>
      </header>

      <section className="about-manifesto">
        <blockquote className="about-quote">
          „Rynek ma pamięć w fazach, nie w nagłówkach. Nie walczymy z cyklem — uczymy się nim poruszać,
          tak jak surfer nie tłumi fali, tylko jedzie na jej energii.”
        </blockquote>
      </section>

      <section className="about-section">
        <div className="about-section-head">
          <h3 className="about-section-title">Kim jesteśmy</h3>
          <p className="about-section-desc">
            Long-term investment corp z własnymi, opracowanymi schematami rynku finansowego.
            Łączymy badania cykliczne z nowoczesnym terminalem — aby decyzje opierały się na
            strukturze, nie na hałasie.
          </p>
        </div>
        <div className="about-pillars">
          {PILLARS.map((p) => (
            <article key={p.title} className="about-pillar">
              <h4>{p.title}</h4>
              <p>{p.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="about-section about-contrast">
        <div className="about-section-head">
          <h3 className="about-section-title">Czym nie jesteśmy</h3>
          <p className="about-section-desc">
            Wiele platform opiera się na ekonomii wydarzeń: CPI, Fed, wybory, konflikty. To ważne
            tło — ale nie nasz rdzeń. My idziemy głębiej: w powtarzalność faz, w cykle i w
            własne modele oceny.
          </p>
        </div>
        <ul className="about-not-list">
          {NOT_US.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </section>

      <section className="about-section about-method">
        <div className="about-section-head">
          <h3 className="about-section-title">Nasza metoda w skrócie</h3>
        </div>
        <ol className="about-method-steps">
          <li>
            <strong>Mapujemy cykle</strong> — od Bitcoina po kadencję prezydencką USA i makro
            regionalne (Europa, Azja, Polska, EM).
          </li>
          <li>
            <strong>Łączymy warstwy</strong> — cena, momentum (RSI), makro i sygnały WEJ/WYJ w
            jednej ocenie instrumentu.
          </li>
          <li>
            <strong>Testujemy dyscyplinę</strong> — paper trading z limitem, stopem i portfelem
            1&nbsp;000&nbsp;000 PLN, bez ryzyka realnego kapitału na start.
          </li>
          <li>
            <strong>Myślimy w latach</strong> — sygnały służą alokacji i cierpliwości, nie
            codziennemu overtradingowi.
          </li>
        </ol>
      </section>

      <section className="about-contact-teaser">
        <div className="about-contact-inner">
          <span className="page-eyebrow">Kontakt · wkrótce</span>
          <h3 className="about-contact-title">Porozmawiajmy o strategii</h3>
          <p>
            Pracujemy nad kanałem kontaktu — mail, bot asystenta i formularz dla partnerów
            instytucjonalnych. Jeśli interesuje Cię współpraca lub dostęp do metodologii, wróć tu
            wkrótce lub obserwuj rozwój platformy.
          </p>
          <div className="about-contact-chips">
            <span className="about-chip about-chip-soon">E-mail</span>
            <span className="about-chip about-chip-soon">Bot AI</span>
            <span className="about-chip about-chip-soon">Partnerstwa</span>
          </div>
        </div>
      </section>

      <footer className="about-disclaimer">
        <p>
          Cyclical Trader służy celom edukacyjno-analitycznym i nie stanowi porady inwestycyjnej
          ani oferty w rozumieniu przepisów prawa. Inwestowanie wiąże się z ryzykiem utraty
          kapitału. Zawsze przeprowadź własną analizę przed podjęciem decyzji finansowych.
        </p>
      </footer>
    </div>
  )
}
