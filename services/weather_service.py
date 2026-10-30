"""
GRIDWISE AI - Live Weather Integration Service
Open-Meteo API Client with 15-Minute Caching, Validation, and Stale Fallback.
Default Location: Tiruchirappalli, Tamil Nadu (Lat: 10.7905, Lon: 78.7047).
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timezone
import json
import logging
import urllib.request
import urllib.error
import numpy as np
import pandas as pd

from config import get_config
from database.database import execute_db, query_db

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ADAPTIVE_DIR = BASE_DIR / "data" / "adaptive"
ADAPTIVE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = ADAPTIVE_DIR / "weather_cache.json"
CSV_FILE = ADAPTIVE_DIR / "live_weather_forecast.csv"


class WeatherService:
    """Manages live weather retrieval, 15-minute caching, validation, and database persistence."""

    DEFAULT_LOCATION = "Tiruchirappalli, Tamil Nadu"
    DEFAULT_LAT = 10.7905
    DEFAULT_LON = 78.7047
    CACHE_TTL_SECONDS = 900  # 15 minutes
    API_TIMEOUT = 6.0  # seconds

    _in_memory_cache: Optional[Dict[str, Any]] = None
    _last_fetch_time: Optional[datetime] = None

    @classmethod
    def get_weather_data(
        cls,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieves current and 24-hour weather forecast.
        Uses in-memory/file cache if younger than 15 minutes unless force_refresh is True.
        """
        lat = latitude if latitude is not None else cls.DEFAULT_LAT
        lon = longitude if longitude is not None else cls.DEFAULT_LON

        # 1. Check valid cache
        if not force_refresh:
            cached = cls._load_cache()
            if cached and cls._is_cache_fresh(cached):
                logger.info("Serving live weather from fresh 15-min cache.")
                cached["source"] = "Cache (Fresh < 15m)"
                cached["is_cached"] = True
                return cached

        # 2. Attempt live API retrieval
        try:
            logger.info(f"Fetching live weather from Open-Meteo for ({lat}, {lon})...")
            live_data = cls._fetch_from_open_meteo(lat, lon)
            validated_data = cls._validate_and_format(live_data, lat, lon)

            # Update caches
            cls._in_memory_cache = validated_data
            cls._last_fetch_time = datetime.now(timezone.utc)
            cls._save_cache(validated_data)
            cls._save_to_csv(validated_data)
            cls._save_to_db(validated_data)

            validated_data["source"] = "Open-Meteo Live API"
            validated_data["is_cached"] = False
            return validated_data

        except Exception as e:
            logger.warning(f"Live weather API fetch failed ({e}); falling back to stale cache/baseline.")
            # 3. Fallback to stale cache if available
            cached = cls._load_cache()
            if cached:
                cached["source"] = "Stale Cache Fallback"
                cached["is_cached"] = True
                cached["is_stale"] = True
                cached["warning"] = f"Live update failed: {str(e)}. Serving last known weather data."
                return cached

            # 4. Fallback to synthetic offline baseline for Tiruchirappalli
            fallback = cls._generate_fallback_weather(lat, lon, reason=str(e))
            cls._save_cache(fallback)
            cls._save_to_csv(fallback)
            return fallback

    @classmethod
    def refresh_weather(cls, latitude: Optional[float] = None, longitude: Optional[float] = None) -> Dict[str, Any]:
        """Explicitly forces a refresh from the Open-Meteo API."""
        return cls.get_weather_data(latitude=latitude, longitude=longitude, force_refresh=True)

    @classmethod
    def _fetch_from_open_meteo(cls, lat: float, lon: float) -> Dict[str, Any]:
        """Executes HTTP GET to Open-Meteo with exact required parameters."""
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&"
            f"current=temperature_2m,relative_humidity_2m,cloud_cover,precipitation,wind_speed_10m&"
            f"hourly=temperature_2m,relative_humidity_2m,precipitation,precipitation_probability,"
            f"cloud_cover,wind_speed_10m,shortwave_radiation,direct_radiation,diffuse_radiation&"
            f"forecast_days=2&timezone=auto"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "GRIDWISE-AI/1.0 Microgrid Management System"})
        with urllib.request.urlopen(req, timeout=cls.API_TIMEOUT) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Open-Meteo HTTP {resp.status}")
            return json.loads(resp.read().decode("utf-8"))

    @classmethod
    def _validate_and_format(cls, raw: Dict[str, Any], lat: float, lon: float) -> Dict[str, Any]:
        """Validates physical ranges and formats 24h horizon for microgrid forecasting."""
        current = raw.get("current", {})
        hourly = raw.get("hourly", {})

        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        rhs = hourly.get("relative_humidity_2m", [])
        precips = hourly.get("precipitation", [])
        precip_probs = hourly.get("precipitation_probability", [])
        clouds = hourly.get("cloud_cover", [])
        winds = hourly.get("wind_speed_10m", [])
        rads = hourly.get("shortwave_radiation", [])
        direct_rads = hourly.get("direct_radiation", [])
        diffuse_rads = hourly.get("diffuse_radiation", [])

        # Format 24-hour horizon starting from current or next available hour
        num_hours = min(24, len(times))
        hourly_records = []
        for i in range(num_hours):
            # Parse hour
            iso_time = times[i] if i < len(times) else f"T{i:02d}:00"
            t_obj = datetime.fromisoformat(iso_time.replace("Z", "+00:00")) if "T" in iso_time else datetime.now(timezone.utc)
            h_int = t_obj.hour

            temp = float(temps[i]) if i < len(temps) and temps[i] is not None else 30.0
            rh = float(rhs[i]) if i < len(rhs) and rhs[i] is not None else 60.0
            precip = float(precips[i]) if i < len(precips) and precips[i] is not None else 0.0
            precip_prob = float(precip_probs[i]) if i < len(precip_probs) and precip_probs[i] is not None else 0.0
            cloud = float(clouds[i]) if i < len(clouds) and clouds[i] is not None else 20.0
            wind = float(winds[i]) if i < len(winds) and winds[i] is not None else 5.0
            rad = float(rads[i]) if i < len(rads) and rads[i] is not None else 0.0
            dir_rad = float(direct_rads[i]) if i < len(direct_rads) and direct_rads[i] is not None else 0.0
            dif_rad = float(diffuse_rads[i]) if i < len(diffuse_rads) and diffuse_rads[i] is not None else 0.0

            # Domain validation: non-negativity and bounds
            temp = float(np.clip(temp, -10.0, 55.0))
            rh = float(np.clip(rh, 0.0, 100.0))
            precip = float(max(0.0, precip))
            precip_prob = float(np.clip(precip_prob, 0.0, 100.0))
            cloud = float(np.clip(cloud, 0.0, 100.0))
            wind = float(max(0.0, wind))

            # Solar radiation strictly 0 at night (hours 20 to 5)
            if h_int in [20, 21, 22, 23, 0, 1, 2, 3, 4, 5]:
                rad = 0.0
                dir_rad = 0.0
                dif_rad = 0.0
            else:
                rad = float(np.clip(rad, 0.0, 1200.0))
                dir_rad = float(np.clip(dir_rad, 0.0, 1100.0))
                dif_rad = float(np.clip(dif_rad, 0.0, 600.0))

            hourly_records.append({
                "hour": i,
                "hour_of_day": h_int,
                "time_iso": iso_time,
                "temperature_c": round(temp, 1),
                "relative_humidity_pct": round(rh, 1),
                "precipitation_mm": round(precip, 2),
                "precipitation_probability_pct": round(precip_prob, 1),
                "cloud_cover_pct": round(cloud, 1),
                "wind_speed_kmh": round(wind, 1),
                "solar_radiation_w_m2": round(rad, 1),
                "direct_radiation_w_m2": round(dir_rad, 1),
                "diffuse_radiation_w_m2": round(dif_rad, 1),
            })

        curr_temp = float(current.get("temperature_2m", hourly_records[0]["temperature_c"]))
        curr_rh = float(current.get("relative_humidity_2m", hourly_records[0]["relative_humidity_pct"]))
        curr_cloud = float(current.get("cloud_cover", hourly_records[0]["cloud_cover_pct"]))
        curr_wind = float(current.get("wind_speed_10m", hourly_records[0]["wind_speed_kmh"]))
        curr_precip = float(current.get("precipitation", hourly_records[0]["precipitation_mm"]))

        now_iso = datetime.now(timezone.utc).isoformat()
        return {
            "status": "SUCCESS",
            "location_name": cls.DEFAULT_LOCATION,
            "latitude": lat,
            "longitude": lon,
            "fetched_at": now_iso,
            "is_stale": False,
            "current": {
                "temperature_c": round(curr_temp, 1),
                "relative_humidity_pct": round(curr_rh, 1),
                "cloud_cover_pct": round(curr_cloud, 1),
                "wind_speed_kmh": round(curr_wind, 1),
                "precipitation_mm": round(curr_precip, 2),
                "time_iso": current.get("time", now_iso),
            },
            "hourly_24h": hourly_records,
        }

    @classmethod
    def _generate_fallback_weather(cls, lat: float, lon: float, reason: str = "") -> Dict[str, Any]:
        """Generates realistic tropical weather baseline for Tiruchirappalli (10.8°N)."""
        logger.info(f"Generating realistic fallback weather data: {reason}")
        now = datetime.now(timezone.utc)
        hourly_records = []

        for h in range(24):
            # Diurnal temperature curve (min at 05h, max at 14h)
            temp = 26.0 + 8.0 * np.sin(np.pi * (h - 5) / 12) if 5 <= h <= 17 else 25.0
            rh = 80.0 - 35.0 * np.sin(np.pi * (h - 5) / 12) if 5 <= h <= 17 else 82.0
            cloud = 20.0 + 10.0 * np.sin(np.pi * h / 24)

            # Solar radiation profile (strictly 0 at night)
            if 6 <= h <= 18:
                rad = 950.0 * np.sin(np.pi * (h - 6) / 12) * (1.0 - 0.5 * (cloud / 100.0))
                dir_rad = rad * 0.7
                dif_rad = rad * 0.3
            else:
                rad = 0.0
                dir_rad = 0.0
                dif_rad = 0.0

            hourly_records.append({
                "hour": h,
                "hour_of_day": h,
                "time_iso": f"{now.strftime('%Y-%m-%d')}T{h:02d}:00:00Z",
                "temperature_c": round(float(temp), 1),
                "relative_humidity_pct": round(float(rh), 1),
                "precipitation_mm": 0.0,
                "precipitation_probability_pct": 10.0,
                "cloud_cover_pct": round(float(cloud), 1),
                "wind_speed_kmh": 6.5,
                "solar_radiation_w_m2": round(float(max(0.0, rad)), 1),
                "direct_radiation_w_m2": round(float(max(0.0, dir_rad)), 1),
                "diffuse_radiation_w_m2": round(float(max(0.0, dif_rad)), 1),
            })

        return {
            "status": "FALLBACK",
            "location_name": cls.DEFAULT_LOCATION,
            "latitude": lat,
            "longitude": lon,
            "fetched_at": now.isoformat(),
            "source": "Offline Fallback Cache",
            "is_cached": True,
            "is_stale": True,
            "warning": f"Serving calibrated fallback weather: {reason}",
            "current": {
                "temperature_c": hourly_records[0]["temperature_c"],
                "relative_humidity_pct": hourly_records[0]["relative_humidity_pct"],
                "cloud_cover_pct": hourly_records[0]["cloud_cover_pct"],
                "wind_speed_kmh": 6.5,
                "precipitation_mm": 0.0,
                "time_iso": now.isoformat(),
            },
            "hourly_24h": hourly_records,
        }

    @classmethod
    def _is_cache_fresh(cls, cache_data: Dict[str, Any]) -> bool:
        """Returns True if cache timestamp is less than CACHE_TTL_SECONDS old."""
        ts_str = cache_data.get("fetched_at")
        if not ts_str:
            return False
        try:
            fetched_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            age_sec = (now_dt - fetched_dt).total_seconds()
            return 0 <= age_sec < cls.CACHE_TTL_SECONDS
        except Exception:
            return False

    @classmethod
    def _load_cache(cls) -> Optional[Dict[str, Any]]:
        """Loads cache from memory or disk."""
        if cls._in_memory_cache:
            return cls._in_memory_cache
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cls._in_memory_cache = data
                    return data
            except Exception as e:
                logger.error(f"Error reading weather cache file: {e}")
        return None

    @classmethod
    def _save_cache(cls, data: Dict[str, Any]) -> None:
        """Saves weather data to JSON cache file."""
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving weather cache file: {e}")

    @classmethod
    def _save_to_csv(cls, data: Dict[str, Any]) -> None:
        """Saves hourly weather data to CSV for tabular auditing."""
        try:
            df = pd.DataFrame(data.get("hourly_24h", []))
            df.to_csv(CSV_FILE, index=False)
        except Exception as e:
            logger.error(f"Error saving live weather CSV: {e}")

    @classmethod
    def _save_to_db(cls, data: Dict[str, Any]) -> None:
        """Inserts hourly weather records into SQLite table weather_records."""
        try:
            hourly = data.get("hourly_24h", [])
            for h in hourly:
                execute_db(
                    """
                    INSERT INTO weather_records (
                        timestamp, location_name, latitude, longitude,
                        temperature_c, relative_humidity_pct, precipitation_mm,
                        precipitation_probability_pct, cloud_cover_pct, wind_speed_kmh,
                        solar_radiation_w_m2, direct_radiation_w_m2, diffuse_radiation_w_m2,
                        data_source, is_cached
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        h["time_iso"],
                        data.get("location_name", cls.DEFAULT_LOCATION),
                        data.get("latitude", cls.DEFAULT_LAT),
                        data.get("longitude", cls.DEFAULT_LON),
                        h["temperature_c"],
                        h["relative_humidity_pct"],
                        h["precipitation_mm"],
                        h["precipitation_probability_pct"],
                        h["cloud_cover_pct"],
                        h["wind_speed_kmh"],
                        h["solar_radiation_w_m2"],
                        h["direct_radiation_w_m2"],
                        h["diffuse_radiation_w_m2"],
                        data.get("source", "Open-Meteo Live API"),
                        1 if data.get("is_cached") else 0,
                    ),
                )
        except Exception as e:
            logger.warning(f"Could not persist weather to database: {e}")

