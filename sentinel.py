# ============================================================
# SENTINEL — Geopolitical Conflict Monitor
# Real-time OSINT dashboard tracking 54 global conflict zones
# Using RSS ingestion, NLP analysis, and geospatial mapping.
# ============================================================

import dash
from dash import dcc, html, callback_context, no_update
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import datetime
import random
import feedparser  # Parses RSS/XML feeds into Python objects
import requests
import re           # Regex for cleaning headline text
import json
import pytz         # Timezone conversions for the clock
import os

# ==========================================
# NLTK — Natural Language Toolkit
# VADER: Sentiment analysis (-1 to +1)
# NER: Named Entity Recognition (GPE=Places, ORG=Organizations, PERSON=People)
# ==========================================
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer  # VADER sentiment scorer
from nltk import word_tokenize, pos_tag, ne_chunk  # Named Entity Recognition
from nltk.tree import Tree  # Used to identify named entities in NER output

# Download required NLTK data files (runs once, skips if already installed)
nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('averaged_perceptron_tagger_eng', quiet=True)
nltk.download('maxent_ne_chunker', quiet=True)
nltk.download('maxent_ne_chunker_tab', quiet=True)
nltk.download('words', quiet=True)

# VADER sentiment analyzer — scores text from -1 (negative) to +1 (positive)
sid = SentimentIntensityAnalyzer()

# ==========================================
# 1. NODE REGISTRY — 54 Global Conflict Zones
# Each node: name, country, base risk score (0-100),
# lat/lon for geospatial map, region for SITREP grouping
# ==========================================
BASE_NODES = [
    # --- ACTIVE CONFLICT ZONES ---
    {"name": "Gaza City", "country": "Palestinian Territories", "adj": "PALESTINIAN", "base": 90, "lat": 31.50, "lon": 34.46, "region": "Middle East"},
    {"name": "Rafah", "country": "Palestinian Territories", "adj": "PALESTINIAN", "base": 88, "lat": 31.28, "lon": 34.25, "region": "Middle East"},
    {"name": "Khan Younis", "country": "Palestinian Territories", "adj": "PALESTINIAN", "base": 87, "lat": 31.34, "lon": 34.30, "region": "Middle East"},
    {"name": "Tel Aviv", "country": "Israel", "adj": "ISRAELI", "base": 80, "lat": 32.08, "lon": 34.78, "region": "Middle East"},
    {"name": "Jerusalem", "country": "Israel", "adj": "ISRAELI", "base": 72, "lat": 31.77, "lon": 35.23, "region": "Middle East"},
    {"name": "Haifa", "country": "Israel", "adj": "ISRAELI", "base": 65, "lat": 32.79, "lon": 34.98, "region": "Middle East"},
    {"name": "Kyiv", "country": "Ukraine", "adj": "UKRAINIAN", "base": 85, "lat": 50.45, "lon": 30.52, "region": "Eastern Europe"},
    {"name": "Kharkiv", "country": "Ukraine", "adj": "UKRAINIAN", "base": 83, "lat": 49.99, "lon": 36.23, "region": "Eastern Europe"},
    {"name": "Zaporizhzhia", "country": "Ukraine", "adj": "UKRAINIAN", "base": 80, "lat": 47.84, "lon": 35.14, "region": "Eastern Europe"},
    {"name": "Donetsk", "country": "Ukraine", "adj": "UKRAINIAN", "base": 88, "lat": 48.00, "lon": 37.80, "region": "Eastern Europe"},
    {"name": "Odesa", "country": "Ukraine", "adj": "UKRAINIAN", "base": 75, "lat": 46.48, "lon": 30.73, "region": "Eastern Europe"},
    {"name": "Khartoum", "country": "Sudan", "adj": "SUDANESE", "base": 85, "lat": 15.50, "lon": 32.55, "region": "Africa"},
    {"name": "El-Fasher", "country": "Sudan", "adj": "SUDANESE", "base": 82, "lat": 13.63, "lon": 25.35, "region": "Africa"},
    {"name": "Port Sudan", "country": "Sudan", "adj": "SUDANESE", "base": 70, "lat": 19.61, "lon": 37.22, "region": "Africa"},
    {"name": "Tehran", "country": "Iran", "adj": "IRANIAN", "base": 75, "lat": 35.68, "lon": 51.38, "region": "Middle East"},
    {"name": "Isfahan", "country": "Iran", "adj": "IRANIAN", "base": 68, "lat": 32.65, "lon": 51.67, "region": "Middle East"},
    {"name": "Moscow", "country": "Russia", "adj": "RUSSIAN", "base": 70, "lat": 55.75, "lon": 37.61, "region": "Eastern Europe"},
    {"name": "Belgorod", "country": "Russia", "adj": "RUSSIAN", "base": 72, "lat": 50.59, "lon": 36.59, "region": "Eastern Europe"},
    {"name": "Sevastopol", "country": "Ukraine", "adj": "UKRAINIAN", "base": 78, "lat": 44.60, "lon": 33.52, "region": "Eastern Europe"},
    {"name": "Pyongyang", "country": "North Korea", "adj": "NORTH KOREAN", "base": 75, "lat": 39.03, "lon": 125.76, "region": "East Asia"},

    # --- ELEVATED THREAT ZONES ---
    {"name": "Taipei", "country": "Taiwan", "adj": "TAIWANESE", "base": 55, "lat": 25.03, "lon": 121.56, "region": "East Asia"},
    {"name": "Mogadishu", "country": "Somalia", "adj": "SOMALI", "base": 78, "lat": 2.05, "lon": 45.34, "region": "Africa"},
    {"name": "Kabul", "country": "Afghanistan", "adj": "AFGHAN", "base": 72, "lat": 34.53, "lon": 69.17, "region": "Central Asia"},
    {"name": "Baghdad", "country": "Iraq", "adj": "IRAQI", "base": 65, "lat": 33.31, "lon": 44.37, "region": "Middle East"},
    {"name": "Damascus", "country": "Syria", "adj": "SYRIAN", "base": 70, "lat": 33.51, "lon": 36.29, "region": "Middle East"},
    {"name": "Aleppo", "country": "Syria", "adj": "SYRIAN", "base": 68, "lat": 36.20, "lon": 37.16, "region": "Middle East"},
    {"name": "Sana'a", "country": "Yemen", "adj": "YEMENI", "base": 76, "lat": 15.35, "lon": 44.21, "region": "Middle East"},
    {"name": "Aden", "country": "Yemen", "adj": "YEMENI", "base": 70, "lat": 12.78, "lon": 45.03, "region": "Middle East"},
    {"name": "Tripoli", "country": "Libya", "adj": "LIBYAN", "base": 62, "lat": 32.90, "lon": 13.18, "region": "Africa"},
    {"name": "Benghazi", "country": "Libya", "adj": "LIBYAN", "base": 60, "lat": 32.12, "lon": 20.07, "region": "Africa"},
    {"name": "Bangui", "country": "Central African Republic", "adj": "CENTRAL AFRICAN", "base": 65, "lat": 4.36, "lon": 18.56, "region": "Africa"},
    {"name": "Goma", "country": "DR Congo", "adj": "CONGOLESE", "base": 74, "lat": -1.67, "lon": 29.23, "region": "Africa"},
    {"name": "Bamako", "country": "Mali", "adj": "MALIAN", "base": 62, "lat": 12.64, "lon": -8.00, "region": "Africa"},
    {"name": "Ouagadougou", "country": "Burkina Faso", "adj": "BURKINABE", "base": 60, "lat": 12.37, "lon": -1.52, "region": "Africa"},
    {"name": "Maiduguri", "country": "Nigeria", "adj": "NIGERIAN", "base": 66, "lat": 11.85, "lon": 13.16, "region": "Africa"},
    {"name": "Naypyidaw", "country": "Myanmar", "adj": "MYANMAR", "base": 70, "lat": 19.76, "lon": 96.07, "region": "Southeast Asia"},
    {"name": "Mandalay", "country": "Myanmar", "adj": "MYANMAR", "base": 68, "lat": 21.97, "lon": 96.08, "region": "Southeast Asia"},
    {"name": "Beirut", "country": "Lebanon", "adj": "LEBANESE", "base": 65, "lat": 33.89, "lon": 35.50, "region": "Middle East"},
    {"name": "Islamabad", "country": "Pakistan", "adj": "PAKISTANI", "base": 55, "lat": 33.69, "lon": 73.04, "region": "South Asia"},
    {"name": "Peshawar", "country": "Pakistan", "adj": "PAKISTANI", "base": 62, "lat": 34.01, "lon": 71.58, "region": "South Asia"},

    # --- MONITORING ZONES (LOW THREAT) ---
    {"name": "Seoul", "country": "South Korea", "adj": "SOUTH KOREAN", "base": 40, "lat": 37.57, "lon": 126.98, "region": "East Asia"},
    {"name": "New Delhi", "country": "India", "adj": "INDIAN", "base": 30, "lat": 28.61, "lon": 77.21, "region": "South Asia"},
    {"name": "Mumbai", "country": "India", "adj": "INDIAN", "base": 15, "lat": 19.07, "lon": 72.87, "region": "South Asia"},
    {"name": "Beijing", "country": "China", "adj": "CHINESE", "base": 35, "lat": 39.90, "lon": 116.40, "region": "East Asia"},
    {"name": "Shanghai", "country": "China", "adj": "CHINESE", "base": 15, "lat": 31.23, "lon": 121.47, "region": "East Asia"},
    {"name": "Lagos", "country": "Nigeria", "adj": "NIGERIAN", "base": 15, "lat": 6.52, "lon": 3.37, "region": "Africa"},
    {"name": "Ankara", "country": "Turkey", "adj": "TURKISH", "base": 35, "lat": 39.93, "lon": 32.85, "region": "Middle East"},
    {"name": "Riyadh", "country": "Saudi Arabia", "adj": "SAUDI", "base": 30, "lat": 24.71, "lon": 46.67, "region": "Middle East"},
    {"name": "London", "country": "UK", "adj": "BRITISH", "base": 10, "lat": 51.50, "lon": -0.12, "region": "Western Europe"},
    {"name": "Washington D.C.", "country": "USA", "adj": "U.S.", "base": 10, "lat": 38.91, "lon": -77.04, "region": "North America"},
    {"name": "New York City", "country": "USA", "adj": "U.S.", "base": 10, "lat": 40.71, "lon": -74.00, "region": "North America"},
    {"name": "Tokyo", "country": "Japan", "adj": "JAPANESE", "base": 10, "lat": 35.67, "lon": 139.65, "region": "East Asia"},
    {"name": "Sydney", "country": "Australia", "adj": "AUSTRALIAN", "base": 12, "lat": -33.86, "lon": 151.20, "region": "Oceania"},
    {"name": "Auckland", "country": "New Zealand", "adj": "NEW ZEALAND", "base": 12, "lat": -36.85, "lon": 174.76, "region": "Oceania"},
]

