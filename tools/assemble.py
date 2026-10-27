# Builds site/index.html from src/app.html, data/campus.json and config.json.
# usage: python3 tools/assemble.py
import html, json, math, pathlib

root = pathlib.Path(__file__).resolve().parent.parent
cfg = json.loads((root / "config.json").read_text(encoding="utf-8"))
tpl = (root / "src" / "app.html").read_text(encoding="utf-8")
data = json.loads((root / "data" / "campus.json").read_text(encoding="utf-8"))


def excluded(data, cfg):
    # buildings checked and found not to be the school's (another school, homes, gone from the aerial photo …), listed in
    # config "exclude" as an OpenStreetMap id ("way/123") or, for 브이월드 buildings whose vw/N numbers change on a refetch,
    # a point inside the footprint ("at": [lat, lon]; the smallest footprint around it)
    ex = cfg.get("exclude") or []
    ids = {x["id"] for x in ex if x.get("id")}
    lat0, lon0 = data["meta"]["lat"], data["meta"]["lon"]
    phi = math.radians(lat0)
    mlat = 111132.92 - 559.82 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    mlon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi)
    pts = [((x["at"][1] - lon0) * mlon, (lat0 - x["at"][0]) * mlat) for x in ex if x.get("at")]

    def inside(p, ring):
        x, z = p; hit = False
        for i in range(len(ring)):
            (x1, z1), (x2, z2) = ring[i - 1], ring[i]
            if (z1 > z) != (z2 > z) and x < x1 + (z - z1) * (x2 - x1) / (z2 - z1): hit = not hit
        return hit
    def area(r): return abs(sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r)))) / 2
    out = {b["id"] for b in data["buildings"] if b["id"] in ids}
    for p in pts:   # a point drops only the smallest footprint around it, so an outline drawn inside another stays apart
        hit = [b for b in data["buildings"] if inside(p, b["o"])]
        if hit: out.add(min(hit, key=lambda b: area(b["o"]))["id"])
    return out


drop = excluded(data, cfg)
if drop:
    data["buildings"] = [b for b in data["buildings"] if b["id"] not in drop]
    print(f"excluded {len(drop)} buildings listed in config.json")
data["config"] = cfg
blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
assert all(k in tpl for k in ("__CAU_DATA__", "__TITLE__", "__PAGE_TITLE__", "__INTRO__"))
# search: a title people would type ("○○대 부수기 게임"), a fuller description and the same text visible while loading
school = cfg.get("school") or cfg["title"]
campus = cfg.get("campusName") or school
page_title = f"{school} 부수기 게임 | {campus} 3D | {cfg['title']}"
desc = (cfg["description"] + ("입니다." if cfg["description"].endswith("게임") else ".")
        + " 폭탄, 야구 배트, 레이저, 운석, 지진, 핵폭탄으로 건물을 무너뜨리고, 설치 없이 휴대폰과 PC 브라우저에서 무료로 할 수 있습니다.")
page = (tpl.replace("__CAU_DATA__", blob).replace("__PAGE_TITLE__", html.escape(page_title))
        .replace("__TITLE__", html.escape(cfg["title"])).replace("__INTRO__", html.escape(desc)))
head, rest = page.split('<div id="app">', 1)
e = lambda v: html.escape(v, quote=True)
url = cfg["url"]
# visit counter (GoatCounter, no cookies); it skips localhost and file:// pages on its own
ld = {
    "@context": "https://schema.org", "@type": "VideoGame", "name": cfg["title"],
    "alternateName": [f"{school} 부수기 게임", f"{campus} 부수기"], "description": desc, "url": url, "image": url + "og.png",
    "inLanguage": "ko", "genre": ["캐주얼", "시뮬레이션"], "gamePlatform": ["웹 브라우저", "PC", "휴대폰"],
    "applicationCategory": "GameApplication", "operatingSystem": "Windows, macOS, Android, iOS",
    "isAccessibleForFree": True, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "KRW"},
    "about": {"@type": "CollegeOrUniversity", "name": cfg.get("fullName") or school},
}
if cfg.get("hub"): ld["isPartOf"] = {"@type": "WebSite", "name": "SMASH 대학교", "url": cfg["hub"]}
# breadcrumb: Google shows it in place of the bare address, e.g. "Hong-Iron › SMASH 대학교 › 중앙대"
crumbs = [("Hong-Iron", "https://hong-iron.github.io/")]
if cfg.get("hub"): crumbs.append(("SMASH 대학교", cfg["hub"]))
crumbs.append((school, url))
ld = [ld, {"@context": "https://schema.org", "@type": "BreadcrumbList",
           "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(crumbs)]}]
ld_tag = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
gc = f'<script data-goatcounter="{e(cfg["goatcounter"])}" async src="https://gc.zgo.at/count.js"></script>\n' if cfg.get("goatcounter") else ""
doc = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:title" content="{e(cfg['title'] + ' — ' + school + ' 부수기 게임')}">
<meta property="og:site_name" content="SMASH 대학교">
<meta property="og:locale" content="ko_KR">
<meta property="og:description" content="{e(cfg['tagline'])}">
<meta property="og:type" content="website">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(url)}og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(cfg['ogAlt'])}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{e(url)}og.png">
<link rel="icon" href="icon-32.png" sizes="32x32">
<link rel="icon" href="icon-512.png" sizes="512x512">
<link rel="apple-touch-icon" href="icon-180.png">
{ld_tag}{gc}{head.strip()}
</head>
<body>
<div id="app">{rest.rstrip()}
</body>
</html>
"""
(root / "site" / "index.html").write_text(doc, encoding="utf-8")
print("site/index.html", len(doc.encode()) // 1024, "KB")
