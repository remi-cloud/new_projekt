# Setup pro — Mac Terminal (od folderów do dysku)

Zrób to **w aplikacji Terminal** na Macu. Kroki są po kolei — kopiuj i wklejaj bloki.

---

## Krok 0 — Terminal

`Cmd + Spacja` → wpisz **Terminal** → Enter.

---

## Krok 1 — Foldery na dysku

```bash
mkdir -p ~/Projects
cd ~/Projects
pwd
ls -la
```

Docelowa ścieżka projektu:

```text
~/Projects/new_projekt
```

---

## Krok 2 — Narzędzia systemowe (raz)

Jeśli pojawi się okno „Command Line Tools” — kliknij **Install** i poczekaj.

```bash
xcode-select --install 2>/dev/null || true
```

Sprawdź `git`:

```bash
git --version
```

---

## Krok 3 — Homebrew + Python + Node (raz)

```bash
# Homebrew (jeśli nie masz)
if ! command -v brew >/dev/null; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # Apple Silicon — dodaj brew do PATH:
  echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi

brew install python@3.12 node
python3.12 --version
node -v
npm -v
```

Zamknij Terminal i otwórz na nowo, jeśli `brew` nie działa.

---

## Krok 4 — Pobierz projekt na dysk

```bash
cd ~/Projects
git clone --branch cursor/paper-trading-21d6 https://github.com/remi-cloud/new_projekt.git
cd new_projekt
pwd
ls
```

Albo jednym skryptem (po clone albo jeśli już jesteś w repo):

```bash
cd ~/Projects/new_projekt
chmod +x scripts/*.sh
./scripts/mac-bootstrap.sh
```

`mac-bootstrap.sh` zrobi: foldery, brew (jeśli brak), clone/pull, build frontendu, venv, backup portfela.

---

## Krok 5 — Start aplikacji

```bash
cd ~/Projects/new_projekt
./scripts/mac-start.sh
```

Otwórz: **http://localhost:8080**

Stop: `Ctrl+C` albo `./scripts/mac-stop.sh`

---

## Struktura na dysku

```text
~/Projects/
└── new_projekt/                 ← repo Git (to jest Twój dysk roboczy)
    ├── scripts/
    │   ├── mac-bootstrap.sh     ← pełna instalacja
    │   ├── mac-start.sh         ← codzienny start
    │   └── mac-stop.sh
    ├── backend/
    │   ├── .venv/               ← Python (nie w git)
    │   ├── data/baza_portfela/  ← portfel (nie w git, lokalny)
    │   └── static/              ← zbudowany frontend
    ├── frontend/
    ├── backups/                 ← backup portfela w git
    └── docs/
        ├── MAC-SETUP.md         ← ten plik
        ├── MAC.md
        └── DEPLOY-AWS.md        ← później online
```

---

## Codziennie (jak już masz na dysku)

```bash
cd ~/Projects/new_projekt
git pull
./scripts/mac-start.sh
```

---

## Problemy

| Objaw | Co zrobić |
|-------|-----------|
| `brew: command not found` | Zamknij Terminal, otwórz nowy; na M1/M2: `eval "$(/opt/homebrew/bin/brew shellenv)"` |
| `xcode-select` | Dokończ instalację CLT, potem powtórz |
| Port 8080 zajęty | `./scripts/mac-stop.sh` albo `PORT=8090 ./scripts/mac-start.sh` |
| Brak przycisku Zamknij | `./scripts/build-www.sh` potem restart |
