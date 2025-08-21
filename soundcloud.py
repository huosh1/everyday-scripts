#!/usr/bin/env python3
import time, subprocess
from typing import Optional, Dict, Any
from pypresence import Presence

APP_ID = "1395094434613563435"   # ton App ID
ASSET_NAME = "_"                 # nom de l'asset (sans extension)
POLL_EVERY = 5                   # secondes

def sh(cmd: list[str]) -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        return out.decode("utf-8", errors="ignore").strip()
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
        if get_status(p).lower() == "listening":
            return p
    for p in players:
        if get_status(p).lower() == "paused":
            return p
    return players[0] if players else None

def main():
    rpc = Presence(APP_ID)
    rpc.connect()
    print("✅ Connected to Discord RPC")

    last_payload: Optional[Dict[str, Any]] = None
    started_at = int(time.time())

    while True:
        p = pick_active_player()
        if not p:
            if last_payload:
                rpc.clear()
                print("ℹ️  RPC cleared (no players).")
                last_payload = None
            time.sleep(POLL_EVERY)
            continue

        status = get_status(p).title() or "Listening"
        meta = get_meta(p)
        title, artist, url = meta["title"], meta["artist"], meta["url"]

        if not title:
            if last_payload:
                rpc.clear()
                print(f"ℹ️  RPC cleared (no title from {p}).")
                last_payload = None
            time.sleep(POLL_EVERY)
            continue

        if not artist and " - " in title:
            maybe_artist, maybe_track = title.split(" - ", 1)
            artist = maybe_artist.strip()
            title = maybe_track.strip()

        # 🎵 + titre
        details = f" ♪ {title}"
        state   = f" — {artist or '알 수 없음'} 신이 듣는 중 "

        payload: Dict[str, Any] = {
            "details": details,
            "state": state,
            "start": started_at,
        }

        # bouton si URL valide
        if url.startswith("http"):
            payload["buttons"] = [{"label": "사운드클라우드에서 열기", "url": url}]

        # image large
        if ASSET_NAME:
            payload["large_image"] = ASSET_NAME
            payload["large_text"]  = "사운드클라우드"  # visible au survol

        if payload != last_payload:
            rpc.update(**payload)
            print(f"♪  {artist or '알 수 없음'} — {title}  [{status}]  (player={p})")
            last_payload = payload

        time.sleep(POLL_EVERY)

if __name__ == "__main__":
    main()
