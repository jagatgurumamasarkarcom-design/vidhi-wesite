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
# ---- every video of each channel (the feed above only gives the newest 15): read the channel's Videos, Shorts and Live tabs ----
YH = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
      "Accept-Language": "hi-IN,hi;q=0.9,en;q=0.5", "Cookie": "CONSENT=YES+1; SOCS=CAI"}
def yget(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers=dict(YH, **({"Content-Type": "application/json"} if body is not None else {})))
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
def txt(x):
    if not isinstance(x, dict): return ""
    return x.get("content") or x.get("simpleText") or "".join(r.get("text", "") for r in x.get("runs", []))
def walk(o, out):
    if isinstance(o, list):
        for x in o: walk(x, out)
        return
    if not isinstance(o, dict): return
    if "lockupViewModel" in o:
        v = o["lockupViewModel"]; md = (v.get("metadata") or {}).get("lockupMetadataViewModel") or {}
        if v.get("contentId"): out["items"].append({"id": v["contentId"], "t": txt(md.get("title")), "s": False})
        return
    if "videoRenderer" in o:
        v = o["videoRenderer"]; out["items"].append({"id": v.get("videoId"), "t": txt(v.get("title")), "s": False}); return
    if "shortsLockupViewModel" in o:
        v = o["shortsLockupViewModel"]
        vid = (((v.get("onTap") or {}).get("innertubeCommand") or {}).get("reelWatchEndpoint") or {}).get("videoId")
        if vid: out["items"].append({"id": vid, "t": txt((v.get("overlayMetadata") or {}).get("primaryText")), "s": True})
        return
    if "continuationItemRenderer" in o:
        t = (((o["continuationItemRenderer"].get("continuationEndpoint") or {}).get("continuationCommand")) or {}).get("token")
        if t: out["cont"] = t
        return
    for k in o: walk(o[k], out)
def channel_tab(handle, tab):
    h = yget("https://www.youtube.com/%s/%s?hl=hi&gl=IN" % (handle, tab))
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", h, re.S)
    key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', h); ver = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', h)
    if not m or not key: return [], None
    d = json.loads(m.group(1))
    tabs = (((d.get("contents") or {}).get("twoColumnBrowseResultsRenderer") or {}).get("tabs")) or []
    sel = next((t for t in tabs if (t.get("tabRenderer") or {}).get("selected")), None)
    out = {"items": [], "cont": None}; walk(sel, out)
    ctx = {"client": {"clientName": "WEB", "clientVersion": ver.group(1) if ver else "2.20241101.00.00", "hl": "hi", "gl": "IN"}}
    n = 0
    while out["cont"] and n < 60:
        n += 1; tok = out["cont"]; out["cont"] = None
        j = json.loads(yget("https://www.youtube.com/youtubei/v1/browse?key=" + key.group(1), {"context": ctx, "continuation": tok}))
        walk(j.get("onResponseReceivedActions") or [], out)
    return out["items"], (key.group(1), ctx)
def player(vid, kc):
    j = json.loads(yget("https://www.youtube.com/youtubei/v1/player?key=" + kc[0], {"context": kc[1], "videoId": vid}))
    vd = j.get("videoDetails") or {}; mf = (j.get("microformat") or {}).get("playerMicroformatRenderer") or {}
    return vd, mf
added = 0
for ci, c in enumerate(CHANNELS):
    for tab in ("videos", "shorts", "streams"):
        try:
            items, kc = channel_tab(c["handle"], tab)
        except Exception as e:
            print("tab failed", c["handle"], tab, e); continue
        print(c["handle"], tab, len(items))
        for it in items:
            vid = it["id"]
            if not vid or vid in vids: continue
            rec = {"id": vid, "t": it["t"], "ch": ci, "at": "", "s": it["s"] or tab == "shorts", "v": 0, "d": ""}
            if tab == "streams": rec["live"] = 1
            try:
                vd, mf = player(vid, kc)
                rec["t"] = vd.get("title") or rec["t"]; rec["v"] = int(vd.get("viewCount") or 0)
                rec["d"] = (vd.get("shortDescription") or "")[:600]; rec["sec"] = int(vd.get("lengthSeconds") or 0)
                pub = mf.get("publishDate") or mf.get("uploadDate") or ""
                if pub:
                    from datetime import datetime, timezone
                    rec["at"] = datetime.fromisoformat(pub).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
            except Exception as e:
                print("player failed", vid, e)
            if rec["at"]:
                vids[vid] = rec; added += 1
print("added from channel pages:", added)
# ---- Instagram: newest posts and reels of the trust's account (best effort; thumbnails are saved into the site) ----
IG_USER = "sanatani_jagatguru_mamasarkar"
SITE = os.path.dirname(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "site/yt.json"))
os.makedirs(os.path.join(SITE, "ig"), exist_ok=True)
def fetch_bin(url, headers=None):
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers or UA), timeout=30).read()
igold = {}
try:
    igold = {p["id"]: p for p in prev.get("ig", [])}
except Exception:
    pass
ig = dict(igold)
TOKEN = os.environ.get("IG_TOKEN", "").strip()
def ig_graph():
    """official Instagram API (token saved as the IG_TOKEN secret of the GitHub repo)"""
    g = "https://graph.instagram.com/"
    me = json.loads(get(g + "me?fields=username,name,followers_count,media_count,profile_picture_url&access_token=" + TOKEN))
    prof = {"user": me.get("username", IG_USER), "name": me.get("name") or me.get("username"), "followers": me.get("followers_count", 0)}
    try:
        open(os.path.join(SITE, "ig", "_avatar.jpg"), "wb").write(fetch_bin(me["profile_picture_url"])); prof["avatar"] = "ig/_avatar.jpg"
    except Exception as e: print("ig avatar failed", e)
    url = g + "me/media?fields=id,caption,media_type,media_product_type,media_url,thumbnail_url,permalink,timestamp,like_count&limit=50&access_token=" + TOKEN
    n = 0
    for page in range(4):
        d = json.loads(get(url))
        for m in d.get("data", []):
            sc = re.search(r"/(?:p|reel|reels|tv)/([\w-]+)", m.get("permalink", ""))
            if not sc: continue
            sc = sc.group(1)
            item = {"id": sc, "t": (m.get("caption") or "")[:500], "at": m["timestamp"].replace("+0000", "+00:00"),
                    "reel": m.get("media_type") == "VIDEO", "likes": m.get("like_count", 0), "v": 0, "img": "ig/%s.jpg" % sc}
            f = os.path.join(SITE, "ig", sc + ".jpg")
            try: open(f, "wb").write(fetch_bin(m.get("thumbnail_url") or m["media_url"]))
            except Exception as e: print("ig thumb failed", sc, e)
            ig[sc] = item; n += 1
        url = (d.get("paging") or {}).get("next")
        if not url: break
    try: get(g + "refresh_access_token?grant_type=ig_refresh_token&access_token=" + TOKEN)  # keeps the token alive
    except Exception as e: print("ig token refresh failed", e)
    print("instagram (api):", n, "posts")
    return prof
igprof = None
if TOKEN:
    try: igprof = ig_graph()
    except Exception as e: print("instagram api failed:", e)
if not igprof:
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
       "videos": sorted(vids.values(), key=lambda v: v["at"], reverse=True)[:1500],
       "igprof": igprof, "ig": sorted(ig.values(), key=lambda v: v["at"], reverse=True)[:300]}
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "site/yt.json", "w"), ensure_ascii=False)
print(len(out["videos"]), "videos")
