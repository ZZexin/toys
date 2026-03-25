"""Registry for Streamlit tools shown on home page.

Add new modules here as the app grows.
"""

TOOLS = [
    {
        "name": "LAS Depth Matching",
        "page": "pages/01_depth_matching.py",
        "description": "Upload two LAS files and compute the best depth shift by gamma correlation.",
        "status": "Ready",
    }
]
