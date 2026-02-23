# Jhaveri Financial Intelligence Engine (FIE)

## Multi-Agent Advisory System for Wealth Management

### Quick Start

```bash
# 1. Clone/download this project
# 2. Run setup
chmod +x setup.sh
./setup.sh

# 3. Edit .env with your Anthropic API key
nano .env

# 4. Add your client data (CSV files in data/ folder)

# 5. Launch dashboard
streamlit run dashboard/app.py
```

### Project Structure

```
fie/
├── agents/                 # The 5 worker agents
│   ├── nlp_parser.py       # Agent 1: FM text → structured directives
│   ├── market_data.py      # Agent 2: Price/NAV data fetcher
│   ├── technical_signals.py # Agent 3: 12+ indicators + composite scoring
│   ├── recommendation.py   # Agent 4: Portfolio-specific recommendations
│   └── maestro.py          # Master orchestrator
├── config/
│   └── settings.py         # All configuration in one place
├── dashboard/
│   └── app.py              # Streamlit FM dashboard
├── database/
│   ├── models.py           # SQLAlchemy models (6 tables)
│   └── fie.db              # SQLite database (auto-created)
├── data/                   # Input data (CSVs)
│   ├── clients.csv         # Your client master data
│   ├── holdings.csv        # Your client holdings
│   ├── sample_clients.csv  # Template
│   └── sample_holdings.csv # Template
├── outputs/                # Generated reports
├── scripts/
│   └── build_universe.py   # Master instrument universe builder
├── templates/              # PDF report templates
├── .env                    # Your API keys (never commit this)
├── .env.example            # Template for .env
├── requirements.txt        # Python dependencies
├── setup.sh                # One-click setup
└── README.md               # This file
```

### Architecture

**5 Independent Agents + 1 Maestro:**

| Agent | Role | Tech |
|-------|------|------|
| 🧠 Maestro | Orchestrates daily pipeline | Python scheduler |
| 💬 NLP Parser | FM text → JSON directives | Claude API |
| 📡 Market Data | Fetches OHLCV + NAV data | yfinance + AMFI |
| 📊 Technical | 12+ indicators, composite scoring | pandas-ta |
| ⚗️ Synthesizer | FM rules × Technical × Portfolio = Recommendations | Claude API |
| 🖥️ Dashboard | FM approval workflow + reports | Streamlit |

### Data Requirements

**clients.csv** — Your client master:
```
client_id, name, risk_profile, strategy_type, total_aum, contact_email, relationship_manager
```

**holdings.csv** — Client portfolio holdings:
```
client_id, instrument_code, instrument_name, instrument_type, sector_tag, current_value, cost_basis, allocation_pct, purchase_date, sip_active, sip_amount
```

### API Key Setup

1. Go to https://console.anthropic.com
2. Create account + add billing ($5 minimum)
3. Generate API key
4. Add to .env: `ANTHROPIC_API_KEY=sk-ant-...`

### Daily Usage

1. FM opens dashboard (8:00 AM)
2. Reviews overnight technical signals
3. Types market views in text box
4. Confirms parsed directives
5. Reviews per-client recommendations
6. Approves/rejects/modifies
7. Exports approved recommendations as PDF

### Cost

- Claude API: ~₹3,000-5,000/month
- All other tools: FREE
- Cloud hosting (optional): ~₹800/month
