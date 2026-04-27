#!/usr/bin/env python3
"""
SCOZ News — Build HTML from noticias-data.json
Design: HAZE (glassmorphism + category-reactive background)
Executar: python3 build_html.py
"""
import json, os, io, base64
from datetime import datetime, timedelta

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "noticias-data.json")
HTML_PATH = os.path.join(BASE_DIR, "noticias-semana.html")

# ── Logo ──────────────────────────────────────────────────────────────────────
def make_logo_b64():
    """Tenta PIL; cai em SVG inline branco."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        font_path = "/usr/share/fonts/truetype/lato/Lato-Black.ttf"
        font = ImageFont.truetype(font_path, 120)
        dummy = Image.new("RGBA", (1, 1))
        draw  = ImageDraw.Draw(dummy)
        bbox  = draw.textbbox((0, 0), "SCOZ", font=font)
        w, h  = bbox[2] - bbox[0] + 20, bbox[3] - bbox[1] + 20
        img   = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw  = ImageDraw.Draw(img)
        draw.text((10, 10 - bbox[1]), "SCOZ", font=font, fill=(255, 255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="90" height="30">'
               '<text y="24" font-family="Arial Black,sans-serif" font-size="26" '
               'font-weight="900" fill="white">SCOZ</text></svg>')
        return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

# ── Helpers ───────────────────────────────────────────────────────────────────
def next_monday_label(from_date=None):
    base = from_date or datetime.today()
    days_ahead = 7 - base.weekday() if base.weekday() != 0 else 7
    nxt = base + timedelta(days=days_ahead)
    months_pt = ["janeiro","fevereiro","março","abril","maio","junho",
                 "julho","agosto","setembro","outubro","novembro","dezembro"]
    return f"{nxt.day} de {months_pt[nxt.month-1]} de {nxt.year}"

# ── SVG icons ─────────────────────────────────────────────────────────────────
SVG_EXTERNAL = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="11" height="11"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"/></svg>'
SVG_COPY     = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="13" height="13"><path stroke-linecap="round" stroke-linejoin="round" d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184"/></svg>'
SVG_CHECK    = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" width="13" height="13"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5"/></svg>'
SVG_SEARCH   = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="16" height="16"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"/></svg>'
SVG_XMARK    = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" width="14" height="14"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12"/></svg>'
SVG_CHEVRON  = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" width="14" height="14"><path stroke-linecap="round" stroke-linejoin="round" d="m19 9-7 7-7-7"/></svg>'
SVG_EXP_ALL  = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="11" height="11"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 5.25 7.5 7.5 7.5-7.5m-15 6 7.5 7.5 7.5-7.5"/></svg>'

# ── Category config ───────────────────────────────────────────────────────────
CATEGORIES = [
    ("meta",   "Meta Ads",             "var(--meta)"),
    ("google", "Google Ads",           "var(--google)"),
    ("ppc",    "Tráfego Pago",         "var(--ppc)"),
    ("mkt",    "Marketing Digital",    "var(--mkt)"),
    ("ia",     "IA &amp; Ferramentas", "var(--ia)"),
]

# ── Accordion item ─────────────────────────────────────────────────────────────
def acc_item_html(item, week_id, idx, cat_color_var):
    title   = item.get("title", "")
    source  = item.get("source", "")
    date    = item.get("date", "")
    url     = item.get("url", "#")
    summary = item.get("summary", "")
    num     = str(idx).zfill(2)
    return f"""      <div class="acc-item" data-week="{week_id}">
        <div class="acc-header">
          <span class="acc-num">{num}</span>
          <div class="acc-info">
            <span class="acc-title">{title}</span>
            <div class="acc-meta">
              <span class="source-dot" style="color:{cat_color_var}"></span>
              <span class="source-tag">{source}</span>
              <span class="acc-date">· {date}</span>
            </div>
          </div>
          <div class="acc-actions">
            <a class="btn-link" href="{url}" target="_blank" rel="noopener">{SVG_EXTERNAL} Acessar</a>
            <button class="btn-copy" aria-label="Copiar resumo">
              <span class="icon-copy">{SVG_COPY}</span>
              <span class="icon-check">{SVG_CHECK}</span>
            </button>
          </div>
          <span class="acc-chevron">{SVG_CHEVRON}</span>
        </div>
        <div class="acc-body"><div class="acc-body-inner"><p>{summary}</p></div></div>
      </div>"""

# ── Build HTML ────────────────────────────────────────────────────────────────
def build_html(data, logo_b64):
    weeks = data.get("weeks", [])
    latest_label = weeks[0].get("label_full", "") if weeks else ""
    badge_text   = f"&#9889; {latest_label}" if latest_label else "&#9889; Sem dados"
    next_update  = next_monday_label()

    panels_html = ""
    for cat_id, cat_name, cat_color in CATEGORIES:
        active_cls  = " active" if cat_id == "meta" else ""
        items_html  = ""
        total_count = 0
        for week in weeks:
            week_id = week.get("id", "")
            for item in week.get("items", {}).get(cat_id, []):
                total_count += 1
                items_html += acc_item_html(item, week_id, total_count, cat_color) + "\n"
        count_label = f"{total_count} {'notícia' if total_count == 1 else 'notícias'}"
        panels_html += f"""  <div class="tab-panel{active_cls}" id="panel-{cat_id}" data-panel="{cat_id}">
    <div class="panel-header">
      <div class="cat-hero-label">Categoria</div>
      <h2 class="cat-hero-title" style="color:{cat_color}">{cat_name}</h2>
      <div class="cat-hero-bottom">
        <span class="panel-count"><strong>{total_count}</strong> {('notícia' if total_count == 1 else 'notícias')} esta semana</span>
        <button class="btn-expand-all" data-panel="{cat_id}">{SVG_EXP_ALL}<span>Expandir tudo</span></button>
      </div>
    </div>
    <div class="acc-list">
{items_html}    </div>
  </div>
