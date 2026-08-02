"""
SafeRoute AI — City Manager
===========================
Orchestrates dynamic loading of crime datasets, ML models, density grids,
and safety engine configuration for any city in the registry.

Design principles
-----------------
• Backward compatible — Bengaluru still loads on startup via legacy path if
  the new data folder is unavailable (graceful fallback).
• Zero-copy — Bengaluru data is read from the new canonical path
  data/karnataka/bengaluru/crime_dataset.csv; if missing it falls back to
  the original data/bangalore_crime_dataset.csv automatically.
• Future-ready — adding a new city only requires:
    1. Placing crime_dataset.csv in  data/<state>/<city>/
    2. Adding a config.json in the same folder
    No Python code changes needed.

Public API
----------
    city_manager.load_city(state_key, city_key)   → CityState
    city_manager.current()                         → CityState
    city_manager.list_all_cities()                → list[dict]
    city_manager.resolve_from_coords(lat, lon)    → dict | None
"""

import os
import json
import pickle
from typing import Optional, Dict, List

import data_processing as dp
import safety_score    as ss
import risk_model      as rm
from city_registry     import (
    CITY_REGISTRY, CityConfig,
    get_city, list_states, list_cities, resolve_city_from_coords,
)

# ─── Paths ────────────────────────────────────────────────────────────────────
_BASE        = os.path.dirname(os.path.abspath(__file__))

# Case-insensitive data root — handles both 'data' (Linux CI) and 'Data' (Windows dev)
def _find_data_root(base: str) -> str:
    for candidate in ["data", "Data", "DATA"]:
        p = os.path.join(base, "..", candidate)
        if os.path.isdir(p):
            return os.path.normpath(p)
    return os.path.normpath(os.path.join(base, "..", "data"))  # fallback

_DATA_ROOT   = _find_data_root(_BASE)
_MODELS_ROOT = os.path.join(_BASE, "../models")

# Legacy fallback paths (original Bengaluru files — never deleted)
_LEGACY_DATA  = os.path.join(_DATA_ROOT, "bangalore_crime_dataset.csv")
_LEGACY_MODEL = os.path.join(_MODELS_ROOT, "risk_model.pkl")


# ─── CityState — holds all runtime data for one active city ──────────────────
class CityState:
    """Container for a fully-loaded city's runtime state."""

    def __init__(
        self,
        config:       CityConfig,
        state_key:    str,
        city_key:     str,
        crime_df,
        density_grid: list,
        model_bundle: dict,
    ):
        self.config        = config
        self.state_key     = state_key
        self.city_key      = city_key
        self.crime_df      = crime_df
        self.density_grid  = density_grid
        self.model_bundle  = model_bundle

    @property
    def label(self) -> str:
        return self.config.label

    @property
    def state_label(self) -> str:
        state = CITY_REGISTRY.get(self.state_key, {})
        return state.get("label", self.state_key.title())

    def to_info_dict(self) -> dict:
        """Serialisable summary returned by /city-status endpoint."""
        return {
            "state_key":    self.state_key,
            "state_label":  self.state_label,
            "city_key":     self.city_key,
            "city_label":   self.label,
            "center_lat":   self.config.center_lat,
            "center_lon":   self.config.center_lon,
            "zoom":         self.config.zoom,
            "bbox": {
                "min_lat": self.config.bbox[0],
                "max_lat": self.config.bbox[1],
                "min_lon": self.config.bbox[2],
                "max_lon": self.config.bbox[3],
            },
            "records":       len(self.crime_df) if self.crime_df is not None else 0,
            "model_name":    self.model_bundle["model_name"] if self.model_bundle else "N/A",
            "model_accuracy": round(self.model_bundle["test_accuracy"] * 100, 2)
                              if self.model_bundle else 0,
            "waypoints":     self.config.waypoints,
            "pilot":         (self.city_key == "bengaluru"),
        }


# ─── Module-level active city ─────────────────────────────────────────────────
_active_city: Optional[CityState] = None


def current() -> Optional[CityState]:
    """Return the currently loaded CityState."""
    return _active_city


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _dataset_path(state_key: str, city_key: str) -> Optional[str]:
    """
    Resolve dataset path with two-level fallback:
      1. data/<state>/<city>/crime_dataset.csv   (new canonical path)
      2. data/bangalore_crime_dataset.csv        (legacy path, Bengaluru only)
    """
    canonical = os.path.join(
        _DATA_ROOT, state_key.lower(), city_key.lower(), "crime_dataset.csv"
    )
    if os.path.exists(canonical):
        return canonical

    # Legacy fallback for Bengaluru only
    if city_key.lower() == "bengaluru" and os.path.exists(_LEGACY_DATA):
        print(f"WARNING: Using legacy dataset path: {_LEGACY_DATA}")
        return _LEGACY_DATA

    return None


def _model_path(state_key: str, city_key: str) -> str:
    """
    Resolve model path with legacy fallback.
    New path:    models/<state>/<city>/risk_model.pkl
    Legacy path: models/risk_model.pkl  (Bengaluru only)
    """
    canonical = os.path.join(
        _MODELS_ROOT, state_key.lower(), city_key.lower(), "risk_model.pkl"
    )
    if os.path.exists(canonical):
        return canonical

    # Legacy fallback for Bengaluru
    if city_key.lower() == "bengaluru":
        return _LEGACY_MODEL

    # For new cities, store model in canonical path
    os.makedirs(os.path.dirname(canonical), exist_ok=True)
    return canonical


