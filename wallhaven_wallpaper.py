import os
import time
import json
import yaml
import argparse
import random
import requests
import subprocess
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

WALLHAVEN_SEARCH_URL = "https://wallhaven.cc/api/v1/search"

DEFAULT_CONFIG = Path.home() / ".config/wallhaven-wallpaper/config.yaml"
STATE_FILE = Path.home() / ".config/wallhaven-wallpaper/state.json"


def expand(p):
    return Path(os.path.expanduser(p))


def load_config(path: Path):
    if not path.exists():
        raise RuntimeError(f"Config não encontrada: {path}")

    with open(path) as f:
        return yaml.safe_load(f) or {}


def save_state(data):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def set_gnome_wallpaper(image_path: Path):
    uri = f"file://{image_path}"

    for key in ["picture-uri", "picture-uri-dark"]:
        subprocess.run(
            ["gsettings", "set", "org.gnome.desktop.background", key, uri],
            check=False,
        )


def download_image(url: str, folder: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = Path(url).suffix or ".jpg"
    path = folder / f"wall_{ts}{suffix}"

    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)

    return path


def build_wallhaven_params(cfg):
    params = {}

    if cfg.get("query"):
        params["q"] = cfg["query"]

    if cfg.get("categories"):
        params["categories"] = cfg["categories"]

    if cfg.get("purity"):
        params["purity"] = cfg["purity"]

    if cfg.get("ratios"):
        params["ratios"] = cfg["ratios"]

    if cfg.get("atleast"):
        params["atleast"] = cfg["atleast"]

    if cfg.get("sorting"):
        params["sorting"] = cfg["sorting"]
    else:
        params["sorting"] = "random"

    params["page"] = 1

    return params


def fetch_wallhaven(params, api_key):
    headers = {"X-API-Key": api_key}

    r = requests.get(WALLHAVEN_SEARCH_URL, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    payload = r.json()

    return payload.get("data", [])


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def update_history(state, new_id, max_size):
    history = state.get("recent_ids", [])

    if new_id in history:
        history.remove(new_id)

    history.insert(0, new_id)

    history = history[:max_size]

    state["recent_ids"] = history
    return state


def cleanup_old_files(folder: Path, max_files: int):
    if max_files <= 0:
        return

    files = sorted(folder.glob("wall_*"), key=lambda p: p.stat().st_mtime)

    excess = len(files) - max_files
    if excess <= 0:
        return

    for f in files[:excess]:
        try:
            f.unlink()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--skip", action="store_true")

    args = parser.parse_args()

    cfg = load_config(expand(args.config))

    state = load_state()
    history_size = int(cfg.get("history_size", 30))
    recent_ids = set(state.get("recent_ids", []))

    interval = int(cfg.get("interval", 900))
    download_dir = expand(cfg.get("download_dir", "~/.local/share/random-wallpapers"))
    download_dir.mkdir(parents=True, exist_ok=True)

    env_path = Path(args.config).parent / ".env"
    load_dotenv(env_path)

    api_key = os.getenv("WALLHAVEN_API_KEY")
    if not api_key:
        raise RuntimeError("WALLHAVEN_API_KEY not defined on .env")

    params = build_wallhaven_params(cfg)

    if args.skip:
        args.once = True

    print("Wallhaven Wallpaper initialized")

    while True:
        try:
            wallpapers = fetch_wallhaven(params, api_key)

            if not wallpapers:
                print("Could not fetch wallpapers")
                if args.once:
                    break
                time.sleep(interval)
                continue

            filtered = [w for w in wallpapers if w.get("id") not in recent_ids]

            pool = filtered if filtered else wallpapers

            chosen = random.choice(pool)

            url = chosen.get("path")
            if not url:
                print("Wallpaper URL not found")
                if args.once:
                    break
                time.sleep(interval)
                continue

            img = download_image(url, download_dir)
            set_gnome_wallpaper(img)
            cleanup_old_files(download_dir, int(cfg.get("max_files", 0)))

            state = update_history(state, chosen.get("id"), history_size)

            state.update(
                {
                    "last_image": str(img),
                    "wallhaven_id": chosen.get("id"),
                    "timestamp": time.time(),
                }
            )

            save_state(state)

            print(f"Wallpaper updated: {img}")

        except Exception as e:
            print("Error:", e)

        if args.once:
            break

        time.sleep(interval)


if __name__ == "__main__":
    main()
