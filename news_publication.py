"""Render and atomically publish the SCOZ News digest."""

import html
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

__all__ = ["Publication", "prepare_publication", "print_guidelines"]


@dataclass(frozen=True)
class Publication:
    """A rendered digest whose HTML and cache commit together."""

    html: str
    cache: dict

    def write(self, html_path: str | Path, cache_path: str | Path) -> None:
        _publish_outputs(html_path, self.html, cache_path, self.cache)


# ── Logo ──────────────────────────────────────────────────────────────────────
def make_logo_b64():
    """Retorna um logo SVG leve para manter o HTML publicado compacto."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="90" height="30" '
        'viewBox="0 0 90 30"><text x="0" y="24" '
        'font-family="Arial Black,Inter,sans-serif" font-size="26" '
        'font-weight="900" fill="white">SCOZ</text></svg>'
    )
    return "data:image/svg+xml," + quote(svg, safe="")

# ── Helpers ───────────────────────────────────────────────────────────────────
def next_monday_label(from_date=None):
    base = from_date or datetime.today()
    days_ahead = 7 - base.weekday() if base.weekday() != 0 else 7
    nxt = base + timedelta(days=days_ahead)
    months_pt = ["janeiro","fevereiro","março","abril","maio","junho",
                 "julho","agosto","setembro","outubro","novembro","dezembro"]
    return f"{nxt.day} de {months_pt[nxt.month-1]} de {nxt.year}"

def monday_week_id(week_id):
    """Return the Monday that starts the reading batch week."""
    try:
        date = datetime.fromisoformat(str(week_id))
        start = date - timedelta(days=date.weekday())
        return start.strftime("%Y-%m-%d")
    except ValueError:
        return str(week_id)


# ── SVG icons ─────────────────────────────────────────────────────────────────
SVG_SPRITE = """<svg xmlns="http://www.w3.org/2000/svg" style="display:none">
  <symbol id="icon-external" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"/></symbol>
  <symbol id="icon-copy" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184"/></symbol>
  <symbol id="icon-check" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5"/></symbol>
  <symbol id="icon-search" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"/></symbol>
  <symbol id="icon-xmark" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12"/></symbol>
  <symbol id="icon-chevron" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="m19 9-7 7-7-7"/></symbol>
  <symbol id="icon-expand-all" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 5.25 7.5 7.5 7.5-7.5m-15 6 7.5 7.5 7.5-7.5"/></symbol>
