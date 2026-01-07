# Sentinel: Geopolitical Conflict Monitor

A real-time dashboard for monitoring global conflict signals. Utilizes a rule-based NLP pipeline to scrub high-velocity news feeds and reconstruct fragmented headlines into formal tactical SITREPs, enabling early detection of emerging regional instability.

## Dashboard Preview
![Dashboard Screenshot](sentinel_ds_hero.png)

## Technical Stack
- **Language:** Python 3.10+
- **Framework:** Plotly Dash (Interactive Visualization)
- **Data Processing:** Pandas, RegEx (Custom NLP Pipeline)
- **Data Source:** RSS Feeds & Live News Integration

## Core Functionality
- **Real-time Monitoring:** Automated scraping of global conflict signals from RSS feeds.
- **SITREP Generation:** A custom NLP engine that reconstructs fragmented news headlines into subject-led tactical SITREPs.
- **Geospatial Mapping:** A real-time heatmap distribution of global conflict "signals" and risk levels.

## How to Run
1. Clone the repository: `git clone https://github.com/Kenneth-Thakur/Sentinel-Monitor.git`
2. Install dependencies: `pip install dash pandas requests feedparser plotly`
3. Run the application: `python sentinel_final.py`
