import os
from typing import Dict, Optional

import requests

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


class BaseProvider:
    def get_aircraft(self, icao24: Optional[str] = None, bbox: Optional[Dict[str, str]] = None) -> Dict:
        raise NotImplementedError()


class OpenSkyProvider(BaseProvider):
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None, base: Optional[str] = None):
        self.username = username or os.getenv("OPENSKY_USERNAME")
        self.password = password or os.getenv("OPENSKY_PASSWORD")
        self.base = base or os.getenv("OPEN_SKY_BASE", "https://opensky-network.org/api")

    def _opensky_request(self, path: str, params: Optional[Dict[str, str]] = None) -> Dict:
        auth = (self.username, self.password) if self.username and self.password else None
        resp = requests.get(f"{self.base}/{path}", params=params, auth=auth, timeout=15, headers={"Accept": "application/json"})
        resp.raise_for_status()
        return resp.json()

    def _normalize_state(self, state: list) -> Dict:
        return {key: state[index] for index, key in enumerate(STATE_COLUMNS)}

    def get_aircraft(self, icao24: Optional[str] = None, bbox: Optional[Dict[str, str]] = None) -> Dict:
        params: Dict[str, str] = {}
        if icao24:
            params["icao24"] = icao24
        if bbox:
            params.update(bbox)

        resp = self._opensky_request("states/all", params=params)
        states = resp.get("states") or []
        return {
            "time": resp.get("time"),
            "aircraft": [self._normalize_state(s) for s in states],
            "query": params,
            "source": "OpenSky Network",
        }


class PaidProvider(BaseProvider):
    """Adapter for a commercial provider. Configure via PAID_API_URL and PAID_API_KEY.

    The adapter attempts to normalize a couple common responses:
    - If the provider returns OpenSky-like `states` arrays it will map them to keys.
    - If the provider returns an `aircraft` array of objects, those are passed through.
    Otherwise the raw payload is returned under `raw`.
    """

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.api_url = api_url or os.getenv("PAID_API_URL")
        self.api_key = api_key or os.getenv("PAID_API_KEY")

    def get_aircraft(self, icao24: Optional[str] = None, bbox: Optional[Dict[str, str]] = None) -> Dict:
        if not self.api_url or not self.api_key:
            raise RuntimeError("PAID_API_URL and PAID_API_KEY must be set for the paid provider")

        params: Dict[str, str] = {}
        if icao24:
            params["icao24"] = icao24
        if bbox:
            params.update(bbox)

        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        resp = requests.get(self.api_url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, dict) and "states" in data:
            states = data.get("states") or []
            return {
                "time": data.get("time"),
                "aircraft": [dict(zip(STATE_COLUMNS, s)) for s in states],
                "query": params,
                "source": "Paid Provider",
            }

        if isinstance(data, dict) and "aircraft" in data:
            return {"time": data.get("time"), "aircraft": data.get("aircraft"), "query": params, "source": "Paid Provider"}

        if isinstance(data, list):
            return {"time": None, "aircraft": data, "query": params, "source": "Paid Provider"}

        return {"time": None, "aircraft": [], "query": params, "source": "Paid Provider", "raw": data}


def get_provider(name: Optional[str] = None) -> BaseProvider:
    n = (name or os.getenv("DATA_PROVIDER", "opensky")).lower()
    if n in ("opensky", "open_sky", "open-sky"):
        return OpenSkyProvider()
    if n in ("paid", "paid_provider", "commercial"):
        return PaidProvider()
    return OpenSkyProvider()
