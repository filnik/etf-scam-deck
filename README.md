# Slide Deck — "Gli ETF sono SCAM?"

Slide deck HTML interattivo per il video YouTube. Self-contained in un singolo `index.html`, design system replicato da **stockpickers.app**.

## Come si usa

```bash
# Apri direttamente nel browser (Chrome / Safari / Firefox)
open index.html
```

Nessun server necessario. Servono solo internet la prima volta per caricare:
- Inter + JetBrains Mono (Google Fonts CDN)
- Chart.js 4.4 (CDN jsdelivr)

Tutto il resto è inline.

## Navigazione

| Tasto | Azione |
|-------|--------|
| `→` `Space` `PageDown` | Slide successiva |
| `←` `PageUp` | Slide precedente |
| `Home` | Prima slide |
| `End` | Ultima slide |
| `F` | Fullscreen toggle |
| swipe ←/→ | Mobile navigation |
| Click `Prev` / `Next` | Buttons in basso a destra |

## Struttura (39 slide · 13 chart Chart.js)

1. **TITLE** — Gli ETF sono SCAM? (provocazione)
2. **HOOK** — €10.33M che non vedrai mai
3. **AGENDA** — i 7 capitoli
4. **TER** — tabella costi cumulativi 30y
5. **TOP 15 SPY** ★ NEW — composizione + YTD bar chart
6. **LIT** — counter -€240K
7. **Contango** — DBO drag strutturale
8. **Index inclusion** — pump +3-8% + drag $16B/anno
9. **Stop loss** — chart 36% → 3% CAGR
10. **HEART** — NoRot2 vs SPY (€1.65M vs €11.98M, 15y)
11. **CAGR 3-way** ★ NEW — bar chart SPY vs QQQ vs NoRot2
12. **PAC growth** ★ NEW — line chart 15y delle 3 strategie
13. **Top1ByVol** — concentrazione +50.7% vs +34.6%
14. **ETF momentum holdings** — top 10 reali (screenshot 2026-05-08)
15. **Alphabet duplicato** — zoom 4.65% combinato
16. **J&J + CAT** — anomalia momentum
17. **349 holdings** — closet indexing
18. **Vero momentum globale** ★ NEW — Top 15 Clenow vs ETF momentum side-by-side
19. **Reframe** — l'idea è giusta, l'ETF la realizza male
20. **All-time winners** — tesi macro tech (lavatrice/orologio analogie)
21. **AVGO secret** — 63% top1 frequency 15y
22. **Sempre comprare** — analogia oro, no timing
23. **Sector rotation** — backtest fallito -14.3pp
24. **Tematici trap** — Cannabis -90%, ARKK -67%, KWEB -80%
25. **ARKK case** — Cathie Wood "value destroyer"
26. **2022 crash** — falsa diversificazione SPY/AGG/TLT/GLD
27. **Algo cascade** — Vol Control $120B chart
28. **UPRO -96%** — leverage decay COVID
29. **Crash test intro** ★ NEW — l'ipotesi di Filippo da testare
30. **Crash 1: Dot-com** ★ NEW — line chart timeline + bar late exit
31. **Crash 2: GFC 2008** ★ NEW — line chart + bar late exit
32. **Crash 3: Memory Glut 2018** ★ NEW — line chart + bar late exit
33. **Crash 4: Rate Hike 2022** ★ NEW — line chart + bar late exit
34. **Crash scoreboard** ★ NEW — 8 scenari, vincitori, lezioni
35. **Plot twist** — quando ETF è giusto (3 condizioni)
36. **Recap scoreboard** — i 4 numeri killer (€10.33M / 4.65% / +16pp / -96%)
37. **CTA** — stockpickers.app
38. **Outro + Disclaimer**
39. **End** — Grazie + brand

**Crash Test data**: generato da `data/crash_simulator.py` (~400 linee Python con yfinance) → `data/crash_data.json` (37KB) embedded inline nel deck.

Costi simulati nel backtest crash:
- Slippage 0.10% per trade
- Costo €1/trade (BG Saxo)
- Bollo 0.20% annuo su NAV
- Tasse 26% capital gain (regime dichiarativo)
- TER 0.07% SPY, 0.40% GLD
- Late exit: −4pp peggio del trough (uscita 1 settimana dopo bottom)

