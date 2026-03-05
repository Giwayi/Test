#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EnergieBerater KI - Build Setup
Wird von build_windows.bat aufgerufen.
"""
import sys, os, subprocess, urllib.request, base64, ast, shutil
from pathlib import Path

HERE = Path(__file__).parent

def status(msg):
    print(f"\n  {msg}")

def fail(msg):
    print(f"\n  FEHLER: {msg}")
    input("  Enter zum Beenden...")
    sys.exit(1)

CACHE_DIR = HERE / "_build_cache"
CACHE_DIR.mkdir(exist_ok=True)

def download(url, label):
    cache_file = CACHE_DIR / (label.lower().replace(".", "_").replace(" ", "_") + ".js")
    if cache_file.exists():
        print(f"    {label}: aus Cache ({len(cache_file.read_bytes())//1024} KB)")
        return cache_file.read_text("utf-8")
    print(f"    Lade {label}...", end="", flush=True)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read().decode("utf-8")
            cache_file.write_text(data, "utf-8")
            print(f" {len(data)//1024} KB")
            return data
        except Exception as e:
            print(f" Versuch {attempt+1} fehlgeschlagen: {e}")
    fail(f"Download fehlgeschlagen: {url}")

print()
print("  ================================================")
print("   EnergieBerater KI - Build Setup")
print("  ================================================")

# ── Schritt 1: Quelldatei lesen ───────────────────────────────────────────────
status("Schritt 1/4: Pruefe Quelldatei...")
app_src_path = HERE / "energie_berater_app.py"
if not app_src_path.exists():
    fail(f"energie_berater_app.py nicht gefunden in {HERE}")
with open(app_src_path, "r", encoding="utf-8") as f:
    app_src = f.read()

# JSX aus _APP_JSX_B64 Variable lesen (base64 - kein Escaping-Problem)
jsx = None
try:
    for line in app_src.splitlines():
        if line.startswith("_APP_JSX_B64 = "):
            b64 = line.split('"', 1)[1].rsplit('"', 1)[0]
            jsx = base64.b64decode(b64).decode("utf-8")
            break
except Exception as e:
    fail(f"Konnte _APP_JSX_B64 nicht lesen: {e}")

if not jsx:
    fail("_APP_JSX_B64 nicht in energie_berater_app.py gefunden")

if "<!--HTML_B64_PLACEHOLDER-->" not in app_src:
    fail("<!--HTML_B64_PLACEHOLDER--> nicht in energie_berater_app.py gefunden")

print(f"    OK: {app_src_path}")
print(f"    JSX: {len(jsx):,} Zeichen")

# ── Schritt 2: Pakete installieren ───────────────────────────────────────────
status("Schritt 2/4: Installiere Pakete (einmalig)...")
for pkg in ["PyQt6", "PyQt6-WebEngine", "pyinstaller"]:
    print(f"    {pkg}...", end="", flush=True)
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", pkg,
         "--quiet", "--no-warn-script-location"],
        capture_output=True
    )
    if r.returncode != 0:
        print(" FEHLER")
        print(r.stderr.decode(errors="replace"))
        fail(f"Installation von {pkg} fehlgeschlagen")
    print(" OK")

# ── Schritt 3: HTML bauen und als Base64 einbetten ───────────────────────────
status("Schritt 3/4: JS-Bibliotheken laden und HTML bauen...")
print("    (Alles wird direkt in die EXE eingebaut - kein Internet nach dem Build)")

CDN = "https://cdnjs.cloudflare.com/ajax/libs"
react_js    = download(f"{CDN}/react/18.2.0/umd/react.production.min.js",       "React")
reactdom_js = download(f"{CDN}/react-dom/18.2.0/umd/react-dom.production.min.js","ReactDOM")
babel_js    = download(f"{CDN}/babel-standalone/7.23.2/babel.min.js",            "Babel")
pdfjs_js    = download(f"{CDN}/pdf.js/3.11.174/pdf.min.js",                      "PDF.js")

# HTML komplett aufbauen - kein Escaping in Python-Strings
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

print(f"    HTML: {len(html)//1024} KB")

# Als Base64 kodieren - vermeidet alle Escaping-Probleme
html_b64 = base64.b64encode(html.encode("utf-8")).decode("ascii")
print(f"    Base64: {len(html_b64)//1024} KB")

# In App-Source einsetzen
final_src = app_src.replace("<!--HTML_B64_PLACEHOLDER-->", html_b64, 1)
if "<!--HTML_B64_PLACEHOLDER-->" in final_src:
    fail("Ersetzen des Platzhalters fehlgeschlagen")

final_path = HERE / "energie_berater_final.py"
with open(final_path, "w", encoding="utf-8") as f:
    f.write(final_src)
print(f"    Finale Datei: {len(final_src)//1024} KB")

# ── Schritt 4: EXE bauen ─────────────────────────────────────────────────────
status("Schritt 4/4: Baue EXE (5-10 Minuten, bitte warten)...")

for p in [HERE / "dist", HERE / "build"]:
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
spec = HERE / "EnergieBerater.spec"
if spec.exists():
    spec.unlink()

# Icon extrahieren
icon_path = None
try:
    for line in final_src.splitlines():
        if line.startswith("APP_ICON_B64"):
            b64 = line.split('"')[1]
            icon_path = HERE / "app_icon.ico"
            icon_path.write_bytes(base64.b64decode(b64))
            print(f"    Icon gesetzt")
            break
except Exception as e:
    print(f"    Icon-Fehler (unkritisch): {e}")

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onedir", "--windowed",
    "--name", "EnergieBerater",
    "--hidden-import", "PyQt6.QtWebEngineWidgets",
    "--hidden-import", "PyQt6.QtWebEngineCore",
    "--hidden-import", "PyQt6.QtWebChannel",
    "--collect-all", "PyQt6",
]
if icon_path and icon_path.exists():
    cmd += ["--icon", str(icon_path)]
cmd.append(str(final_path))

r = subprocess.run(cmd, cwd=str(HERE))
if r.returncode != 0:
    fail("PyInstaller fehlgeschlagen - Fehlermeldung oben lesen")

# Aufraumen
for cleanup in [HERE/"build", HERE/"EnergieBerater.spec",
                HERE/"energie_berater_final.py", HERE/"app_icon.ico"]:
    try:
        if cleanup.is_dir(): shutil.rmtree(cleanup, ignore_errors=True)
        elif cleanup.exists(): cleanup.unlink()
    except Exception: pass

exe = HERE / "dist" / "EnergieBerater" / "EnergieBerater.exe"
print()
print("  ================================================")
print("   FERTIG!")
print("  ================================================")
print()
print(f"  EXE: dist\\EnergieBerater\\EnergieBerater.exe")
print()
print("  Fuer OneDrive:")
print("  Ganzen Ordner dist\\EnergieBerater\\ kopieren!")
print("  (nicht nur die .exe, der ganze Ordner muss mit)")
print()
print("  - Kein Browser noetig (Chromium eingebettet)")
print("  - JS komplett eingebaut (offline-faehig)")
print("  - Nur Anthropic-API braucht Internet")
print()

if exe.exists():
    ans = input("  Jetzt testen? (j/n): ").strip().lower()
    if ans == "j":
        os.startfile(str(exe))
