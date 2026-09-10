"""Collect only public assets from the three user-supplied WAWA pages.

Staging files are ignored by Git and excluded from deployment. The public
asset selection is copied separately after visual review.
"""
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "tools/data/brand-upgrade"
BASE = "https://www.wawacenter.com"
PAGES = {"brand": "/brand/wawacenter", "coaching": "/intro/coachingSystem", "ai": "/intro/AISystem"}
SELECTION = [
    "Main_CD_wawa.png", "w1.png", "w3.png", "w2.png",
    "system_02_m.png", "system_03.png", "system_04.png", "system_05.png",
    "system_06_01.png", "system_07_01.png", "system_08_01.png",
    "ais_step02.png", "ais_math_content02.png", "ais_kor_content03.png",
    "ais_read_portfolio.png", "ais01.png",
]


def fetch(url):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                return response.read()
        except OSError:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


class MediaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.videos = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "img" and attrs.get("src"):
            self.images.append(attrs)
        if tag == "iframe" and "youtube.com/embed/" in attrs.get("src", ""):
            self.videos.append(attrs)


def asset(name):
    path = STAGE / name
    data = path.read_bytes() if path.exists() else fetch(f"{BASE}/assets/img/{name}")
    if not path.exists():
        path.write_bytes(data)
    with Image.open(path) as img:
        dimensions = img.size
    return {"file": name, "source": f"{BASE}/assets/img/{name}", "width": dimensions[0], "height": dimensions[1], "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    STAGE.mkdir(parents=True, exist_ok=True)
    pages = {}
    for label, relative in PAGES.items():
        url = urljoin(BASE, relative)
        snapshot = STAGE / f"{label}.html"
        html = snapshot.read_text(encoding="utf-8") if snapshot.exists() else fetch(url).decode("utf-8")
        if not snapshot.exists():
            snapshot.write_text(html, encoding="utf-8")
        parser = MediaParser()
        parser.feed(html)
        pages[label] = {"url": url, "images": parser.images, "videos": parser.videos}
    with ThreadPoolExecutor(max_workers=2) as pool:
        assets = list(pool.map(asset, SELECTION))
    video_ids = list(dict.fromkeys(v["src"].split("/embed/")[1].split("?")[0] for v in pages["brand"]["videos"]))
    videos = []
    for video_id in video_ids:
        path = STAGE / f"video-{video_id}.json"
        watch = f"https://www.youtube.com/watch?v={video_id}"
        metadata = json.loads(path.read_text(encoding="utf-8")) if path.exists() else json.loads(fetch("https://www.youtube.com/oembed?format=json&url=" + quote(watch, safe="")))
        if not path.exists():
            path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        thumbnail = STAGE / f"video-{video_id}.jpg"
        if not thumbnail.exists():
            thumbnail.write_bytes(fetch(metadata["thumbnail_url"]))
        with Image.open(thumbnail) as img:
            size = img.size
        videos.append({"id": video_id, "url": watch, "title": metadata["title"], "poster": thumbnail.name, "width": size[0], "height": size[1], "bytes": thumbnail.stat().st_size})
    result = {"pages": pages, "assets": assets, "videos": videos}
    (STAGE / "source-manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"assets": assets, "videos": videos}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
