"""Capture des videos d'une playlist YouTube non listee via l'API Data v3.

Une playlist non listee est lisible avec une simple cle API (pas d'OAuth).
On pagine playlistItems.list, on ajoute les nouvelles videos a la base.
Optionnel : si YOUTUBE_API_KEY est vide, ce module ne fait rien.
"""
import json
import urllib.request
import urllib.parse
from . import config, db

API = "https://www.googleapis.com/youtube/v3/playlistItems"


def _get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())


def ingest(conn, verbose=True):
    if not config.YOUTUBE_API_KEY or not config.YOUTUBE_PLAYLIST_ID:
        return 0
    added = 0
    page_token = None
    while True:
        params = {
            "part": "snippet",
            "playlistId": config.YOUTUBE_PLAYLIST_ID,
            "maxResults": 50,
            "key": config.YOUTUBE_API_KEY,
        }
        if page_token:
            params["pageToken"] = page_token
        data = _get(params)
        for item in data.get("items", []):
            sn = item["snippet"]
            vid = sn["resourceId"].get("videoId")
            if not vid:
                continue
            url = f"https://www.youtube.com/watch?v={vid}"
            bid = db.add_bookmark(
                conn, url, source="youtube",
                author=sn.get("videoOwnerChannelTitle") or sn.get("channelTitle"),
                caption=sn.get("description"),
            )
            if bid:
                added += 1
                if verbose:
                    print(f"  + YouTube: {sn.get('title')}")
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return added
