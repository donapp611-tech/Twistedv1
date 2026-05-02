import os
from typing import Dict, Optional

import requests #these are the only non-standard dependencies, install with `pip install requests python-dotenv flask flask-limiter python-json-logger`
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from pythonjsonlogger import jsonlogger

import providers
load_dotenv()

OPENSKY_USERNAME = os.getenv("OPENSKY_USERNAME")
OPENSKY_PASSWORD = os.getenv("OPENSKY_PASSWORD")
DATA_PROVIDER = os.getenv("DATA_PROVIDER", "opensky")

OPEN_SKY_BASE = os.getenv("OPEN_SKY_BASE", "https://opensky-network.org/api")
STATE_COLUMNS = [
    "icao24",
    "callsign",
    "origin_country",
    "time_position",
    "last_contact",
    "longitude",
    "latitude",
    "baro_altitude",
    "on_ground",
    "velocity",
    "heading",
    "vertical_rate",
    "sensors",
    "geo_altitude",
    "squawk",
    "spi",
    "position_source",
]

app = Flask(__name__)


# structured logging setup
logger = logging.getLogger("plane_tracker")
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logger.setLevel(getattr(logging, log_level, logging.INFO))
if not logger.handlers:
    sh = logging.StreamHandler()
    fmt = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    sh.setFormatter(fmt)
    logger.addHandler(sh)

# rate limiter (apply per-route or default as needed)
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
limiter.init_app(app)


