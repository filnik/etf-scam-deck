#!/usr/bin/env python3
"""
build.py — genera la serie di 5 video dal deck sorgente.

Il deck sorgente (`index.html.orig`, snapshot del monolite originale) è la
single source of truth per: CSS, framework JS, slide esistenti, chart cases.
Questo script lo spacchetta e riassembla in:
  - assets/deck.css        (CSS condiviso)
  - assets/deck.js         (framework JS condiviso: nav, counter, init charts)
  - v1..v4 .html           (5 file video, thin: linkano gli asset condivisi)
  - index.html             (landing page con le 5 card)

Le slide NUOVE (title/hook/outro per video + contenuti V2a/V2b/V3) vivono come
snippet HTML in `slides_new/`. Eventuali chart cases nuovi in `slides_new/new_charts.js`.

Ri-eseguibile: cambi il MANIFEST o uno snippet → `python3 build.py` → tutto rigenerato.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "index.html.orig"
SLIDES_NEW = ROOT / "slides_new"
ASSETS = ROOT / "assets"


# ============================================================
# MANIFEST — la struttura della serie
# ============================================================
# Ogni voce di `slides` è:
#   "NN"            → slide esistente nel deck sorgente (per data-id)
#   "@nome"         → snippet da slides_new/nome.html
# `data` = lista di id di <script type="application/json"> da includere.

VIDEOS = [
    {
        "file": "v1-concentrazione.html",
        "title": "V1 · Concentrare batte l'indice",
        "slides": [
            "@v1_title", "09", "09b", "@v1_pac_12m", "@v1_top2_algo",
            "14b", "@v1_iwmo_history", "14", "@v1_etf_constraints", "15", "16", "17",
            "@v1_mu_pac_fail", "@v1_single_name", "@v1_outro",
        ],
        "data": ["v1-charts-data"],
    },
    {
        "file": "v2a-rebalancing-costo.html",
        "title": "V2a · Il rebalancing ti costa",
        "slides": [
            "@v2a_title", "04", "04b", "05", "06", "07", "08",
            "@v2a_diversify_rebalancing", "@v2a_outro",
        ],
        "data": [],
    },
    {
        "file": "v2b-regimi-difesa.html",
        "title": "V2b · Gestire i regimi: rate hikes, oro, XOM, difesa",
        "slides": [
            "@v2b_title", "23b",
            "@v2b_cpi_signal", "@v2b_static_hedge", "@v2b_xom_vs_xle",
            "@v2b_inflation_type", "@v2b_gold_role", "@v2b_defense",
            "@v2b_outro",
        ],
        "data": [],
    },
    {
        "file": "v3-timing-lost-decades.html",
        "title": "V3 · Il mercato non sale sempre",
        "slides": [
            "@v3_title", "@v3_thesis",
            "@v3_lost_intro", "@v3_lost_1966", "@v3_lost_2000", "@v3_lost_scoreboard",
            "18", "19",
            "@v3_timing_vs_accumulo", "@v3_bear_strategies",
            "@v3_outro",
        ],
        "data": ["lost-decades-data"],
    },
    {
        "file": "v4-diversificazione.html",
        "title": "V4 · La diversificazione non ha senso",
        "slides": [
            "@v4_title", "22", "22b",
            "@v4_chapter_8d_glossario",  # 22c — INTL/EAFE/EM glossario + 5 epoche regime 1985-2026
            "@v4_chapter_8e_deepdive",   # 22d — 2003-2009 EM +150% (commodity supercycle + gold +170%)
            # Nascoste 2026-05-28: 10 (Concentration alpha 8C), 23-28 (crash test 9 + bear strategies).
            # Da rivalutare prima di rimetterle in produzione.
        ],
        "data": ["crash-data"],
    },
    {
        "file": "v5-anatomia-crash.html",
        "title": "V5 · Anatomia di 7 crash · come reagisce il sistema",
        "slides": [
            "@v5_title", "@v5_how_it_works", "@v5_overview",
            "@v5_crash_01_1990_gulf_war",
            "@v5_crash_02_2000_dotcom",
            "@v5_crash_03_2007_gfc",
            "@v5_crash_04_2018_powell_q4",
            "@v5_crash_05_2020_covid",
            "@v5_crash_06_2022_inflation",
            "@v5_crash_07_2025_liberation_day",
            "@v5_outro",
        ],
        "data": ["crash-anatomy-data", "crash-anatomy-narratives"],
    },
]

LANDING = {
    "file": "index.html",
    "title": "Gli ETF sono SCAM? — Serie in 5 video",
}


# ============================================================
# PARSING del deck sorgente
# ============================================================

def read_src() -> str:
    if not SRC.exists():
        sys.exit(f"ERRORE: manca {SRC} (lo snapshot del deck monolite)")
    return SRC.read_text(encoding="utf-8")


def extract_between(text: str, start: str, end: str) -> str:
    i = text.index(start) + len(start)
    j = text.index(end, i)
    return text[i:j]


def extract_css(src: str) -> str:
    return extract_between(src, "<style>\n", "\n</style>").strip("\n")


def brace_match(text: str, open_idx: int) -> int:
    """Dato l'indice di una '{', ritorna l'indice della '}' che la chiude."""
    depth = 0
    for k in range(open_idx, len(text)):
        c = text[k]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return k
    raise ValueError("graffa non bilanciata")


def extract_framework_js(src: str) -> tuple[str, str]:
    """Ritorna (framework_js, build_chart_fn_body_raw).

    framework_js = IIFE completa MENO la funzione buildChart, con
    initChartsInSlide modificata per usare window.buildChart con guardia.
    """
    # ultima coppia <script>...</script> (il framework, non il JSON crash-data)
    script_open = src.rindex("<script>")
    script_close = src.index("</script>", script_open)
    iife = src[script_open + len("<script>"):script_close]

    # individua e ritaglia `function buildChart(canvas) { ... }`
    bc_start = iife.index("function buildChart(canvas) {")
    bc_brace = iife.index("{", bc_start)
    bc_end = brace_match(iife, bc_brace)
    build_chart_fn = iife[bc_start:bc_end + 1]
    # rimuovi la funzione dall'IIFE (lasciando una riga vuota pulita)
    framework = iife[:bc_start].rstrip() + "\n\n" + iife[bc_end + 1:].lstrip("\n")

    # initChartsInSlide deve usare window.buildChart con guardia
    framework = framework.replace(
        "      chartsInitialized.add(canvas.id);\n      buildChart(canvas);",
        "      if (typeof window.buildChart === 'function') {\n"
        "        chartsInitialized.add(canvas.id);\n"
        "        window.buildChart(canvas);\n"
        "      }",
    )
    # forza l'init dello slide 0 al load (init charts + counter anche sul primo)
    framework = framework.replace(
        "  // Initialize first slide animations\n"
        "  setTimeout(() => {\n"
        "    animateCountersInSlide(slides[0]);\n"
        "  }, 200);",
        "  // Initialize first slide (counters + charts)\n"
        "  setTimeout(() => { showSlide(0); }, 60);",
    )
    return framework.strip("\n"), build_chart_fn


def parse_chart_cases(build_chart_fn: str) -> tuple[str, dict]:
    """Spacchetta buildChart in (preamble, {chart_id: case_code}).

    Il blocco `id.startsWith('chart-crash-')` è salvato con chiave '__crash__'.
    """
    body_start = build_chart_fn.index("{") + 1
    body_end = build_chart_fn.rindex("}")
    body = build_chart_fn[body_start:body_end]

    # il preamble è tutto fino al primo `if (id`
    first_if = body.index("    if (id")
    preamble = body[:first_if].rstrip("\n")

    cases = {}
    rest = body[first_if:]
    # trova ogni `    if (` di livello top e brace-match
    idx = 0
    while True:
        m = re.search(r"\n? *if \(", rest[idx:])
        if not m:
            break
        if_start = idx + m.start()
        brace = rest.index("{", if_start)
        brace_end = brace_match(rest, brace)
        block = rest[if_start:brace_end + 1].strip("\n")
        cond = rest[if_start:brace]
        cm = re.search(r"id === '([^']+)'", cond)
        if cm:
            cases[cm.group(1)] = block
        elif "startsWith('chart-crash-')" in cond:
            cases["__crash__"] = block
        elif "startsWith('chart-anatomy-')" in cond:
            cases["__anatomy__"] = block
        else:
            print(f"  WARN: blocco buildChart non riconosciuto: {cond[:60]!r}", file=sys.stderr)
        idx = brace_end + 1
    return preamble, cases


SECTION_RE = re.compile(
    r'<section\b[^>]*\bdata-id="([^"]+)"[^>]*>.*?</section>', re.DOTALL
)


def parse_sections(src: str) -> dict:
    main = extract_between(src, '<main class="deck" id="deck">', "</main>")
    out = {}
    for m in SECTION_RE.finditer(main):
        sec = m.group(0)
        # togli is-active da tutte (lo rimettiamo sulla prima di ogni video)
        sec = sec.replace('class="slide is-active ', 'class="slide ', 1)
        sec = sec.replace('class="slide is-active"', 'class="slide"', 1)
        out[m.group(1)] = sec
    return out


def parse_data_scripts(src: str) -> dict:
    out = {}
    for m in re.finditer(
        r'<script id="([^"]+)" type="application/json">.*?</script>', src, re.DOTALL
    ):
        out[m.group(1)] = m.group(0)
    return out


def resolve_data_script(data_id: str, embedded: dict) -> str | None:
    """Risolve un data id: prima dagli script embedded nel sorgente, poi da
    un file data/<id_con_underscore>.json."""
    if data_id in embedded:
        return embedded[data_id]
    fname = ROOT / "data" / (data_id.replace("-", "_") + ".json")
    if fname.exists():
        content = fname.read_text(encoding="utf-8").strip()
        return f'<script id="{data_id}" type="application/json">\n{content}\n</script>'
    print(f"  WARN: data script '{data_id}' non trovato (né embedded né file)", file=sys.stderr)
    return None


# ============================================================
# GENERAZIONE
# ============================================================

HEAD_TMPL = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="theme-color" content="#0f0f1a">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
<link rel="stylesheet" href="assets/deck.css">
</head>
<body>
"""


def load_snippet(name: str) -> str | None:
    p = SLIDES_NEW / f"{name}.html"
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8").strip("\n")


def canvas_ids(html: str) -> list:
    return re.findall(r'<canvas id="([^"]+)"', html)


def build_video(video: dict, sections: dict, data_scripts: dict,
                preamble: str, cases: dict) -> tuple[str, list]:
    parts = []
    missing = []
    for ref in video["slides"]:
        if ref.startswith("@"):
            snip = load_snippet(ref[1:])
            if snip is None:
                missing.append(ref[1:])
                snip = (f'<section class="slide layout-center" data-id="{ref[1:]}">'
                        f'<div class="slide-inner layout-center" style="text-align:center">'
                        f'<div class="eyebrow accent-red">SNIPPET MANCANTE</div>'
                        f'<h2 class="h2">{ref[1:]}</h2></div></section>')
            parts.append(snip)
        else:
            if ref not in sections:
                missing.append(ref)
                continue
            parts.append(sections[ref])

    # is-active sulla prima slide
    if parts:
        parts[0] = parts[0].replace('class="slide ', 'class="slide is-active ', 1)
        parts[0] = parts[0].replace('class="slide"', 'class="slide is-active"', 1)

    body_slides = "\n\n".join(parts)

    # quali chart servono?
    all_html = body_slides
    needed = []
    for cid in canvas_ids(all_html):
        if cid in cases:
            if cid not in needed:
                needed.append(cid)
        elif cid.startswith("chart-crash-"):
            if "__crash__" not in needed:
                needed.append("__crash__")
        elif cid.startswith("chart-anatomy-"):
            if "__anatomy__" not in needed:
                needed.append("__anatomy__")
        else:
            print(f"  WARN: {video['file']}: nessun chart case per '{cid}'", file=sys.stderr)
    chart_blocks = "\n\n".join(cases[c] for c in needed)
    build_chart_js = (
        "window.buildChart = function(canvas) {\n"
        + preamble + "\n\n"
        + ("    " + chart_blocks if chart_blocks else "")
        + "\n  };"
    )

    data_html = "\n".join(
        s for s in (resolve_data_script(d, data_scripts) for d in video.get("data", []))
        if s
    )

    html = HEAD_TMPL.format(title=video["title"])
    html += '<div class="progress-bar" id="progressBar"></div>\n'
    html += '<div class="deck-brand"><span class="dot"></span>stockpickers.app</div>\n'
    if data_html:
        html += data_html + "\n"
    html += '\n<main class="deck" id="deck">\n\n'
    html += body_slides
    html += '\n\n</main>\n\n'
    html += '<div class="disclaimer-tag">⚠ Educational only · DYOR · Capital at risk</div>\n'
    html += ('<div class="nav-controls">\n'
             '  <button class="nav-btn" id="btnPrev" aria-label="Previous slide">←</button>\n'
             '  <div class="nav-counter"><span class="current" id="navCurrent">01</span>'
             ' / <span id="navTotal">01</span></div>\n'
             '  <button class="nav-btn" id="btnNext" aria-label="Next slide">→</button>\n'
             '</div>\n\n')
    html += "<script>\n" + build_chart_js + "\n</script>\n"
    html += '<script src="assets/deck.js"></script>\n'
    html += "</body>\n</html>\n"
    return html, missing


def build_landing() -> str:
    cards = []
    for i, v in enumerate(VIDEOS, 1):
        cards.append(
            f'  <a class="series-card" href="{v["file"]}">\n'
            f'    <div class="series-card__num">{i:02d}</div>\n'
            f'    <div class="series-card__title">{v["title"]}</div>\n'
            f'  </a>'
        )
    html = HEAD_TMPL.format(title=LANDING["title"])
    html += '<div class="deck-brand"><span class="dot"></span>stockpickers.app</div>\n'
    html += '<main class="deck" id="deck">\n'
    html += '<section class="slide is-active layout-center" data-id="landing">\n'
    html += '<div class="slide-inner layout-center" style="text-align:center;align-items:center;gap:32px;">\n'
    html += '  <div class="eyebrow">Serie · 5 video</div>\n'
    html += '  <h1 class="h1">Gli ETF sono <span class="accent-red">SCAM</span>?</h1>\n'
    html += '  <p class="lead" style="max-width:720px;">Una serie in 5 video. Il PAC passivo su SPY ti è costato '
    html += '<strong class="accent-green">18,65 milioni</strong> in 16 anni — ecco perché, e cosa fare invece.</p>\n'
    html += '  <div class="series-grid">\n' + "\n".join(cards) + '\n  </div>\n'
    html += '</div>\n</section>\n</main>\n'
    html += '<div class="disclaimer-tag">⚠ Educational only · DYOR · Capital at risk</div>\n'
    html += "</body>\n</html>\n"
    return html


# ============================================================
# MAIN
# ============================================================

def main():
    src = read_src()
    ASSETS.mkdir(exist_ok=True)

    css = extract_css(src)
    framework_js, build_chart_fn = extract_framework_js(src)
    preamble, cases = parse_chart_cases(build_chart_fn)
    sections = parse_sections(src)
    data_scripts = parse_data_scripts(src)

    # chart cases nuovi (opzionale)
    new_charts_file = SLIDES_NEW / "new_charts.js"
    if new_charts_file.exists():
        new_src = new_charts_file.read_text(encoding="utf-8")
        # ogni blocco `if (id === 'chart-x') { ... }` separato
        _, new_cases = parse_chart_cases("x(){" + new_src + "}")
        cases.update(new_cases)
        print(f"  + {len(new_cases)} chart case nuovi da new_charts.js")

    # landing CSS extra (series-grid / series-card) appeso a deck.css
    css += "\n\n" + LANDING_CSS
    # crash anatomy CSS extra (V5)
    css += "\n\n" + CRASH_ANATOMY_CSS

    (ASSETS / "deck.css").write_text(css + "\n", encoding="utf-8")
    (ASSETS / "deck.js").write_text(framework_js + "\n", encoding="utf-8")
    print(f"  ✓ assets/deck.css  ({len(css)} char)")
    print(f"  ✓ assets/deck.js   ({len(framework_js)} char)")
    print(f"  parsed: {len(sections)} sezioni, {len(cases)} chart case")

    all_missing = {}
    for video in VIDEOS:
        html, missing = build_video(video, sections, data_scripts, preamble, cases)
        (ROOT / video["file"]).write_text(html, encoding="utf-8")
        n = len(video["slides"])
        flag = f"  ⚠ {len(missing)} snippet mancanti: {missing}" if missing else ""
        print(f"  ✓ {video['file']:<32} {n:>2} slide{flag}")
        if missing:
            all_missing[video["file"]] = missing

    (ROOT / LANDING["file"]).write_text(build_landing(), encoding="utf-8")
    print(f"  ✓ {LANDING['file']:<32} (landing)")

    if all_missing:
        print("\n  NOTA: snippet mancanti → placeholder rosso nel deck. "
              "Crearli in slides_new/ e ri-eseguire build.py.")


LANDING_CSS = """/* --- landing serie --- */
.series-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px; width: 100%; max-width: 980px; }
.series-card { display: flex; flex-direction: column; gap: 10px; padding: 22px;
  border-radius: 16px; background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08); text-decoration: none;
  transition: transform .2s, border-color .2s, background .2s; }
.series-card:hover { transform: translateY(-4px); border-color: var(--accent-cyan, #00d9ff);
  background: rgba(0,217,255,0.06); }
.series-card__num { font-family: 'JetBrains Mono', monospace; font-size: 13px;
  color: var(--accent-cyan, #00d9ff); }
.series-card__title { font-size: 16px; font-weight: 700; color: #f0f0f5; line-height: 1.3; }"""


CRASH_ANATOMY_CSS = """/* --- V5 crash anatomy --- */
.crash-layout { display: grid; grid-template-columns: 2fr 1fr; gap: 18px; align-items: stretch; }
.crash-side { display: flex; flex-direction: column; gap: 10px; }

.verdict-card { padding: 14px 16px; border-radius: 12px; background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.10); display: flex; flex-direction: column; gap: 4px; }
.verdict-card--win   { border-color: rgba(0,210,106,0.45);   background: rgba(0,210,106,0.10); }
.verdict-card--early { border-color: rgba(0,217,255,0.45);   background: rgba(0,217,255,0.10); }
.verdict-card--miss  { border-color: rgba(255,165,2,0.45);   background: rgba(255,165,2,0.10); }
.verdict-card--skip  { border-color: rgba(180,180,200,0.30); background: rgba(180,180,200,0.06); }
.verdict-card--na    { border-color: rgba(180,180,200,0.20); background: rgba(180,180,200,0.04); }
.verdict-label { font-family: 'JetBrains Mono', monospace; font-size: 10px; letter-spacing: 0.10em;
  color: #7a7a90; text-transform: uppercase; }
.verdict-value { font-size: 19px; font-weight: 700; color: #f0f0f5; line-height: 1.15;
  letter-spacing: -0.01em; }
.verdict-sub { font-size: 12px; color: #b0b0c0; font-family: 'JetBrains Mono', monospace; }

.delta-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.delta-cell { padding: 12px 10px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.10);
  border-radius: 10px; display: flex; flex-direction: column; gap: 4px; text-align: center; }
.delta-num { font-family: 'JetBrains Mono', monospace; font-size: 26px; font-weight: 700;
  letter-spacing: -0.02em; line-height: 1; color: #00d26a; }
.delta-num--zero { color: #7a7a90; }
.delta-num--red { color: #ff4757; }
.delta-label { font-family: 'JetBrains Mono', monospace; font-size: 9px; letter-spacing: 0.08em;
  text-transform: uppercase; color: #7a7a90; }

.fire-state { padding: 12px 14px; background: rgba(255,255,255,0.03);
  border: 1px solid rgba(0,217,255,0.18); border-radius: 10px; }
.fire-state__title { font-family: 'JetBrains Mono', monospace; font-size: 10px; letter-spacing: 0.08em;
  color: #00d9ff; text-transform: uppercase; margin-bottom: 8px; display: block; }
.fire-state__list { list-style: none; display: flex; flex-direction: column; gap: 5px;
  font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: #b0b0c0; }
.fire-state__list li { display: flex; justify-content: space-between; gap: 10px; }
.fire-state__list li b { color: #f0f0f5; font-weight: 700; }
.fire-state__voters { display: block; margin-top: 8px; padding-top: 8px;
  border-top: 1px dashed rgba(255,255,255,0.08); font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px; color: #00d26a; line-height: 1.4; }
.fire-state__voters b { color: #00d26a; }

.skip-state { padding: 12px 14px; background: rgba(180,180,200,0.04);
  border: 1px solid rgba(180,180,200,0.20); border-radius: 10px; font-size: 12.5px;
  line-height: 1.45; color: #b0b0c0; }
.skip-state b { color: #f0f0f5; font-weight: 700; }

.events-strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 6px; font-size: 11px; line-height: 1.35; color: #b0b0c0; margin-top: 2px; }
.events-strip__cell { padding: 8px 10px; background: rgba(255,255,255,0.025);
  border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; }
.events-strip__date { font-family: 'JetBrains Mono', monospace; font-size: 10px;
  color: #00d9ff; letter-spacing: 0.04em; display: block; margin-bottom: 2px; }
.events-strip__label { color: #f0f0f5; font-weight: 700; display: block; margin-bottom: 2px;
  font-size: 11.5px; }

/* Term tooltip — hover to expand */
.term { border-bottom: 1px dotted rgba(0,217,255,0.55); cursor: help; position: relative;
  color: #6bd5ff; font-weight: 500; }
.term::after { content: attr(data-tip); position: absolute; bottom: calc(100% + 10px); left: 50%;
  transform: translateX(-50%) translateY(8px); background: #1a1a36;
  border: 1px solid rgba(0,217,255,0.40); padding: 12px 14px; border-radius: 10px;
  font-size: 12.5px; font-weight: 400; line-height: 1.5; width: 320px; z-index: 1000;
  text-align: left; color: #f0f0f5; white-space: normal; opacity: 0; pointer-events: none;
  transition: opacity 0.18s ease, transform 0.18s ease; box-shadow: 0 16px 48px rgba(0,0,0,0.55);
  font-family: 'Inter', sans-serif; }
.term:hover::after { opacity: 1; transform: translateX(-50%) translateY(0); }

/* V5 overview table */
.overview-table { width: 100%; border-collapse: separate; border-spacing: 0;
  font-family: 'JetBrains Mono', monospace; font-size: 13px; }
.overview-table th { background: rgba(0,217,255,0.06); color: #00d9ff;
  padding: 10px 12px; text-align: left; font-size: 11px; letter-spacing: 0.08em;
  text-transform: uppercase; font-weight: 600; border-bottom: 1px solid rgba(0,217,255,0.2); }
.overview-table td { padding: 9px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); color: #d0d0e0; }
.overview-table td.num { text-align: right; font-weight: 700; }
.overview-table tr.row--win td { color: #f0f0f5; }
.overview-table tr.row--miss { opacity: 0.65; }
.overview-table tr.row--skip { opacity: 0.5; }
.overview-table .pill { display: inline-block; padding: 2px 8px; border-radius: 100px;
  font-size: 10px; letter-spacing: 0.06em; font-weight: 700; }
.overview-table .pill--win   { background: rgba(0,210,106,0.18); color: #4ade80; }
.overview-table .pill--early { background: rgba(0,217,255,0.18); color: #6bd5ff; }
.overview-table .pill--miss  { background: rgba(255,165,2,0.18); color: #ffc16b; }
.overview-table .pill--skip  { background: rgba(180,180,200,0.14); color: #b0b0c0; }
.overview-table .pill--na    { background: rgba(180,180,200,0.10); color: #7a7a90; }
.overview-table .delta-pos { color: #00d26a; }
.overview-table .delta-zero { color: #7a7a90; }

@media (max-width: 900px) {
  .crash-layout { grid-template-columns: 1fr; }
  .delta-pair { grid-template-columns: 1fr 1fr; }
  .term::after { width: 240px; }
}"""


if __name__ == "__main__":
    main()
