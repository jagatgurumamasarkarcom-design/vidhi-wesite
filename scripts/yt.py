#!/usr/bin/env python3
"""Collect the latest videos of the JagatGuru MamaSarkar YouTube channels into site/yt.json.
YouTube's channel feed gives the newest 15 videos per channel, so earlier videos are kept
from the copy already on the website and the list grows over time."""
import json, re, urllib.request, html, time, sys
CHANNELS = [
    {"id": "UCxCFUMc_dG9oPxjenLvojjg", "name": "JagatGuru MamaSarkar", "handle": "@JagatGuruMamaSarkar"},
    {"id": "UCZwdH_knjfDFogSlZVcZBVA", "name": "JagatGuru MamaSarkar (Mama ni Moj)", "handle": "@mamanimoj1580"},
    {"id": "UC6T4zWHsVTsGZmeNNc6PXZg", "name": "Jagatguru Mamasarkar Vlog", "handle": "@JagatguruMamasarkarVlog"},
]
UA = {"User-Agent": "Mozilla/5.0 (site build)"}
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "replace")
old = {}
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
out = {"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "channels": CHANNELS,
       "videos": sorted(vids.values(), key=lambda v: v["at"], reverse=True)[:400]}
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "site/yt.json", "w"), ensure_ascii=False)
print(len(out["videos"]), "videos")
