# Utilities

Small local utilities for inspecting project files during early prototyping.

## KMZ/KML PNG previews

Use `kmz_to_png.py` to create quick local PNG previews from KMZ or KML files.

```powershell
.\.venv\Scripts\python.exe .\utils\kmz_to_png.py
```

By default, the script scans the repository root for `*.kmz` and `*.kml` files and writes preview images to `outputs/kmz_previews/`.

You can also pass files or directories explicitly:

```powershell
.\.venv\Scripts\python.exe .\utils\kmz_to_png.py .\projects\trails\inputs\trail_route_alternatives.kmz
```

This utility is for visual inspection only. It is not a GIS analysis engine and does not replace field verification or source-backed review.