# ==========================================
# 2. NLP PIPELINE
# Tactical Dossiers: Pre-written military-format templates
# Escalation Weights: Keyword-to-risk-point mapping
# Functions: extract_named_entities(), compute_sentiment(),
#            compute_nlp_risk_score(), refine_intel()
# ==========================================
TACTICAL_DOSSIERS = {
    "GAZA CITY": [
        "ISRAELI FORCES NEUTRALIZE HIGH-VALUE COMMAND TARGETS IN GAZA CITY AIR STRIKE.",
        "ISRAELI FORCES CONDUCT KINETIC OPERATION AGAINST TUNNEL INFRASTRUCTURE IN GAZA CITY."
    ],
    "RAFAH": [
        "ISRAELI GROUND FORCES ADVANCE INTO EASTERN RAFAH SECTOR TARGETING MILITANT POSITIONS.",
        "IDF ENGINEERING UNITS DISMANTLE CROSS-BORDER TUNNEL NETWORK IN RAFAH CORRIDOR."
    ],
    "KHAN YOUNIS": [
        "ISRAELI FORCES CONDUCT TARGETED RAID ON MILITANT COMMAND POST IN KHAN YOUNIS.",
        "IDF ARMORED UNITS ENGAGE HOSTILE FIGHTERS IN URBAN COMBAT ZONE IN KHAN YOUNIS."
    ],
    "TEL AVIV": [
        "IRON DOME AIR DEFENSE INTERCEPTS MULTIPLE PROJECTILES OVER CENTRAL TEL AVIV SECTOR.",
        "ISRAELI SECURITY FORCES INCREASE READINESS LEVELS FOLLOWING BORDER RETALIATION SIGNALS."
    ],
    "KHARTOUM": [
        "SUDANESE ARMED FORCES (SAF) CLASH WITH RSF PARAMILITARIES IN HEAVY URBAN COMBAT.",
        "SUDANESE MILITARY CONDUCT ARTILLERY BARRAGE AGAINST RSF POSITIONS ACROSS KHARTOUM."
    ],
    "TEHRAN": [
        "ISRAELI MILITARY EXECUTES PRECISION SABOTAGE AGAINST RESEARCH INFRASTRUCTURE IN TEHRAN.",
        "MOSSAD OPERATIVES NEUTRALIZE STRATEGIC INTERNAL SECURITY TARGETS WITHIN TEHRAN PERIMETER."
    ],
    "KYIV": [
        "RUSSIAN FORCES LAUNCH LARGE-SCALE DRONE SALVO TARGETING POWER INFRASTRUCTURE IN KYIV.",
        "UKRAINIAN AIR DEFENSE UNITS INTERCEPT CRUISE MISSILES ENTERING KYIV RESTRICTED AIRSPACE."
    ],
    "MOSCOW": [
        "RUSSIAN DEFENSE SYSTEMS NEUTRALIZE MULTIPLE UNMANNED AERIAL VEHICLES OVER MOSCOW PERIMETER.",
        "SECURITY FORCES RESTRICT AIRSPACE ACCESS FOLLOWING SIGNAL ANOMALIES DETECTED IN MOSCOW SECTOR."
    ],
    "DONETSK": [
        "UKRAINIAN ARTILLERY UNITS ENGAGE RUSSIAN FORWARD POSITIONS ACROSS DONETSK FRONT LINE.",
        "RUSSIAN FORCES LAUNCH GROUND ASSAULT ON FORTIFIED POSITIONS WEST OF DONETSK CITY."
    ],
    "KHARKIV": [
        "RUSSIAN GUIDED BOMB STRIKES RESIDENTIAL INFRASTRUCTURE IN NORTHERN KHARKIV DISTRICT.",
        "UKRAINIAN AIR DEFENSE SYSTEMS INTERCEPT BALLISTIC MISSILE APPROACHING KHARKIV."
    ],
}

