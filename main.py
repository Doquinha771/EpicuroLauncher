import os
import sys
import time
import threading
import webbrowser
import logging
import subprocess
import shutil
import zipfile
import glob

# ==============================================================================
# Epicuro Aura
# "A simplicidade e o ultimo grau de sofisticacao."
# ==============================================================================

# --- CONFIGURACAO DE AMBIENTE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "retool_downloads")
HOST = os.getenv("EPICURO_HOST", "127.0.0.1")
PORT = int(os.getenv("EPICURO_PORT", "5000"))
AUTO_OPEN_BROWSER = os.getenv("EPICURO_AUTO_OPEN", "1") != "0"

# Configuracoes de Log e Estado
logging.basicConfig(level=logging.ERROR)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Estado Global com Thread Lock
state_lock = threading.Lock()
app_state = {
    "active": False,
    "completed": False,
    "error": None,
    "file_path": None
}
browser_opened = False

try:
    from flask import Flask, request, render_template_string, jsonify, send_file
    import yt_dlp
    import imageio_ffmpeg
except ImportError as exc:
    missing_module = getattr(exc, "name", "uma dependencia")
    print(f"[CRITICAL] Dependencia ausente: {missing_module}")
    print("Instale as dependencias com: python -m pip install -r requirements.txt")
    sys.exit(1)

# Configura FFmpeg
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
os.environ["PATH"] += os.pathsep + os.path.dirname(FFMPEG_PATH)

app = Flask(__name__)