**Chart.js attivi** (13):
- `chart-spy-ytd` (slide 5) — horizontal bar Top 15 SPY YTD performance
- `chart-stop-loss` (slide 9) — bar chart stop loss devastation
- `chart-cagr-3way` (slide 11) — bar chart CAGR comparativo 3-way
- `chart-pac-growth` (slide 12) — line chart 15y crescita PAC
- `chart-volcontrol` (slide 27) — bar chart vol control selling cascade
- `chart-crash-dotcom-1y` + `chart-crash-dotcom-bars` (slide 30)
- `chart-crash-gfc2008-1y` + `chart-crash-gfc2008-bars` (slide 31)
- `chart-crash-memory2018-1y` + `chart-crash-memory2018-bars` (slide 32)
- `chart-crash-rate2022-1y` + `chart-crash-rate2022-bars` (slide 33)

## Design system

Replica `site/styles_landing.css` di investing project:

- **Background**: `#0f0f1a` con radial gradients ambient + noise SVG overlay
- **Brand**: cyan `#00d9ff`, green `#00d26a`, red `#ff4757`, yellow `#ffa502`
- **Typography**: Inter (heading + body), JetBrains Mono (numeri/ticker)
- **Glassmorphism**: `backdrop-filter: blur(20px)` su card
- **Big numbers**: counter animati (rollup easeOutExpo 1.6s)
- **Charts**: Chart.js bar charts (stop loss, vol control)

## Personalizzazione

Tutto inline in `index.html`. Per modificare:

- **Colori / palette** → tag `<style>`, sezione `:root` (linee 14-30 ca.)
- **Contenuto slide** → `<section class="slide" data-id="NN">` (rispetta numerazione)
- **Counter animati** → attributo `data-counter="NUM"` + `data-prefix` / `data-suffix` / `data-decimals`
- **Charts** → funzione `buildChart()` in `<script>` → aggiungi nuovi case per nuovi chart id

## Stampa / Export PDF

Apri il file in browser → stampa (`Cmd+P`) → salva come PDF.
La media query `@media print` espande tutte le slide su pagine separate.

## Verification checklist

- [ ] Apri index.html in Chrome → naviga tutte le 28 slide
- [ ] Counter animati funzionano (€1.65M, €11.98M, +50.7%, ecc.)
- [ ] Chart 8 (stop loss) e chart 23 (vol control) renderizzano
- [ ] Frecce / spacebar / swipe mobile funzionano
- [ ] Progress bar in alto si riempie correttamente
- [ ] Stampa PDF: tutte le slide presenti su pagine dedicate
- [ ] Link a stockpickers.app verificato (slide 26)

## Fonti dati (cross-reference investing project)

| Slide | File sorgente |
|-------|---------------|
| 04 (TER) | `guides/strategie/03_sp500.md:12` |
| 08 (Stop loss) | `guides/strategie/dynamic_momentum_tuning.md:127-135` |
| 09 (NoRot2) | `guides/strategie/no_rotation_focused_pool_apr2026.md:46,203-212` |
| 10 (Top1ByVol) | `guides/strategie/adopted/top1_by_vol.md:5,41-45` |
| 11-14 (MTUM holdings) | screenshot live 2026-05-08 |
| 17 (AVGO 63%) | `guides/strategie/no_rotation_focused_pool_apr2026.md:108` |
| 19 (Sector rotation) | `backtest/etf_rotation_backtest.py:691` |
| 21 (ARKK) | `guides/investors/GROWTH_INVESTORS_E_FONDI.md:206-244` |
| 22 (2022 crash) | `guides/strategie/04_multi_asset.md:89-101` |
| 23 (Vol Control) | `algorithm/04_vol_control.md:67-80` |
| 24 (UPRO) | `guides/strategie/06_levered.md:15-42` |

## License / Use

Questo deck è strumento di lavoro personale per il video YouTube. Il design system è derivato da `stockpickers.app` (progetto investing personale di Filippo De Pretto). I dati di backtest provengono dal repository investing privato.
