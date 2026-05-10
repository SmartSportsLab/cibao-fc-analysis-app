# Wyscout Analysis

A Streamlit-based football analytics workspace originally built for **Cibao FC** (Liga Dominicana de Fútbol) to drive collective and opposition analysis from raw Wyscout exports.

This is a **portfolio version** of the project. The login gate that protected the production deployment has been removed so it can be opened directly. All real club data, branding, and the original Spanish UI have been preserved so the app behaves identically to the version delivered to the club.

---

## What it does

The app converts a Wyscout team export into per-90 normalised JSONs and exposes them through a hub of analysis modules. Coaches and analysts can pick a fixture or competition, drill into team performance vs. opponents, and export a polished PDF report.

### Pages

| Page | Module | Purpose |
| --- | --- | --- |
| `0_Upload_Wyscout_Data.py` | Data ingestion | Upload a Wyscout team export, clean headers, convert to per-90, persist to `data/processed/Wyscout/` |
| `1_Rendimiento_Colectivo_-_Liga.py` | Liga collective performance | Cibao's own metrics across the Liga Dominicana season, benchmarked against league context |
| `2_Analisis_del_Rival_-_Liga.py` | Liga opposition analysis | Side-by-side opponent profiling for upcoming Liga fixtures |
| `3_Exportar_Reporte_PDF.py` | PDF export | One-click generation of a styled PDF match report |
| `4_Rendimiento_Colectivo_-_Copa.py` | Copa collective performance | Same lens but for the CONCACAF Copa Centroamericana run |
| `5_Analisis_del_Rival_-_Copa.py` | Copa opposition analysis | Opposition profiling for Copa fixtures |

### Architecture

```text
.
├── app.py                            # Hub + entry point (login removed)
├── pages/                            # Six Streamlit pages above
├── src/
│   ├── data_processing/              # Wyscout header fixing, per-90 conversion,
│   │                                 # Scoresway scraping, loaders
│   └── utils/                        # Dark theme, navigation, metrics dictionaries,
│                                     # PDF generators
├── graficos_de_navaja_suiza.py       # Reusable chart helpers ("Swiss Army knife")
├── data/
│   ├── raw/                          # Raw Wyscout + Concacaf inputs
│   └── processed/                    # Per-90 JSONs, lineups, team stats
├── assets/                           # Logo, colour scheme, metrics dictionaries
├── requirements.txt                  # Python dependencies
└── packages.txt                      # System packages (for Streamlit Cloud)
```

---

## Run it locally

```bash
cd "App Protoypes/Wyscout Analysis"
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The hub loads at `http://localhost:8501` with no login.

> If you already have other Streamlit apps running, pick a free port:
> `streamlit run app.py --server.port 8502`

### Optional: Playwright (Concacaf scraper)

The Concacaf scraping path uses Playwright. If you intend to run it:

```bash
playwright install chromium
```

Most portfolio viewers won't need this — the processed Concacaf data is already shipped in `data/processed/Concacaf/`.

---

## What I built

Everything in `app.py`, `pages/`, `src/`, and the chart helpers in `graficos_de_navaja_suiza.py` — including the data ingestion pipeline (Wyscout header normalisation, per-90 conversion, JSON persistence), the analysis pages, the dark Streamlit theme, navigation, the PDF export, and the orange-on-black UI styling.

### Highlights worth pointing out

- **Per-90 normalisation pipeline** that reconciles inconsistent Wyscout column headers across exports and emits a single canonical schema per team
- **Reusable charting layer** (`graficos_de_navaja_suiza.py`) for radar plots, percentile bars, and grouped bar comparisons used across every analysis page
- **One-click PDF report generator** (`src/utils/html_pdf_generator.py`, `pdf_generator_page1.py`) that produces club-styled multi-page exports
- **Two competition contexts** (Liga Dominicana + CONCACAF Copa Centroamericana) with separate metrics dictionaries and processing paths
- **Production-ready hub UI** with branded buttons, cached navigation, and a router that supports `?go=<module>` deep links

---

## Differences from the production version

| Item | Production (Cibao FC) | Portfolio version |
| --- | --- | --- |
| Login | Required (`USERNAME`/`PASSWORD` from `.env`) | Removed — hub loads directly |
| `.env` file | Present, gitignored | Removed entirely |
| Page title | "Cibao FC - Data Hub" | "Wyscout Analysis" |
| Internal docs | 7 markdown SOPs (coaching staff guide, automation manuals, debugging notes, Scoresway credential lookup) | Excluded |
| Automation Testing folder | Present | Excluded |

Everything else — branding colours, the Cibao logo, Spanish copy, the layout, the data pipeline, the charts, the PDFs — is identical to what was deployed to the club.

---

## Notes on the data

- Real anonymised data from the Liga Dominicana 2024/25 season for Cibao + nine opponents is included under `data/processed/Wyscout/`.
- Concacaf Copa Centroamericana fixtures are included under `data/raw/concacaf/` and `data/processed/Concacaf/`.
- The upload page (`pages/0_Upload_Wyscout_Data.py`) lets you ingest a fresh Wyscout export end-to-end, which is the simplest way to confirm the pipeline works on new data.

---

Built by **Daniel Levitt** ([daniellevitt32@gmail.com](mailto:daniellevitt32@gmail.com)) during the engagement with Cibao FC.