def opensky_request(path: str, params: Optional[Dict[str, str]] = None) -> Dict:
    auth = (OPENSKY_USERNAME, OPENSKY_PASSWORD) if OPENSKY_USERNAME and OPENSKY_PASSWORD else None
    response = requests.get(
        f"{OPEN_SKY_BASE}/{path}",
        params=params,
        auth=auth,
        timeout=15,
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    return response.json()


def normalize_state(state: list) -> Dict:
    return {key: state[index] for index, key in enumerate(STATE_COLUMNS)}


def fetch_aircraft(icao24: Optional[str] = None, bbox: Optional[Dict[str, str]] = None) -> Dict:
    # Prefer configured provider, fall back to OpenSky implementation on error.
    try:
        provider = providers.get_provider(DATA_PROVIDER)
        return provider.get_aircraft(icao24=icao24, bbox=bbox)
    except Exception as exc:
        logger.warning("provider_fallback", extra={"provider": DATA_PROVIDER, "error": str(exc)})
        params: Dict[str, str] = {}
        if icao24:
            params["icao24"] = icao24
        if bbox:
            params.update(bbox)

        response = opensky_request("states/all", params=params)
        states = response.get("states") or []
        return {
            "time": response.get("time"),
            "aircraft": [normalize_state(state) for state in states],
            "query": params,
            "source": "OpenSky Network (fallback)",
            "error": str(exc),
        }


@app.route("/")
def index():
    return render_template_string(
        """
        <html>
            <head>
                <title>Plane Tracker</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
                <style>
                    body { font-family: Arial, sans-serif; margin: 10px; }
                    input, button { margin: 4px 0; padding: 8px; width: 100%; max-width: 420px; }
                    .box { max-width: 980px; margin: auto; }
                    .resource { margin-top: 12px; }
                    #map { height: 520px; margin-top: 12px; border: 1px solid #ddd; }
                </style>
            </head>
            <body>
                <div class="box">
                    <h1>Plane Tracker</h1>
                    <p>Map visualization + API (provider: {{ provider }})</p>
                    <form id="queryForm">
                        <label>ICAO 24-bit address (optional)</label><br>
                        <input type="text" name="icao24" placeholder="e.g. a0b1c2" />
                        <label>Latitude min</label><br>
                        <input type="text" name="lamin" placeholder="34.0" />
                        <label>Latitude max</label><br>
                        <input type="text" name="lamax" placeholder="38.0" />
                        <label>Longitude min</label><br>
                        <input type="text" name="lomin" placeholder="-123.0" />
                        <label>Longitude max</label><br>
                        <input type="text" name="lomax" placeholder="-118.0" />
                        <button type="submit">Fetch aircraft</button>
                    </form>
                    <div id="map"></div>
                    <div class="resource">
                        <h2>API endpoint</h2>
                        <p>GET <code>/api/aircraft</code></p>
                        <p>Query params:</p>
                        <ul>
                            <li><code>icao24</code> - optional filter by aircraft ICAO address</li>
                            <li><code>lamin</code>, <code>lamax</code>, <code>lomin</code>, <code>lomax</code> - optional bounding box</li>
                        </ul>
                    </div>
                </div>
                <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
                <script>
                    document.addEventListener('DOMContentLoaded', function() {
                        var map = L.map('map').setView([20, 0], 2);
                        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                            attribution: '&copy; OpenStreetMap contributors'
                        }).addTo(map);

                        window.aircraftLayer = L.layerGroup().addTo(map);

                        function toParams(obj) { var s=[]; for (var k in obj){ if(obj[k]) s.push(k+'='+encodeURIComponent(obj[k])); } return s.join('&'); }

                        function updateAircraft() {
                            var icao24 = document.querySelector('input[name=icao24]').value;
                            var lamin = document.querySelector('input[name=lamin]').value;
                            var lamax = document.querySelector('input[name=lamax]').value;
                            var lomin = document.querySelector('input[name=lomin]').value;
                            var lomax = document.querySelector('input[name=lomax]').value;
                            var q = toParams({icao24:icao24, lamin:lamin, lamax:lamax, lomin:lomin, lomax:lomax});
                            var url = '/api/aircraft' + (q?('?'+q):'');
                            fetch(url).then(function(r){ return r.json(); }).then(function(data){
                                window.aircraftLayer.clearLayers();
                                var markers = [];
                                (data.aircraft||[]).forEach(function(a){
                                    var lat = parseFloat(a.latitude);
                                    var lon = parseFloat(a.longitude);
                                    if (!isNaN(lat) && !isNaN(lon)){
                                        var popup = '<b>' + (a.callsign||'') + '</b><br/>' + (a.icao24||'') + '<br/>' + (a.origin_country||'');
                                        var m = L.marker([lat,lon]).bindPopup(popup);
                                        markers.push(m);
                                    }
                                });
                                if (markers.length){
                                    var group = L.featureGroup(markers);
                                    window.aircraftLayer.addLayer(group);
                                    map.fitBounds(group.getBounds().pad(0.5));
                                }
                            }).catch(function(err){ console.error(err); });
                        }

                        document.getElementById('queryForm').addEventListener('submit', function(e){ e.preventDefault(); updateAircraft(); });
                        updateAircraft();
                        setInterval(updateAircraft, 15000);
                    });
                </script>
            </body>
        </html>
        """,
        provider=DATA_PROVIDER,
    )


@app.before_request
def log_request():
    logger.info("http_request", extra={
        "method": request.method,
        "path": request.path,
        "remote_addr": request.remote_addr,
        "query_args": dict(request.args),
    })


@app.route("/api/aircraft")
@limiter.limit("60 per minute")
def api_aircraft():
    icao24 = request.args.get("icao24")
    lamin = request.args.get("lamin")
    lamax = request.args.get("lamax")
    lomin = request.args.get("lomin")
    lomax = request.args.get("lomax")

    bbox: Dict[str, str] = {}
    if lamin and lamax and lomin and lomax:
        bbox = {"lamin": lamin, "lamax": lamax, "lomin": lomin, "lomax": lomax}

    try:
        data = fetch_aircraft(icao24=icao24, bbox=bbox if bbox else None)
    except requests.HTTPError as exc:
        logger.exception("fetch_failed", exc_info=exc)
        return jsonify({"error": "Failed to fetch aircraft data", "details": str(exc)}), 502
    except Exception as exc:
        logger.exception("unexpected_error", exc_info=exc)
        return jsonify({"error": "Internal server error", "details": str(exc)}), 500
    logger.info("aircraft_response", extra={"count": len(data.get("aircraft", [])), "source": data.get("source")})
    return jsonify(data)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
