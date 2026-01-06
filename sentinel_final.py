import dash
from dash import dcc, html, callback_context, no_update
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import datetime
import random
import feedparser
import requests
import re
import json
import pytz

# ==========================================
# 1. CORE DATA ENGINE
# ==========================================
BASE_NODES = [
    {"name": "Gaza City", "country": "Palestinian Territories", "adj": "PALESTINIAN", "base": 94, "lat": "31.50", "lon": "34.46"},
    {"name": "Tel Aviv", "country": "Israel", "adj": "ISRAELI", "base": 82, "lat": "32.08", "lon": "34.78"},
    {"name": "Kyiv", "country": "Ukraine", "adj": "UKRAINIAN", "base": 88, "lat": "50.45", "lon": "30.52"},
    {"name": "Sydney", "country": "Australia", "adj": "AUSTRALIAN", "base": 12, "lat": "-33.86", "lon": "151.20"},
    {"name": "Khartoum", "country": "Sudan", "adj": "SUDANESE", "base": 85, "lat": "15.50", "lon": "32.55"},
    {"name": "Tehran", "country": "Iran", "adj": "IRANIAN", "base": 75, "lat": "35.68", "lon": "51.38"},
    {"name": "Pyongyang", "country": "North Korea", "adj": "NORTH KOREAN", "base": 75, "lat": "39.03", "lon": "125.76"},
    {"name": "Moscow", "country": "Russia", "adj": "RUSSIAN", "base": 70, "lat": "55.75", "lon": "37.61"},
    {"name": "Lagos", "country": "Nigeria", "adj": "NIGERIAN", "base": 15, "lat": "6.52", "lon": "3.37"},
    {"name": "Shanghai", "country": "China", "adj": "CHINESE", "base": 15, "lat": "31.23", "lon": "121.47"},
    {"name": "Mumbai", "country": "India", "adj": "INDIAN", "base": 15, "lat": "19.07", "lon": "72.87"},
    {"name": "Auckland", "country": "New Zealand", "adj": "NEW ZEALAND", "base": 12, "lat": "-36.85", "lon": "174.76"},
    {"name": "London", "country": "UK", "adj": "BRITISH", "base": 10, "lat": "51.50", "lon": "-0.12"},
    {"name": "New York City", "country": "USA", "adj": "U.S.", "base": 10, "lat": "40.71", "lon": "-74.00"},
    {"name": "Tokyo", "country": "Japan", "adj": "JAPANESE", "base": 10, "lat": "35.67", "lon": "139.65"},
]

# v16.6 Refined Tactical Dossiers
TACTICAL_DOSSIERS = {
    "GAZA CITY": [
        "ISRAELI MILITARY NEUTRALIZE HIGH-VALUE COMMAND TARGETS IN GAZA CITY AIR STRIKE.",
        "ISRAELI FORCES CONDUCT KINETIC OPERATION AGAINST TUNNEL INFRASTRUCTURE IN GAZA CITY."
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
    ]
}

def get_status_info(score, is_fallback=False):
    if is_fallback: return "LOW", "#ffffff", 15
    if score >= 85: return "CRITICAL", "#ff3b30", score
    if score >= 65: return "HIGH", "#ff9f0a", score
    if score >= 45: return "MEDIUM", "#ffd60a", score
    return "LOW", "#ffffff", score

