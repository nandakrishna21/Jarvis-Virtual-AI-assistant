"""Weather service using the free Open-Meteo API (no API key required)."""
import logging

import httpx

logger = logging.getLogger("jarvis.weather")

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 12.0

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Light showers",
    81: "Showers",
    82: "Violent showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Severe thunderstorm",
}


def describe(code: int | None) -> str:
    if code is None:
        return "Unknown"
    return WEATHER_CODES.get(int(code), f"Weather code {code}")


async def geocode(city: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(
            GEOCODE_URL,
            params={"name": city, "count": 1, "language": "en", "format": "json"},
        )
        r.raise_for_status()
        data = r.json()
    results = data.get("results") or []
    if not results:
        return {"ok": False, "error": f"Could not find a place named '{city}'."}
    hit = results[0]
    return {
        "ok": True,
        "name": hit.get("name", city),
        "country": hit.get("country", ""),
        "admin1": hit.get("admin1", ""),
        "latitude": hit.get("latitude"),
        "longitude": hit.get("longitude"),
    }


async def current(city: str = "Hyderabad") -> dict:
    place = await geocode(city)
    if not place.get("ok"):
        return place

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",
                "forecast_days": 3,
            },
        )
        r.raise_for_status()
        data = r.json()

    cur = data.get("current") or {}
    daily = data.get("daily") or {}
    days = []
    for i, code in enumerate(daily.get("weather_code") or []):
        days.append(
            {
                "date": (daily.get("time") or [None])[i],
                "condition": describe(code),
                "temp_max": (daily.get("temperature_2m_max") or [None])[i],
                "temp_min": (daily.get("temperature_2m_min") or [None])[i],
                "precipitation": (daily.get("precipitation_sum") or [None])[i],
            }
        )

    return {
        "ok": True,
        "location": {
            "name": place["name"],
            "region": place.get("admin1", ""),
            "country": place.get("country", ""),
        },
        "current": {
            "temperature": cur.get("temperature_2m"),
            "apparent_temperature": cur.get("apparent_temperature"),
            "humidity": cur.get("relative_humidity_2m"),
            "wind_speed": cur.get("wind_speed_10m"),
            "precipitation": cur.get("precipitation"),
            "is_day": cur.get("is_day"),
            "condition": describe(cur.get("weather_code")),
            "time": cur.get("time"),
        },
        "forecast": days,
        "source": "Open-Meteo",
    }


def summarize(data: dict) -> str:
    if not data.get("ok"):
        return str(data.get("error") or "Weather is unavailable right now.")
    cur = data.get("current") or {}
    loc = data.get("location") or {}
    label = ", ".join([x for x in [loc.get("name"), loc.get("region"), loc.get("country")] if x])
    temp = cur.get("temperature")
    unit = "C" if temp is not None else ""
    return (
        f"{loc.get('name', 'Your location')}: {cur.get('condition', 'Unknown')}, "
        f"{temp}{unit} (feels like {cur.get('apparent_temperature')}{unit}), "
        f"humidity {cur.get('humidity')}%, wind {cur.get('wind_speed')} km/h."
    )