</svg>"""

def svg_icon(name, width, height, stroke_width="1.5"):
    stroke_cls = " sw-2" if str(stroke_width) == "2" else ""
    return f'<svg class="ico ico-{width}{stroke_cls}" aria-hidden="true"><use href="#icon-{name}"></use></svg>'

SVG_EXTERNAL = svg_icon("external", 11, 11)
SVG_COPY     = svg_icon("copy", 13, 13)
SVG_CHECK    = svg_icon("check", 13, 13, "2")
SVG_SEARCH   = svg_icon("search", 16, 16)
SVG_XMARK    = svg_icon("xmark", 14, 14, "2")
SVG_CHEVRON  = svg_icon("chevron", 14, 14, "2")
SVG_EXP_ALL  = svg_icon("expand-all", 11, 11)

# ── Category config ───────────────────────────────────────────────────────────
CATEGORIES = [
    ("meta",   "Meta Ads",             "var(--meta)",   "14,165,233",  ".30", ".10", ".13", "20% 20%"),
    ("google", "Google Ads",           "var(--google)", "52,168,83",   ".26", ".08", ".11", "78% 22%"),
    ("ppc",    "Tráfego Pago",         "var(--ppc)",    "139,92,246",  ".28", ".09", ".12", "18% 75%"),
    ("mkt",    "Marketing Digital",    "var(--mkt)",    "245,158,11",  ".24", ".07", ".10", "80% 72%"),
    ("ia",     "IA &amp; Ferramentas", "var(--ia)",     "234,67,53",   ".26", ".08", ".11", "22% 28%"),
]

# ── Category guidelines (referência para curadoria) ──────────────────────────
CATEGORY_GUIDELINES = {
    "meta": {
        "name": "Meta Ads",
        "includes": [
            "Ads Manager — funcionalidades e atualizações",
            "Targeting (Advantage+, Andromeda, audiências)",
            "Formatos de anúncio (AR ads, Reels ads, Stories ads, carousel, collection)",
            "Políticas de anúncio e reprovações",
            "Conversion API (CAPI) e mensuração",
            "Criativos para anúncios (best practices específicas de ads)",
            "Meta Business Suite (recursos de advertising)",
            "Atribuição e relatórios para anunciantes",
            "Benchmarks de ad spend, CPM, CPA",
        ],
        "excludes": [
            "Algoritmo orgânico (exceto se impactar diretamente entrega de ads)",
            "Meta Verified / produtos de assinatura social",
            "Estratégia de conteúdo orgânico (não-pago)",
            "Features de plataforma não ligadas a ads (Reels orgânico, Threads, etc.)",
            "Notícias corporativas da Meta (earnings, layoffs, etc.)",
        ],
    },
    "google": {
        "name": "Google Ads",
        "includes": [
            "Google Ads — atualizações de plataforma",
            "Performance Max, AI Max, Smart Bidding",
            "Google Ads API e Editor",
            "Shopping ads e Merchant Center",
            "YouTube advertising",
            "Políticas do Google Ads",
            "Enhanced Conversions e mensuração",
            "Google Tag Manager para ads",
        ],
        "excludes": [
            "Algoritmo de busca orgânica do Google (→ ppc ou mkt)",
            "Google Workspace ou produtos não-ads",
            "Chrome browser updates",
        ],
    },
    "ppc": {
        "name": "Tráfego Pago",
        "includes": [
            "Estratégia e tendências cross-platform de PPC",
            "Microsoft/Bing Ads, TikTok Ads, LinkedIn Ads, X Ads",
            "Mídia programática",
            "Benchmarks e relatórios da indústria de PPC",
            "Landing pages para ads",
            "Tendências de SEO que impactam estratégia paga",
        ],
        "excludes": [
            "Notícias específicas de Meta Ads (→ meta)",
            "Notícias específicas de Google Ads (→ google)",
        ],
    },
    "mkt": {
        "name": "Marketing Digital",
        "includes": [
            "Content marketing e estratégia",
            "Email marketing",
            "Social media marketing (orgânico)",
            "SEO não-PPC",
            "Analytics e dados",
            "Branding e estratégia digital",
            "Automação de marketing",
            "Tendências e relatórios da indústria",
        ],
        "excludes": [
            "Notícias de plataformas de ads (→ meta, google, ppc)",
            "Ferramentas de IA (→ ia)",
        ],
    },
    "ia": {
        "name": "IA & Ferramentas",
        "includes": [
            "Ferramentas de IA para marketers",
            "ChatGPT, Claude, Gemini — updates relevantes para marketing",
            "Plataformas e tools de IA para marketing",
            "Automação com IA",
            "MarTech stack updates",
        ],
        "excludes": [
            "IA genérica sem relevância para marketing",
            "Features de IA específicas de plataformas de ads (→ meta, google)",
        ],
    },
}

MIN_ITEMS_PER_CATEGORY = 10
MAX_ITEMS_PER_CATEGORY = 15

# ── Accordion item ─────────────────────────────────────────────────────────────
def acc_item_html(item, week_id, idx, cat_id, cat_color_var):
    title   = html.escape(str(item.get("title", "")), quote=False)
    source  = html.escape(str(item.get("source", "")), quote=False)
    date    = html.escape(str(item.get("date", "")), quote=False)
    url     = html.escape(str(item.get("url", "#")), quote=True)
    summary = html.escape(str(item.get("summary", "")), quote=False)
    week_id = html.escape(monday_week_id(week_id), quote=True)
    num     = str(idx).zfill(2)
    summary_id = f"summary-{cat_id}-{week_id}-{idx}"
    return f"""      <div class="acc-item" data-week="{week_id}">
        <div class="acc-header">
          <button class="acc-trigger" type="button" aria-expanded="false" aria-controls="{summary_id}">
            <span class="acc-num">{num}</span>
            <span class="acc-info">
              <span class="acc-title">{title}</span>
              <span class="acc-meta">
                <span class="source-dot" style="color:{cat_color_var}"></span>
                <span class="source-tag">{source}</span>
                <span class="acc-date">· {date}</span>
              </span>
            </span>
            <span class="acc-chevron">{SVG_CHEVRON}</span>
          </button>
          <div class="acc-actions">
            <a class="btn-link" href="{url}" target="_blank" rel="noopener">{SVG_EXTERNAL} Acessar</a>
            <button class="btn-copy" type="button" aria-label="Copiar resumo">
              <span class="icon-copy">{SVG_COPY}</span>
              <span class="icon-check">{SVG_CHECK}</span>
            </button>
          </div>
        </div>
        <div class="acc-body" id="{summary_id}" hidden>
          <div class="acc-body-inner"><p>{summary}</p></div>
        </div>
      </div>"""

# ── Build HTML ────────────────────────────────────────────────────────────────
def _build_html(data, logo_b64):
    weeks = data.get("weeks", [])
    next_update  = next_monday_label()

    category_bg_css = "\n    ".join(
        f'#bg-{cat_id} {{ background-image: radial-gradient(ellipse 2400px 1800px at 50% 38%, rgba({rgb},{a1}) 0%, rgba({rgb},{a2}) 42%, transparent 65%), radial-gradient(ellipse 1200px 900px at {aux_pos}, rgba({rgb},{a3}) 0%, transparent 55%); }}'
        for cat_id, _, _, rgb, a1, a2, a3, aux_pos in CATEGORIES
    )
    category_tab_css = "\n    ".join(
        f'.tab-btn[data-tab="{cat_id}"].active {{ background: rgba({rgb},.15); border-color: rgba({rgb},.34); color: {cat_color}; }}'
        for cat_id, _, cat_color, rgb, *_ in CATEGORIES
    )
    category_border_css = "\n    ".join(
        f'[data-panel="{cat_id}"] {{ --cat-rgb: {rgb}; }}'
        for cat_id, _, _, rgb, *_ in CATEGORIES
    )
    tabs_html = "\n  ".join(
        f'<button class="tab-btn{" active" if i == 0 else ""}" id="tab-{cat_id}" role="tab" '
        f'aria-selected="{"true" if i == 0 else "false"}" aria-controls="panel-{cat_id}" '
        f'tabindex="{0 if i == 0 else -1}" data-tab="{cat_id}"><span class="tab-dot"></span>{cat_name}</button>'
        for i, (cat_id, cat_name, *_rest) in enumerate(CATEGORIES)
    )
    bg_layers_html = "\n".join(
        f'<div class="bg-cat{" active" if i == 0 else ""}" id="bg-{cat_id}"></div>'
        for i, (cat_id, *_rest) in enumerate(CATEGORIES)
    )

    first_week_id = weeks[0].get("id", "") if weeks else ""

    panels_html = ""
    for cat_id, cat_name, cat_color, *_ in CATEGORIES:
        active_cls  = " active" if cat_id == "meta" else ""
        hidden_attr = "" if cat_id == "meta" else " hidden"
        items_html  = ""
        total_count = 0
        first_week_count = 0
        for week in weeks:
            week_id = week.get("id", "")
            for item in week.get("items", {}).get(cat_id, []):
                total_count += 1
                if week_id == first_week_id:
                    first_week_count += 1
                items_html += acc_item_html(item, week_id, total_count, cat_id, cat_color) + "\n"
        # Contagem inicial = semana mais recente (JS atualiza ao filtrar)
        init_count = first_week_count
        panels_html += f"""  <section class="tab-panel{active_cls}" id="panel-{cat_id}" data-panel="{cat_id}" role="tabpanel" aria-labelledby="tab-{cat_id}"{hidden_attr}>
    <div class="panel-header">
      <h2 class="cat-hero-title" style="color:{cat_color}">{cat_name}</h2>
      <div class="cat-hero-bottom">
        <span class="panel-count"><strong>{init_count}</strong> {('notícia' if init_count == 1 else 'notícias')} esta semana</span>
        <button class="btn-expand-all" type="button" data-panel="{cat_id}">{SVG_EXP_ALL}<span>Expandir tudo</span></button>
      </div>
    </div>
    <div class="acc-list">
{items_html}    </div>
    <div class="empty-state" hidden>
      <strong>Nenhuma notícia por aqui.</strong>
      <span>Tente outra busca ou escolha uma semana diferente.</span>
    </div>
  </section>