def _dataset_available(state_key: str, city_key: str) -> bool:
    return _dataset_path(state_key, city_key) is not None


# ─── Public: load a city ─────────────────────────────────────────────────────

def load_city(state_key: str, city_key: str) -> CityState:
    """
    Load and activate a city.

    Steps
    -----
    1. Resolve CityConfig from registry.
    2. Find the dataset CSV.
    3. Load + clean crime data (using city's bounding box — not hardcoded).
    4. Compute density grid and update safety engine.
    5. Update safety engine city center.
    6. Load or train the ML model.
    7. Store as active city.

    Raises
    ------
    ValueError  — city not in registry
    FileNotFoundError — dataset missing and no legacy fallback
    """
    global _active_city

    # 1. Registry lookup
    config = get_city(state_key, city_key)
    if config is None:
        raise ValueError(f"City '{city_key}' in state '{state_key}' not found in registry.")

    # 2. Dataset path
    data_path = _dataset_path(state_key, city_key)
    if data_path is None:
        raise FileNotFoundError(
            f"No dataset found for {config.label}. "
            f"Expected: data/{state_key}/{city_key}/crime_dataset.csv"
        )

    print(f"\nLoading city: {config.label} ({state_key.upper()})")
    print(f"   Dataset : {data_path}")

    # 3. Load crime data with city-specific bounding box
    crime_df = dp.load_and_clean(data_path, bbox=config.bbox)
    crime_df, _ = dp.cluster_hotspots(crime_df)

    # 4. Compute density grid + update safety engine
    # Fix: reset index to avoid duplicate-label reindex error from cluster_hotspots
    crime_df = crime_df.reset_index(drop=True)
    hotspot_counts = crime_df.groupby("cluster_id").size().reindex(crime_df["cluster_id"].values, fill_value=0)
    hotspot_counts.index = crime_df.index
    hotspot_scale = max(float(hotspot_counts.max()), 1.0)
    crime_df["hotspot_score"] = (hotspot_counts / hotspot_scale).astype(float)
    
    density_grid = dp.compute_density_grid(crime_df)
    ss.load_density_grid(density_grid)

    # 5. Update city center for lighting heuristic
    ss.set_city_center(config.center_lat, config.center_lon)

    # 6. ML model
    model_path = _model_path(state_key, city_key)
    if os.path.exists(model_path):
        model_bundle = rm.load_model(model_path)
        print(f"   Model   : {model_bundle['model_name']} (loaded from {model_path})")
    else:
        print(f"   Model   : Training new model for {config.label}...")
        model_bundle = rm.train(data_path, model_path)

    # 7. Store active city
    _active_city = CityState(
        config       = config,
        state_key    = state_key,
        city_key     = city_key,
        crime_df     = crime_df,
        density_grid = density_grid,
        model_bundle = model_bundle,
    )

    print(f"{config.label} ready - "
          f"{len(crime_df)} records, "
          f"model={model_bundle['model_name']}, "
          f"accuracy={round(model_bundle['test_accuracy']*100,1)}%\n")

    return _active_city


# ─── Public: list all cities with availability flags ─────────────────────────

def list_all_cities() -> List[dict]:
    """
    Return all cities across all states with availability and pilot flags.
    Used by the /cities endpoint.
    """
    result = []
    for state_key, state_data in CITY_REGISTRY.items():
        for city_key, cfg in state_data["cities"].items():
            available = _dataset_available(state_key, city_key)
            result.append({
                "state_key":   state_key,
                "state_label": state_data["label"],
                "city_key":    city_key,
                "city_label":  cfg.label,
                "available":   available,
                "pilot":       (city_key == "bengaluru"),
                "center_lat":  cfg.center_lat,
                "center_lon":  cfg.center_lon,
                "zoom":        cfg.zoom,
                "waypoints":   cfg.waypoints,
                "status":      "active" if available else "coming_soon",
            })
    return result


def list_states_api() -> List[dict]:
    """Return states list with city counts."""
    result = []
    for state_key, state_data in CITY_REGISTRY.items():
        cities = state_data["cities"]
        available_count = sum(
            1 for ck in cities
            if _dataset_available(state_key, ck)
        )
        result.append({
            "key":             state_key,
            "label":           state_data["label"],
            "total_cities":    len(cities),
            "available_cities": available_count,
        })
    return result


def resolve_from_coords(lat: float, lon: float) -> Optional[dict]:
    """
    GPS-based city detection.
    Returns city info dict or None if coords don't fall in any known bbox.
    """
    match = resolve_city_from_coords(lat, lon)
    if not match:
        return None
    cfg = match["config"]
    return {
        "state_key":  match["state_key"],
        "city_key":   match["city_key"],
        "city_label": cfg.label,
        "available":  _dataset_available(match["state_key"], match["city_key"]),
        "center_lat": cfg.center_lat,
        "center_lon": cfg.center_lon,
        "zoom":       cfg.zoom,
    }
