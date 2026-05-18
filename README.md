# EpicuroLauncher

Launcher em Python para baixar e organizar videos com uma interface local direta e facil de manter. O app roda em Flask, abre no navegador e suporta download de video, extracao de audio, playlists e downloads via `spotdl`.

> Use este projeto apenas com midias suas, em dominio publico, ou que voce tenha permissao para baixar. Respeite os termos de uso de cada plataforma.

## Features

- Local web UI at `http://127.0.0.1:5000`
- Video download with quality preferences: best, 1080p, or 720p
- Audio extraction to MP3 at 320 kbps or 192 kbps
- Playlist and album handling with ZIP packaging
- Bundled FFmpeg binary through `imageio-ffmpeg`

## Requirements

- Python 3.10+
- Internet access for dependency installation and media downloads

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

## Install As A Package

You can install the project directly from GitHub:

```powershell
python -m pip install git+https://github.com/Doquinha771/EpicuroLauncher.git
epicuro-launcher
```

Useful command options:

```powershell
epicuro-launcher --help
epicuro-launcher --version
epicuro-launcher --port 8080 --no-open-browser
```

For local development:

```powershell
python -m pip install -e .
epicuro-launcher
```

The app opens the browser automatically. To disable that behavior:

```powershell
$env:EPICURO_AUTO_OPEN="0"
python main.py
```

You can also customize the host and port:

```powershell
$env:EPICURO_HOST="127.0.0.1"
$env:EPICURO_PORT="8080"
python main.py
```

## Project Files

- `main.py` - Flask app, frontend template, download logic, and API routes.
- `pyproject.toml` - Package metadata and the `epicuro-launcher` command.
- `requirements.txt` - Python dependencies.
- `.gitignore` - Keeps local environments, caches, generated downloads, and ZIP bundles out of Git.
- `.github/workflows/release.yml` - Builds package files and creates GitHub Releases from version tags.

## Releases

Releases are generated automatically when a version tag is pushed:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

The workflow builds both `.whl` and `.tar.gz` files and attaches them to the GitHub Release.

## Notes

Downloaded files are written to `retool_downloads/`. Multi-file downloads are packaged as `aura_bundle_*.zip`. Both are ignored by Git.
