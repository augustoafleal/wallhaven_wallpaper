# Wallhaven Wallpaper Rotator (Linux / GNOME)

A lightweight Python-based wallpaper rotator for Linux (tested on Arch + GNOME).

This tool periodically fetches random wallpapers from the Wallhaven API, downloads them locally, and sets them as your GNOME desktop background.
It is designed to run unattended in the background using `systemd --user`.

Key goals:

- Fully automated wallpaper rotation
- Wallhaven API integration (with API key)
- YAML-based configuration
- Secrets isolated in `.env`
- GNOME background support (light + dark)
- systemd user service + timer (no long-running Python loop)
- Simple CLI for manual refresh (“skip”)

## Features

- Random wallpapers from Wallhaven
- Configurable search (query, categories, purity, aspect ratio, minimum resolution)
- Local download cache
- GNOME wallpaper auto-update (`picture-uri` + `picture-uri-dark`)
- Runs in background via systemd timer
- Manual refresh on demand
- State persisted to `state.json`


## Project Structure

Expected layout:

``` 
~/.config/wallhaven-wallpaper/
│
├── wallhaven_wallpaper.py
├── config.yaml
├── .env
└── state.json        (auto-generated)
```

Systemd user units:

```
~/.config/systemd/user/
├── wallhaven-wallpaper.service
└── wallhaven-wallpaper.timer
``` 

## Requirements

- Python 3
- GNOME (uses `gsettings`)
- systemd (user services)

Python dependencies:

- requests
- PyYAML
- python-dotenv

On Arch Linux:

```shell
sudo pacman -S python python-requests python-yaml python-dotenv
```

If you are using pyenv or a custom Python:

```shell
pip install requests pyyaml python-dotenv
```

## Configuration

### 1. config.yaml

Example:

```yaml
interval: 1800
query: "nature"
categories: "100"
purity: "100"
ratios: "16x9"
atleast: "3840x2160"
sorting: "random"
download_dir: "~/.local/share/random-wallpapers"
history_size: 30
max_files: 20
``` 

### Fields

- interval – seconds between updates (only used when running without systemd)
- query – Wallhaven search query (supports OR, multiple keywords, etc.)
- categories – category bitmask ("100" recommended to avoid people/anime)
- purity – SFW / sketchy / NSFW filter
- ratios – aspect ratio (e.g. 16x9, 21x9)
- atleast – minimum resolution (e.g. 3840x2160)
- download_dir – where images are stored locally
- history_size – number of recent wallpaper IDs remembered to avoid repeats
- max_files – maximum number of local wallpapers to keep (0 = unlimited)

All fields are optional.

### 2. .env

Create:

```shell
~/.config/wallhaven-wallpaper/.env
```

Content:

WALLHAVEN_API_KEY=YOUR_API_KEY_HERE

Permissions:

```shell
chmod 600 ~/.config/wallhaven-wallpaper/.env
```

This keeps your API key out of source control and out of YAML.

## Running Manually

From the project directory:

Run once:

```shell
python wallhaven_wallpaper.py --once
```
Skip / force refresh:

```shell
python wallhaven_wallpaper.py --skip
```

Use a custom config:

```shell
python wallhaven_wallpaper.py --config /path/to/config.yaml --once
```
---

## Running in Background (systemd --user)

Instead of keeping Python running in a loop, the recommended setup uses:

- a oneshot service
- triggered periodically by a user timer

This is cleaner, crash-safe, and integrates with journald.

### 1. Create systemd user directory

```shell
mkdir -p ~/.config/systemd/user
```

### 2. Service file

Create:

```shell
~/.config/systemd/user/wallhaven-wallpaper.service
```

Content:

```conf
[Unit]
Description=Wallhaven Wallpaper Rotator

[Service]
Type=oneshot
ExecStart=/usr/bin/python %h/.config/wallhaven-wallpaper/wallhaven_wallpaper.py --once
WorkingDirectory=%h/.config/wallhaven-wallpaper
Environment=PYTHONUNBUFFERED=1
TimeoutStartSec=120
``` 

Adjust /usr/bin/python if your Python lives elsewhere (which python).

### 3. Timer file

Create:

```shell
~/.config/systemd/user/wallhaven-wallpaper.timer
```

Example (every 15 minutes):

```conf
[Unit]
Description=Run Wallhaven Wallpaper periodically

[Timer]
OnBootSec=2min
OnUnitActiveSec=15min
AccuracySec=1min
Persistent=true

[Install]
WantedBy=timers.target
```

You can change OnUnitActiveSec to 15min, 1h, etc.

When using the timer, the interval in config.yaml is effectively ignored.

### 4. Enable

Reload systemd:

systemctl --user daemon-reload

Enable and start timer:

```shell
systemctl --user enable --now wallhaven-wallpaper.timer
```

Verify:

```shell
systemctl --user list-timers
```

### 5. Stop and remove the service

Stop and disable the timer:

```shell
systemctl --user disable --now wallhaven-wallpaper.timer
```

If you want to remove the unit files entirely:

```shell
rm ~/.config/systemd/user/wallhaven-wallpaper.service
rm ~/.config/systemd/user/wallhaven-wallpaper.timer
systemctl --user daemon-reload
```

## Logs

Follow service logs:

```shell
journalctl --user -u wallhaven-wallpaper.service -f
```

## Manual Refresh (Skip)

Instead of calling Python directly:

```shell
systemctl --user start wallhaven-wallpaper.service
```

You may optionally add an alias:

```shell
alias wallskip="systemctl --user start wallhaven-wallpaper.service"
```

> For an example, you can add an alias in your ~/.zshrc

## State File

state.json is automatically created and contains:

- last downloaded image
- Wallhaven wallpaper ID
- timestamp

Example:

```json
{
  "last_image": "/home/user/.local/share/random-wallpapers/wall_20260131_142233.jpg",
  "wallhaven_id": "abc123",
  "timestamp": 1706713353.2
}
```

## Notes

- The script downloads the original wallpaper (path) provided by Wallhaven.
- GNOME light and dark backgrounds are both updated.
- Requests are intentionally low-frequency to respect the API.
- Categories set to "100" reliably exclude people.

## Possible Future Improvements

- Avoid repeating recent wallpapers
- Blacklist by ID
- Automatic monitor resolution detection
- Hotkey integration for skip
- Fade transitions
- Preloading next wallpaper
