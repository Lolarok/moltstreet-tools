# MoltStreet Tools

Crypto intelligence toolkit — automated scanners, signal engines, and content tools.

## 🚀 Come farlo partire (passo-passo)

### Prerequisiti
- **Python 3.10+**
- **Git**

### Passo 1: Clona
```bash
git clone https://github.com/Lolarok/moltstreet-tools.git
cd moltstreet-tools
```

### Passo 2: Esegui gli scanner

**Crypto Signals v3** — Scanner dinamico Top 100:
```bash
# Scan completo top 100 (default)
python3 crypto-signals/crypto_signals.py

# Top 50 soltanto (più veloce)
MOLTSTREET_TOP=50 python3 crypto-signals/crypto_signals.py

# Output in output/signals_top100.json (per SignalHub o dashboard)
python3 crypto-signals/crypto_signals.py
```

**Crypto Alpha Hunter** — DeFi screener con filtri per settore:
```bash
python3 crypto-signals/crypto_alpha_hunter.py --top 20
python3 crypto-signals/crypto_alpha_hunter.py --sector perp
python3 crypto-signals/crypto_alpha_hunter.py --json
```

**RSS Aggregator** — auto-post WordPress:
```bash
python3 rss-aggregator/rss_aggregator.py --site crypto --dry-run
python3 rss-aggregator/rss_aggregator.py --site all --max 3
```

### Passo 3: Email alerts (opzionale)
```bash
export MAIL_APPPASSWORD=your_gmail_app_password
python3 crypto-signals/crypto_signals.py        # invia report HTML
python3 crypto-signals/crypto_alpha_hunter.py --top 20 --email
```

### Nessuna dipendenza da installare!
Tutto usa Python stdlib + API gratuite. Zero pip install.

---

## 📊 Tools

### 📡 Crypto Signals v3 (`crypto-signals/crypto_signals.py`)
Scanner dinamico che prende le **top 100 crypto** da CoinGecko, le scoreggia con segnali tecnici (momento, volume, ATH drawdown, TVL DeFiLlama, trending), e genera report HTML + JSON.

**Feature v3.0:**
- Top 100 dinamico (no more hardcoded watchlist)
- Classificazione settoriale automatica (DeFi, L1, L2, Meme, AI, RWA, Gaming, Infra)
- Output JSON per dashboard e SignalHub
- Sector breakdown con avg score
- ATH deep value detection
- Trending bonus da CoinGecko

```bash
python3 crypto-signals/crypto_signals.py
MOLTSTREET_TOP=50 python3 crypto-signals/crypto_signals.py  # solo top 50
```

**Output:**
- `output/signals_top100.json` — dati grezzi per dashboard
- `output/report_top100.html` — report visualizzabile

### 🔬 Crypto Alpha Hunter (`crypto-signals/crypto_alpha_hunter.py`)
Protocol scanner che scoreggia progetti DeFi per TVL growth, volume, GitHub activity. Supporta filtri per settore (perp, rwa, ai, l2, defi, infra).

```bash
python3 crypto-signals/crypto_alpha_hunter.py --top 20 --email
python3 crypto-signals/crypto_alpha_hunter.py --sector perp
python3 crypto-signals/crypto_alpha_hunter.py --json
```

### 📰 RSS Aggregator (`rss-aggregator/rss_aggregator.py`)
Fetches crypto news from RSS feeds, scores relevance, and auto-posts drafts to WordPress sites.

```bash
python3 rss-aggregator/rss_aggregator.py --site crypto --dry-run
python3 rss-aggregator/rss_aggregator.py --site all --max 3
```

---

## 🏗️ Architecture

```
moltstreet-tools/
├── crypto-signals/
│   ├── crypto_signals.py          # v3.0 — Top 100 dynamic scanner
│   ├── crypto_alpha_hunter.py     # DeFi protocol screener (sector-based)
│   └── README.md
├── rss-aggregator/
│   └── rss_aggregator.py          # RSS → WordPress auto-poster
├── output/                        # Generated reports (gitignored or committed)
│   ├── signals_top100.json        # JSON for dashboards / SignalHub
│   └── report_top100.html         # HTML report
├── docs/
│   ├── EMAIL_SETUP.md
│   └── SETUP_GUIDE.md
├── .github/workflows/
│   └── daily-scans.yml            # Daily cron: signals v3 + alpha hunter
└── README.md
```

## 🔄 GitHub Actions

La workflow `daily-scans.yml` gira ogni giorno alle **07:00 UTC**:

1. **Crypto Signals v3** → scansiona top 100, genera JSON + HTML, invia email
2. **Alpha Hunter** → screener DeFi top 50, invia email
3. **Commit** → salva i report nel repo

Puoi anche triggerarla manualmente da GitHub → Actions → "Daily Crypto Scans" → "Run workflow".

### Variabili d'ambiente (GitHub Secrets)

| Secret | Descrizione |
|--------|-------------|
| `MAIL_APPPASSWORD` | Gmail App Password per invio email |
| `ALERT_EMAIL` | Indirizzo destinatario (default: mittente) |

### Variabili configurabili

| Env Var | Default | Descrizione |
|---------|---------|-------------|
| `MOLTSTREET_TOP` | `100` | Quante crypto scansionare |
| `MOLTSTREET_JSON` | `1` | Genera output JSON (0 = skip) |

---

## 🔗 Integrazione con altri progetti

- **SignalHub** — legge `output/signals_top100.json` per popolare la dashboard
- **moltstreet-intelligence** — può usare `signals_top100.json` come input per lo scoring
- **crypto-trading-agents** — può usare i punteggi come filtro per le analisi

---

## Cost

$0/month — Python stdlib + free APIs (CoinGecko, DeFiLlama) + GitHub Actions free tier (2,000 min/month).

---
*Not financial advice. DYOR. MoltStreet*
