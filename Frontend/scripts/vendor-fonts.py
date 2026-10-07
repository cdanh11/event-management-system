"""Vendor the official Google Fonts WOFF2 subsets and OFL licenses for local demos."""
import re
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "public" / "fonts"
FONTS.mkdir(parents=True, exist_ok=True)
URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Be+Vietnam+Pro:wght@400;500;600&"
    "family=Bricolage+Grotesque:wght@400..800&display=swap"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"}

def download(url):
    with urlopen(Request(url, headers=HEADERS), timeout=30) as response:
        return response.read()

css = download(URL).decode("utf-8")
blocks = re.findall(r"/\* ([^*]+) \*/\s*(@font-face\s*\{[^}]+\})", css)
chosen = [block for subset, block in blocks if subset.strip() in {"latin", "latin-ext", "vietnamese"}]
if not chosen or not any("vietnamese" in subset for subset, _ in blocks):
    raise RuntimeError("Google Fonts did not return the requested Vietnamese subsets")
css = "/* Local Google Fonts subsets. See public/fonts/*-OFL.txt for licenses. */\n\n" + "\n\n".join(chosen) + "\n"
for url in set(re.findall(r"https://fonts\.gstatic\.com/[^)\s]+", css)):
    name = url.rsplit("/", 1)[-1]
    if not name.endswith(".woff2"):
        raise RuntimeError("Expected compressed WOFF2 fonts")
    (FONTS / name).write_bytes(download(url))
    css = css.replace(url, f"/fonts/{name}")
for family in ("bevietnampro", "bricolagegrotesque"):
    (FONTS / f"{family}-OFL.txt").write_bytes(download(f"https://raw.githubusercontent.com/google/fonts/main/ofl/{family}/OFL.txt"))
(ROOT / "src" / "styles" / "fonts.css").write_text(css, encoding="utf-8")
print(f"Saved {len(chosen)} font faces and both licenses")
