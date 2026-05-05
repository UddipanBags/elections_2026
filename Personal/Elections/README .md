# India Assembly Elections 2026 — Results Maps

Interactive constituency-level results maps for the 2026 assembly elections in West Bengal, Tamil Nadu, Assam, Kerala, and Puducherry.

**Live site:** [https://uddipanbags.github.io/elections_2026/](https://uddipanbags.github.io/elections_2026/)

## What's in this repo

```
.
├── index.html                          ← landing page
├── wb_results_map.html                 ← West Bengal (294 ACs)
├── tn_results_map.html                 ← Tamil Nadu (234 ACs)
├── as_results_map.html                 ← Assam (126 ACs)
├── kl_results_map.html                 ← Kerala (140 ACs)
├── py_results_map.html                 ← Puducherry (30 ACs)
├── *_results.csv                       ← scraped final results, one per state
├── multiple_states_map_config.json     ← party palette + bucket thresholds
└── build_index.py                      ← regenerates index.html from the CSVs
```

Each state HTML embeds its own results, candidate lists, and constituency geometries. The only runtime network requests are for Leaflet / jQuery / Bootstrap (jsdelivr + cloudflare CDNs) and the CARTO base-map tiles.

## Each map's interactive features

- **Hover** any constituency to see leader, margin, rounds, electors, and Muslim population %.
- **Click** a cell in the "Constituencies by margin" table to see all the constituencies in that party / margin bucket — sortable by candidate, constituency, AC number, or margin. The matching constituencies are softly highlighted on the map.
- **Toggle** the "Overlay victory margins on AC" button to print exact margin numbers on each constituency.
- **Switch states** via the dropdown at top right.

## Regenerating `index.html`

If you edit a results CSV (e.g. ECI publishes a correction), regenerate the index page:

```bash
python build_index.py .
```

The script reads each `<slug>_results.csv` and rebuilds the seat-distribution bars and party legends. The state HTMLs are not regenerated — those would require re-running the upstream pipeline (`Multiple_Election_Results_Map.py`).

## Sources

- **Results:** Election Commission of India, [results.eci.gov.in](https://results.eci.gov.in/)
- **Boundaries (WB, TN):** [OpenCity](https://data.opencity.in/), CC-BY
- **Boundaries (AS, KL, PY):** [ramSeraph/indian_admin_boundaries](https://github.com/ramSeraph/indian_admin_boundaries), CC-BY
- **Base map tiles:** [CARTO](https://carto.com/), data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)

## File sizes

| State | HTML size |
|-------|----------:|
| Puducherry | 0.4 MB |
| Assam | 4.0 MB |
| Kerala | 4.0 MB |
| West Bengal | 13.5 MB |
| Tamil Nadu | 17.8 MB |

GitHub Pages bandwidth cap is 100 GB/month. Even at the full 40 MB per visitor the site can serve ~2,500 full visits per month before any throttling.
