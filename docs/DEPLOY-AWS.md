# Deploy online — AWS (prosty plan)

Cel: ta sama zabawka co na Macu, dostępna z internetu 24/7.  
Na start wystarczy **jeden mały VPS** — nie trzeba Kubernetes ani Lambda.

## Rekomendacja na start: AWS Lightsail

Najprostsza droga (cena ~\$3–7/mies.):

1. AWS Console → **Lightsail** → Create instance
2. OS: **Ubuntu 22.04 / 24.04**
3. Plan: **\$5** (1 GB RAM) zwykle wystarczy na start
4. Networking → open port **8080** (lub 80 jeśli z reverse proxy)
5. SSH do maszyny

### Na serwerze (Docker — najłatwiej)

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker "$USER"
# wyloguj / zaloguj się ponownie

git clone https://github.com/remi-cloud/new_projekt.git
cd new_projekt
git checkout cursor/paper-trading-21d6

# opcjonalnie .env z numerem alertów (nie commituj)
# cp .env.example .env

docker compose up --build -d
```

Aplikacja: `http://<IP-LIGHTSAIL>:8080`

Persystencja portfela: volume `portfolio-data` w `docker-compose.yml`.

### Bez Dockera (jak na Macu)

```bash
sudo apt install -y python3 python3-venv python3-pip nodejs npm
git clone https://github.com/remi-cloud/new_projekt.git
cd new_projekt && git checkout cursor/paper-trading-21d6
./scripts/build-www.sh
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# trzymać proces: systemd albo screen/tmux
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Na produkcji lepiej **systemd** + opcjonalnie **Caddy/nginx** na porcie 80/443 z HTTPS.

---

## Alternatywy

| Opcja | Kiedy |
|-------|--------|
| **Lightsail** | Najszybszy start, stała cena |
| **EC2 t3.small / t4g.small** | Więcej kontroli, VPC, Security Groups |
| **Render / Railway / Fly.io** | Jeszcze mniej AWS-owej biurokracji (nie AWS, ale OK na start) |
| **ECS / Fargate** | Później, gdy chcesz kontenery zarządzane |

Na etap „zabawka online” **Lightsail + Docker** wystarczy.

## Checklist przed online

- [ ] `docker compose up --build` działa lokalnie
- [ ] Port otwarty (8080 lub 80/443)
- [ ] Volume na `data/` / `baza_portfela` (żeby nie tracić portfela po restarcie)
- [ ] Brak numeru telefonu / Twilio w git
- [ ] (opcjonalnie) domena + HTTPS (Caddy: auto Let’s Encrypt)

## Co NIE jest jeszcze potrzebne

- Rust rewrite  
- Multi-AZ / load balancer  
- RDS (SQLite na volume jest OK dla jednego użytkownika)

---

Gdy będziesz na Macu i aplikacja działa lokalnie, następny krok to jeden Lightsail + `docker compose up -d`.