# Keyword weights for risk scoring — positive values escalate, negative de-escalate
ESCALATION_WEIGHTS = {
    "NUCLEAR": 30, "CHEMICAL": 25, "BIOLOGICAL": 25, "WMD": 30,
    "INVASION": 20, "WAR": 15, "MOBILIZATION": 15, "ANNEX": 15,
    "MISSILE": 12, "ROCKET": 12, "ARTILLERY": 10, "AIRSTRIKE": 12, "BOMBING": 12,
    "CASUALTIES": 10, "KILLED": 10, "DEAD": 10, "FATAL": 10, "MASSACRE": 15,
    "DRONE": 8, "STRIKE": 8, "RAID": 8, "SHELLING": 8, "AMBUSH": 8,
    "COMBAT": 6, "MILITARY": 5, "FORCES": 4, "ATTACK": 6, "ASSAULT": 7,
    "HOSTAGE": 10, "SIEGE": 10, "BLOCKADE": 8, "COUP": 15,
    "TERROR": 12, "INSURGENT": 8, "MILITIA": 6, "GUERRILLA": 6,
    "CEASEFIRE": -5, "PEACE": -5, "NEGOTIATE": -3, "WITHDRAW": -3, "TRUCE": -5,
}


def extract_named_entities(text):
    """Extract named entities (GPE=Places, PERSON=People, ORG=Organizations) using NLTK NER."""
    entities = {"GPE": [], "PERSON": [], "ORGANIZATION": []}
    try:
        tokens = word_tokenize(text)  # Split text into individual words
        tagged = pos_tag(tokens)  # Label each word (noun, verb, adjective, etc.)
        chunked = ne_chunk(tagged)  # Group words into named entities (countries, orgs, people)
        for subtree in chunked:
            if isinstance(subtree, Tree):
                entity_type = subtree.label()
                entity_name = " ".join(word for word, tag in subtree.leaves())
                if entity_type in entities:
                    entities[entity_type].append(entity_name)
    except Exception:
        pass
    return entities


def compute_sentiment(text):
    """Return VADER sentiment scores (compound, negative, neutral, positive)."""
    scores = sid.polarity_scores(text)
    return {
        "compound": round(scores["compound"], 3),
        "negative": round(scores["neg"], 3),
        "neutral": round(scores["neu"], 3),
        "positive": round(scores["pos"], 3),
    }


def compute_nlp_risk_score(text, base_score):
    """
    Compute risk score by combining:
      - Keyword escalation weights (matched against headline)
      - VADER sentiment (negative = higher threat)
      - Named entity density (more entities = more significant)
    Returns: final_score, matched_keywords, sentiment_dict, entities_dict
    """
    upper_text = text.upper()
    tokens = upper_text.split()

    # 1. Keyword-weighted escalation score
    keyword_boost = 0
    matched_keywords = []
    for keyword, weight in ESCALATION_WEIGHTS.items():
        if keyword in upper_text:
            keyword_boost += weight
            matched_keywords.append(keyword)

    # 2. Sentiment-based adjustment (negative sentiment = higher threat)
    sentiment = compute_sentiment(text)
    sentiment_boost = 0
    if sentiment["compound"] <= -0.5:  # Very negative headline = +10 risk
        sentiment_boost = 10
    elif sentiment["compound"] <= -0.2:  # Moderately negative = +5 risk
        sentiment_boost = 5
    elif sentiment["compound"] >= 0.3:  # Positive headline = -3 risk (de-escalation)
        sentiment_boost = -3

    # 3. Entity density (more named entities = more geopolitically significant)
    entities = extract_named_entities(text)
    entity_count = sum(len(values) for values in entities.values())
    entity_boost = min(entity_count * 2, 10)  # More named entities = more significant (max +10)

    # Combine all three NLP signals into final risk score
    # Formula: base + keywords + sentiment + entities, capped between 0-100
    final_score = base_score + keyword_boost + sentiment_boost + entity_boost
    final_score = max(0, min(100, final_score))

    return final_score, matched_keywords, sentiment, entities