"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>SCOZ News — Marketing Digital</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..125,300..900&display=swap" rel="stylesheet">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%2322181C'/%3E%3Ctext x='12' y='47' font-family='Arial Black,sans-serif' font-size='42' fill='%23A5F1E6'%3ES%3C/text%3E%3C/svg%3E">
  <style>
    :root {{
      --bg:     #22181C;
      --text:   #F4F4F9;
      --muted:  #B7B0AC;
      --accent: #A5F1E6;
      --border: rgba(255,255,255,.08);
      --radius: 10px;
      --surface: #2A2226;
      --surface-strong: #33292E;
      --focus: #D7FFF9;
      --ease-out: cubic-bezier(.22,1,.36,1);
      --meta:   #0EA5E9;
      --google: #34A853;
      --ppc:    #8B5CF6;
      --mkt:    #F59E0B;
      --ia:     #EA4335;
    }}
    *,*::before,*::after {{ box-sizing:border-box; margin:0; padding:0 }}
    .sr-only {{
      position:absolute; width:1px; height:1px; padding:0; margin:-1px;
      overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0;
    }}
    .ico {{ display:block; flex-shrink:0; fill:none; stroke:currentColor; stroke-width:1.5; }}
    .ico.sw-2 {{ stroke-width:2; }}
    .ico-11 {{ width:11px; height:11px; }}
    .ico-13 {{ width:13px; height:13px; }}
    .ico-14 {{ width:14px; height:14px; }}
    .ico-16 {{ width:16px; height:16px; }}

    body {{
      background-color: var(--bg);
      color: var(--text);
      font-family: 'Archivo', -apple-system, BlinkMacSystemFont, sans-serif;
      min-height: 100vh;
      line-height: 1.6;
    }}
    button, input {{ font: inherit; }}
    :focus-visible {{ outline: 3px solid var(--focus); outline-offset: 3px; }}

    /* ── Background overlays ─────────────────────────────── */
    .bg-base, .bg-cat {{
      position: fixed; inset: 0; z-index: -1; pointer-events: none;
    }}
    .bg-base {{
      background-image:
        radial-gradient(ellipse 1600px 1200px at 82% 12%, rgba(165,241,230,.16) 0%, rgba(165,241,230,.05) 38%, transparent 60%),
        radial-gradient(ellipse 1200px 900px at 14% 88%, rgba(165,241,230,.10) 0%, transparent 60%);
    }}
    .bg-cat {{ opacity: 0; transition: opacity .3s var(--ease-out); }}
    .bg-cat.active {{ opacity: 1; }}
    {category_bg_css}

    /* ── Header ──────────────────────────────────────────── */
    header {{
      position: relative; z-index: 1;
      background: rgba(24,20,22,.34);
      border-bottom: 1px solid rgba(255,255,255,.1);
      padding: 18px 40px;
      display: flex; align-items: center; justify-content: space-between; gap: 16px;
    }}
    .header-left {{ display: flex; align-items: center; gap: 18px; }}
    .header-logo img {{ display: block; height: 28px; width: auto; }}
    .header-brand-copy {{
      border-left: 1px solid rgba(255,255,255,.16); padding-left: 18px;
      color: rgba(255,255,255,.78); font-size: .78rem; font-weight: 650;
      letter-spacing: .01em; line-height: 1.3; white-space: nowrap;
    }}
    .badge {{
      background: rgba(165,241,230,.10); border: 1px solid rgba(165,241,230,.28);
      color: var(--accent); padding: 4px 14px; border-radius: 20px;
      font-size: .7rem; font-weight: 600; letter-spacing: .15px; white-space: nowrap;
    }}
    .header-meta {{ font-size: .78rem; color: var(--muted); }}
    .header-meta strong {{ color: rgba(255,255,255,.72); font-weight: 600; }}

    /* ── Tabs ─────────────────────────────────────────────── */
    .tabs-wrapper {{
      position: relative; z-index: 1;
      background: rgba(29,24,27,.40);
      border-bottom: 1px solid rgba(255,255,255,.09);
      padding: 8px 40px; display: flex; gap: 6px; overflow-x: auto;
      scrollbar-width: none; scroll-snap-type: x proximity;
    }}
    .tabs-wrapper::-webkit-scrollbar, .week-bar::-webkit-scrollbar {{ display:none; }}
    .tab-btn {{
      display: flex; align-items: center; gap: 7px; min-height: 44px; padding: 8px 16px; border-radius: 8px;
      background: transparent; border: 1px solid transparent;
      color: var(--muted); font-size: .82rem; font-weight: 620;
      cursor: pointer; white-space: nowrap; scroll-snap-align:start;
      transition: color .18s var(--ease-out), background .18s var(--ease-out), border-color .18s var(--ease-out);
    }}
    .tab-dot {{ width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: .3; flex-shrink: 0; transition: opacity .18s; }}
    .tab-btn:hover {{ color: var(--text); border-color: rgba(255,255,255,.1); }}
    .tab-btn.active .tab-dot {{ opacity: 1; }}
    {category_tab_css}

    /* ── Week bar ─────────────────────────────────────────── */
    .week-bar {{
      position: relative; z-index: 1;
      background: rgba(37,30,34,.46);
      border-bottom: 1px solid rgba(255,255,255,.08);
      padding: 8px 40px; display: grid; grid-template-columns: auto minmax(0,1fr) minmax(240px,340px);
      align-items: center; gap: 12px; overflow: hidden;
    }}
    .week-label {{ font-size: .78rem; font-weight: 700; color: var(--muted); flex-shrink: 0; }}
    .week-pills {{ display: flex; gap: 5px; min-width:0; overflow-x:auto; scrollbar-width:none; scroll-snap-type:x proximity; }}
    .week-pills::-webkit-scrollbar {{ display:none; }}
    .week-pill {{
      min-height: 44px; font-size: .78rem; font-weight: 600; padding: 6px 12px; border-radius: 7px;
      border: 1px solid rgba(255,255,255,.07); background: transparent; color: var(--muted);
      cursor: pointer; transition: color .15s var(--ease-out), background .15s var(--ease-out), border-color .15s var(--ease-out);
      white-space: nowrap; scroll-snap-align:start;
    }}
    .week-pill:hover {{ color: var(--text); border-color: rgba(255,255,255,.16); }}
    .week-pill.active {{ background: rgba(165,241,230,.10); border-color: rgba(165,241,230,.28); color: var(--accent); }}

    /* ── Search bar ───────────────────────────────────────── */
    .search-bar {{
      display: flex; align-items: center; gap: 10px;
      min-height: 44px; margin-bottom: 0; padding: 2px 8px 2px 12px;
      background: rgba(42,34,38,.82); border: 1px solid rgba(255,255,255,.14);
      border-radius: 8px; transition: border-color .2s var(--ease-out);
    }}
    .search-bar:focus-within {{ border-color: rgba(255,255,255,.2); }}
    .search-icon {{ color: var(--muted); flex-shrink: 0; display: flex; }}
    #news-search {{
      flex: 1; background: none; border: none; outline: none;
      min-height: 38px; color: var(--text); font-size: .84rem; min-width: 0;
    }}
    #news-search::placeholder {{ color: var(--muted); }}
    .search-count {{ font-size: .72rem; font-weight: 500; color: var(--muted); white-space: nowrap; flex-shrink: 0; }}
    .search-clear {{
      background: none; border: none; color: var(--muted); cursor: pointer;
      width: 44px; height: 44px; padding: 0; display: flex; align-items: center; justify-content:center;
      transition: color .15s var(--ease-out); flex-shrink: 0;
    }}
    .search-clear:hover {{ color: var(--text); }}
    [hidden] {{ display: none !important; }}

    /* ── Main ────────────────────────────────────────────── */
    main {{ max-width: 1100px; margin: 0 auto; padding: 0 40px 80px; }}
    .tab-panel {{ display: none; }}
    .tab-panel.active {{ display: block; }}

    /* ── Panel hero header ───────────────────────────────── */
    .panel-header {{ padding: 52px 0 28px; border-bottom: 1px solid rgba(255,255,255,.07); margin-bottom: 8px; }}
    .cat-hero-title {{ font-size: clamp(2.5rem, 5vw, 3.8rem); font-weight: 850; font-stretch: 82%; letter-spacing: -.035em; line-height: 1; margin-bottom: 18px; text-wrap:balance; }}
    .cat-hero-bottom {{ display: flex; align-items: center; gap: 14px; }}
    .panel-count {{ font-size: .85rem; color: rgba(255,255,255,.55); }}
    .panel-count strong {{ font-weight: 700; color: var(--text); font-size: 1rem; }}
    .btn-expand-all {{
      display: flex; align-items: center; gap: 5px;
      background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.12);
      min-height: 44px; color: var(--muted); font-size: .78rem; font-weight: 600;
      padding: 7px 13px; border-radius: 7px; cursor: pointer; transition: all .15s var(--ease-out); margin-left: auto;
    }}
    .btn-expand-all:hover {{ color: var(--text); border-color: rgba(255,255,255,.22); background: rgba(255,255,255,.08); }}

    /* ── Accordion ───────────────────────────────────────── */
    .acc-list {{ display: flex; flex-direction: column; gap: 0; padding-top: 4px; }}
    .acc-item {{
      background: transparent; border: 0; border-bottom: 1px solid rgba(255,255,255,.1);
      border-radius: 0; overflow: hidden; content-visibility: auto; contain-intrinsic-size: 78px;
      transition: background .2s var(--ease-out), border-color .2s var(--ease-out);
    }}
    .acc-list > .acc-item:first-of-type {{ border-top: 1px solid rgba(255,255,255,.1); }}
    .acc-item:hover {{ background: rgba(var(--cat-rgb),.045); border-color: rgba(255,255,255,.16); }}
    .acc-item.open {{
      background: rgba(var(--cat-rgb),.075);
      border-color: rgba(var(--cat-rgb),.42);
    }}
    {category_border_css}

    .acc-header {{ display: flex; align-items: center; gap: 12px; padding: 8px 8px 8px 0; user-select: none; }}
    .acc-trigger {{
      flex:1; min-width:0; display:flex; align-items:center; gap:16px; min-height:56px;
      padding:8px; border:0; border-radius:6px; background:transparent; color:inherit;
      text-align:left; cursor:pointer;
    }}
    .acc-num {{ font-size: .75rem; font-weight: 760; color: rgba(var(--cat-rgb),.92); letter-spacing: .04em; flex-shrink: 0; width: 24px; text-align: right; transition: color .15s; }}
    .acc-item.open .acc-num, .acc-trigger:hover .acc-num {{ color: var(--text); }}
    .acc-info {{ flex: 1; min-width: 0; }}
    .acc-title {{ font-size: .96rem; font-weight: 650; color: var(--text); line-height: 1.42; display: block; margin-bottom: 6px; letter-spacing: -.012em; text-wrap:pretty; transition: color .15s; }}
    .acc-trigger:hover .acc-title {{ color: #fff; }}
    .acc-meta {{ display: flex; align-items: center; gap: 7px; flex-wrap: wrap; }}
    .source-dot {{ width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; background: currentColor; opacity: .6; }}
    .source-tag {{ font-size: .75rem; font-weight: 650; color: rgba(255,255,255,.7); white-space: nowrap; }}
    .acc-date {{ font-size: .75rem; color: rgba(255,255,255,.58); }}
    .acc-actions {{ display: flex; align-items: center; gap: 6px; flex-shrink: 0; }}
    .btn-link {{
      display: flex; align-items: center; gap: 5px;
      min-height:44px; font-size: .78rem; font-weight: 620; padding: 7px 12px; border-radius: 6px;
      text-decoration: none; white-space: nowrap;
      border: 1px solid rgba(255,255,255,.18); color: rgba(255,255,255,.65);
      background: rgba(255,255,255,.05); transition: all .15s; font-family: inherit;
    }}
    .btn-link:hover {{ color: var(--accent); border-color: rgba(165,241,230,.45); background: rgba(165,241,230,.08); }}
    .btn-copy {{
      display: flex; align-items: center; justify-content: center;
      width:44px; min-height:44px; padding: 0; border-radius: 6px; border: 1px solid rgba(255,255,255,.18);
      color: rgba(255,255,255,.55); background: rgba(255,255,255,.05); cursor: pointer; transition: all .15s;
    }}
    .btn-copy:hover {{ color: var(--text); border-color: rgba(255,255,255,.28); background: rgba(255,255,255,.08); }}
    .btn-copy.copied {{ color: #22C55E; border-color: rgba(34,197,94,.3); }}
    .btn-copy.copy-error {{ color: #FFB4AB; border-color: rgba(255,180,171,.45); }}
    .btn-copy .icon-copy {{ display: flex; }}
    .btn-copy .icon-check {{ display: none; }}
    .btn-copy.copied .icon-copy {{ display: none; }}
    .btn-copy.copied .icon-check {{ display: flex; }}
    .acc-chevron {{ color: var(--muted); transition: transform .2s var(--ease-out), color .15s; flex-shrink: 0; display: flex; align-items: center; }}
    .acc-item.open .acc-chevron {{ transform: rotate(180deg); color: rgba(255,255,255,.55); }}
    .acc-body {{ overflow: hidden; }}
    .acc-body-inner {{ padding: 0 18px 18px 56px; border-top: 1px solid rgba(255,255,255,.06); }}
    .acc-body-inner p {{ max-width:72ch; font-size: .92rem; color: #C6C0BD; line-height: 1.75; padding-top: 16px; text-wrap:pretty; }}
    .week-divider {{
      padding:28px 8px 10px; color:rgba(255,255,255,.72); font-size:.86rem; font-weight:720;
      border-bottom:1px solid rgba(255,255,255,.16);
    }}
    .empty-state {{
      margin-top:20px; padding:28px; border:1px dashed rgba(255,255,255,.2); border-radius:8px;
      color:var(--muted); text-align:center;
    }}
    .empty-state strong, .empty-state span {{ display:block; }}
    .empty-state strong {{ color:var(--text); margin-bottom:4px; }}

    /* ── Footer ──────────────────────────────────────────── */
    footer {{
      border-top: 1px solid rgba(255,255,255,.06);
      padding: 22px 40px; display: flex; align-items: center; justify-content: center; gap: 16px; flex-wrap: wrap;
    }}
    .footer-text {{ font-size: .7rem; color: var(--muted); text-align: center; }}
    .footer-text strong {{ color: var(--accent); font-weight: 600; }}
    .footer-logo {{ opacity: .3; }}
    .footer-logo img {{ display: block; height: 16px; width: auto; }}

    /* ── Responsive ──────────────────────────────────────── */
    @media (max-width: 640px) {{
      header, .tabs-wrapper, .week-bar, main, footer {{ padding-left: 16px; padding-right: 16px; }}
      header {{ padding-top:16px; padding-bottom:16px; }}
      .tab-btn, .week-pill {{ min-height:44px; font-size:.875rem; }}
      .cat-hero-title {{ font-size: 2.2rem; }}
      .header-left {{ gap: 12px; min-width: 0; }}
      .header-brand-copy {{
        padding-left: 12px; max-width: 190px; white-space: normal;
        font-size: .875rem; line-height: 1.25;
      }}
      .header-meta {{ display: none; }}
      .week-bar {{ grid-template-columns:1fr; gap:8px; padding-top:8px; padding-bottom:10px; }}
      .week-label {{ display:none; }}
      .search-bar {{ grid-row:1; width:100%; }}
      .week-pills {{ grid-row:2; width:100%; }}
      .panel-header {{ padding-top:34px; }}
      .acc-header {{ display:grid; grid-template-columns:1fr; gap:10px; padding:10px 0 14px; }}
      .acc-trigger {{ width:100%; align-items:flex-start; gap:12px; min-height:0; padding:8px 4px; }}
      .acc-title {{ font-size:1rem; line-height:1.42; }}
      .source-tag, .acc-date {{ font-size:.875rem; }}
      .acc-actions {{ margin-left:40px; gap:8px; }}
      .btn-link, .btn-copy, .btn-expand-all, .search-clear {{ min-height:44px; }}
      .btn-copy {{ width:44px; }}
      .acc-body-inner {{ padding: 0 8px 20px 40px; }}
      .acc-body-inner p {{ font-size:.96rem; line-height:1.7; }}
      .search-count {{ font-size:.78rem; }}
      .week-divider {{ padding-top:24px; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      *,*::before,*::after {{ scroll-behavior:auto !important; transition-duration:.01ms !important; animation-duration:.01ms !important; animation-iteration-count:1 !important; }}
    }}
  </style>
</head>
<body>

{SVG_SPRITE}

<div class="bg-base"></div>
{bg_layers_html}

<header>
  <div class="header-left">
    <div class="header-logo"><img src="{logo_b64}" alt="SCOZ"/></div>
    <h1 class="sr-only">SCOZ News</h1>
    <div class="header-brand-copy">News - O boletim semanal da preguiça</div>
  </div>
  <div class="header-meta">Próxima atualização: <strong>{next_update}</strong></div>
</header>

<div class="tabs-wrapper" id="tabs" role="tablist" aria-label="Categorias de notícias">
  {tabs_html}
</div>

<div class="week-bar">
  <span class="week-label">Semana</span>
  <div class="week-pills" id="week-pills"></div>
  <div class="search-bar">
    <span class="search-icon">{SVG_SEARCH}</span>
    <label class="sr-only" for="news-search">Buscar notícias na categoria atual</label>
    <input type="search" id="news-search" placeholder="Buscar nesta categoria..." autocomplete="off" spellcheck="false">
    <span class="search-count" id="search-count" role="status" aria-live="polite" hidden></span>
    <button class="search-clear" id="search-clear" type="button" aria-label="Limpar busca" hidden>{SVG_XMARK}</button>
  </div>
</div>

<main>

{panels_html}</main>

<footer>
  <div class="footer-text">
    SCOZ News &nbsp;&bull;&nbsp; Atualizado semanalmente &nbsp;&bull;&nbsp;
    Próxima edição: <strong>{next_update}</strong>
  </div>
  <div class="footer-logo" aria-hidden="true"><img src="{logo_b64}" alt=""/></div>
</footer>

<script>
  const allItems = [...document.querySelectorAll('.acc-item')];
  const tabPanels = [...document.querySelectorAll('.tab-panel')];
  const panelItems = new Map(tabPanels.map(panel => [panel, [...panel.querySelectorAll('.acc-item')]]));
  const searchIndex = new WeakMap();
  allItems.forEach(item => {{
    const title = item.querySelector('.acc-title')?.textContent || '';
    const summary = item.querySelector('.acc-body-inner p')?.textContent || '';
    searchIndex.set(item, (title + ' ' + summary).toLowerCase());
  }});

  function setItemOpen(item, open) {{
    item.classList.toggle('open', open);
    const trigger = item.querySelector('.acc-trigger');
    const body = item.querySelector('.acc-body');
    if (trigger) trigger.setAttribute('aria-expanded', String(open));
    if (body) body.hidden = !open;
  }}
  function closeAll(items = allItems) {{ items.forEach(item => setItemOpen(item, false)); }}

  const tabsEl = document.getElementById('tabs');
  const tabButtons = [...document.querySelectorAll('.tab-btn')];
  function activateTab(btn, focus = false) {{
    tabButtons.forEach(b => {{
      const active = b === btn;
      b.classList.toggle('active', active);
      b.setAttribute('aria-selected', String(active));
      b.tabIndex = active ? 0 : -1;
    }});
    tabPanels.forEach(panel => {{
      const active = panel.id === 'panel-' + btn.dataset.tab;
      panel.classList.toggle('active', active);
      panel.hidden = !active;
    }});
    document.querySelectorAll('.bg-cat').forEach(bg => bg.classList.remove('active'));
    document.getElementById('bg-' + btn.dataset.tab)?.classList.add('active');
    applyFilters();
    if (focus) btn.focus();
  }}
  if (tabsEl) {{
    tabsEl.addEventListener('click', e => {{
      const btn = e.target.closest('.tab-btn');
      if (btn) activateTab(btn);
    }});
    tabsEl.addEventListener('keydown', e => {{
      const current = e.target.closest('.tab-btn');
      if (!current) return;
      const index = tabButtons.indexOf(current);
      let next = null;
      if (e.key === 'ArrowRight') next = tabButtons[(index + 1) % tabButtons.length];
      if (e.key === 'ArrowLeft') next = tabButtons[(index - 1 + tabButtons.length) % tabButtons.length];
      if (e.key === 'Home') next = tabButtons[0];
      if (e.key === 'End') next = tabButtons[tabButtons.length - 1];
      if (next) {{ e.preventDefault(); activateTab(next, true); }}
    }});
  }}

  const months = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
  function pad2(n) {{ return String(n).padStart(2, '0'); }}
  function isoDate(d) {{ return `${{d.getFullYear()}}-${{pad2(d.getMonth() + 1)}}-${{pad2(d.getDate())}}`; }}
  function mondayFromDate(d) {{
    const start = new Date(d);
    start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
    return isoDate(start);
  }}
  function normalizeWeekId(id) {{
    const date = new Date(id + 'T12:00:00');
    return Number.isNaN(date.getTime()) ? id : mondayFromDate(date);
  }}
  function fmtWeek(id) {{
    const d = new Date(normalizeWeekId(id) + 'T12:00:00'), e = new Date(d);
    e.setDate(e.getDate() + 6);
    return d.getMonth() === e.getMonth()
      ? `${{pad2(d.getDate())}}-${{pad2(e.getDate())}}/${{months[d.getMonth()]}}`
      : `${{pad2(d.getDate())}}/${{months[d.getMonth()]}}-${{pad2(e.getDate())}}/${{months[e.getMonth()]}}`;
  }}

  const allWeeks = [...new Set(allItems.map(item => normalizeWeekId(item.dataset.week)))].sort().reverse();
  let currentWeek = allWeeks[0] || 'all';
  const pillsEl = document.getElementById('week-pills');
  allWeeks.slice(0, 4).forEach((week, index) => {{
    const pill = document.createElement('button');
    pill.type = 'button'; pill.className = 'week-pill' + (index === 0 ? ' active' : '');
    pill.dataset.week = week; pill.textContent = fmtWeek(week);
    pill.setAttribute('aria-pressed', String(index === 0));
    pillsEl.appendChild(pill);
  }});
  const archivePill = document.createElement('button');
  archivePill.type = 'button'; archivePill.className = 'week-pill'; archivePill.dataset.week = 'all';
  archivePill.textContent = 'Arquivo'; archivePill.setAttribute('aria-pressed', 'false');
  pillsEl.appendChild(archivePill);
  pillsEl.addEventListener('click', e => {{
    const pill = e.target.closest('.week-pill');
    if (pill) {{ currentWeek = pill.dataset.week; applyFilters(); }}
  }});

  const panelWeekDividers = new Map();
  tabPanels.forEach(panel => {{
    const dividers = new Map();
    let previousWeek = '';
    (panelItems.get(panel) || []).forEach(item => {{
      const week = normalizeWeekId(item.dataset.week);
      if (week !== previousWeek) {{
        const marker = document.createElement('div');
        marker.className = 'week-divider'; marker.dataset.week = week;
        marker.textContent = 'Semana ' + fmtWeek(week); marker.hidden = true;
        item.before(marker); dividers.set(week, marker); previousWeek = week;
      }}
    }});
    panelWeekDividers.set(panel, dividers);
  }});

  let currentSearch = '';
  let searchTimer = 0;
  function getVisible(item) {{
    const weekOk = currentWeek === 'all' || normalizeWeekId(item.dataset.week) === currentWeek;
    return weekOk && (!currentSearch || (searchIndex.get(item) || '').includes(currentSearch));
  }}
  function applyFilters() {{
    closeAll();
    const activePanel = document.querySelector('.tab-panel.active');
    let activeCount = 0;
    tabPanels.forEach(panel => {{
      let count = 0;
      const byWeek = new Map();
      (panelItems.get(panel) || []).forEach(item => {{
        const show = getVisible(item);
        item.style.display = show ? '' : 'none';
        if (show) {{
          count++;
          const week = normalizeWeekId(item.dataset.week);
          byWeek.set(week, (byWeek.get(week) || 0) + 1);
        }}
      }});
      if (panel === activePanel) activeCount = count;
      (panelWeekDividers.get(panel) || new Map()).forEach((marker, week) => {{
        marker.hidden = currentWeek !== 'all' || !(byWeek.get(week) > 0);
      }});
      const countEl = panel.querySelector('.panel-count');
      const label = currentSearch ? 'encontrada' + (count === 1 ? '' : 's') : (currentWeek === 'all' ? 'no arquivo' : 'esta semana');
      if (countEl) countEl.innerHTML = `<strong>${{count}}</strong> ${{count === 1 ? 'notícia' : 'notícias'}} ${{label}}`;
      const expandButton = panel.querySelector('.btn-expand-all');
      if (expandButton) {{
        expandButton.disabled = count === 0;
        expandButton.querySelector('span').textContent = 'Expandir tudo';
      }}
      const empty = panel.querySelector('.empty-state');
      if (empty) empty.hidden = panel !== activePanel || count > 0;
    }});
    document.querySelectorAll('.week-pill').forEach(pill => {{
      const active = pill.dataset.week === currentWeek;
      pill.classList.toggle('active', active); pill.setAttribute('aria-pressed', String(active));
    }});
    const countEl = document.getElementById('search-count');
    const clearEl = document.getElementById('search-clear');
    const searchInput = document.getElementById('news-search');
    const activeTitle = activePanel?.querySelector('.cat-hero-title')?.textContent || 'esta categoria';
    if (searchInput) searchInput.placeholder = 'Buscar em ' + activeTitle + '...';
    if (currentSearch) {{
      if (countEl) {{ countEl.textContent = activeCount + ' resultado' + (activeCount !== 1 ? 's' : ''); countEl.hidden = false; }}
      if (clearEl) clearEl.hidden = false;
    }} else {{
      if (countEl) countEl.hidden = true;
      if (clearEl) clearEl.hidden = true;
    }}
  }}
  function scheduleFilters() {{ clearTimeout(searchTimer); searchTimer = setTimeout(applyFilters, 100); }}
  const searchInput = document.getElementById('news-search');
  const searchClear = document.getElementById('search-clear');
  searchInput?.addEventListener('input', () => {{ currentSearch = searchInput.value.trim().toLowerCase(); scheduleFilters(); }});
  searchClear?.addEventListener('click', () => {{
    clearTimeout(searchTimer); searchInput.value = ''; currentSearch = ''; applyFilters(); searchInput.focus();
  }});

  function legacyCopy(text) {{
    const area = document.createElement('textarea');
    area.value = text; area.setAttribute('readonly', ''); area.style.position = 'fixed'; area.style.opacity = '0';
    document.body.appendChild(area); area.select();
    const ok = document.execCommand('copy'); area.remove();
    if (!ok) throw new Error('copy failed');
  }}
  async function copyText(text) {{
    if (navigator.clipboard?.writeText) return navigator.clipboard.writeText(text);
    legacyCopy(text);
  }}

  document.addEventListener('click', e => {{
    const copyBtn = e.target.closest('.btn-copy');
    if (copyBtn) {{
      const item = copyBtn.closest('.acc-item');
      const title = item.querySelector('.acc-title')?.textContent.trim() || '';
      const summary = item.querySelector('.acc-body-inner p')?.textContent.trim() || '';
      const source = item.querySelector('.source-tag')?.textContent.trim() || '';
      const url = item.querySelector('.btn-link')?.href || '';
      const text = title + '\\n\\n' + summary + '\\n\\nFonte: ' + source + ' — ' + url;
      copyText(text).then(() => {{
        copyBtn.classList.add('copied'); copyBtn.setAttribute('aria-label', 'Resumo copiado');
        setTimeout(() => {{ copyBtn.classList.remove('copied'); copyBtn.setAttribute('aria-label', 'Copiar resumo'); }}, 2000);
      }}).catch(() => {{
        copyBtn.classList.add('copy-error'); copyBtn.setAttribute('aria-label', 'Não foi possível copiar');
        setTimeout(() => {{ copyBtn.classList.remove('copy-error'); copyBtn.setAttribute('aria-label', 'Copiar resumo'); }}, 2500);
      }});
      return;
    }}

    const expandBtn = e.target.closest('.btn-expand-all');
    if (expandBtn) {{
      const panel = document.getElementById('panel-' + expandBtn.dataset.panel);
      const items = (panelItems.get(panel) || []).filter(item => item.style.display !== 'none');
      const allOpen = items.length > 0 && items.every(item => item.classList.contains('open'));
      items.forEach(item => setItemOpen(item, !allOpen));
      expandBtn.querySelector('span').textContent = allOpen ? 'Expandir tudo' : 'Recolher tudo';
      return;
    }}

    const trigger = e.target.closest('.acc-trigger');
    if (!trigger) return;
    const item = trigger.closest('.acc-item');
    const isOpen = item.classList.contains('open');
    (panelItems.get(item.closest('.tab-panel')) || []).forEach(other => setItemOpen(other, false));
    if (!isOpen) setItemOpen(item, true);
  }});

  applyFilters();
</script>
</body>
</html>"""

def _build_cache(data):
    weeks = data.get("weeks", [])
    seen_urls = set()
    seen_titles = set()
    for week in weeks:
        items = week.get("items", {})
        for cat_id, *_ in CATEGORIES:
            for item in items.get(cat_id, []):
                url = str(item.get("url", "")).strip()
                title = str(item.get("title", "")).strip()
                if url:
                    seen_urls.add(url)
                if title:
                    seen_titles.add(title)
    return {
        "last_week_id": weeks[0].get("id", "") if weeks else "",
        "seen_urls": sorted(seen_urls),
        "seen_titles": sorted(seen_titles),
    }


def prepare_publication(data: dict) -> Publication:
    """Render HTML and cache from one validated archive snapshot."""
    return Publication(
        html=_build_html(data, make_logo_b64()),
        cache=_build_cache(data),
    )

def _publish_outputs(html_path, html_out, cache_path, cache):
    """Stage both outputs and roll back cache if the HTML commit fails."""
    cache_out = json.dumps(cache, ensure_ascii=False, indent=2)
    cache_destination = Path(cache_path)
    html_destination = Path(html_path)
    staged = []
    cache_backup = None
    cache_existed = cache_destination.exists()
    try:
        for destination, content in (
            (cache_destination, cache_out),
            (html_destination, html_out),
        ):
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=destination.parent,
                prefix=f".{destination.name}.",
                delete=False,
            ) as temporary:
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())
                staged.append((Path(temporary.name), destination))

        if cache_existed:
            with tempfile.NamedTemporaryFile(
                "wb",
                dir=cache_destination.parent,
                prefix=f".{cache_destination.name}.backup.",
                delete=False,
            ) as temporary:
                cache_backup = Path(temporary.name)
                temporary.write(cache_destination.read_bytes())
                temporary.flush()
                os.fsync(temporary.fileno())

        cache_temporary, _ = staged[0]
        html_temporary, _ = staged[1]
        try:
            os.replace(cache_temporary, cache_destination)
            os.replace(html_temporary, html_destination)
        except BaseException:
            if cache_backup is not None:
                os.replace(cache_backup, cache_destination)
                cache_backup = None
            elif not cache_existed:
                cache_destination.unlink(missing_ok=True)
            raise
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
        if cache_backup is not None:
            cache_backup.unlink(missing_ok=True)


def print_guidelines():
    """Imprime guidelines de categorias para referência durante curadoria."""
    for cat_id, info in CATEGORY_GUIDELINES.items():
        print(f"\n{'=' * 60}")
        print(f"  {info['name']}  (id: {cat_id})")
        print(f"{'=' * 60}")
        print("  ✅ INCLUIR:")
        for item in info["includes"]:
            print(f"     • {item}")
        print("  ❌ EXCLUIR:")
        for item in info["excludes"]:
            print(f"     • {item}")
    print(f"\n  Itens por categoria: {MIN_ITEMS_PER_CATEGORY}–{MAX_ITEMS_PER_CATEGORY} (alvo: 10)")
