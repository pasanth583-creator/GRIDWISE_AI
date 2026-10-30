# GRIDWISE AI — PHASE 8: LIVE WEATHER INTEGRATION
## Open-Meteo API Client, 15-Minute Caching, Validation & Fallback Handling

---

### 1. Open-Meteo Integration Architecture
Open-Meteo provides high-resolution numerical weather prediction (NWP) forecasts without requiring an API key. GRIDWISE AI configures coordinates for **Tiruchirappalli, Tamil Nadu** (Latitude: 10.7905°N, Longitude: 78.7047°E).

#### Endpoint Configuration:
- **Base URL**: `https://api.open-meteo.com/v1/forecast`
- **Current Parameters**: `temperature_2m`, `relative_humidity_2m`, `cloud_cover`, `precipitation`, `wind_speed_10m`
- **Hourly Parameters (48h window)**: `temperature_2m`, `relative_humidity_2m`, `precipitation`, `precipitation_probability`, `cloud_cover`, `wind_speed_10m`, `shortwave_radiation`, `direct_radiation`, `diffuse_radiation`
- **Timezone**: Auto / Asia/Kolkata (IST)

---

### 2. Caching & Resilience Strategy

#### 2.1 15-Minute Cache (TTL = 900 seconds)
To avoid rate-limiting and unnecessary network latency during frequent UI visits or automated dispatch cycles:
1. Every successful API fetch is serialized to `data/adaptive/weather_cache.json` with an ISO-8601 UTC timestamp `fetched_at`.
2. Subsequent calls check `age = now - fetched_at`. If `age < 900s` and `force_refresh=False`, the cached JSON is served instantly in $< 5\text{ ms}$.
3. Users and operators can bypass the cache at any time via `POST /api/weather/refresh` or the "Refresh Live Weather" UI button.

#### 2.2 Physical Range Validation
All raw meteorological data passes through physical bounding filters:
- Temperature: clipped to $[-10^\circ\text{C}, 55^\circ\text{C}]$.
- Relative Humidity: clipped to $[0\%, 100\%]$.
- Cloud Cover: clipped to $[0\%, 100\%]$.
- Wind Speed & Precipitation: non-negativity enforced ($\ge 0$).
- Solar Radiation: non-negativity enforced; strictly zero during night hours ($20:00$ to $05:00$).

#### 2.3 Stale-Cache & Offline Fallback
When network connectivity is unavailable (or in restricted sandboxed test environments):
1. **Tier 1 (Stale Cache)**: If `weather_cache.json` exists on disk, it is returned with metadata `is_stale=True`, `source="Stale Cache Fallback"`, and a descriptive warning message.
2. **Tier 2 (Synthetic Fallback)**: If no cache exists, `WeatherService._generate_fallback_weather()` generates a calibrated diurnal meteorological cycle typical of Tiruchirappalli's tropical climate ($26^\circ\text{C} - 34^\circ\text{C}$, clear-sky solar noon curve).

---

### 3. Database Persistence (`weather_records`)
Every successful live weather retrieval logs all 24 hourly periods to the SQLite table `weather_records`:
```sql
CREATE TABLE IF NOT EXISTS weather_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    location_name TEXT NOT NULL DEFAULT 'Tiruchirappalli, Tamil Nadu',
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    temperature_c REAL,
    relative_humidity_pct REAL,
    precipitation_mm REAL,
    precipitation_probability_pct REAL,
    cloud_cover_pct REAL,
    wind_speed_kmh REAL,
    solar_radiation_w_m2 REAL,
    direct_radiation_w_m2 REAL,
    diffuse_radiation_w_m2 REAL,
    data_source TEXT DEFAULT 'Open-Meteo Live API',
    is_cached INTEGER DEFAULT 0,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