def refine_intel(text, city_name, country_name, country_adj):
    """Clean raw RSS headline into military-format intelligence string."""
    text = text.upper()
    city_upper = city_name.upper()
    country_upper = country_name.upper()

    # Remove source attributions
    text = re.sub(r"\s+[-|\u2014\u2013]\s+.*$", "", text)
    text = re.sub(fr"[;,\u2014-]\s*[A-Z\s]{{2,25}} (SAYS|CLAIMS|WARNS|REPORTS|INVESTIGATING|REGRETS).*$", "", text)
    text = re.sub(r"^['\"]*(AND|AS|BUT|SO|HOW|WHY|WHAT|WHEN|WATCH|BREAKING|REPORT|SITREP)[\s:]+", "", text)

    is_strike = any(word in text for word in ["STRIKE", "BOMB", "ATTACK", "STRIKED", "EXPLOSION", "DRONE"])

    # If a real attack is detected, use tactical dossier templates
    if city_upper in TACTICAL_DOSSIERS and is_strike:
        return random.choice(TACTICAL_DOSSIERS[city_upper])

    actor = f"{country_adj} FORCES"
    if city_upper in ["GAZA CITY", "TEL AVIV", "RAFAH", "KHAN YOUNIS"] or "IDF" in text:
        actor = "ISRAELI MILITARY"
    elif city_upper == "KHARTOUM" or city_upper == "EL-FASHER":
        actor = "SUDANESE ARMED FORCES"
    elif "RUSSIA" in text:
        actor = "RUSSIAN FORCES"

    # Strip country/city name from start of headline
    text = re.sub(fr"^{country_upper} (SAYS|CLAIMS|WARNS|REPORTS|ITS) ", "", text)
    text = re.sub(fr"^{country_upper}[:\s]+", "", text)
    text = re.sub(fr"^{city_upper}[:\s]+", "", text)

    verb_map = {
        "CONDUCTS": "CONDUCT", "ELIMINATES": "NEUTRALIZE", "DETAINS": "DETAIN",
        "STRIKES": "CONDUCT STRIKE", "TARGETS": "TARGET", "LAUNCHES": "LAUNCH"
    }
    words = text.split()
    if words and words[0] in verb_map:
        text = f"{actor} {verb_map[words[0]]} {' '.join(words[1:])}"

    # Final cleanup: remove punctuation, reject if too long, ensure ends with period
    text = text.replace(";", "").replace("-", " ")
    text = re.sub(r'[\-\u2014,:|]\s*$', '', text).strip()
    if len(text.split()) > 16:
        return "NULL_SIGNAL"
    if text and not text.endswith("."):
        text += "."

    high_stakes = [
        "STRIKE", "WAR", "COMBAT", "MILITARY", "FORCES", "NEUTRALIZE", "DETAIN",
        "SECURITY", "BORDER", "INTERCEPT", "TARGET", "RAID", "DRONE", "MISSILE",
        "ATTACK", "ASSAULT", "BOMB", "SHELL", "ARTILLERY", "DEFENSE"
    ]
    if not any(word in text for word in high_stakes) or city_upper not in text:
        return "NULL_SIGNAL"

    return text


# ==========================================
# 3. RSS DATA INGESTION
# Fetches Google News RSS feeds per city
# Runs headlines through NLP pipeline
# Falls back to static status for low-threat cities
# ==========================================
STATUS_REPORTS = {
    "Auckland": "INFRASTRUCTURE MONITOR: NOMINAL NETWORK TRAFFIC RECORDED IN REGIONAL HUB.",
    "Lagos": "SECURITY UPDATE: LOCAL FORCES MAINTAINING STANDARD PERIMETER POSTURE.",
    "New York City": "DOMESTIC SECURITY: NO DEVIATIONS DETECTED AT KEY TRANSPORTATION NODES.",
    "Washington D.C.": "NATIONAL SECURITY: STANDARD PROTECTIVE MEASURES ACTIVE AT ALL FEDERAL SITES.",
    "Tokyo": "MARITIME SURVEILLANCE: COAST GUARD PATROLS REPORT NO UNUSUAL ACTIVITY.",
    "Mumbai": "PATTERN ANALYSIS: BACKGROUND SIGNALS REMAIN WITHIN NOMINAL LEVELS.",
    "New Delhi": "BORDER MONITOR: STANDARD PATROL ROUTINES ALONG NORTHERN FRONTIER.",
    "Shanghai": "NAVAL LOG: MONITORING PLANNED MARITIME MANEUVERS NEAR HARBOR ENTRANCE.",
    "Beijing": "SIGINT OVERVIEW: MILITARY COMMUNICATIONS TRAFFIC AT BASELINE LEVELS.",
    "London": "URBAN MONITOR: STANDARD VISIBILITY MAINTAINED BY SECURITY UNITS.",
    "Sydney": "SIGINT SCAN: REGIONAL COMMUNICATIONS GRIDS OPERATING AT BASELINE LEVELS.",
    "Seoul": "DMZ MONITOR: STANDARD SURVEILLANCE POSTURE ALONG DEMILITARIZED ZONE.",
    "Ankara": "BORDER PATROL: ROUTINE MONITORING OF SOUTHERN FRONTIER CROSSINGS.",
    "Riyadh": "COALITION LOG: AIR DEFENSE SYSTEMS OPERATING AT STANDARD READINESS.",
}

# Cities that only show fallback status (low-threat monitoring)
MONITOR_ONLY = list(STATUS_REPORTS.keys())


# Classify risk score into threat levels
def get_status_info(score, is_fallback=False):
    if is_fallback:
        return "LOW", "#ffffff", 15
    if score >= 85:                        # 85-100 = CRITICAL (red)
        return "CRITICAL", "#ff3b30", score
    if score >= 65:                        # 65-84 = HIGH (orange)
        return "HIGH", "#ff9f0a", score
    if score >= 45:                        # 45-64 = MEDIUM (yellow)
        return "MEDIUM", "#ffd60a", score
    return "LOW", "#ffffff", score         # 0-44 = LOW (white)


def fetch_real_intelligence():
    """Fetch Google News RSS for each node, run NLP pipeline, assign risk scores."""
    print("[*] SYNCING GLOBAL SIGNAL GRID...")
    print(f"[*] MONITORING {len(BASE_NODES)} NODES ACROSS {len(set(node['region'] for node in BASE_NODES))} REGIONS")
    headers = {'User-Agent': 'Mozilla/5.0'}
    processed_data = []

    for node in BASE_NODES:
        name = node['name']
        base_score = node['base']
        final_intel = ""
        is_fallback = False
        nlp_keywords = []
        nlp_sentiment = {"compound": 0, "negative": 0, "neutral": 1, "positive": 0}
        nlp_entities = {"GPE": [], "PERSON": [], "ORGANIZATION": []}
        raw_headline = ""

        if name not in MONITOR_ONLY:
            try:
                # Build Google News RSS search URL: "CityName" + conflict keywords
                query = f"%22{name}%22+(Military+OR+Conflict+OR+Strike+OR+Attack)"
                url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
                r = requests.get(url, headers=headers, timeout=5)
                feed = feedparser.parse(r.content)  # Parse RSS XML into Python objects  # Parse RSS XML into Python objects
                if feed.entries:
                    # Try up to 15 headlines until one passes NLP quality filter
                    for entry in feed.entries[:15]:
                        raw_headline = entry.title
                        candidate = refine_intel(entry.title, name, node['country'], node['adj'])
                        if candidate != "NULL_SIGNAL":
                            final_intel = candidate
                            break
            except Exception as e:
                print(f"    [!] RSS FAULT: {name} — {e}")

        # If no valid headline found, use a pre-written fallback status message
        if not final_intel:
            final_intel = STATUS_REPORTS.get(name, f"SECTOR MONITORING: {name.upper()} DATA STREAM REMAINS NOMINAL.")
            is_fallback = True

        if not final_intel.endswith("."):
            final_intel += "."

        # Run NLP pipeline on live headlines (skip for fallback/low-threat cities)
        if not is_fallback:
            analysis_text = raw_headline if raw_headline else final_intel
            current_score, nlp_keywords, nlp_sentiment, nlp_entities = compute_nlp_risk_score(analysis_text, base_score)  # Run all 3 NLP signals
        else:
            current_score = base_score

        status_label, color, final_score = get_status_info(current_score, is_fallback)

        processed_data.append({
            "name": name,
            "country": node['country'],
            "region": node['region'],
            "intel": final_intel,
            "source": "SAT_UPLINK_0" + str(random.randint(1, 9)),
            "risk": final_score,
            "status": status_label,
            "color": color,
            "lat": node['lat'],
            "lon": node['lon'],
            "nlp_keywords": nlp_keywords,
            "nlp_sentiment": nlp_sentiment,
            "nlp_entities": nlp_entities,
        })

        # Log each node's status to terminal during startup
        if is_fallback:
            print(f"    [FALLBACK] {name} — RISK: {final_score}% | {status_label}")
        else:
            print(f"    [    LIVE] {name} — RISK: {final_score}% | {status_label}")

    print(f"[*] GRID SYNC COMPLETE — {len(processed_data)} NODES ONLINE")
    return sorted(processed_data, key=lambda x: x['risk'], reverse=True)


