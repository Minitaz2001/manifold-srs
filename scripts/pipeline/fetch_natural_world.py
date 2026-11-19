"""
Build-time Workstream D content generator for Natural World (Visual) — NYC / Northeast launch set.
Queries Wikimedia Commons API directly, filters strictly to PD / CC0 / CC-BY / CC-BY-SA licenses,
downloads lightweight offline thumbnails into public/media/natural-world/, and records full attribution + source_url.
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import date

HEADERS = {"User-Agent": "ManifoldSRS-ContentPipeline/0.1 (local educational build; https://github.com/manifold-srs)"}

# 20 Northeast / NYC trees, clouds, birds, and rocks/minerals
SPECIMENS = [
    # Trees (7)
    ("red-maple", "Red Maple (Acer rubrum)", "tree", "Acer rubrum leaf", "Opposite toothed 3-5 lobed leaf; dominant Northeast deciduous tree; red petioles and autumn foliage."),
    ("eastern-white-pine", "Eastern White Pine (Pinus strobus)", "tree", "Pinus strobus needles", "Only native Northeast pine with needles in bundles of 5 ('W-H-I-T-E'); soft feathery plumes."),
    ("northern-red-oak", "Northern Red Oak (Quercus rubra)", "tree", "Quercus rubra leaf", "Pointed bristle-tipped lobes (red oak group); flat saucer-like acorn cap; ski-track bark ridges."),
    ("american-sycamore", "American Sycamore (Platanus occidentalis)", "tree", "Platanus occidentalis bark", "Camouflage exfoliating bark (white, olive, brown); massive maple-like leaves; single fuzzy seed balls."),
    ("paper-birch", "Paper Birch (Betula papyrifera)", "tree", "Betula papyrifera bark", "Chalky white peeling bark with horizontal dark lenticels; cool Northeast woods."),
    ("ginkgo-biloba", "Ginkgo (Ginkgo biloba)", "tree", "Ginkgo biloba leaf", "Unmistakable fan-shaped dichotomous-veined leaf; living fossil ubiquitous as an NYC street tree."),
    ("american-beech", "American Beech (Fagus grandifolia)", "tree", "Fagus grandifolia bark", "Smooth elephant-skin silver-gray bark; serrated parallel-veined leaves that cling tan through winter."),
    # Clouds (5)
    ("cumulonimbus", "Cumulonimbus", "cloud", "Cumulonimbus anvil cloud", "Towering convective storm cloud reaching the tropopause with an ice-crystal anvil top; lightning & downpours."),
    ("cirrus", "Cirrus", "cloud", "Cirrus clouds sky", "High-altitude (>6 km) wispy ice-crystal filaments ('mares' tails'); often precede a warm front by 12-24h."),
    ("altocumulus", "Altocumulus", "cloud", "Altocumulus cloud", "Mid-level (2-6 km) dappled gray-white rolls or patches ('mackerel sky'); signals mid-tropospheric instability."),
    ("lenticular-cloud", "Altocumulus Lenticularis", "cloud", "Lenticular cloud", "Stationary lens-shaped standing wave cloud formed downwind of terrain; marks strong winds aloft and rotor turbulence."),
    ("mammatus-cloud", "Mammatus", "cloud", "Mammatus clouds", "Pouch-like cellular lobes hanging beneath a cumulonimbus anvil; formed by sinking cold moist air pockets."),
    # Birds (5)
    ("red-tailed-hawk", "Red-tailed Hawk (Buteo jamaicensis)", "bird", "Buteo jamaicensis perched", "Broad-winged soaring raptor; dark belly band and rust-red upper tail; common over NYC parks and highways."),
    ("peregrine-falcon", "Peregrine Falcon (Falco peregrinus)", "bird", "Falco peregrinus perched", "Dark malar 'helmet' stripe, slate back, barred breast; fastest animal in a stoop (>300 km/h); nests on bridges."),
    ("great-blue-heron", "Great Blue Heron (Ardea herodias)", "bird", "Ardea herodias", "Tall blue-gray wading bird (~1.2 m) with S-curved neck in flight and dagger bill; Northeast marshes and parks."),
    ("northern-cardinal", "Northern Cardinal (Cardinalis cardinalis)", "bird", "Cardinalis cardinalis male", "Crested crimson male with black mask and heavy conical seed-cracking bill; year-round Northeast resident."),
    ("black-capped-chickadee", "Black-capped Chickadee (Poecile atricapillus)", "bird", "Poecile atricapillus", "Black cap and bib, crisp white cheeks; caches thousands of seeds and grows its hippocampus each autumn."),
    # Rocks & Minerals (3)
    ("manhattan-schist", "Mica Schist", "rock", "Mica schist rock", "Foliated metamorphic rock sparkling with platy muscovite/biotite mica; forms the bedrock supporting Midtown and Downtown Manhattan."),
    ("granite", "Granite", "rock", "Granite rock close up", "Coarse-grained felsic intrusive igneous rock: interlocking quartz, pink/white feldspar, and dark biotite/hornblende."),
    ("basalt-columns", "Columnar Basalt", "rock", "Columnar basalt", "Fine-grained dark mafic volcanic rock; hexagonal cooling joints (as in the Palisades sill across the Hudson)."),
]

ALLOWED_LICENSE_PATTERNS = ("cc", "public domain", "pd", "cc0")

def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()

def fetch_json(url: str):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))

def download_file(url: str, dest: str):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)

def search_commons_image(query: str):
    params = urllib.parse.urlencode({
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": 6,
        "gsrlimit": 8,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|mime|size",
        "iiurlwidth": 480,
    })
    url = f"https://commons.wikimedia.org/w/api.php?{params}"
    data = fetch_json(url)
    pages = data.get("query", {}).get("pages", {})
    # Sort by search index
    ordered = sorted(pages.values(), key=lambda p: p.get("index", 999))
    for page in ordered:
        infos = page.get("imageinfo", [])
        if not infos:
            continue
        info = infos[0]
        mime = info.get("mime", "")
        if mime not in ("image/jpeg", "image/png"):
            continue
        thumb = info.get("thumburl")
        desc_url = info.get("descriptionurl")
        if not thumb or not desc_url:
            continue
        meta = info.get("extmetadata", {})
        lic = strip_html(meta.get("LicenseShortName", {}).get("value", ""))
        artist = strip_html(meta.get("Artist", {}).get("value", "Unknown"))
        if len(artist) > 90:
            artist = artist[:87] + "..."
        if not any(pat in lic.lower() for pat in ALLOWED_LICENSE_PATTERNS):
            continue
        return {
            "thumburl": thumb,
            "source_url": desc_url,
            "license": lic,
            "artist": artist,
            "ext": "png" if mime == "image/png" else "jpg",
        }
    return None

def main():
    media_dir = os.path.join("public", "media", "natural-world")
    os.makedirs(media_dir, exist_ok=True)

    entities = []
    plain_cards = []
    verification_log = []

    for slug, name, kind, query, desc in SPECIMENS:
        print(f"Querying Wikimedia Commons for {slug} ({query})...")
        found = search_commons_image(query)
        if not found:
            raise RuntimeError(f"Could not find openly licensed Commons image for {slug}")
        filename = f"{slug}.{found['ext']}"
        rel_media = f"media/natural-world/{filename}"
        dest_path = os.path.join("public", rel_media)
        if not os.path.exists(dest_path):
            size = download_file(found["thumburl"], dest_path)
            print(f"  Downloaded {rel_media} ({size} bytes) [{found['license']}]")
            time.sleep(0.25)
        else:
            print(f"  Using cached {rel_media} [{found['license']}]")

        entities.append({
            "id": slug,
            "name": name,
            "kind": kind,
            "module": "natural_world",
            "tags": ["northeast", "nyc", kind],
        })
        plain_cards.append({
            "id": f"nw-{slug}",
            "module": "natural_world",
            "entity_id": slug,
            "tags": ["northeast", kind],
            "front": f"Identify this {kind}",
            "back": f"{name} — {desc}",
            "media": rel_media,
            "attribution": f"{found['artist']} · {found['license']} (Wikimedia Commons)",
            "source_url": found["source_url"],
            "source_note": f"Wikimedia Commons openly licensed photograph ({found['license']})",
            "as_of": str(date.today()),
            "volatile": False,
        })
        verification_log.append({
            "id": f"nw-{slug}",
            "source_url": found["source_url"],
            "license": found["license"],
            "artist": found["artist"],
            "media": rel_media,
        })

    pack = {
        "pack_id": "natural-world-northeast",
        "version": "0.1.0",
        "release_date": str(date.today()),
        "module": "natural_world",
        "entities": entities,
        "dimensions": [],
        "facts": [],
        "anchor_sets": [],
        "figures": [],
        "plain_cards": plain_cards,
    }

    os.makedirs(os.path.join("content", "packs"), exist_ok=True)
    with open(os.path.join("content", "packs", "natural_world.json"), "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2)
    with open(os.path.join("content", "verification-natural-world.json"), "w", encoding="utf-8") as f:
        json.dump(verification_log, f, indent=2)

    print(f"Wrote natural_world.json: {len(plain_cards)} visually verified cards.")

if __name__ == "__main__":
    main()