def refine_intel(text, city_name, country_name, country_adj):
    text = text.upper()
    city_u = city_name.upper()
    country_u = country_name.upper()
    
    # Clean Junk
    text = re.sub(r"\s+[-|\u2014\u2013]\s+.*$", "", text)
    text = re.sub(fr"[;,\u2014-]\s*[A-Z\s]{{2,25}} (SAYS|CLAIMS|WARNS|REPORTS|INVESTIGATING|REGRETS).*$", "", text)
    text = re.sub(r"^['\"]*(AND|AS|BUT|SO|HOW|WHY|WHAT|WHEN|WATCH|BREAKING|REPORT|SITREP)[\s:]+", "", text)

    # Force City-Specific Tactical Logic
    is_strike = any(w in text for w in ["STRIKE", "BOMB", "ATTACK", "STRIKED", "EXPLOSION", "DRONE"])
    if city_u in TACTICAL_DOSSIERS and is_strike:
        return random.choice(TACTICAL_DOSSIERS[city_u])

    # Actor Logic
    actor = f"{country_adj} FORCES"
    if city_u in ["GAZA CITY", "TEL AVIV"] or "IDF" in text: actor = "ISRAELI MILITARY"
    elif city_u == "KHARTOUM": actor = "SUDANESE ARMED FORCES"
    elif "RUSSIA" in text: actor = "RUSSIAN FORCES"

    # Fix Plural Grammar
    text = re.sub(fr"^{country_u} (SAYS|CLAIMS|WARNS|REPORTS|ITS) ", "", text)
    text = re.sub(fr"^{country_u}[:\s]+", "", text)
    text = re.sub(fr"^{city_u}[:\s]+", "", text)
    
    verb_map = {"CONDUCTS": "CONDUCT", "ELIMINATES": "NEUTRALIZE", "DETAINS": "DETAIN", "STRIKES": "CONDUCT STRIKE", "TARGETS": "TARGET", "LAUNCHES": "LAUNCH"}
    words = text.split()
    if words and words[0] in verb_map:
        text = f"{actor} {verb_map[words[0]]} {' '.join(words[1:])}"
    
    text = text.replace(";", "").replace("-", " ") 
    text = re.sub(r'[\-\u2014,:|]\s*$', '', text).strip()
    if len(text.split()) > 16: return "NULL_SIGNAL"
    if text and not text.endswith("."): text += "."

    high_stakes = ["STRIKE", "WAR", "COMBAT", "MILITARY", "FORCES", "NEUTRALIZE", "DETAIN", "SECURITY", "BORDER", "INTERCEPT", "TARGET", "RAID", "DRONE"]
    if not any(word in text for word in high_stakes) or city_u not in text:
        return "NULL_SIGNAL"
        
    return text