# ==========================================
# 4. SITREP — Daily Situation Report Generator
# Outputs: executive summary, top 10 threats
# Regional breakdown, geospatial coordinates
# Saved to sitreps in a timestamped .txt file
# ==========================================
def generate_sitrep(data):
    """Generate daily Situation Report with threat summary and regional breakdown."""
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    date_string = now.strftime("%Y%m%d")

    critical = [node for node in data if node['status'] == 'CRITICAL']
    high = [node for node in data if node['status'] == 'HIGH']
    medium = [node for node in data if node['status'] == 'MEDIUM']
    low = [node for node in data if node['status'] == 'LOW']

    # Group by region
    regions = {}
    for node in data:
        region = node['region']
        if region not in regions:
            regions[region] = []
        regions[region].append(node)

    lines = []
    lines.append("=" * 80)
    lines.append("SENTINEL // DAILY SITUATION REPORT (SITREP)")
    lines.append("=" * 80)
    lines.append(f"GENERATED:     {timestamp}")
    lines.append(f"REPORT ID:     SITREP-{date_string}-{random.randint(1000,9999)}")
    lines.append(f"CLASSIFICATION: UNCLASSIFIED // FOR OFFICIAL USE ONLY")
    lines.append(f"NODES ONLINE:  {len(data)}")
    lines.append(f"REGIONS:       {len(regions)}")
    lines.append("")
    lines.append("-" * 80)
    lines.append("1. EXECUTIVE SUMMARY")
    lines.append("-" * 80)
    lines.append(f"   CRITICAL ZONES:  {len(critical)}")
    lines.append(f"   HIGH ZONES:      {len(high)}")
    lines.append(f"   MEDIUM ZONES:    {len(medium)}")
    lines.append(f"   LOW ZONES:       {len(low)}")
    lines.append(f"   AVERAGE RISK:    {sum(node['risk'] for node in data) / len(data):.1f}%")
    lines.append("")

    # Top threats
    lines.append("-" * 80)
    lines.append("2. TOP THREAT ASSESSMENT")
    lines.append("-" * 80)
    for i, node in enumerate(data[:10], 1):
        lines.append(f"   {i:>2}. {node['name']:<22} [{node['status']:>8}] RISK: {node['risk']}%")
        lines.append(f"       REGION: {node['region']}")
        lines.append(f"       INTEL:  {node['intel']}")
        if node['nlp_keywords']:
            lines.append(f"       NLP ESCALATION KEYWORDS: {', '.join(node['nlp_keywords'][:5])}")
        if node['nlp_sentiment']['compound'] != 0:
            lines.append(f"       SENTIMENT: compound={node['nlp_sentiment']['compound']}")
        gpe = node['nlp_entities'].get('GPE', [])
        if gpe:
            lines.append(f"       ENTITIES DETECTED: {', '.join(gpe[:5])}")
        lines.append("")

    # Regional breakdown
    lines.append("-" * 80)
    lines.append("3. REGIONAL BREAKDOWN")
    lines.append("-" * 80)
    for region, nodes in sorted(regions.items()):
        avg_risk = sum(node_item['risk'] for node_item in nodes) / len(nodes)
        max_node = max(nodes, key=lambda x: x['risk'])
        lines.append(f"   {region.upper()}")
        lines.append(f"       Nodes: {len(nodes)} | Avg Risk: {avg_risk:.1f}% | Hotspot: {max_node['name']} ({max_node['risk']}%)")
        lines.append("")

    # Geospatial summary
    lines.append("-" * 80)
    lines.append("4. GEOSPATIAL COORDINATES (ACTIVE ZONES)")
    lines.append("-" * 80)
    lines.append(f"   {'NODE':<22} {'LAT':>8} {'LON':>10} {'RISK':>6}  STATUS")
    lines.append(f"   {'-'*22} {'-'*8} {'-'*10} {'-'*6}  {'-'*8}")
    for node in data:
        if node['risk'] >= 45:
            lines.append(f"   {node['name']:<22} {node['lat']:>8.2f} {node['lon']:>10.2f} {node['risk']:>5}%  {node['status']}")

    lines.append("")
    lines.append("=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)

    sitrep_text = "\n".join(lines)

    # Save to file
    os.makedirs("sitreps", exist_ok=True)
    filename = f"sitreps/SITREP_{date_string}_{now.strftime('%H%M%S')}.txt"
    with open(filename, 'w') as file:
        file.write(sitrep_text)
    print(f"[*] SITREP SAVED: {filename}")
    return sitrep_text, filename


# ==========================================
# 5. INITIALIZE — Fetch data and generate SITREP on startup
# ==========================================
LIVE_DATA = fetch_real_intelligence()
SITREP_TEXT, SITREP_FILE = generate_sitrep(LIVE_DATA)

# ==========================================
# 6. DASHBOARD UI
# ==========================================
app = dash.Dash(__name__, title='SENTINEL // OSINT', update_title=None)

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}<title>SENTINEL</title>{%favicon%}{%css%}
        <style>
            body { background-color: #000; color: #f2f2f7; font-family: -apple-system, system-ui, sans-serif; margin: 0; user-select: text; }
            .terminal-grid { display: grid; grid-template-columns: 420px 1fr 320px; grid-template-rows: 100px 1fr; height: 100vh; gap: 1px; background: #1c1c1e; }
            .module { background: #000; padding: 40px; overflow-y: auto; }
            .header-container { grid-column: 1 / span 3; background: #000; display: flex; justify-content: space-between; align-items: center; padding: 0 60px; border-bottom: 1px solid #2c2c2e; height: 100px; overflow: visible !important; z-index: 1000; }
            .data-row { padding: 16px 20px; border-bottom: 1px solid #1c1c1e; border-left: 5px solid transparent; cursor: pointer; display: flex; justify-content: space-between; transition: 0.2s; align-items: center; min-height: 70px; }
            .data-row:hover { background: #1c1c1e; }
            .city-label { font-weight: 700; font-size: 15px; color: #ffffff; }
            .sub-info { font-size: 10px; color: #8e8e93 !important; margin-top: 4px; display: block; font-family: 'Courier New', monospace; font-weight: bold; line-height: 1.3; }
            .status-tag { font-size: 9px; font-weight: 800; height: 24px; line-height: 22px; width: 85px; border: 1px solid; text-align: center; font-family: 'Courier New', monospace; display: inline-block; box-sizing: border-box; flex-shrink: 0; }
            .risk-bar { height: 6px; background: #1c1c1e; width: 100%; margin-top: 15px; position: relative; border-radius: 3px; }
            .risk-fill { height: 100%; position: absolute; left: 0; top: 0; transition: width 0.8s ease-in-out; border-radius: 3px; }
            @keyframes blink-green { 0% { opacity: 1; box-shadow: 0 0 12px #32d74b; } 50% { opacity: 0.3; box-shadow: 0 0 0px #32d74b; } 100% { opacity: 1; box-shadow: 0 0 12px #32d74b; } }
            .live-dot { height: 10px; width: 10px; background-color: #32d74b; border-radius: 50%; display: inline-block; margin-right: 15px; animation: blink-green 2s infinite ease-in-out; }
            .scanline { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.05) 50%); z-index: 1000; pointer-events: none; background-size: 100% 4px; }
            .timezone-dropdown { min-width: 160px; }
            .timezone-dropdown .Select-control { background-color: #1c1c1e !important; border: 1px solid #2c2c2e !important; height: 34px !important; cursor: pointer; }
            .timezone-dropdown .Select-placeholder, .timezone-dropdown .Select-value-label { color: #8e8e93 !important; font-family: monospace; font-size: 11px; line-height: 32px !important; }
            .timezone-dropdown .Select-menu-outer { background-color: #1c1c1e !important; border: 1px solid #2c2c2e !important; top: 100% !important; }
            .timezone-dropdown .VirtualizedSelectOption { background-color: #1c1c1e !important; color: #8e8e93 !important; font-family: monospace; font-size: 11px; padding: 10px; }
            .timezone-dropdown .VirtualizedSelectFocusedOption { background-color: #2c2c2e !important; color: #fff !important; }
            .tab-button { background: none; border: 1px solid #2c2c2e; color: #8e8e93; padding: 8px 16px; font-family: monospace; font-size: 11px; cursor: pointer; font-weight: 700; letter-spacing: 1px; }
            .tab-button:hover { background: #1c1c1e; color: #fff; }
            .tab-button.active { background: #1c1c1e; color: #ff3b30; border-color: #ff3b30; }
        </style>
    </head>
    <body><div class="scanline"></div>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body>
</html>
'''

# ==========================================
# 7. GEOSPATIAL MAP — Plotly Scattergeo
# Plots all 54 nodes on a world map
# Marker size = risk level, color = threat color
# ==========================================
def build_globe_map():
    """Build Plotly scattergeo map with all nodes colored by threat level."""
    fig = go.Figure()

    for node in LIVE_DATA:
        fig.add_trace(go.Scattergeo(
            lat=[node['lat']],
            lon=[node['lon']],
            text=f"{node['name'].upper()}<br>{node['country']}<br>RISK: {node['risk']}% [{node['status']}]<br>{node['intel'][:80]}...",
            hoverinfo='text',
            marker=dict(
                size=max(6, node['risk'] / 6),
                color=node['color'],
                opacity=0.9,
                line=dict(width=1, color='#2c2c2e'),
                symbol='circle',
            ),
            name=node['name'],
            showlegend=False,
        ))

    fig.update_geos(
        projection_type="natural earth",
        showland=True, landcolor="#0d0d0d",
        showocean=True, oceancolor="#000000",
        showlakes=False,
        showcountries=True, countrycolor="#1c1c1e",
        showcoastlines=True, coastlinecolor="#2c2c2e",
        showframe=False,
        bgcolor="#000000",
    )
    fig.update_layout(
        height=500,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='#000',
        plot_bgcolor='#000',
        font=dict(color='#8e8e93', family='monospace'),
    )
    return fig


# ==========================================
# 8. LAYOUT
# ==========================================
app.layout = html.Div(className="terminal-grid", children=[
    html.Div(className="header-container", children=[
        html.Div([
            html.H1("SENTINEL // NODE MONITOR", style={'margin': 0, 'letterSpacing': '4px', 'fontSize': '28px', 'fontWeight': '800'}),
            html.P(f"Strategic intelligence grid — {len(BASE_NODES)} nodes across {len(set(node['region'] for node in BASE_NODES))} regions.",
                   style={'fontSize': '11px', 'color': '#8e8e93', 'marginTop': '4px', 'maxWidth': '700px'})
        ]),
        html.Div([
            html.Div([
                html.Span("TIMEZONE:", style={'fontSize': '9px', 'color': '#48484a', 'marginRight': '10px', 'fontWeight': '800', 'fontFamily': 'monospace'}),
                dcc.Dropdown(
                    id='timezone-selector',
                    options=[
                        {'label': 'UTC (ZULU)', 'value': 'UTC'},
                        {'label': 'LOCAL (AUTO)', 'value': 'LOCAL'},
                        {'label': 'EST (NEW YORK)', 'value': 'US/Eastern'},
                        {'label': 'GMT (LONDON)', 'value': 'Europe/London'},
                        {'label': 'JST (TOKYO)', 'value': 'Asia/Tokyo'}
                    ],
                    value='UTC',
                    clearable=False,
                    className="timezone-dropdown"
                ),
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'}),
            html.Div(id="utc-clock", style={'fontSize': '24px', 'color': '#ff3b30', 'fontWeight': '700', 'fontFamily': 'monospace', 'textAlign': 'right', 'letterSpacing': '2px'})
        ])
    ]),

    # SIDEBAR — NODE LIST
    html.Div(className="module", children=[
        html.Div([
            html.Span(className="live-dot"),
            html.Span(f"NETWORK SENSORS ({len(LIVE_DATA)})", style={'color': '#8e8e93', 'fontSize': '12px', 'fontWeight': '700', 'letterSpacing': '2px'})
        ], style={'marginBottom': '20px'}),
        html.Div([
            html.Div([
                html.Div([
                    html.Span(city['name'].upper(), className="city-label"),
                    html.Span(f"SCORE: {city['risk']}% // {city['region'].upper()}", className="sub-info")
                ]),
                html.Span(city['status'], style={'color': city['color'], 'borderColor': city['color']}, className="status-tag")
            ], className="data-row", id={'type': 'city-row', 'index': city['name']}, n_clicks=0)
            for city in LIVE_DATA
        ])
    ]),

    # CENTER PANEL — 3 tabs: Intel briefing, World map, SITREP report
    html.Div(className="module", children=[
        html.Div([
            html.Button("INTELLIGENCE DOSSIER", id="tab-intel", className="tab-button active", n_clicks=1),
            html.Button("GEOSPATIAL MAP", id="tab-map", className="tab-button", n_clicks=0),
            html.Button("SITREP", id="tab-sitrep", className="tab-button", n_clicks=0),
        ], style={'display': 'flex', 'gap': '10px', 'marginBottom': '30px'}),
        html.Div(id="center-content", children=[
            html.Div("SELECT A NODE TO BEGIN ANALYSIS.", style={'color': '#3a3a3c', 'textAlign': 'center', 'marginTop': '250px', 'fontSize': '16px', 'fontWeight': '600'})
        ])
    ]),

    # ANALYTICS SIDEBAR
    html.Div(className="module", children=[
        html.Div("SIGNAL ANALYTICS", style={'color': '#8e8e93', 'fontSize': '12px', 'fontWeight': '700', 'letterSpacing': '3px', 'marginBottom': '30px'}),
        html.Div(id="dynamic-metrics", children=[
            # Default summary stats
            html.Div([
                html.Div("TOTAL NODES", style={'fontSize': '11px', 'color': '#48484a', 'marginBottom': '8px', 'fontWeight': '700'}),
                html.Div(str(len(LIVE_DATA)), style={'color': '#fff', 'fontSize': '36px', 'fontWeight': '800', 'fontFamily': 'monospace'})
            ], style={'marginBottom': '30px'}),
            html.Div([
                html.Div("CRITICAL", style={'fontSize': '11px', 'color': '#48484a', 'marginBottom': '8px', 'fontWeight': '700'}),
                html.Div(str(len([node for node in LIVE_DATA if node['status'] == 'CRITICAL'])), style={'color': '#ff3b30', 'fontSize': '36px', 'fontWeight': '800', 'fontFamily': 'monospace'})
            ], style={'marginBottom': '30px'}),
            html.Div([
                html.Div("HIGH", style={'fontSize': '11px', 'color': '#48484a', 'marginBottom': '8px', 'fontWeight': '700'}),
                html.Div(str(len([node for node in LIVE_DATA if node['status'] == 'HIGH'])), style={'color': '#ff9f0a', 'fontSize': '36px', 'fontWeight': '800', 'fontFamily': 'monospace'})
            ], style={'marginBottom': '30px'}),
            html.Div([
                html.Div("AVG RISK", style={'fontSize': '11px', 'color': '#48484a', 'marginBottom': '8px', 'fontWeight': '700'}),
                html.Div(f"{sum(node['risk'] for node in LIVE_DATA) / len(LIVE_DATA):.1f}%", style={'color': '#ffd60a', 'fontSize': '36px', 'fontWeight': '800', 'fontFamily': 'monospace'})
            ]),
        ])
    ]),

    dcc.Interval(id='clock-interval', interval=1000, n_intervals=0),
    dcc.Store(id='active-tab', data='intel'),
    dcc.Store(id='selected-city', data=None),
])


# ==========================================
# 9. Dashboard Interactivity
# ==========================================
@app.callback(
    Output('utc-clock', 'children'),
    [Input('clock-interval', 'n_intervals'), Input('timezone-selector', 'value')]
)
def update_clock(tick, timezone_name):
    if timezone_name == 'LOCAL':
        now = datetime.datetime.now()
        suffix = "LCL"
    else:
        timezone = pytz.timezone(timezone_name)
        now = datetime.datetime.now(timezone)
        suffix = timezone_name.split('/')[-1] if '/' in timezone_name else timezone_name
    return f"{now.strftime('%H:%M:%S')} {suffix[:3].upper()}"


@app.callback(
    Output('active-tab', 'data'),
    [Input('tab-intel', 'n_clicks'), Input('tab-map', 'n_clicks'), Input('tab-sitrep', 'n_clicks')],
    prevent_initial_call=True
)
def switch_tab(intel_clicks, map_clicks, sitrep_clicks):
    context = callback_context
    if not context.triggered:
        return 'intel'
    button = context.triggered[0]['prop_id'].split('.')[0]
    if button == 'tab-map':
        return 'map'
    elif button == 'tab-sitrep':
        return 'sitrep'
    return 'intel'


# When a city is clicked or tab is switched, update the center panel, analytics, and tab styles
@app.callback(
    [Output('center-content', 'children'),
     Output('dynamic-metrics', 'children'),
     Output({'type': 'city-row', 'index': dash.ALL}, 'style'),
     Output('tab-intel', 'className'),
     Output('tab-map', 'className'),
     Output('tab-sitrep', 'className')],
    [Input({'type': 'city-row', 'index': dash.ALL}, 'n_clicks'),
     Input('active-tab', 'data')]
)
def handle_interaction(n_clicks_list, active_tab):
    context = callback_context

    # Determine selected city
    city_name = None
    if context.triggered:
        for trigger in context.triggered:
            try:
                clicked = json.loads(trigger['prop_id'].split('.')[0])
                if clicked.get('type') == 'city-row':
                    city_name = clicked['index']
            except (json.JSONDecodeError, KeyError):
                pass

    # Tab styling
    tab_classes = ["tab-button", "tab-button", "tab-button"]
    if active_tab == 'intel':
        tab_classes[0] = "tab-button active"
    elif active_tab == 'map':
        tab_classes[1] = "tab-button active"
    elif active_tab == 'sitrep':
        tab_classes[2] = "tab-button active"

    # Row styles
    row_styles = []
    for city in LIVE_DATA:
        if city_name and city['name'] == city_name:
            row_styles.append({'background': '#1c1c1e', 'borderLeft': '5px solid #ff3b30'})
        else:
            row_styles.append({'borderLeft': '5px solid transparent'})

    # MAP TAB — builds the geospatial world map with all 54 nodes
    if active_tab == 'map':
        fig = build_globe_map()
        content = html.Div([
            html.Div("GEOSPATIAL THREAT MAP", style={'color': '#8e8e93', 'fontSize': '12px', 'fontWeight': '700', 'letterSpacing': '3px', 'marginBottom': '20px'}),
            dcc.Graph(figure=fig, config={'displayModeBar': False}, style={'height': '500px'}),
            html.Div(f"NODES PLOTTED: {len(LIVE_DATA)} | COORDINATE SYSTEM: WGS84", style={'color': '#48484a', 'fontSize': '10px', 'fontFamily': 'monospace', 'marginTop': '15px'})
        ])
        return content, no_update, row_styles, *tab_classes

    # SITREP TAB
    if active_tab == 'sitrep':
        content = html.Div([
            html.Div([
                html.Span("DAILY SITUATION REPORT", style={'color': '#8e8e93', 'fontSize': '12px', 'fontWeight': '700', 'letterSpacing': '3px'}),
                html.Span(f" — {SITREP_FILE}", style={'color': '#48484a', 'fontSize': '10px', 'fontFamily': 'monospace', 'marginLeft': '15px'}),
            ], style={'marginBottom': '20px'}),
            html.Pre(SITREP_TEXT, style={
                'fontSize': '11px', 'color': '#8e8e93', 'fontFamily': 'Courier New, monospace',
                'background': '#0d0d0d', 'padding': '30px', 'border': '1px solid #2c2c2e',
                'borderRadius': '4px', 'whiteSpace': 'pre-wrap', 'lineHeight': '1.6',
                'maxHeight': '600px', 'overflowY': 'auto'
            })
        ])
        return content, no_update, row_styles, *tab_classes

    # INTEL TAB (default)
    if not city_name or sum(n_clicks_list) == 0:
        content = html.Div("SELECT A NODE TO BEGIN ANALYSIS.", style={'color': '#3a3a3c', 'textAlign': 'center', 'marginTop': '250px', 'fontSize': '16px', 'fontWeight': '600'})
        return content, no_update, row_styles, *tab_classes

    match = next((item for item in LIVE_DATA if item["name"] == city_name), LIVE_DATA[0])

    # NLP Analytics panel
    sentiment = match['nlp_sentiment']
    entities = match['nlp_entities']
    keywords = match['nlp_keywords']

    metrics = html.Div([
        html.Div([
            html.Div("THREAT RISK", style={'fontSize': '11px', 'color': '#48484a', 'marginBottom': '8px', 'fontWeight': '700'}),
            html.Div(className="risk-bar", children=html.Div(className="risk-fill", style={'width': f"{match['risk']}%", 'backgroundColor': match['color']})),
            html.Div(f"{match['risk']}%", style={'color': match['color'], 'fontSize': '28px', 'fontWeight': '800', 'fontFamily': 'monospace', 'marginTop': '10px'})
        ], style={'marginBottom': '25px'}),
        html.Div([
            html.Div("NLP SENTIMENT", style={'fontSize': '11px', 'color': '#48484a', 'marginBottom': '8px', 'fontWeight': '700'}),
            html.Div(f"{sentiment['compound']}", style={
                'color': '#ff3b30' if sentiment['compound'] < -0.2 else '#32d74b' if sentiment['compound'] > 0.2 else '#ffd60a',
                'fontSize': '28px', 'fontWeight': '800', 'fontFamily': 'monospace'
            }),
            html.Div(f"NEG: {sentiment['negative']} / NEU: {sentiment['neutral']} / POS: {sentiment['positive']}",
                     style={'color': '#48484a', 'fontSize': '9px', 'fontFamily': 'monospace', 'marginTop': '5px'})
        ], style={'marginBottom': '25px'}),
        html.Div([
            html.Div("ESCALATION KEYWORDS", style={'fontSize': '11px', 'color': '#48484a', 'marginBottom': '8px', 'fontWeight': '700'}),
            html.Div(", ".join(keywords[:6]) if keywords else "NONE DETECTED",
                     style={'color': '#ff9f0a' if keywords else '#3a3a3c', 'fontSize': '11px', 'fontFamily': 'monospace', 'lineHeight': '1.5'})
        ], style={'marginBottom': '25px'}),
        html.Div([
            html.Div("NAMED ENTITIES", style={'fontSize': '11px', 'color': '#48484a', 'marginBottom': '8px', 'fontWeight': '700'}),
            html.Div([
                html.Div(f"GPE: {', '.join(entities['GPE'][:3]) if entities['GPE'] else '—'}", style={'fontSize': '10px', 'color': '#8e8e93', 'fontFamily': 'monospace'}),
                html.Div(f"ORG: {', '.join(entities['ORGANIZATION'][:3]) if entities['ORGANIZATION'] else '—'}", style={'fontSize': '10px', 'color': '#8e8e93', 'fontFamily': 'monospace'}),
                html.Div(f"PER: {', '.join(entities['PERSON'][:3]) if entities['PERSON'] else '—'}", style={'fontSize': '10px', 'color': '#8e8e93', 'fontFamily': 'monospace'}),
            ])
        ], style={'marginBottom': '25px'}),
        html.Div([
            html.Div("COORDINATES", style={'fontSize': '11px', 'color': '#48484a', 'marginBottom': '8px', 'fontWeight': '700'}),
            html.Div(f"{match['lat']:.4f}°N, {match['lon']:.4f}°E", style={'color': '#8e8e93', 'fontSize': '12px', 'fontFamily': 'monospace'})
        ]),
    ])

    # Briefing panel
    briefing = html.Div([
        html.Div([
            html.Div(f"ORIGIN: {match['country'].upper()} // {match['region'].upper()}", style={'color': '#636366', 'fontSize': '13px', 'fontWeight': '700', 'fontFamily': 'monospace'}),
            html.H2(city_name.upper(), style={'fontSize': '64px', 'margin': '10px 0', 'color': '#fff', 'fontWeight': '900', 'letterSpacing': '-1px'}),
            html.Div(f"LAST SYNC: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC", style={'color': '#32d74b', 'fontSize': '14px', 'fontWeight': '700', 'fontFamily': 'monospace'}),
        ], style={'marginBottom': '50px'}),

        html.Div([
            html.Div([
                html.Span("REPORT CAPTURE: ", style={'color': '#8e8e93', 'fontWeight': '700', 'fontSize': '13px'}),
                html.Span(f"SOURCE_SAT_UPLINK_{match['source'][-2:]}", style={'color': '#48484a', 'fontSize': '12px', 'marginLeft': '10px', 'fontFamily': 'monospace'})
            ], style={'marginBottom': '25px'}),
            html.P(match['intel'], style={'fontSize': '24px', 'lineHeight': '1.4', 'color': match['color'], 'fontWeight': '800', 'margin': '0'}),
        ], style={'padding': '40px', 'border': f'1px solid {match["color"]}44', 'background': 'rgba(28,28,30,0.4)', 'borderRadius': '8px'}),
    ])

    return briefing, metrics, row_styles, *tab_classes


# ==========================================
# 10. RUN
# ==========================================
if __name__ == '__main__':
    print(f"\n[*] SENTINEL v2.0 — {len(BASE_NODES)} NODES | NLP ENGINE ONLINE | SITREP READY")
    print(f"[*] LAUNCHING DASHBOARD ON http://localhost:8091\n")
    app.run(debug=False, port=8091)
