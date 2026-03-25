# Well Log Toolkit (Streamlit)

A modular Streamlit app for well-log workflows.

## Current pages
- **Home (`app.py`)**: function hub and extension roadmap.
- **LAS Depth Matching (`pages/1_Depth_Matching.py`)**: upload two LAS files and compute best depth shift by gamma-correlation.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Design for extension
- Add new reusable logic in `services/`.
- Add new pages in `pages/`.
- Register page metadata in `modules/registry.py` so it appears on the home hub.
