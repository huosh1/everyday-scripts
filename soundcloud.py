#!/usr/bin/env python3
import os
import time
import subprocess
import json
import urllib.request
from typing import Optional, Dict, Any, List
from pypresence import Presence

APP_ID = "1395094434613563435"   # ton App ID
ASSET_NAME = "_"             # grande image (asset dans Dev Portal)
SMALL_PLAY = "jouer"         # petit asset ▶
SMALL_PAUSE = "pause1"        # petit asset ⏸
POLL_EVERY = 5

# Ports DevTools (Chromium/Vivaldi/Brave...)
DEVTOOLS_PORTS = range(9222, 9226)

# Domaines media pour ranker les onglets DevTools
MEDIA_DOMAINS = (
    "music.youtube.com", "youtube.com", "youtu.be",
    "twitch.tv", "soundcloud.com",
    "open.spotify.com", "deezer.com", "tidal.com",
    "bandcamp.com", "vimeo.com"
)

FALLBACK_URL = "https://www.youtube.com/"

def sh(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    except subprocess.CalledProcessError:
        return ""

def list_players() -> list[str]:
    out = sh(["playerctl", "-l"])
    return [p for p in out.splitlines() if p.strip()] if out else []

def get_status(p: str) -> str:
    return sh(["playerctl", "-p", p, "status"])

def get_meta(p: str) -> Dict[str, str]:
    fmt = "{{xesam:title}}|{{xesam:artist}}|{{xesam:url}}"
    line = sh(["playerctl", "-p", p, "metadata", "--format", fmt])
    t, a, u = (line.split("|") + ["", "", ""])[:3]
    return {"title": t.strip(), "artist": a.strip(), "url": u.strip()}

def pick_active_player() -> Optional[str]:
    players = list_players()
    for p in players:
        if get_status(p).lower() == "playing":
            return p
    for p in players:
        if get_status(p).lower() == "paused":
            return p
    return players[0] if players else None

def _devtools_pages() -> List[str]:
    """Récupère toutes les pages ouvertes via DevTools"""
    pages: List[str] = []
    for port in DEVTOOLS_PORTS:
        for path in ("/json/list", "/json"):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=0.5) as r:
                    data = json.load(r)
                items = data.get("TargetInfos", data) if isinstance(data, dict) else data
                for it in items or []:
                    url = it.get("url", "")
                    if url.startswith("http"):
                        pages.append(url)
            except Exception:
                pass
    return pages

def _rank_url(url: str) -> int:
    """Donne un score aux URLs selon leur pertinence pour les médias"""
    return sum(domain in url for domain in MEDIA_DOMAINS)

def get_current_media_url(meta_url: Optional[str]) -> str:
    """Récupère l'URL de ce que tu écoutes/regardes actuellement"""
    # Si playerctl nous donne déjà l'URL, on l'utilise
    if meta_url:
        return meta_url
    
    # Sinon, on cherche dans les onglets ouverts via DevTools
    pages = _devtools_pages()
    if pages:
        # On prend l'URL avec le meilleur score (plus de domaines média)
        best_url = max(pages, key=_rank_url)
        return best_url
    
    # Fallback si rien n'est trouvé
    return FALLBACK_URL

def build_payload(title: str, artist: str, url: str, status: str, started_at: int) -> Dict[str, Any]:
    details = f"♪  {title}"
    state   = f"— {artist or '알 수 없음'} 신이 듣는 중 "

    payload: Dict[str, Any] = {
        "details": details,
        "state": state,
        "start": started_at,
        "large_image": ASSET_NAME,
        "large_text": "Listening / Watching",
    }

    if status.lower() == "playing":
        payload["small_image"] = SMALL_PLAY
        payload["small_text"]  = "▶ Playing"
        btn_label = "🎧 Play"
    elif status.lower() == "paused":
        payload["small_image"] = SMALL_PAUSE
        payload["small_text"]  = "⏸ Paused"
        btn_label = "🎧 Open"
    else:
        payload["small_image"] = SMALL_PLAY
        payload["small_text"]  = "▶ Playing"
        btn_label = "🎧 Play"

    # Boutons avec l'URL actuelle
    buttons = [
        {"label": btn_label, "url": url},
        {"label": "by huoshi", "url": "https://github.com/huosh1"},
    ]
    payload["buttons"] = buttons

    return payload

def main():
    rpc = Presence(APP_ID)
    rpc.connect()
    print("✅ Connected to Discord RPC.")

    last_payload: Optional[Dict[str, Any]] = None
    started_at = int(time.time())
    last_track: Optional[tuple] = None

    while True:
        p = pick_active_player()
        if not p:
            if last_payload:
                rpc.clear()
                print("ℹ️  RPC cleared (no player).")
                last_payload = None
            time.sleep(POLL_EVERY)
            continue

        status = get_status(p) or "Playing"
        meta = get_meta(p)
        title, artist = meta["title"], meta["artist"]

        if not title:
            time.sleep(POLL_EVERY)
            continue

        # Vérifier si c'est une nouvelle piste
        current_track = (title, artist)
        if current_track != last_track:
            started_at = int(time.time())
            last_track = current_track

        # Récupère l'URL de ce que tu écoutes/regardes
        url = get_current_media_url(meta.get("url"))

        payload = build_payload(title, artist, url, status, started_at)

        if payload != last_payload:
            rpc.update(**payload)
            print(f"♪ {artist or '알 수 없음'} — {title} [{status}] → {url}")
            last_payload = payload

        time.sleep(POLL_EVERY)

if __name__ == "__main__":
    main()