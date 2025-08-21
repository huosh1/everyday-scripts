#!/usr/bin/env python3
import os
import time
import subprocess
from typing import Optional, Dict, Any
from pypresence import Presence

APP_ID = "A"   # ton App ID
ASSET_NAME = "_"             # grande image (asset dans Dev Portal)
SMALL_PLAY = "soundcloud"         # petit asset ▶
SMALL_PAUSE = "soundcloud"       # petit asset ⏸
POLL_EVERY = 5

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

def build_payload(title: str, artist: str, url: str, status: str, started_at: int) -> Dict[str, Any]:
    details = f"♪  {title}"
    state   = f"— {artist or '알 수 없음'} 신이 듣는 중 "

    payload: Dict[str, Any] = {
        "details": details,
        "state": state,
        "start": started_at,  # timer “elapsed” qui monte
        "large_image": ASSET_NAME,
        "large_text": "사운드클라우드",
    }

    # Petite icône dynamique ▶ ou ⏸
    if status.lower() == "playing":
        payload["small_image"] = SMALL_PLAY
        payload["small_text"]  = "▶ Playing"
    elif status.lower() == "paused":
        payload["small_image"] = SMALL_PAUSE
        payload["small_text"]  = "⏸ Paused"

    # Boutons
    buttons = []
    buttons.append({"label": "🎧 Play", "url": "https://soundcloud.com/"})
    buttons.append({"label": "by huoshi", "url": "https://github.com/huosh1"})
    payload["buttons"] = buttons

    return payload

def main():
    rpc = Presence(APP_ID)
    rpc.connect()
    print("✅ Connected to Discord RPC aesthetic mode.")

    last_payload: Optional[Dict[str, Any]] = None
    started_at = int(time.time())

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
        title, artist, url = meta["title"], meta["artist"], meta["url"]

        if not title:
            time.sleep(POLL_EVERY)
            continue

        payload = build_payload(title, artist, url, status, started_at)

        if payload != last_payload:
            rpc.update(**payload)
            print(f"♪ {artist or '알 수 없음'} — {title} [{status}]")
            last_payload = payload

        time.sleep(POLL_EVERY)

if __name__ == "__main__":
    main()
