# Sentinel: Geopolitical Conflict Monitor

A real-time dashboard that monitors 54 global conflict zones using RSS feeds, NLP analysis, and geospatial mapping.

## Dashboard Preview
![Dashboard Screenshot](sentinel_grid.png)

## Technical Stack
- **Language:** Python 3.10+
- **Framework:** Plotly Dash (Interactive Visualization)
- **Data Processing:** Pandas, RegEx (Rule-Based NLP Logic)
- **Data Source:** Automated Google News RSS Aggregation

## Core Functionality
- **Real-time Monitoring:** Automated scraping of global conflict signals from RSS feeds.
- **SITREP Generation:** A rule-based NLP engine that reconstructs fragmented news headlines into subject-led tactical SITREPs.
- **Global Node Grid:** Tracks real-time intelligence across 54 global conflict zones with automated risk scoring.

## How to Run
1. Clone the repository: `git clone https://github.com/Kenneth-Thakur/Sentinel-Monitor.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python sentinel.py`
