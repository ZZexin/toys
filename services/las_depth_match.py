from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

import lasio
import numpy as np
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d


@dataclass(frozen=True)
class MatchConfig:
    """Configuration for depth-matching runs."""

    depth_curve: str = "DEPT"
    gamma_curve_ref: str = "GR"
    gamma_curve_run: str = "GR"
    resample_step: float = 0.01
    shift_min: float = -1.0
    shift_max: float = 1.0
    shift_step: float = 0.001
    smooth_sigma: float = 2.0
    match_min: float | None = None
    match_max: float | None = None


def read_las_from_upload(uploaded_file: Any) -> lasio.LASFile:
    """Parse LAS file uploaded in Streamlit."""
    raw = uploaded_file.getvalue()
    text = raw.decode("latin-1", errors="ignore")
    return lasio.read(StringIO(text))


def load_las(source: lasio.LASFile | str | Path) -> lasio.LASFile:
    if isinstance(source, lasio.LASFile):
        return source
    return lasio.read(str(source))


def list_curve_names(las: lasio.LASFile) -> list[str]:
    return [curve.mnemonic for curve in las.curves]


def read_las_curve(las: lasio.LASFile, depth_curve: str = "DEPT", gamma_curve: str = "GR") -> tuple[np.ndarray, np.ndarray, float]:
    if depth_curve in las.curves:
        depth = np.array(las[depth_curve], dtype=float)
    else:
        depth = np.array(las.index, dtype=float)

    if gamma_curve not in las.curves:
        raise ValueError(f"Curve '{gamma_curve}' not found.")

    gamma = np.array(las[gamma_curve], dtype=float)
    null_value = las.well.NULL.value if "NULL" in las.well else -999.25

    return depth, gamma, float(null_value)


def clean_curve(depth: np.ndarray, curve: np.ndarray, null_value: float) -> tuple[np.ndarray, np.ndarray]:
    mask = np.isfinite(depth) & np.isfinite(curve) & (curve != null_value)
    return depth[mask], curve[mask]


def normalise(x: np.ndarray) -> np.ndarray:
    std = np.std(x)
    if std == 0:
        return x - np.mean(x)
    return (x - np.mean(x)) / std


def depth_match_las(
    las_ref: lasio.LASFile | str | Path,
    las_run: lasio.LASFile | str | Path,
    config: MatchConfig,
) -> dict[str, np.ndarray | float]:
    las_ref_obj = load_las(las_ref)
    las_run_obj = load_las(las_run)

    depth_ref, gamma_ref, null_ref = read_las_curve(las_ref_obj, config.depth_curve, config.gamma_curve_ref)
    depth_run, gamma_run, null_run = read_las_curve(las_run_obj, config.depth_curve, config.gamma_curve_run)

    depth_ref, gamma_ref = clean_curve(depth_ref, gamma_ref, null_ref)
    depth_run, gamma_run = clean_curve(depth_run, gamma_run, null_run)

    zmin = max(np.min(depth_ref), np.min(depth_run))
    zmax = min(np.max(depth_ref), np.max(depth_run))

    if zmax <= zmin:
        raise ValueError("No overlapping depth interval found.")

    common_depth = np.arange(zmin, zmax, config.resample_step)

    f_ref = interp1d(depth_ref, gamma_ref, bounds_error=False, fill_value=np.nan)
    f_run = interp1d(depth_run, gamma_run, bounds_error=False, fill_value=np.nan)

    ref = f_ref(common_depth)
    run = f_run(common_depth)

    if config.match_min is not None and config.match_max is not None:
        interval_mask = (common_depth >= config.match_min) & (common_depth <= config.match_max)
        common_depth = common_depth[interval_mask]
        ref = ref[interval_mask]
        run = run[interval_mask]

    if common_depth.size < 20:
        raise ValueError("Insufficient samples in overlap/matching interval. Increase interval or decrease resampling.")

    ref = gaussian_filter1d(ref, sigma=config.smooth_sigma, mode="nearest")
    run = gaussian_filter1d(run, sigma=config.smooth_sigma, mode="nearest")

    shifts = np.arange(config.shift_min, config.shift_max + config.shift_step, config.shift_step)
    correlations = []

    for shift in shifts:
        shifted_depth = common_depth + shift
        shifted_run = interp1d(common_depth, run, bounds_error=False, fill_value=np.nan)(shifted_depth)

        valid = np.isfinite(ref) & np.isfinite(shifted_run)
        if np.sum(valid) < 20:
            correlations.append(np.nan)
            continue

        x = normalise(ref[valid])
        y = normalise(shifted_run[valid])
        corr = np.corrcoef(x, y)[0, 1]
        correlations.append(corr)

    correlations_arr = np.array(correlations)
    best_idx = np.nanargmax(correlations_arr)
    best_shift = shifts[best_idx]
    best_corr = correlations_arr[best_idx]

    best_shifted_run = interp1d(common_depth, run, bounds_error=False, fill_value=np.nan)(common_depth + best_shift)

    return {
        "best_shift": best_shift,
        "best_corr": best_corr,
        "common_depth": common_depth,
        "ref": ref,
        "run": run,
        "shifted_run": best_shifted_run,
        "shifts": shifts,
        "correlations": correlations_arr,
    }
