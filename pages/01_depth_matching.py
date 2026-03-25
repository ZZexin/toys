from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

from services.las_depth_match import (
    MatchConfig,
    depth_match_las,
    list_curve_names,
    read_las_from_upload,
)


DEPTH_CURVE_HINTS = ("DEPT", "DEPTH", "MD", "TVD", "TVDSS", "Z")


def _depth_curve_options(curves: list[str]) -> list[str]:
    depth_like = [curve for curve in curves if any(hint in curve.upper() for hint in DEPTH_CURVE_HINTS)]
    return sorted(depth_like)


st.set_page_config(page_title="LAS Depth Matching", page_icon="📏", layout="wide")
st.title("LAS Depth Matching")
st.caption("Upload a reference LAS and a run LAS, then estimate depth shift from gamma correlation.")

left, right = st.columns(2)
with left:
    ref_file = st.file_uploader("Reference LAS", type=["las"], key="ref")
with right:
    run_file = st.file_uploader("Run LAS (to shift)", type=["las"], key="run")

if ref_file and run_file:
    try:
        las_ref = read_las_from_upload(ref_file)
        las_run = read_las_from_upload(run_file)
    except Exception as exc:
        st.error(f"Failed to parse LAS file: {exc}")
        st.stop()

    ref_curves = list_curve_names(las_ref)
    run_curves = list_curve_names(las_run)
    ref_depth_options = _depth_curve_options(ref_curves)
    run_depth_options = _depth_curve_options(run_curves)
    common_depth_candidates = [c for c in ["DEPT", "DEPTH", "MD"] if c in ref_depth_options and c in run_depth_options]

    st.subheader("Parameters")
    c1, c2, c3 = st.columns(3)
    with c1:
        has_common_depth = bool(common_depth_candidates)
        depth_curve = "DEPT"
        if has_common_depth:
            depth_curve = st.selectbox(
                "Depth curve",
                options=common_depth_candidates,
                index=0,
                help="Only depth-like curves shared by both LAS files are shown.",
            )
        else:
            st.warning(
                "No shared depth mnemonic found (e.g., DEPT/DEPTH/MD). The LAS index will be used as depth axis."
            )

        gamma_ref_options = [curve for curve in ref_curves if curve not in ref_depth_options] or ref_curves
        gamma_run_options = [curve for curve in run_curves if curve not in run_depth_options] or run_curves

        gamma_curve_ref = st.selectbox(
            "Reference gamma curve",
            options=gamma_ref_options,
            index=gamma_ref_options.index("GR") if "GR" in gamma_ref_options else 0,
        )
        gamma_curve_run = st.selectbox(
            "Run gamma curve",
            options=gamma_run_options,
            index=gamma_run_options.index("GR") if "GR" in gamma_run_options else 0,
        )

    with c2:
        match_mode = st.radio(
            "Match mode",
            options=["Global match", "Windowed match"],
            horizontal=True,
            help="Global = your script (1), Windowed = your script (2) with depth interval.",
        )
        resample_step = st.number_input("Resample step (m)", min_value=0.001, value=0.01, step=0.001)
        smooth_sigma = st.number_input("Gaussian sigma", min_value=0.0, value=1.0, step=0.5)

    with c3:
        shift_min = st.number_input("Shift min (m)", value=-2.5, step=0.1)
        shift_max = st.number_input("Shift max (m)", value=2.5, step=0.1)
        shift_step = st.number_input("Shift step (m)", min_value=0.0001, value=0.001, step=0.0005, format="%.4f")

    match_min = match_max = None
    if match_mode == "Windowed match":
        w1, w2 = st.columns(2)
        with w1:
            match_min = st.number_input("Window min depth (m)", value=0.0, step=1.0)
        with w2:
            match_max = st.number_input("Window max depth (m)", value=40.0, step=1.0)

    if st.button("Run depth matching", type="primary"):
        config = MatchConfig(
            depth_curve=depth_curve,
            gamma_curve_ref=gamma_curve_ref,
            gamma_curve_run=gamma_curve_run,
            resample_step=resample_step,
            shift_min=shift_min,
            shift_max=shift_max,
            shift_step=shift_step,
            smooth_sigma=smooth_sigma,
            match_min=match_min,
            match_max=match_max,
        )

        try:
            result = depth_match_las(las_ref, las_run, config)
        except Exception as exc:
            st.error(f"Depth matching failed: {exc}")
            st.stop()

        best_shift = float(result["best_shift"])
        best_corr = float(result["best_corr"])

        direction = "UP" if best_shift > 0 else "DOWN"
        st.success(f"Apply {abs(best_shift):.3f} m {direction} | Best correlation: {best_corr:.3f}")

        p1, p2 = st.columns(2)
        with p1:
            fig1, ax1 = plt.subplots(figsize=(6, 9))
            ax1.plot(result["ref"], result["common_depth"], label="Reference GR")
            ax1.plot(result["run"], result["common_depth"], label="Run GR (original)", alpha=0.7)
            ax1.plot(result["shifted_run"], result["common_depth"], label="Run GR (shifted)", linestyle="--")
            ax1.invert_yaxis()
            ax1.set_xlabel("Gamma")
            ax1.set_ylabel("Depth (m)")
            ax1.legend()
            ax1.set_title("Gamma Depth Matching")
            st.pyplot(fig1, clear_figure=True)

        with p2:
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            ax2.plot(result["shifts"], result["correlations"])
            ax2.axvline(best_shift, linestyle="--", label=f"Best shift = {best_shift:.3f} m")
            ax2.set_xlabel("Shift (m)")
            ax2.set_ylabel("Correlation")
            ax2.legend()
            ax2.set_title("Correlation vs Shift")
            st.pyplot(fig2, clear_figure=True)
else:
    st.info("Upload both LAS files to enable parameter setup.")
