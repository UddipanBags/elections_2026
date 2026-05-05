"""
Build a static landing index.html for the 2026 assembly-election results
microsite. Reads the per-state results CSVs and the master palette config,
then emits a single index.html alongside the 5 state HTMLs.

Design direction: editorial-analytical. Serif headline, humanist sans body,
party colours doing the visual work against a neutral monochrome ground.

Run:
    python build_index.py /path/to/dir/with/csvs/and/htmls

Output:
    <dir>/index.html
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Supplementary palette: regional/state-specific parties not in the main
# palette config. Without these, parties like Tamilaga Vettri Kazhagam (which
# won 108 of TN's 234 seats) would render as undifferentiated grey on the
# index — making the headline visual misleading. These shades match the
# pastel tone of the main palette so they sit cohesively beside it.
SUPPLEMENTARY_PALETTE = {
    "tamilaga vettri kazhagam":             ("TVK",   "#D5C7E0"),
    "indian union muslim league":           ("IUML",  "#C8DCC2"),
    "all india n.r. congress":              ("AINRC", "#FBD9C0"),
    "bodoland peoples front":               ("BPF",   "#D6CDB8"),
    "asom gana parishad":                   ("AGP",   "#C8DBE0"),
    "communist party of india":             ("CPI",   "#F0C9C9"),
    "kerala congress":                      ("KEC",   "#D8E0BC"),
    "pattali makkal katchi":                ("PMK",   "#E0C9D5"),
    "all india united democratic front":    ("AIUDF", "#C2D7DC"),
    "raijor dal":                           ("RJD-A", "#D8C2C7"),
    "viduthalai chiruthaigal katchi":       ("VCK",   "#C7D5E0"),
    "revolutionary socialist party":        ("RSP",   "#E0C7C2"),
    "independent":                          ("Ind.",  "#D6D0CB"),
}

OTHER_FALLBACK = ("Others", "#CCCCCC")

STATES = [
    # (slug, full_name, csv_filename, html_filename, expected_ac_count)
    ("wb", "West Bengal",  "wb_results.csv", "wb_results_map.html", 294),
    ("tn", "Tamil Nadu",   "tn_results.csv", "tn_results_map.html", 234),
    ("as", "Assam",        "as_results.csv", "as_results_map.html", 126),
    ("kl", "Kerala",       "kl_results.csv", "kl_results_map.html", 140),
    ("py", "Puducherry",   "py_results.csv", "py_results_map.html",  30),
]


def load_palette(config_path: Path) -> dict[str, tuple[str, str]]:
    """
    Build a name/alias -> (abbr, hex) lookup. Combines the main JSON palette
    with our SUPPLEMENTARY_PALETTE for regional parties. Lookups are
    lowercased and stripped to match how the script normalises party names
    elsewhere.
    """
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    out: dict[str, tuple[str, str]] = {}
    for entry in cfg["party_palette"]:
        if entry.get("full_name") is None:
            continue  # catch-all "Others" handled by OTHER_FALLBACK
        abbr = entry["abbr"]
        hex_ = entry["hex"]
        out[entry["full_name"].lower().strip()] = (abbr, hex_)
        for alias in entry.get("aliases", []):
            out[alias.lower().strip()] = (abbr, hex_)
    out.update(SUPPLEMENTARY_PALETTE)
    return out


def lookup_party(party_name: str | None,
                 palette: dict[str, tuple[str, str]]) -> tuple[str, str]:
    """Resolve a party string to (abbreviation, hex). Falls back to Others."""
    if not party_name:
        return OTHER_FALLBACK
    key = party_name.lower().strip()
    return palette.get(key, OTHER_FALLBACK)


def load_state_summary(csv_path: Path,
                       palette: dict[str, tuple[str, str]]
                       ) -> dict:
    """
    Read a results CSV, return a dict with totals + ordered party list.
    Each party entry is {full_name, abbr, hex, seats}, sorted by seats desc.
    """
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    counts = Counter(r["leading_party"] for r in rows if r.get("leading_party"))
    parties = []
    for full_name, seats in counts.most_common():
        abbr, hex_ = lookup_party(full_name, palette)
        parties.append({
            "full_name": full_name,
            "abbr":      abbr,
            "hex":       hex_,
            "seats":     seats,
        })
    return {
        "total_acs":   len(rows),
        "parties":     parties,
        "leader":      parties[0] if parties else None,
    }


def render_seat_bar(parties: list[dict], total: int) -> str:
    """
    Stacked horizontal bar showing seat distribution. Each segment carries
    the party hex; widths are exact percentages. A 1px gap between segments
    keeps the bar legible even when one party has narrow share. The bar is
    inert (no tooltips) — parsing the legend below it is the intended UX.
    """
    if total == 0:
        return '<div class="seat-bar empty"></div>'
    segments = []
    for p in parties:
        pct = (p["seats"] / total) * 100
        segments.append(
            f'<span class="seg" style="width:{pct:.4f}%;background:{p["hex"]};" '
            f'title="{html.escape(p["full_name"])}: {p["seats"]} seats"></span>'
        )
    return f'<div class="seat-bar">{"".join(segments)}</div>'


def render_party_legend(parties: list[dict], total: int, max_show: int = 4) -> str:
    """
    Top-N parties as small colour-swatch chips with abbr + seat count.
    Anything past max_show rolls into a "+N more" pill at the end.
    """
    chips = []
    shown = parties[:max_show]
    for p in shown:
        chips.append(
            f'<span class="chip">'
            f'  <span class="chip-swatch" style="background:{p["hex"]}"></span>'
            f'  <span class="chip-abbr">{html.escape(p["abbr"])}</span>'
            f'  <span class="chip-count">{p["seats"]}</span>'
            f'</span>'
        )
    leftover = parties[max_show:]
    if leftover:
        leftover_seats = sum(p["seats"] for p in leftover)
        chips.append(
            f'<span class="chip chip-more">+{len(leftover)} more · {leftover_seats}</span>'
        )
    return f'<div class="legend-row">{"".join(chips)}</div>'


def render_state_card(slug: str, name: str, html_filename: str,
                      summary: dict, expected_ac_count: int) -> str:
    """Render one state card (linked, hoverable)."""
    leader = summary["leader"]
    leader_html = ""
    if leader:
        leader_html = (
            f'<div class="leader-line">'
            f'  <span class="leader-label">Leading</span>'
            f'  <span class="leader-name" style="--accent:{leader["hex"]}">'
            f'    {html.escape(leader["abbr"])}'
            f'  </span>'
            f'  <span class="leader-seats">{leader["seats"]} of {summary["total_acs"]}</span>'
            f'</div>'
        )
    completeness = ""
    if summary["total_acs"] != expected_ac_count:
        completeness = (
            f'<span class="completeness" title="Expected {expected_ac_count} ACs">'
            f'{summary["total_acs"]}/{expected_ac_count}'
            f'</span>'
        )
    return f'''<a class="state-card" href="{html_filename}" data-slug="{slug}">
  <div class="card-head">
    <span class="card-rule"></span>
    <h2 class="state-name">{html.escape(name)}</h2>
    <span class="card-meta">
      <span class="ac-count">{summary["total_acs"]} constituencies</span>
      {completeness}
    </span>
  </div>
  {leader_html}
  {render_seat_bar(summary["parties"], summary["total_acs"])}
  {render_party_legend(summary["parties"], summary["total_acs"])}
  <div class="card-cta">View map &rarr;</div>
</a>'''


def render_page(state_cards_html: str, generated_at: str) -> str:
    """The full HTML document."""
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>India Assembly Elections 2026 — Results Maps</title>
  <meta name="description" content="Interactive constituency-level results maps for the 2026 assembly elections in West Bengal, Tamil Nadu, Assam, Kerala, and Puducherry.">

  <!--
    Editorial-analytical aesthetic. Serif display + humanist sans body.
    Party palette colours carry the visual interest against a near-monochrome
    page chrome. No load animations — this is a results reference, not a
    splash page; users have arrived for data.
  -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">

  <style>
    /* ---------- design tokens ---------- */
    :root {{
      --paper:        #FAFAF7;
      --paper-2:      #F2F1EB;
      --ink:          #1A1A1A;
      --ink-soft:     #4A4843;
      --ink-mute:     #8C887F;
      --rule:         #D9D6CC;
      --accent-ink:   #38322A;
      --accent-warm:  #B5562F;   /* used very sparingly — page-title flourish only */
      --serif:        'Fraunces', Georgia, 'Times New Roman', serif;
      --sans:         'IBM Plex Sans', -apple-system, system-ui, sans-serif;
      --mono:         'IBM Plex Mono', ui-monospace, monospace;
    }}

    * {{ box-sizing: border-box; }}

    html, body {{
      margin: 0; padding: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: var(--sans);
      font-size: 16px;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
      font-feature-settings: "kern" 1, "tnum" 0;
    }}

    /* ---------- layout ---------- */
    .page {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 56px 24px 80px;
    }}

    @media (min-width: 720px) {{
      .page {{ padding: 96px 48px 120px; }}
    }}

    /* ---------- masthead ---------- */
    .masthead {{
      border-bottom: 1px solid var(--rule);
      padding-bottom: 28px;
      margin-bottom: 56px;
    }}
    .masthead-eyebrow {{
      font-family: var(--mono);
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink-mute);
      margin-bottom: 12px;
    }}
    .masthead-title {{
      font-family: var(--serif);
      font-weight: 500;
      font-size: clamp(36px, 6.4vw, 64px);
      line-height: 1.05;
      letter-spacing: -0.015em;
      margin: 0 0 16px 0;
      color: var(--ink);
      font-variation-settings: "opsz" 144;
    }}
    .masthead-title em {{
      font-style: italic;
      font-weight: 400;
      color: var(--accent-warm);
    }}
    .masthead-blurb {{
      font-family: var(--serif);
      font-size: clamp(16px, 1.6vw, 19px);
      line-height: 1.55;
      color: var(--ink-soft);
      max-width: 64ch;
      margin: 0;
      font-variation-settings: "opsz" 32;
    }}

    /* ---------- state cards grid ---------- */
    .states {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 24px;
    }}
    @media (min-width: 720px) {{
      .states {{
        grid-template-columns: 1fr 1fr;
        gap: 28px;
      }}
    }}

    .state-card {{
      display: block;
      text-decoration: none;
      color: inherit;
      background: var(--paper);
      border: 1px solid var(--rule);
      padding: 24px 24px 20px;
      transition: transform 0.18s ease, border-color 0.18s ease,
                  box-shadow 0.18s ease;
      position: relative;
    }}
    .state-card:hover {{
      transform: translateY(-2px);
      border-color: var(--ink-soft);
      box-shadow: 0 8px 22px -10px rgba(0, 0, 0, 0.18);
    }}
    .state-card:focus-visible {{
      outline: 2px solid var(--accent-warm);
      outline-offset: 3px;
    }}

    .card-head {{
      margin-bottom: 16px;
    }}
    .card-rule {{
      display: block;
      width: 32px; height: 2px;
      background: var(--ink);
      margin-bottom: 14px;
    }}
    .state-name {{
      font-family: var(--serif);
      font-weight: 500;
      font-size: 30px;
      letter-spacing: -0.012em;
      line-height: 1.1;
      margin: 0 0 6px 0;
      font-variation-settings: "opsz" 72;
    }}
    .card-meta {{
      display: flex;
      gap: 10px;
      align-items: baseline;
      font-family: var(--mono);
      font-size: 11px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--ink-mute);
    }}
    .completeness {{
      color: var(--accent-warm);
    }}

    /* ---------- leader line ---------- */
    .leader-line {{
      display: flex;
      gap: 10px;
      align-items: baseline;
      margin: 8px 0 14px 0;
      padding-bottom: 14px;
      border-bottom: 1px dotted var(--rule);
    }}
    .leader-label {{
      font-family: var(--mono);
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink-mute);
    }}
    .leader-name {{
      font-family: var(--serif);
      font-style: italic;
      font-weight: 500;
      font-size: 22px;
      color: var(--ink);
      position: relative;
      padding: 0 4px;
      background: linear-gradient(transparent 60%, var(--accent) 60%);
    }}
    .leader-seats {{
      font-family: var(--mono);
      font-size: 13px;
      font-variant-numeric: tabular-nums;
      color: var(--ink-soft);
      margin-left: auto;
    }}

    /* ---------- stacked seat bar ---------- */
    .seat-bar {{
      display: flex;
      width: 100%;
      height: 14px;
      margin: 4px 0 16px 0;
      border-radius: 1px;
      overflow: hidden;
      background: var(--paper-2);
    }}
    .seat-bar .seg {{
      display: block;
      height: 100%;
      flex-shrink: 0;
    }}
    .seat-bar .seg + .seg {{
      box-shadow: -1px 0 0 0 var(--paper);
    }}

    /* ---------- party legend chips ---------- */
    .legend-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px 10px;
      margin-bottom: 18px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: var(--ink-soft);
      font-variant-numeric: tabular-nums;
    }}
    .chip-swatch {{
      display: inline-block;
      width: 11px; height: 11px;
      border-radius: 1px;
      border: 1px solid rgba(0,0,0,0.06);
    }}
    .chip-abbr {{
      font-weight: 500;
      color: var(--ink);
    }}
    .chip-count {{
      font-family: var(--mono);
      font-size: 11px;
      color: var(--ink-soft);
    }}
    .chip-more {{
      font-family: var(--mono);
      font-size: 11px;
      color: var(--ink-mute);
      font-variant-numeric: tabular-nums;
    }}

    /* ---------- card CTA ---------- */
    .card-cta {{
      font-family: var(--sans);
      font-size: 13px;
      font-weight: 500;
      color: var(--ink);
      letter-spacing: 0.005em;
      padding-top: 4px;
      border-top: 1px solid var(--rule);
      margin-top: 4px;
      display: flex;
      align-items: center;
      gap: 4px;
      transition: color 0.15s ease, gap 0.15s ease;
    }}
    .state-card:hover .card-cta {{
      color: var(--accent-warm);
      gap: 8px;
    }}

    /* ---------- footer ---------- */
    .footer {{
      margin-top: 80px;
      padding-top: 28px;
      border-top: 1px solid var(--rule);
      font-size: 13px;
      line-height: 1.65;
      color: var(--ink-soft);
      max-width: 64ch;
    }}
    .footer h3 {{
      font-family: var(--mono);
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink-mute);
      font-weight: 500;
      margin: 0 0 8px 0;
    }}
    .footer p {{ margin: 0 0 12px 0; }}
    .footer a {{
      color: var(--ink);
      text-decoration: underline;
      text-decoration-color: var(--rule);
      text-underline-offset: 3px;
      transition: text-decoration-color 0.15s ease;
    }}
    .footer a:hover {{
      text-decoration-color: var(--accent-warm);
    }}
    .timestamp {{
      font-family: var(--mono);
      font-size: 11px;
      color: var(--ink-mute);
      letter-spacing: 0.04em;
      margin-top: 18px;
    }}
  </style>
</head>
<body>
  <main class="page">

    <header class="masthead">
      <div class="masthead-eyebrow">India · Assembly Elections · 2026</div>
      <h1 class="masthead-title">
        Five states. <em>One map each.</em>
      </h1>
      <p class="masthead-blurb">
        Constituency-level results for the West Bengal, Tamil Nadu, Assam,
        Kerala, and Puducherry assembly elections of 2026. Each map shows
        the leading party in every assembly constituency, with hover
        details, victory-margin overlays, and clickable margin buckets
        that reveal the full candidate list for that band.
      </p>
    </header>

    <section class="states">
{state_cards_html}
    </section>

    <footer class="footer">
      <h3>Sources & Credits</h3>
      <p>
        Election results scraped from the
        <a href="https://results.eci.gov.in/" rel="noopener">Election Commission of India</a>.
        Constituency boundaries from
        <a href="https://data.opencity.in/" rel="noopener">OpenCity</a>
        (West Bengal, Tamil Nadu) and
        <a href="https://github.com/ramSeraph/indian_admin_boundaries" rel="noopener">ramSeraph/indian_admin_boundaries</a>
        (Assam, Kerala, Puducherry), both released under CC-BY.
        Base map tiles by
        <a href="https://carto.com/attributions" rel="noopener">CARTO</a>,
        with data from
        <a href="https://www.openstreetmap.org/copyright" rel="noopener">OpenStreetMap contributors</a>.
      </p>
      <h3 style="margin-top:24px">Notes</h3>
      <p>
        Each state map is a self-contained HTML file with the data baked in.
        The pages need an internet connection only for the base-map tiles and
        client-side libraries (Leaflet, etc.); all results, candidate lists,
        and constituency geometries are embedded.
      </p>
      <div class="timestamp">Generated {generated_at}</div>
    </footer>

  </main>
</body>
</html>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "site_dir",
        type=Path,
        help="Directory containing the per-state CSVs, HTMLs, and config JSON.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to multiple_states_map_config.json (default: <site_dir>/multiple_states_map_config.json)",
    )
    args = parser.parse_args()

    site_dir = args.site_dir.resolve()
    config_path = args.config or (site_dir / "multiple_states_map_config.json")

    palette = load_palette(config_path)

    cards = []
    for slug, name, csv_name, html_name, expected in STATES:
        csv_path = site_dir / csv_name
        if not csv_path.exists():
            print(f"  [skip] {csv_path} not found")
            continue
        if not (site_dir / html_name).exists():
            print(f"  [skip] {site_dir / html_name} not found")
            continue
        summary = load_state_summary(csv_path, palette)
        cards.append(render_state_card(slug, name, html_name, summary, expected))
        leader = summary["leader"]
        if leader:
            print(f"  [ok] {slug}: {summary['total_acs']} ACs, "
                  f"leader {leader['abbr']} ({leader['seats']} seats)")

    state_cards_html = "\n".join(cards)
    generated_at = dt.datetime.now().strftime("%-d %B %Y")

    page = render_page(state_cards_html, generated_at)
    out_path = site_dir / "index.html"
    out_path.write_text(page, encoding="utf-8")
    size_kb = out_path.stat().st_size / 1024
    print(f"\nWrote {out_path} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