"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>SCOZ News — Marketing Digital</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg:     #22181C;
      --text:   #F4F4F9;
      --muted:  #9A9590;
      --accent: #A5F1E6;
      --border: rgba(255,255,255,.08);
      --radius: 10px;
      --meta:   #0EA5E9;
      --google: #34A853;
      --ppc:    #8B5CF6;
      --mkt:    #F59E0B;
      --ia:     #EA4335;
    }}
    *,*::before,*::after {{ box-sizing:border-box; margin:0; padding:0 }}

    body {{
      background-color: var(--bg);
      color: var(--text);
      font-family: 'Inter', -apple-system, sans-serif;
      min-height: 100vh;
      line-height: 1.6;
    }}

    /* ── Background overlays ─────────────────────────────── */
    .bg-base, .bg-cat {{
      position: fixed; inset: 0; z-index: -1; pointer-events: none;
    }}
    .bg-base {{
      background-image:
        radial-gradient(ellipse 1600px 1200px at 82% 12%, rgba(165,241,230,.16) 0%, rgba(165,241,230,.05) 38%, transparent 60%),
        radial-gradient(ellipse 1200px 900px at 14% 88%, rgba(165,241,230,.10) 0%, transparent 60%);
    }}
    .bg-cat {{ opacity: 0; transition: opacity .55s ease; }}
    .bg-cat.active {{ opacity: 1; }}
    #bg-meta   {{ background-image: radial-gradient(ellipse 2400px 1800px at 50% 38%, rgba(14,165,233,.30) 0%, rgba(14,165,233,.10) 42%, transparent 65%), radial-gradient(ellipse 1200px 900px at 20% 20%, rgba(14,165,233,.13) 0%, transparent 55%); }}
    #bg-google {{ background-image: radial-gradient(ellipse 2400px 1800px at 50% 38%, rgba(52,168,83,.26) 0%, rgba(52,168,83,.08) 42%, transparent 65%), radial-gradient(ellipse 1200px 900px at 78% 22%, rgba(52,168,83,.11) 0%, transparent 55%); }}
    #bg-ppc    {{ background-image: radial-gradient(ellipse 2400px 1800px at 50% 38%, rgba(139,92,246,.28) 0%, rgba(139,92,246,.09) 42%, transparent 65%), radial-gradient(ellipse 1200px 900px at 18% 75%, rgba(139,92,246,.12) 0%, transparent 55%); }}
    #bg-mkt    {{ background-image: radial-gradient(ellipse 2400px 1800px at 50% 38%, rgba(245,158,11,.24) 0%, rgba(245,158,11,.07) 42%, transparent 65%), radial-gradient(ellipse 1200px 900px at 80% 72%, rgba(245,158,11,.10) 0%, transparent 55%); }}
    #bg-ia     {{ background-image: radial-gradient(ellipse 2400px 1800px at 50% 38%, rgba(234,67,53,.26) 0%, rgba(234,67,53,.08) 42%, transparent 65%), radial-gradient(ellipse 1200px 900px at 22% 28%, rgba(234,67,53,.11) 0%, transparent 55%); }}

    /* ── Header ──────────────────────────────────────────── */
    header {{
      position: sticky; top: 0; z-index: 50;
      background: rgba(34,24,28,.18);
      backdrop-filter: blur(56px) saturate(280%) brightness(1.06);
      -webkit-backdrop-filter: blur(56px) saturate(280%) brightness(1.06);
      border-bottom: 1px solid rgba(165,241,230,.12);
      padding: 14px 40px;
      display: flex; align-items: center; justify-content: space-between; gap: 16px;
    }}
    .header-left {{ display: flex; align-items: center; gap: 18px; }}
    .header-logo img {{ display: block; height: 28px; width: auto; }}
    .badge {{
      background: rgba(165,241,230,.10); border: 1px solid rgba(165,241,230,.28);
      color: var(--accent); padding: 4px 14px; border-radius: 20px;
      font-size: .7rem; font-weight: 600; letter-spacing: .15px; white-space: nowrap;
    }}
    .header-meta {{ font-size: .7rem; color: var(--muted); }}
    .header-meta strong {{ color: rgba(255,255,255,.42); font-weight: 500; }}

    /* ── Tabs ─────────────────────────────────────────────── */
    .tabs-wrapper {{
      position: sticky; z-index: 40;
      background: rgba(34,24,28,.26);
      backdrop-filter: blur(40px) saturate(220%);
      -webkit-backdrop-filter: blur(40px) saturate(220%);
      border-bottom: 1px solid rgba(255,255,255,.06);
      padding: 10px 40px; display: flex; gap: 5px; overflow-x: auto;
    }}
    .tab-btn {{
      display: flex; align-items: center; gap: 7px; padding: 7px 18px; border-radius: 24px;
      background: transparent; border: 1px solid transparent;
      color: var(--muted); font-size: .78rem; font-weight: 500; font-family: inherit;
      cursor: pointer; white-space: nowrap; transition: color .18s, background .18s, border-color .18s;
    }}
    .tab-dot {{ width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: .3; flex-shrink: 0; transition: opacity .18s; }}
    .tab-btn:hover {{ color: var(--text); border-color: rgba(255,255,255,.1); }}
    .tab-btn.active .tab-dot {{ opacity: 1; }}
    .tab-btn[data-tab="meta"].active   {{ background: rgba(14,165,233,.15);  border-color: rgba(14,165,233,.34);  color: #0EA5E9; }}
    .tab-btn[data-tab="google"].active {{ background: rgba(52,168,83,.15);   border-color: rgba(52,168,83,.34);   color: #34A853; }}
    .tab-btn[data-tab="ppc"].active    {{ background: rgba(139,92,246,.15);  border-color: rgba(139,92,246,.34);  color: #8B5CF6; }}
    .tab-btn[data-tab="mkt"].active    {{ background: rgba(245,158,11,.15);  border-color: rgba(245,158,11,.34);  color: #F59E0B; }}
    .tab-btn[data-tab="ia"].active     {{ background: rgba(234,67,53,.15);   border-color: rgba(234,67,53,.34);   color: #EA4335; }}

    /* ── Week bar ─────────────────────────────────────────── */
    .week-bar {{
      position: sticky; z-index: 30;
      background: rgba(34,24,28,.46);
      backdrop-filter: blur(22px); -webkit-backdrop-filter: blur(22px);
      border-bottom: 1px solid rgba(255,255,255,.05);
      padding: 8px 40px; display: flex; align-items: center; gap: 10px; overflow-x: auto;
    }}
    .week-label {{ font-size: .62rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: .7px; flex-shrink: 0; }}
    .week-pills {{ display: flex; gap: 5px; }}
    .week-pill {{
      font-size: .7rem; font-weight: 500; padding: 3px 13px; border-radius: 20px;
      border: 1px solid rgba(255,255,255,.07); background: transparent; color: var(--muted);
      cursor: pointer; font-family: inherit; transition: all .15s; white-space: nowrap;
    }}
    .week-pill:hover {{ color: var(--text); border-color: rgba(255,255,255,.16); }}
    .week-pill.active {{ background: rgba(165,241,230,.10); border-color: rgba(165,241,230,.28); color: var(--accent); }}

    /* ── Search bar ───────────────────────────────────────── */
    .search-bar {{
      display: flex; align-items: center; gap: 10px;
      margin-bottom: 0; padding: 10px 14px;
      background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.09);
      border-radius: var(--radius); transition: border-color .2s;
    }}
    .search-bar:focus-within {{ border-color: rgba(255,255,255,.2); }}
    .search-icon {{ color: var(--muted); flex-shrink: 0; display: flex; }}
    #news-search {{
      flex: 1; background: none; border: none; outline: none;
      color: var(--text); font-size: .875rem; font-family: inherit; min-width: 0;
    }}
    #news-search::placeholder {{ color: var(--muted); }}
    .search-count {{ font-size: .72rem; font-weight: 500; color: var(--muted); white-space: nowrap; flex-shrink: 0; }}
    .search-clear {{
      background: none; border: none; color: var(--muted); cursor: pointer;
      padding: 2px; display: flex; align-items: center; transition: color .15s; flex-shrink: 0;
    }}
    .search-clear:hover {{ color: var(--text); }}
    [hidden] {{ display: none !important; }}

    /* ── Main ────────────────────────────────────────────── */
    main {{ max-width: 1100px; margin: 0 auto; padding: 0 40px 80px; }}
    .tab-panel {{ display: none; }}
    .tab-panel.active {{ display: block; }}

    /* search wrapper */
    .search-wrapper {{ padding: 24px 0 0; }}

    /* ── Panel hero header ───────────────────────────────── */
    .panel-header {{ padding: 52px 0 28px; border-bottom: 1px solid rgba(255,255,255,.07); margin-bottom: 8px; }}
    .cat-hero-label {{ font-size: .65rem; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; color: var(--muted); margin-bottom: 10px; }}
    .cat-hero-title {{ font-size: clamp(2.8rem, 5vw, 4.2rem); font-weight: 900; letter-spacing: -.04em; line-height: 1; margin-bottom: 18px; }}
    .cat-hero-bottom {{ display: flex; align-items: center; gap: 14px; }}
    .panel-count {{ font-size: .85rem; color: rgba(255,255,255,.55); }}
    .panel-count strong {{ font-weight: 700; color: var(--text); font-size: 1rem; }}
    .btn-expand-all {{
      display: flex; align-items: center; gap: 5px;
      background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.12);
      color: var(--muted); font-size: .7rem; font-weight: 500; font-family: inherit;
      padding: 5px 14px; border-radius: 20px; cursor: pointer; transition: all .15s; margin-left: auto;
    }}
    .btn-expand-all:hover {{ color: var(--text); border-color: rgba(255,255,255,.22); background: rgba(255,255,255,.08); }}

    /* ── Accordion ───────────────────────────────────────── */
    .acc-list {{ display: flex; flex-direction: column; gap: 6px; padding-top: 4px; }}
    .acc-item {{
      background: rgba(255,255,255,.028); border: 1px solid rgba(255,255,255,.07);
      border-radius: var(--radius); overflow: hidden;
      transition: background .2s, border-color .2s, box-shadow .2s;
    }}
    .acc-item:hover {{ background: rgba(255,255,255,.05); border-color: rgba(255,255,255,.12); }}
    .acc-item.open {{
      background: rgba(255,255,255,.06);
      backdrop-filter: blur(16px) saturate(160%);
      -webkit-backdrop-filter: blur(16px) saturate(160%);
      border-color: rgba(255,255,255,.15);
    }}
    [data-panel="meta"]   .acc-item {{ border-left: 3px solid rgba(14,165,233,.50); }}
    [data-panel="google"] .acc-item {{ border-left: 3px solid rgba(52,168,83,.50); }}
    [data-panel="ppc"]    .acc-item {{ border-left: 3px solid rgba(139,92,246,.50); }}
    [data-panel="mkt"]    .acc-item {{ border-left: 3px solid rgba(245,158,11,.50); }}
    [data-panel="ia"]     .acc-item {{ border-left: 3px solid rgba(234,67,53,.50); }}
    [data-panel="meta"]   .acc-item.open {{ box-shadow: inset 6px 0 40px rgba(14,165,233,.14),  0 0 0 1px rgba(14,165,233,.22); }}
    [data-panel="google"] .acc-item.open {{ box-shadow: inset 6px 0 40px rgba(52,168,83,.14),   0 0 0 1px rgba(52,168,83,.22); }}
    [data-panel="ppc"]    .acc-item.open {{ box-shadow: inset 6px 0 40px rgba(139,92,246,.14),  0 0 0 1px rgba(139,92,246,.22); }}
    [data-panel="mkt"]    .acc-item.open {{ box-shadow: inset 6px 0 40px rgba(245,158,11,.14),  0 0 0 1px rgba(245,158,11,.22); }}
    [data-panel="ia"]     .acc-item.open {{ box-shadow: inset 6px 0 40px rgba(234,67,53,.14),   0 0 0 1px rgba(234,67,53,.22); }}

    .acc-header {{ display: flex; align-items: center; gap: 16px; padding: 16px 18px 16px 16px; cursor: pointer; user-select: none; }}
    .acc-num {{ font-size: .7rem; font-weight: 700; color: rgba(255,255,255,.38); letter-spacing: .04em; flex-shrink: 0; width: 24px; text-align: right; transition: color .15s; }}
    .acc-item.open .acc-num, .acc-header:hover .acc-num {{ color: rgba(255,255,255,.65); }}
    .acc-info {{ flex: 1; min-width: 0; }}
    .acc-title {{ font-size: .93rem; font-weight: 600; color: var(--text); line-height: 1.45; display: block; margin-bottom: 7px; letter-spacing: -.015em; transition: color .15s; }}
    .acc-header:hover .acc-title {{ color: #fff; }}
    .acc-meta {{ display: flex; align-items: center; gap: 7px; flex-wrap: wrap; }}
    .source-dot {{ width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; background: currentColor; opacity: .6; }}
    .source-tag {{ font-size: .68rem; font-weight: 600; color: rgba(255,255,255,.55); white-space: nowrap; }}
    .acc-date {{ font-size: .68rem; color: rgba(255,255,255,.38); }}
    .acc-actions {{ display: flex; align-items: center; gap: 6px; flex-shrink: 0; }}
    .btn-link {{
      display: flex; align-items: center; gap: 5px;
      font-size: .7rem; font-weight: 500; padding: 5px 12px; border-radius: 7px;
      text-decoration: none; white-space: nowrap;
      border: 1px solid rgba(255,255,255,.18); color: rgba(255,255,255,.65);
      background: rgba(255,255,255,.05); transition: all .15s; font-family: inherit;
    }}
    .btn-link:hover {{ color: var(--accent); border-color: rgba(165,241,230,.45); background: rgba(165,241,230,.08); }}
    .btn-copy {{
      display: flex; align-items: center; justify-content: center;
      padding: 5px 8px; border-radius: 7px; border: 1px solid rgba(255,255,255,.18);
      color: rgba(255,255,255,.55); background: rgba(255,255,255,.05); cursor: pointer; transition: all .15s;
    }}
    .btn-copy:hover {{ color: var(--text); border-color: rgba(255,255,255,.28); background: rgba(255,255,255,.08); }}
    .btn-copy.copied {{ color: #22C55E; border-color: rgba(34,197,94,.3); }}
    .btn-copy .icon-copy {{ display: flex; }}
    .btn-copy .icon-check {{ display: none; }}
    .btn-copy.copied .icon-copy {{ display: none; }}
    .btn-copy.copied .icon-check {{ display: flex; }}
    .acc-chevron {{ color: var(--muted); transition: transform .25s ease, color .15s; flex-shrink: 0; display: flex; align-items: center; }}
    .acc-item.open .acc-chevron {{ transform: rotate(180deg); color: rgba(255,255,255,.55); }}
    .acc-body {{ max-height: 0; overflow: hidden; transition: max-height .35s ease; }}
    .acc-item.open .acc-body {{ max-height: 600px; }}
    .acc-body-inner {{ padding: 0 18px 18px 56px; border-top: 1px solid rgba(255,255,255,.06); }}
    .acc-body-inner p {{ font-size: .875rem; color: #9EA4AC; line-height: 1.85; padding-top: 16px; }}

    /* ── Footer ──────────────────────────────────────────── */
    footer {{
      border-top: 1px solid rgba(255,255,255,.06);
      padding: 22px 40px; display: flex; align-items: center; justify-content: center; gap: 16px; flex-wrap: wrap;
    }}
    .footer-text {{ font-size: .7rem; color: var(--muted); text-align: center; }}
    .footer-text strong {{ color: var(--accent); font-weight: 600; }}
    .footer-logo {{ opacity: .25; transition: opacity .2s; }}
    .footer-logo:hover {{ opacity: .55; }}
    .footer-logo img {{ display: block; height: 16px; width: auto; }}

    /* ── Responsive ──────────────────────────────────────── */
    @media (max-width: 640px) {{
      header, .tabs-wrapper, .week-bar, main, footer {{ padding-left: 16px; padding-right: 16px; }}
      .cat-hero-title {{ font-size: 2.2rem; }}
      .acc-header {{ flex-wrap: wrap; }}
      .acc-body-inner {{ padding-left: 16px; }}
    }}
  </style>
</head>
<body>

<div class="bg-base"></div>
<div class="bg-cat active" id="bg-meta"></div>
<div class="bg-cat" id="bg-google"></div>
<div class="bg-cat" id="bg-ppc"></div>
<div class="bg-cat" id="bg-mkt"></div>
<div class="bg-cat" id="bg-ia"></div>

<header>
  <div class="header-left">
    <div class="header-logo"><img src="{logo_b64}" alt="SCOZ"/></div>
  </div>
  <div class="header-meta">Próxima atualização: <strong>{next_update}</strong></div>
</header>

<div class="tabs-wrapper" id="tabs">
  <button class="tab-btn active" data-tab="meta"><span class="tab-dot"></span>Meta Ads</button>
  <button class="tab-btn" data-tab="google"><span class="tab-dot"></span>Google Ads</button>
  <button class="tab-btn" data-tab="ppc"><span class="tab-dot"></span>Tráfego Pago</button>
  <button class="tab-btn" data-tab="mkt"><span class="tab-dot"></span>Marketing Digital</button>
  <button class="tab-btn" data-tab="ia"><span class="tab-dot"></span>IA &amp; Ferramentas</button>
</div>

<div class="week-bar">
  <span class="week-label">Semana</span>
  <div class="week-pills" id="week-pills"></div>
</div>

<main>
  <div class="search-wrapper">
    <div class="search-bar">
      <span class="search-icon">{SVG_SEARCH}</span>
      <input type="text" id="news-search" placeholder="Buscar notícias..." autocomplete="off" spellcheck="false">
      <span class="search-count" id="search-count" hidden></span>
      <button class="search-clear" id="search-clear" aria-label="Limpar" hidden>{SVG_XMARK}</button>
    </div>
  </div>

{panels_html}</main>

<footer>
  <div class="footer-text">
    Compilado gerado automaticamente às segundas-feiras &nbsp;&bull;&nbsp;
    Próxima atualização: <strong>{next_update}</strong>
  </div>
  <a class="footer-logo" href="#"><img src="{logo_b64}" alt="SCOZ"/></a>
</footer>

<script>
  // ── Sticky top cascade ────────────────────────────────────────────────────
  (function() {{
    const hdr  = document.querySelector('header');
    const tabs = document.getElementById('tabs');
    const wbar = document.querySelector('.week-bar');
    if (hdr && tabs && wbar) {{
      tabs.style.top = hdr.offsetHeight + 'px';
      wbar.style.top = (hdr.offsetHeight + tabs.offsetHeight) + 'px';
    }}
  }})();

  // ── Tab switching + background crossfade ──────────────────────────────────
  document.querySelectorAll('.tab-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.bg-cat').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('panel-' + btn.dataset.tab).classList.add('active');
      const bg = document.getElementById('bg-' + btn.dataset.tab);
      if (bg) bg.classList.add('active');
      applyFilters();
    }});
  }});

  // ── Accordion toggle ──────────────────────────────────────────────────────
  document.querySelectorAll('.acc-header').forEach(h => {{
    h.addEventListener('click', e => {{
      if (e.target.closest('.btn-link') || e.target.closest('.btn-copy')) return;
      const item   = h.closest('.acc-item');
      const isOpen = item.classList.contains('open');
      item.closest('.tab-panel').querySelectorAll('.acc-item.open').forEach(i => i.classList.remove('open'));
      if (!isOpen) item.classList.add('open');
    }});
  }});

  // ── Week pills (dynamic from data-week attrs) ─────────────────────────────
  const months = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
  function fmtWeek(id) {{
    const d = new Date(id + 'T12:00:00'), e = new Date(d);
    e.setDate(e.getDate() + 6);
    const y = String(d.getFullYear()).slice(2);
    return d.getMonth() === e.getMonth()
      ? `${{d.getDate()}}-${{e.getDate()}} ${{months[d.getMonth()]}}/${{y}}`
      : `${{d.getDate()}} ${{months[d.getMonth()]}} — ${{e.getDate()}} ${{months[e.getMonth()]}}/${{y}}`;
  }}
  const weekSet  = new Set([...document.querySelectorAll('.acc-item[data-week]')].map(i => i.dataset.week));
  const allWeeks = [...weekSet].sort().reverse();
  let currentWeek = allWeeks[0] || 'all';
  const pillsEl = document.getElementById('week-pills');
  allWeeks.forEach((w, i) => {{
    const p = document.createElement('button');
    p.className = 'week-pill' + (i === 0 ? ' active' : '');
    p.dataset.week = w; p.textContent = fmtWeek(w);
    pillsEl.appendChild(p);
  }});
  const allPill = document.createElement('button');
  allPill.className = 'week-pill'; allPill.dataset.week = 'all'; allPill.textContent = 'Todas';
  pillsEl.appendChild(allPill);
  pillsEl.addEventListener('click', e => {{
    const p = e.target.closest('.week-pill');
    if (p) {{ currentWeek = p.dataset.week; applyFilters(); }}
  }});

  // ── Combined filter (week + search) ──────────────────────────────────────
  let currentSearch = '';
  function getVisible(item) {{
    const weekOk = currentWeek === 'all' || item.dataset.week === currentWeek;
    if (!weekOk) return false;
    if (!currentSearch) return true;
    const text = (item.querySelector('.acc-title')?.textContent || '') + ' ' +
                 (item.querySelector('.acc-body-inner p')?.textContent || '');
    return text.toLowerCase().includes(currentSearch);
  }}
  function applyFilters() {{
    document.querySelectorAll('.acc-item.open').forEach(i => i.classList.remove('open'));
    document.querySelectorAll('.tab-panel').forEach(panel => {{
      let n = 0;
      panel.querySelectorAll('.acc-item').forEach(item => {{
        const show = getVisible(item);
        item.style.display = show ? '' : 'none';
        if (show) n++;
      }});
      const countEl = panel.querySelector('.panel-count');
      if (countEl) countEl.innerHTML = `<strong>${{n}}</strong> ${{n === 1 ? 'notícia' : 'notícias'}} esta semana`;
      const expBtn = panel.querySelector('.btn-expand-all span');
      if (expBtn) expBtn.textContent = 'Expandir tudo';
    }});
    document.querySelectorAll('.week-pill').forEach(p =>
      p.classList.toggle('active', p.dataset.week === currentWeek)
    );
    const countEl = document.getElementById('search-count');
    const clearEl = document.getElementById('search-clear');
    if (currentSearch) {{
      const total = [...document.querySelectorAll('.acc-item')].filter(i => i.style.display !== 'none').length;
      if (countEl) {{ countEl.textContent = total + ' resultado' + (total !== 1 ? 's' : ''); countEl.hidden = false; }}
      if (clearEl) clearEl.hidden = false;
    }} else {{
      if (countEl) countEl.hidden = true;
      if (clearEl) clearEl.hidden = true;
    }}
  }}
  const searchInput = document.getElementById('news-search');
  const searchClear = document.getElementById('search-clear');
  if (searchInput) searchInput.addEventListener('input', () => {{
    currentSearch = searchInput.value.trim().toLowerCase(); applyFilters();
  }});
  if (searchClear) searchClear.addEventListener('click', () => {{
    searchInput.value = ''; currentSearch = ''; applyFilters(); searchInput.focus();
  }});

  // ── Expand / collapse all ─────────────────────────────────────────────────
  document.querySelectorAll('.btn-expand-all').forEach(btn => {{
    btn.addEventListener('click', () => {{
      const panel   = document.getElementById('panel-' + btn.dataset.panel);
      const items   = [...panel.querySelectorAll('.acc-item')].filter(i => i.style.display !== 'none');
      const allOpen = items.length > 0 && items.every(i => i.classList.contains('open'));
      items.forEach(i => i.classList.toggle('open', !allOpen));
      btn.querySelector('span').textContent = allOpen ? 'Expandir tudo' : 'Recolher tudo';
    }});
  }});

  // ── Copy summary ──────────────────────────────────────────────────────────
  document.querySelectorAll('.btn-copy').forEach(btn => {{
    btn.addEventListener('click', e => {{
      e.stopPropagation();
      const item    = btn.closest('.acc-item');
      const title   = item.querySelector('.acc-title')?.textContent.trim() || '';
      const summary = item.querySelector('.acc-body-inner p')?.textContent.trim() || '';
      const source  = item.querySelector('.source-tag')?.textContent.trim() || '';
      const url     = item.querySelector('.btn-link')?.href || '';
      navigator.clipboard.writeText(title + '\\n\\n' + summary + '\\n\\nFonte: ' + source + ' — ' + url)
        .then(() => {{ btn.classList.add('copied'); setTimeout(() => btn.classList.remove('copied'), 2000); }});
    }});
  }});

  applyFilters();
</script>
</body>
</html>"""

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    logo_b64 = make_logo_b64()
    html     = build_html(data, logo_b64)

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    weeks = data.get("weeks", [])
    total = sum(
        sum(len(w.get("items", {}).get(c, [])) for c in ["meta","google","ppc","mkt","ia"])
        for w in weeks
    )
    print(f"OK — {len(weeks)} semana(s), {total} notícias → {HTML_PATH}")

if __name__ == "__main__":
    main()
