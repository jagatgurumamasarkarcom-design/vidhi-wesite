#!/usr/bin/env python3
"""Collect the latest videos of the JagatGuru MamaSarkar YouTube channels into site/yt.json.
YouTube's channel feed gives the newest 15 videos per channel, so earlier videos are kept
from the copy already on the website and the list grows over time."""
import json, re, urllib.request, html, time, sys, os
CHANNELS = [
    {"id": "UCxCFUMc_dG9oPxjenLvojjg", "name": "JagatGuru MamaSarkar", "handle": "@JagatGuruMamaSarkar"},
    {"id": "UCZwdH_knjfDFogSlZVcZBVA", "name": "JagatGuru MamaSarkar (Mama ni Moj)", "handle": "@mamanimoj1580"},
    {"id": "UC6T4zWHsVTsGZmeNNc6PXZg", "name": "Jagatguru Mamasarkar Vlog", "handle": "@JagatguruMamasarkarVlog"},
]
UA = {"User-Agent": "Mozilla/5.0 (site build)"}
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "replace")
old = {}
prev = {}
try:
    prev = json.loads(get("https://jagatgurumamasarkar.in/yt.json?t=%d" % time.time()))
    old = {v["id"]: v for v in prev.get("videos", [])}
    for c in CHANNELS:
        for pc in prev.get("channels", []):
            if pc.get("id") == c["id"] and pc.get("avatar"):
                c["avatar"] = pc["avatar"]
except Exception as e:
    print("no previous list:", e)
vids = dict(old)
for ci, c in enumerate(CHANNELS):
    try:
        x = get("https://www.youtube.com/feeds/videos.xml?channel_id=" + c["id"])
    except Exception as e:
        print("feed failed", c["id"], e); continue
    for e in x.split("<entry>")[1:]:
        vid = re.search(r"<yt:videoId>(.*?)</", e).group(1)
        title = html.unescape(re.search(r"<title>(.*?)</title>", e, re.S).group(1)).strip()
        pub = re.search(r"<published>(.*?)</", e).group(1)
        link = re.search(r'<link rel="alternate" href="(.*?)"', e).group(1)
        views = re.search(r'views="(\d+)"', e)
        desc = re.search(r"<media:description>(.*?)</media:description>", e, re.S)
        vids[vid] = {"id": vid, "t": title, "ch": ci, "at": pub, "s": "/shorts/" in link,
                     "v": int(views.group(1)) if views else 0,
                     "d": html.unescape(desc.group(1)).strip()[:600] if desc else ""}
    try:
        page = get("https://www.youtube.com/channel/" + c["id"])
        m = re.search(r'<meta property="og:image" content="([^"]+)"', page)
        if m: c["avatar"] = re.sub(r"=s\d+-", "=s176-", html.unescape(m.group(1)))
    except Exception as e:
        print("avatar failed", c["id"], e)
# ---- Instagram: newest posts and reels of the trust's account (best effort; thumbnails are saved into the site) ----
IG_USER = "sanatani_jagatguru_mamasarkar"
SITE = os.path.dirname(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "site/yt.json"))
os.makedirs(os.path.join(SITE, "ig"), exist_ok=True)
def fetch_bin(url, headers=None):
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers or UA), timeout=30).read()
igold = {}
prev = {}
try:
    igold = {p["id"]: p for p in prev.get("ig", [])}
except Exception:
    pass
ig = dict(igold)
try:
    hdr = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 300.0.0.0",
           "x-ig-app-id": "936619743392459", "Accept": "application/json"}
    j = json.loads(fetch_bin("https://i.instagram.com/api/v1/users/web_profile_info/?username=" + IG_USER, hdr).decode())
    user = j["data"]["user"]
    igprof = {"user": IG_USER, "name": user.get("full_name") or IG_USER, "followers": (user.get("edge_followed_by") or {}).get("count", 0)}
    try:
        open(os.path.join(SITE, "ig", "_avatar.jpg"), "wb").write(fetch_bin(user.get("profile_pic_url_hd") or user["profile_pic_url"]))
        igprof["avatar"] = "ig/_avatar.jpg"
    except Exception as e:
        print("ig avatar failed", e)
    for ed in user["edge_owner_to_timeline_media"]["edges"]:
        n = ed["node"]; sc = n["shortcode"]
        cap = ""
        try: cap = n["edge_media_to_caption"]["edges"][0]["node"]["text"]
        except Exception: pass
        item = {"id": sc, "t": cap[:500], "at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(n["taken_at_timestamp"])),
                "reel": n.get("product_type") == "clips" or bool(n.get("is_video")), "likes": (n.get("edge_liked_by") or n.get("edge_media_preview_like") or {}).get("count", 0),
                "v": n.get("video_view_count") or 0, "img": "ig/%s.jpg" % sc}
        try:
            open(os.path.join(SITE, "ig", sc + ".jpg"), "wb").write(fetch_bin(n.get("thumbnail_src") or n["display_url"]))
        except Exception as e:
            print("ig thumb failed", sc, e)
        ig[sc] = item
    print("instagram:", len(user["edge_owner_to_timeline_media"]["edges"]), "posts")
except Exception as e:
    igprof = None
    print("instagram failed:", e)
# keep thumbnails of older posts: copy them from the live website
for sc, p in ig.items():
    f = os.path.join(SITE, "ig", sc + ".jpg")
    if not os.path.exists(f):
        try: open(f, "wb").write(fetch_bin("https://jagatgurumamasarkar.in/ig/%s.jpg" % sc))
        except Exception: p["img"] = ""
if not igprof:
    igprof = prev.get("igprof") if isinstance(prev, dict) else None
    try:
        if igprof and igprof.get("avatar") and not os.path.exists(os.path.join(SITE, "ig", "_avatar.jpg")):
            open(os.path.join(SITE, "ig", "_avatar.jpg"), "wb").write(fetch_bin("https://jagatgurumamasarkar.in/ig/_avatar.jpg"))
    except Exception: igprof["avatar"] = ""
out = {"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "channels": CHANNELS,
       "videos": sorted(vids.values(), key=lambda v: v["at"], reverse=True)[:400],
       "igprof": igprof, "ig": sorted(ig.values(), key=lambda v: v["at"], reverse=True)[:300]}
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "site/yt.json", "w"), ensure_ascii=False)
print(len(out["videos"]), "videos")