# --- FRONTEND (AURA MINIMAL THEME) ---
# Mantido em uma string para preservar o app como um unico script.
RETOOL_INDEX = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Epicuro Aura</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg-default: #0f172a; --surface: rgba(255, 255, 255, 0.08); --surface-hover: rgba(255, 255, 255, 0.12); --primary: #ffffff; --text-sec: rgba(255, 255, 255, 0.6); }
        body { background-color: var(--bg-default); color: var(--primary); font-family: 'Plus Jakarta Sans', sans-serif; height: 100vh; width: 100vw; overflow: hidden; display: flex; align-items: center; justify-content: center; position: relative; }
        .ambient-bg { position: absolute; inset: -50px; background-size: cover; background-position: center; filter: blur(80px) saturate(180%) brightness(0.6); opacity: 0; transition: opacity 1.5s ease-in-out; z-index: 0; transform: scale(1.1); }
        .ambient-bg.active { opacity: 1; }
        .noise-overlay { position: absolute; inset: 0; background: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.03'/%3E%3C/svg%3E"); z-index: 1; pointer-events: none; mix-blend-mode: overlay; }
        .aura-card { position: relative; z-index: 10; width: 90%; max-width: 580px; background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px); border: 1px solid rgba(255,255,255,0.1); border-radius: 40px; padding: 48px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); display: flex; flex-direction: column; gap: 32px; transition: 0.4s cubic-bezier(0.2, 0.8, 0.2, 1); }
        .brand-area { text-align: center; } .logo { font-weight: 700; font-size: 24px; letter-spacing: -0.5px; margin-bottom: 4px; } .tagline { color: var(--text-sec); font-size: 13px; font-weight: 500; }
        .input-wrapper { background: var(--surface); border-radius: 24px; padding: 8px 8px 8px 24px; display: flex; align-items: center; border: 1px solid transparent; transition: 0.3s; }
        .input-wrapper:focus-within { background: var(--surface-hover); border-color: rgba(255,255,255,0.2); box-shadow: 0 0 0 4px rgba(255,255,255,0.05); }
        .url-input { flex: 1; background: transparent; border: none; color: white; font-size: 15px; font-weight: 500; outline: none; padding: 12px 0; font-family: inherit; }
        .url-input::placeholder { color: var(--text-sec); }
        .btn-paste { padding: 12px; color: var(--text-sec); cursor: pointer; border-radius: 50%; transition: 0.2s; } .btn-paste:hover { color: white; background: rgba(255,255,255,0.1); }
        .controls-row { display: flex; justify-content: space-between; align-items: center; padding: 0 8px; }
        .tabs { display: flex; background: var(--surface); padding: 4px; border-radius: 99px; }
        .tab { padding: 8px 20px; border-radius: 99px; font-size: 12px; font-weight: 600; color: var(--text-sec); cursor: pointer; transition: all 0.3s ease; } .tab:hover { color: white; } .tab.active { background: white; color: black; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .action-btn { background: white; color: black; border: none; padding: 14px 32px; border-radius: 99px; font-weight: 700; font-size: 13px; cursor: pointer; transition: 0.3s cubic-bezier(0.2, 0.8, 0.2, 1); display: flex; align-items: center; gap: 8px; }
        .action-btn:hover { transform: scale(1.05); box-shadow: 0 0 30px rgba(255,255,255,0.3); } .action-btn:disabled { opacity: 0.5; transform: none; cursor: not-allowed; }
        .quality-label { font-size: 11px; font-weight: 700; color: var(--text-sec); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px; display: block; padding-left: 8px; }
        .q-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
        .q-card { background: var(--surface); border-radius: 20px; padding: 16px; cursor: pointer; text-align: center; border: 1px solid transparent; transition: 0.3s; }
        .q-card:hover { background: var(--surface-hover); } .q-card.selected { background: rgba(255,255,255,0.15); border-color: rgba(255,255,255,0.3); }
        .q-main { font-size: 14px; font-weight: 700; display: block; margin-bottom: 2px; } .q-sub { font-size: 11px; color: var(--text-sec); }
        .toast { position: fixed; top: 40px; background: white; color: black; padding: 12px 24px; border-radius: 99px; font-size: 13px; font-weight: 600; box-shadow: 0 10px 40px rgba(0,0,0,0.3); transform: translateY(-100px); opacity: 0; transition: 0.5s cubic-bezier(0.2, 0.8, 0.2, 1); z-index: 100; } .toast.show { transform: translateY(0); opacity: 1; }
        .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); backdrop-filter: blur(10px); z-index: 50; opacity: 0; pointer-events: none; transition: 0.3s; display: flex; align-items: center; justify-content: center; } .modal-overlay.active { opacity: 1; pointer-events: auto; }
        .modal { background: #111; border-radius: 32px; padding: 32px; width: 360px; border: 1px solid rgba(255,255,255,0.1); text-align: center; transform: scale(0.9); transition: 0.3s; } .modal-overlay.active .modal { transform: scale(1); }
    </style>
</head>
<body>
    <div id="ambient-bg" class="ambient-bg"></div>
    <div class="noise-overlay"></div>
    <div class="aura-card">
        <div class="brand-area"><div class="logo">Epicuro</div><div class="tagline">Minimal Asset Extraction</div></div>
        <div class="input-wrapper">
            <i class="fas fa-link text-gray-500 mr-3 text-sm"></i>
            <input type="text" id="url-input" class="url-input" placeholder="Paste link..." autocomplete="off">
            <div class="btn-paste" onclick="clearInput()" title="Clear"><i class="fas fa-times"></i></div>
        </div>
        <div class="controls-row">
            <div class="tabs">
                <div onclick="setMode('video')" id="tab-video" class="tab active">Video</div>
                <div onclick="setMode('audio')" id="tab-audio" class="tab">Audio</div>
                <div onclick="setMode('spotify')" id="tab-spotify" class="tab">Spotify</div>
            </div>
            <button id="process-btn" onclick="analyzeUrl()" class="action-btn"><span>Download</span><i class="fas fa-arrow-right text-xs"></i></button>
        </div>
        <div id="settings-area">
            <span class="quality-label">Quality Preference</span>
            <div id="grid-video" class="q-grid">
                <div class="q-card selected" onclick="setQuality(this, 'best')"><span class="q-main">Max</span><span class="q-sub">Source</span></div>
                <div class="q-card" onclick="setQuality(this, '1080p')"><span class="q-main">1080p</span><span class="q-sub">Full HD</span></div>
                <div class="q-card" onclick="setQuality(this, '720p')"><span class="q-main">720p</span><span class="q-sub">Fast</span></div>
            </div>
            <div id="grid-audio" class="q-grid hidden">
                <div class="q-card selected" onclick="setQuality(this, '320')"><span class="q-main">320k</span><span class="q-sub">High Res</span></div>
                <div class="q-card" onclick="setQuality(this, '192')"><span class="q-main">192k</span><span class="q-sub">Standard</span></div>
            </div>
        </div>
    </div>
    <div id="toast" class="toast"><i class="fas fa-check-circle mr-2"></i> <span id="toast-msg">Success</span></div>
    <div id="playlist-modal" class="modal-overlay">
        <div class="modal">
            <div class="text-3xl mb-4">&#127873;</div>
            <h3 class="text-white font-bold text-lg mb-2">Playlist Found</h3>
            <p class="text-gray-400 text-xs mb-6 leading-relaxed">Multiple items detected.<br>Selection?</p>
            <div class="flex flex-col gap-2">
                <button onclick="resolvePlaylist('all')" class="w-full bg-white text-black font-bold py-3 rounded-full text-sm hover:bg-gray-200 transition">Download All</button>
                <button onclick="resolvePlaylist('single')" class="w-full bg-white/10 text-white font-medium py-3 rounded-full text-sm hover:bg-white/20 transition">Just One</button>
            </div>
            <div onclick="closeModal()" class="mt-4 text-xs text-gray-600 cursor-pointer hover:text-white">Cancel</div>
        </div>
    </div>
    <script>
        let currentMode = 'video', currentQuality = 'best', pendingUrl = '';
        const urlInput = document.getElementById('url-input'), ambientBg = document.getElementById('ambient-bg');
        
        urlInput.addEventListener('input', (e) => {
            const vid = extractYouTubeID(e.target.value);
            if (vid) { ambientBg.style.backgroundImage = `url('https://img.youtube.com/vi/${vid}/maxresdefault.jpg')`; ambientBg.classList.add('active'); }
            else if (!e.target.value) ambientBg.classList.remove('active');
        });
        function extractYouTubeID(url) { const m = url.match(/^.*((youtu.be\/)|(v\/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#&?]*).*/); return (m&&m[7].length==11)?m[7]:false; }
        
        function setMode(mode) {
            currentMode = mode;
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById('tab-' + mode).classList.add('active');
            document.getElementById('grid-video').classList.toggle('hidden', mode !== 'video');
            document.getElementById('grid-audio').classList.toggle('hidden', mode !== 'audio');
            document.getElementById('settings-area').style.opacity = mode === 'spotify' ? '0.3' : '1';
        }
        function setQuality(el, val) {
            el.parentElement.querySelectorAll('.q-card').forEach(c => c.classList.remove('selected'));
            el.classList.add('selected'); currentQuality = val;
        }
        function analyzeUrl() {
            const url = urlInput.value.trim();
            if (!url) return showToast('Please enter a URL first', true);
            pendingUrl = url;
            (url.includes('list=') || url.includes('/playlist/') || url.includes('/album/')) ? document.getElementById('playlist-modal').classList.add('active') : startProcess(url, 'single');
        }
        function resolvePlaylist(t) { closeModal(); startProcess(pendingUrl, t); }
        function closeModal() { document.getElementById('playlist-modal').classList.remove('active'); }
        async function startProcess(url, dlType) {
            const btn = document.getElementById('process-btn'); btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            try {
                const res = await fetch('/api/process', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ url, mode: currentMode, download_type: dlType, quality: currentQuality }) });
                if(res.ok) monitorProgress(); else throw new Error();
            } catch(e) { showToast('Connection Failed', true); resetState(); }
        }
        function monitorProgress() {
            const intv = setInterval(async () => {
                try {
                    const data = await (await fetch('/api/status')).json();
                    if (data.completed) { clearInterval(intv); finishSuccess(); }
                    else if (data.error) { clearInterval(intv); showToast(data.error || 'Error', true); resetState(); }
                } catch(e) { clearInterval(intv); resetState(); }
            }, 1000);
        }
        function finishSuccess() { showToast('Download Ready'); window.location.href = '/api/download_file'; resetState(); }
        function resetState() {
            const btn = document.getElementById('process-btn'); btn.disabled = false; btn.innerHTML = '<span>Download</span> <i class="fas fa-arrow-right text-xs"></i>';
            urlInput.value = ''; ambientBg.classList.remove('active');
        }
        function showToast(msg, err=false) {
            const t = document.getElementById('toast'); document.getElementById('toast-msg').innerText = msg;
            t.style.color = err ? '#ef4444' : 'black'; t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 3000);
        }
        function clearInput() { urlInput.value = ''; ambientBg.classList.remove('active'); }
    </script>
</body>
</html>
"""

# --- BACKEND LOGIC ---
def prepare_download_folder():
    """Limpa e recria a pasta de downloads de forma segura."""
    if os.path.exists(DOWNLOAD_DIR):
        try:
            shutil.rmtree(DOWNLOAD_DIR)
        except Exception as e:
            print(f"Erro ao limpar pasta: {e}")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def package_results():
    """Empacota os resultados: arquivo unico ou ZIP se houver multiplos itens."""
    files = glob.glob(os.path.join(DOWNLOAD_DIR, '*'))
    if not files:
        return None

    if len(files) == 1 and os.path.isfile(files[0]):
        return files[0]

    zip_name = f"aura_bundle_{int(time.time())}.zip"
    zip_path = os.path.join(BASE_DIR, zip_name)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, filenames in os.walk(DOWNLOAD_DIR):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                arcname = os.path.relpath(file_path, DOWNLOAD_DIR)
                zipf.write(file_path, arcname)
    
    return zip_path

def process_task(url, mode, download_type, quality):
    with state_lock:
        app_state.update({"active": True, "completed": False, "error": None, "file_path": None})
    
    prepare_download_folder()
    
    try:
        # --- SPOTIFY HANDLER ---
        if mode == 'spotify':
            # Usa o modulo instalado no mesmo ambiente Python.
            cmd = [sys.executable, "-m", "spotdl", "download", url, "--output", DOWNLOAD_DIR]
            subprocess.run(cmd, check=True, capture_output=True)

        # --- YOUTUBE / GERAL HANDLER ---
        else:
            ydl_opts = {
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'ffmpeg_location': FFMPEG_PATH,
                'noplaylist': download_type == 'single'
            }

            if "list=" in url and download_type != 'single':
                ydl_opts['outtmpl'] = os.path.join(DOWNLOAD_DIR, '%(playlist_title)s', '%(title)s.%(ext)s')

            if mode == 'audio':
                bitrate = quality if quality in ['320', '192'] else '192'
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': bitrate,
                    }],
                })
            else: # Video
                if quality == '1080p': fmt = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
                elif quality == '720p': fmt = 'bestvideo[height<=720]+bestaudio/best[height<=720]'
                else: fmt = 'bestvideo+bestaudio/best'
                ydl_opts['format'] = fmt
                ydl_opts['merge_output_format'] = 'mp4'

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        final_file = package_results()
        if not final_file:
            raise Exception("Nenhum arquivo gerado.")

        with state_lock:
            app_state["file_path"] = final_file
            app_state["completed"] = True

    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'stderr') and e.stderr:
            error_msg += f" | {e.stderr.decode()}"
        print(f"[ERROR] {error_msg}")
        with state_lock:
            app_state["error"] = "Download Failed. Check Console."
    finally:
        with state_lock:
            app_state["active"] = False

def validate_process_payload(data):
    if not isinstance(data, dict):
        return "Invalid request."

    url = (data.get("url") or "").strip()
    mode = data.get("mode")
    download_type = data.get("download_type")
    quality = data.get("quality")

    if not url.startswith(("http://", "https://")):
        return "Enter a valid URL."
    if mode not in {"video", "audio", "spotify"}:
        return "Invalid mode."
    if download_type not in {"single", "all"}:
        return "Invalid download type."
    if quality not in {"best", "1080p", "720p", "320", "192"}:
        return "Invalid quality."

    return None

# --- ROTAS FLASK ---
@app.route('/')
def home(): return render_template_string(RETOOL_INDEX)

@app.route('/api/process', methods=['POST'])
def api_process():
    data = request.get_json(silent=True) or {}
    validation_error = validate_process_payload(data)
    if validation_error:
        return jsonify({'error': validation_error}), 400

    with state_lock:
        is_active = app_state["active"]

    if is_active:
        return jsonify({'error': 'Busy'}), 429

    threading.Thread(target=process_task, args=(
        data.get('url'), data.get('mode'), data.get('download_type'), data.get('quality')
    ), daemon=True).start()
    return jsonify({'status': 'started'})

@app.route('/api/status')
def api_status():
    with state_lock:
        return jsonify(app_state)

@app.route('/api/download_file')
def download_file():
    with state_lock:
        fpath = app_state["file_path"]
    
    if fpath and os.path.exists(fpath):
        return send_file(fpath, as_attachment=True)
    return "File not found or expired.", 404

def open_browser():
    global browser_opened
    if AUTO_OPEN_BROWSER and not browser_opened:
        time.sleep(1)
        webbrowser.open(f'http://{HOST}:{PORT}')
        browser_opened = True

if __name__ == '__main__':
    threading.Thread(target=open_browser, daemon=True).start()
    print("--- EPICURO AURA STARTED ---")
    print(f"Open http://{HOST}:{PORT} in your browser.")
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