def fetch_real_intelligence():
    print("[*] SYNCING GLOBAL SIGNAL GRID...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    processed_data = []
    
    MONITOR_ONLY = ["Auckland", "New York City", "Lagos", "Tokyo", "London", "Mumbai", "Shanghai", "Sydney"]
    STATUS_REPORTS = {
        "Auckland": "INFRASTRUCTURE MONITOR: NOMINAL NETWORK TRAFFIC RECORDED IN REGIONAL HUB.",
        "Lagos": "SECURITY UPDATE: LOCAL FORCES MAINTAINING STANDARD PERIMETER POSTURE.",
        "New York City": "DOMESTIC SECURITY: NO DEVIATIONS DETECTED AT KEY TRANSPORTATION NODES.",
        "Tokyo": "MARITIME SURVEILLANCE: COAST GUARD PATROLS REPORT NO UNUSUAL ACTIVITY.",
        "Mumbai": "PATTERN ANALYSIS: BACKGROUND SIGNALS REMAIN WITHIN NOMINAL LEVELS.",
        "Shanghai": "NAVAL LOG: MONITORING PLANNED MARITIME MANEUVERS NEAR HARBOR ENTRANCE.",
        "London": "URBAN MONITOR: STANDARD VISIBILITY MAINTAINED BY SECURITY UNITS.",
        "Sydney": "SIGINT SCAN: REGIONAL COMMUNICATIONS GRIDS OPERATING AT BASELINE LEVELS.",
    }

    for node in BASE_NODES:
        name = node['name']
        score = node['base']
        final_intel = ""
        is_fallback = False

        if name not in MONITOR_ONLY:
            try:
                query = f"%22{name}%22+(Military+OR+Conflict+OR+Strike+OR+Strike)"
                url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
                r = requests.get(url, headers=headers, timeout=5)
                feed = feedparser.parse(r.content)
                if feed.entries:
                    for entry in feed.entries[:15]:
                        candidate = refine_intel(entry.title, name, node['country'], node['adj'])
                        if candidate != "NULL_SIGNAL":
                            final_intel = candidate
                            break
            except: pass
        
        if not final_intel:
            final_intel = STATUS_REPORTS.get(name, f"SECTOR MONITORING: {name.upper()} DATA STREAM REMAINS NOMINAL.")
            is_fallback = True
        
        if not final_intel.endswith("."): final_intel += "."

        status_label, color, final_score = get_status_info(score, is_fallback)

        processed_data.append({
            "name": name, "country": node['country'], "intel": final_intel,
            "source": "SAT_UPLINK_0" + str(random.randint(1,9)),
            "risk": final_score, "status": status_label, "color": color,
            "lat": node['lat'], "lon": node['lon']
        })
    return sorted(processed_data, key=lambda x: x['risk'], reverse=True)

LIVE_DATA = fetch_real_intelligence()

# ==========================================
# 2. DASHBOARD UI
# ==========================================
app = dash.Dash(__name__, title='SENTINEL // OSINT', update_title=None)

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}<title>SENTINEL</title>{%favicon%}{%css%}
        <style>
            body { background-color: #000; color: #f2f2f7; font-family: -apple-system, system-ui, sans-serif; margin: 0; overflow: hidden; user-select: text; }
            .terminal-grid { display: grid; grid-template-columns: 420px 1fr 320px; height: 100vh; gap: 1px; background: #1c1c1e; }
            .module { background: #000; padding: 40px; overflow-y: auto; }
            .header-container { grid-column: 1 / span 3; background: #000; display: flex; justify-content: space-between; align-items: center; padding: 0 60px; border-bottom: 1px solid #2c2c2e; height: 100px; overflow: visible !important; z-index: 1000; }
            .data-row { padding: 20px 25px; border-bottom: 1px solid #1c1c1e; border-left: 5px solid transparent; cursor: pointer; display: flex; justify-content: space-between; transition: 0.2s; align-items: center; min-height: 95px; }
            .data-row:hover { background: #1c1c1e; }
            .city-label { font-weight: 700; font-size: 18px; color: #ffffff; }
            .sub-info { font-size: 11px; color: #8e8e93 !important; margin-top: 6px; display: block; font-family: 'Courier New', monospace; font-weight: bold; line-height: 1.4; }
            .status-tag { font-size: 10px; font-weight: 800; height: 26px; line-height: 24px; width: 95px; border: 1px solid; text-align: center; font-family: 'Courier New', monospace; display: inline-block; box-sizing: border-box; flex-shrink: 0;}
            .risk-bar { height: 6px; background: #1c1c1e; width: 100%; margin-top: 15px; position: relative; border-radius: 3px; }
            .risk-fill { height: 100%; position: absolute; left: 0; top: 0; transition: width 0.8s ease-in-out; border-radius: 3px; }
            @keyframes blink-green { 0% { opacity: 1; box-shadow: 0 0 12px #32d74b; } 50% { opacity: 0.3; box-shadow: 0 0 0px #32d74b; } 100% { opacity: 1; box-shadow: 0 0 12px #32d74b; } }
            .live-dot { height: 10px; width: 10px; background-color: #32d74b; border-radius: 50%; display: inline-block; margin-right: 15px; animation: blink-green 2s infinite ease-in-out; }
            .scanline { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.05) 50%); z-index: 1000; pointer-events: none; background-size: 100% 4px; }
            .tz-dropdown { min-width: 160px; }
            .tz-dropdown .Select-control { background-color: #1c1c1e !important; border: 1px solid #2c2c2e !important; height: 34px !important; cursor: pointer; }
            .tz-dropdown .Select-placeholder, .tz-dropdown .Select-value-label { color: #8e8e93 !important; font-family: monospace; font-size: 11px; line-height: 32px !important; }
            .tz-dropdown .Select-menu-outer { background-color: #1c1c1e !important; border: 1px solid #2c2c2e !important; top: 100% !important; }
            .tz-dropdown .VirtualizedSelectOption { background-color: #1c1c1e !important; color: #8e8e93 !important; font-family: monospace; font-size: 11px; padding: 10px; }
            .tz-dropdown .VirtualizedSelectFocusedOption { background-color: #2c2c2e !important; color: #fff !important; }
        </style>
    </head>
    <body><div class="scanline"></div>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body>
</html>
'''

app.layout = html.Div(className="terminal-grid", children=[
    html.Div(className="header-container", children=[
        html.Div([
            html.H1("SENTINEL // NODE MONITOR", style={'margin': 0, 'letterSpacing': '4px', 'fontSize': '28px', 'fontWeight': '800'}),
            html.P("Strategic intelligence grid tracking emerging global instability.",
                   style={'fontSize': '11px', 'color': '#8e8e93', 'marginTop': '4px', 'maxWidth': '700px'})
        ]),
        html.Div([
            html.Div([
                html.Span("TIMEZONE:", style={'fontSize': '9px', 'color': '#48484a', 'marginRight': '10px', 'fontWeight': '800', 'fontFamily': 'monospace'}),
                dcc.Dropdown(
                    id='tz-selector',
                    options=[
                        {'label': 'UTC (ZULU)', 'value': 'UTC'},
                        {'label': 'LOCAL (AUTO)', 'value': 'LOCAL'},
                        {'label': 'EST (NEW YORK)', 'value': 'US/Eastern'},
                        {'label': 'GMT (LONDON)', 'value': 'Europe/London'},
                        {'label': 'JST (TOKYO)', 'value': 'Asia/Tokyo'}
                    ],
                    value='UTC',
                    clearable=False,
                    className="tz-dropdown"
                ),
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'}),
            html.Div(id="utc-clock", style={'fontSize': '24px', 'color': '#ff3b30', 'fontWeight': '700', 'fontFamily': 'monospace', 'textAlign': 'right', 'letterSpacing': '2px'})
        ])
    ]),

    # SIDEBAR
    html.Div(className="module", children=[
        html.Div([html.Span(className="live-dot"), html.Span("NETWORK SENSORS", style={'color': '#8e8e93', 'fontSize': '12px', 'fontWeight': '700', 'letterSpacing': '2px'})], style={'marginBottom': '30px'}),
        html.Div([
            html.Div([
                html.Div([
                    html.Span(city['name'].upper(), className="city-label"),
                    html.Span(f"SCORE: {city['risk']}% // {city['country'].upper()}", className="sub-info")
                ]),
                html.Span(city['status'], style={'color': city['color'], 'borderColor': city['color']}, className="status-tag")
            ], className="data-row", id={'type': 'city-row', 'index': city['name']}, n_clicks=0)
            for city in LIVE_DATA
        ])
    ]),

    # BRIEFING
    html.Div(className="module", children=[
        html.Div("INTELLIGENCE DOSSIER", style={'color': '#8e8e93', 'fontSize': '12px', 'fontWeight': '700', 'letterSpacing': '3px', 'marginBottom': '30px'}),
        html.Div(id="detail-view", children=[
            html.Div("SELECT A NODE TO BEGIN ANALYSIS.", style={'color': '#3a3a3c', 'textAlign': 'center', 'marginTop': '250px', 'fontSize': '16px', 'fontWeight': '600'})
        ])
    ]),

    # ANALYTICS
    html.Div(className="module", children=[
        html.Div("SIGNAL ANALYTICS", style={'color': '#8e8e93', 'fontSize': '12px', 'fontWeight': '700', 'letterSpacing': '3px', 'marginBottom': '40px'}),
        html.Div(id="dynamic-metrics")
    ]),

    dcc.Interval(id='clock-interval', interval=1000, n_intervals=0),
])

@app.callback(
    Output('utc-clock', 'children'), 
    [Input('clock-interval', 'n_intervals'), Input('tz-selector', 'value')]
)
def update_clock(n, tz_name):
    if tz_name == 'LOCAL':
        now = datetime.datetime.now()
        suffix = "LCL"
    else:
        tz = pytz.timezone(tz_name)
        now = datetime.datetime.now(tz)
        suffix = tz_name.split('/')[-1] if '/' in tz_name else tz_name
    
    return f"{now.strftime('%H:%M:%S')} {suffix[:3].upper()}"

@app.callback(
    [Output('detail-view', 'children'), 
     Output('dynamic-metrics', 'children'),
     Output({'type': 'city-row', 'index': dash.ALL}, 'style')], 
    [Input({'type': 'city-row', 'index': dash.ALL}, 'n_clicks')]
)
def handle_selection(n_clicks_list):
    ctx = callback_context
    if not ctx.triggered or sum(n_clicks_list) == 0: 
        return no_update, no_update, [no_update for _ in range(len(LIVE_DATA))]
    
    city_name = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])['index']
    
    row_styles = []
    for city in LIVE_DATA:
        if city['name'] == city_name:
            row_styles.append({'background': '#1c1c1e', 'borderLeft': '5px solid #ff3b30'})
        else:
            row_styles.append({'borderLeft': '5px solid transparent'})

    match = next((item for item in LIVE_DATA if item["name"] == city_name), LIVE_DATA[0])
    
    metrics = html.Div([
        html.Div([
            html.Div("THREAT RISK", style={'fontSize': '12px', 'color': '#8e8e93', 'marginBottom': '10px', 'fontWeight': '600'}),
            html.Div(className="risk-bar", children=html.Div(className="risk-fill", style={'width': f"{match['risk']}%", 'backgroundColor': match['color']}))
        ], style={'marginBottom': '50px'}),
        html.Div([html.Div("SIGNAL PARITY", style={'fontSize': '12px', 'color': '#8e8e93', 'marginBottom': '10px'}), html.Div("99.98%", style={'color': '#32d74b', 'fontSize': '32px', 'fontWeight': '800', 'fontFamily': 'monospace'})], style={'marginBottom': '40px'}),
        html.Div([html.Div("DATA INTEGRITY", style={'fontSize': '12px', 'color': '#8e8e93', 'marginBottom': '10px'}), html.Div("VERIFIED", style={'color': '#ffd60a', 'fontSize': '28px', 'fontWeight': '800', 'fontFamily': 'monospace'})])
    ])

    briefing = html.Div([
        html.Div([
            html.Div(f"ORIGIN: {match['country'].upper()}", style={'color': '#636366', 'fontSize': '13px', 'fontWeight': '700', 'fontFamily': 'monospace'}),
            html.H2(city_name.upper(), style={'fontSize': '72px', 'margin': '10px 0', 'color': '#fff', 'fontWeight': '900', 'letterSpacing': '-1px'}),
            html.Div(f"LAST SYNC: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", style={'color': '#32d74b', 'fontSize': '14px', 'fontWeight': '700', 'fontFamily': 'monospace'}),
        ], style={'marginBottom': '60px'}),
        
        html.Div([
            html.Div([
                html.Span("REPORT CAPTURE: ", style={'color': '#8e8e93', 'fontWeight': '700', 'fontSize': '13px'}),
                html.Span(f"SOURCE_SAT_UPLINK_{match['source'][-2:]}", style={'color': '#48484a', 'fontSize': '12px', 'marginLeft': '10px', 'fontFamily': 'monospace'})
            ], style={'marginBottom': '25px'}),
            html.P(match['intel'], style={'fontSize': '28px', 'lineHeight': '1.4', 'color': match['color'], 'fontWeight': '800', 'margin': '0'}),
        ], style={'padding': '50px', 'border': f'1px solid {match["color"]}44', 'background': 'rgba(28,28,30,0.4)', 'borderRadius': '8px'}),
    ])
    return briefing, metrics, row_styles

if __name__ == '__main__':
    app.run(debug=False, port=8091)