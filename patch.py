#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EnergieBerater KI - Patcher
Aktualisiert eine bestehende Installation ohne vollen Rebuild.

Wie es funktioniert:
  1. JSX aus energie_berater_app.py lesen
  2. JS-Bibliotheken aus _build_cache/ laden (oder einmalig herunterladen)
  3. Fertige HTML bauen und als html_patch.b64 neben die EXE legen
  4. App neu starten – fertig!

Kein PyInstaller, kein Loeschen von dist/, dauert Sekunden statt Minuten.
"""
import sys, os, base64, urllib.request
from pathlib import Path

HERE       = Path(__file__).parent
DIST_DIR   = HERE / "dist" / "EnergieBerater"
CACHE_DIR  = HERE / "_build_cache"
CACHE_DIR.mkdir(exist_ok=True)

# Gleiche CDN-Versionen wie build_setup.py
CDN = "https://cdnjs.cloudflare.com/ajax/libs"
LIBS = [
    ("react_js",    f"{CDN}/react/18.2.0/umd/react.production.min.js",       "React"),
    ("reactdom_js", f"{CDN}/react-dom/18.2.0/umd/react-dom.production.min.js","ReactDOM"),
    ("babel_js",    f"{CDN}/babel-standalone/7.23.2/babel.min.js",            "Babel"),
    ("pdfjs_js",    f"{CDN}/pdf.js/3.11.174/pdf.min.js",                      "PDF.js"),
]


def status(msg):  print(f"\n  {msg}")
def ok(msg):      print(f"    {msg}")

def fail(msg):
    print(f"\n  FEHLER: {msg}")
    input("\n  Enter zum Beenden...")
    sys.exit(1)


print()
print("  ================================================")
print("   EnergieBerater KI - Patcher")
print("  ================================================")

# ── Schritt 1: Quelldatei prüfen ──────────────────────────────────────────────
status("Schritt 1/3: Quelldatei lesen...")

src_path = HERE / "energie_berater_app.py"
if not src_path.exists():
    fail(f"energie_berater_app.py nicht gefunden in {HERE}")

with open(src_path, encoding="utf-8") as f:
    app_src = f.read()

jsx = None
for line in app_src.splitlines():
    if line.startswith("_APP_JSX_B64 = "):
        try:
            b64 = line.split('"', 1)[1].rsplit('"', 1)[0]
            jsx = base64.b64decode(b64).decode("utf-8")
        except Exception as e:
            fail(f"_APP_JSX_B64 konnte nicht dekodiert werden: {e}")
        break

if not jsx:
    fail("_APP_JSX_B64 nicht in energie_berater_app.py gefunden")

ok(f"JSX: {len(jsx):,} Zeichen")

if not DIST_DIR.exists():
    fail(
        f"dist/EnergieBerater/ nicht gefunden.\n"
        f"  Bitte zuerst build_windows.bat ausfuehren um die EXE zu erstellen.\n"
        f"  Danach genuegt der Patcher fuer Updates."
    )

# ── Schritt 2: JS-Bibliotheken (aus Cache oder Download) ─────────────────────
status("Schritt 2/3: JS-Bibliotheken laden...")

def get_lib(cache_name, url, label):
    cache_file = CACHE_DIR / cache_name
    if cache_file.exists():
        size = len(cache_file.read_bytes()) // 1024
        ok(f"{label}: aus Cache ({size} KB)")
        return cache_file.read_text("utf-8")
    print(f"    {label}: lade...", end="", flush=True)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read().decode("utf-8")
            cache_file.write_text(data, "utf-8")
            print(f" {len(data)//1024} KB")
            return data
        except Exception as e:
            print(f"\n    Versuch {attempt+1} fehlgeschlagen: {e}")
    fail(f"Download fehlgeschlagen: {url}")

react_js    = get_lib("react_js.js",    LIBS[0][1], LIBS[0][2])
reactdom_js = get_lib("reactdom_js.js", LIBS[1][1], LIBS[1][2])
babel_js    = get_lib("babel_js.js",    LIBS[2][1], LIBS[2][2])
pdfjs_js    = get_lib("pdfjs_js.js",    LIBS[3][1], LIBS[3][2])

# ── Schritt 3: HTML bauen und als Patch einsetzen ────────────────────────────
status("Schritt 3/3: HTML bauen und Patch einspielen...")

html = "\n".join([
    "<!DOCTYPE html>",
    '<html lang="de">',
    "<head>",
    '  <meta charset="UTF-8">',
    "  <title>EnergieBerater KI</title>",
    f"  <script>{react_js}</script>",
    f"  <script>{reactdom_js}</script>",
    f"  <script>{babel_js}</script>",
    "  <script>",
    pdfjs_js,
    "  window.pdfjsLib.GlobalWorkerOptions.workerSrc = '';",
    "  </script>",
    "  <style>*{box-sizing:border-box;margin:0;padding:0}",
    "  html,body,#root{height:100%;overflow:hidden}",
    "  body{background:#0e1118}</style>",
    "</head>",
    "<body>",
    '  <div id="root" style="height:100%"></div>',
    '  <script type="text/babel" data-presets="react">',
    jsx,
    "  </script>",
    "</body>",
    "</html>",
])

html_b64 = base64.b64encode(html.encode("utf-8")).decode("ascii")
ok(f"HTML: {len(html)//1024} KB  |  Base64: {len(html_b64)//1024} KB")

patch_target = DIST_DIR / "html_patch.b64"
patch_target.write_text(html_b64, "utf-8")
ok(f"Patch geschrieben: {patch_target}")

print()
print("  ================================================")
print("   FERTIG!")
print("  ================================================")
print()
print("  EnergieBerater.exe neu starten um die Aenderungen zu sehen.")
print()
input("  Enter zum Beenden...")
