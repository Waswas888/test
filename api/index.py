import json
import os
import threading
import time
import requests
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse

PORTAL_URL = "http://pon.access.ly/stalker_portal/server/load.php"
MAC_BASE = "00:1A:79:5C:B3:A3"
JSON_FILE_PATH = "/tmp/playlist.json"
BASE_HF_URL = "https://stream-tv-digital.hf.space"

app = FastAPI()

status_data = {
    "last_update": "Hali yangilanmagan",
    "total_channels": 0,
    "status": "Ishga tushmoqda...",
}

def create_fresh_session():
    """Создает свежую сессию и получает новый токен для обхода ограничений портала"""
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "X-User-Agent": "Model: MAG250; Link: WiFi",
        "Referer": "http://pon.access.ly/stalker_portal/c/index.html",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        "Pragma": "no-cache",
    }
    session.headers.update(headers)
    session.cookies.set("mac", MAC_BASE, domain="pon.access.ly")
    session.cookies.set("stb_lang", "en", domain="pon.access.ly")
    session.cookies.set("timezone", "Europe/London", domain="pon.access.ly")

    try:
        session.get("http://pon.access.ly/stalker_portal/c/", timeout=5)
        session.get("http://pon.access.ly/stalker_portal/c/xpcom.common.js", timeout=5)
        session.get("http://pon.access.ly/stalker_portal/c/version.js", timeout=5)
    except Exception:
        pass

    try:
        hs_url = f"{PORTAL_URL}?type=stb&action=handshake&token=&JsHttpRequest=1-xml"
        r = session.get(hs_url, timeout=8).json()
        token = r.get("js", {}).get("token")
        if token:
            session.cookies.set("token", token, domain="pon.access.ly")
            session.headers.update({"Authorization": f"Bearer {token}"})
    except Exception as e:
        print(f"[Session] Handshake xatoligi: {e}")

    metrics_data = json.dumps({
        "type": "stb",
        "model": "MAG254",
        "mac": MAC_BASE,
        "sn": "3F100914EEAF3",
        "uid": "2E858D27FD71853972013E6456B2DE4A3F228BA5241843CD292943E4F6D9507B",
        "random": "76f6f0ea9329a09d278a2dcc81721e6d6835d283",
    })
    prof_url = (
        f"{PORTAL_URL}?type=stb&action=get_profile&hd=1"
        "&ver=ImageDescription: 0.2.18-r23-250; ImageDate: Thu Sep 13 11:31:16 EEST 2018; PORTAL version: 5.3.0; API Version: JS API version: 343; STB API version: 146; Player Engine version: 0x58c"
        "&num_banks=2&sn=3F100914EEAF3&stb_type=MAG250&client_type=STB&image_version=218&video_out=hdmi"
        "&device_id=B6CA12E4100838EF6A18271EE7C5683F75438ADC28793E5A21AE776C483069A3"
        "&device_id2=B6CA12E4100838EF6A18271EE7C5683F75438ADC28793E5A21AE776C483069A3"
        "&signature=D2CC6F6C14D72DFD01CCB620188EF0449296615237E89BA9CABA8F881A68AA7A"
        "&auth_second_step=1&hw_version=1.7-BD-00&not_valid_token=0"
        f"&metrics={metrics_data}"
        f"&hw_version_2=d02e388e47ad401804696dd8814fc68736b6d150&timestamp={int(time.time())}&api_signature=262&JsHttpRequest=1-xml"
    )
    try:
        session.get(prof_url, timeout=8)
    except Exception:
        pass

    return session

def update_playlist():
    global status_data
    status_data["status"] = "Yangilanmoqda..."
    print("--- Kanallarni yig'ish boshlandi ---")

    try:
        session = create_fresh_session()
        channels_url = f"{PORTAL_URL}?type=itv&action=get_all_channels&JsHttpRequest=1-xml"

        channels = []
        for attempt in range(3):
            try:
                res = session.get(channels_url, timeout=15)
                channels_res = res.json()
                channels = channels_res.get("js", {}).get("data", [])
                if channels:
                    print(f"Portal jami {len(channels)} ta kanal topdi.")
                    break
            except Exception as e:
                print(f"Kanallarni olishda xatolik (urinish {attempt + 1}): {e}")
                time.sleep(2)

        channels_list = []
        if channels:
            for idx, target_channel in enumerate(channels):
                ch_name = target_channel.get("name", f"Kanal {idx}")
                cmd = target_channel.get("cmd", "")
                if cmd:
                    channels_list.append({"name": ch_name, "cmd": cmd})

        temp_file = "/tmp/playlist.tmp"
        final_file = JSON_FILE_PATH

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(channels_list, f, ensure_ascii=False, indent=4)

        if os.path.exists(final_file):
            os.remove(final_file)
        os.rename(temp_file, final_file)

        status_data["total_channels"] = len(channels_list)
        status_data["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        status_data["status"] = "Muvaffaqiyatli ishlayapti ✅"
        print(f"--- Bajarildi! Jami {len(channels_list)} ta kanal tayyorlandi. ---")

    except Exception as e:
        status_data["status"] = f"Xatolik: {e}"
        print(f"Kritik xatolik update_playlist da: {e}")

def background_worker_initial():
    time.sleep(3)
    try:
        update_playlist()
    except Exception as e:
        print(f"Boshlang'ich xatolik: {e}")

    while True:
        time.sleep(86400)
        try:
            update_playlist()
        except Exception as e:
            print(f"Background worker xatoligi: {e}")

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=background_worker_initial, daemon=True)
    t.start()

@app.get("/", response_class=HTMLResponse)
def admin_panel():
    return f"""
    <!DOCTYPE html>
    <html lang="uz">
    <head>
        <meta charset="UTF-8">
        <title>IPTV Admin Panel</title>
        <style>
            body {{ font-family: Arial, sans-serif; background: #0f172a; color: #f8fafc; text-align: center; padding: 50px; }}
            .card {{ background: #1e293b; padding: 30px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }}
            .badge {{ background: #22c55e; color: white; padding: 5px 12px; border-radius: 20px; font-weight: bold; }}
            a {{ color: #38bdf8; text-decoration: none; display: block; margin-top: 15px; font-size: 18px; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🚀 IPTV Proxy Admin Panel</h2>
            <p>Holati: <span class="badge">{status_data["status"]}</span></p>
            <p><b>Kanal:</b> {status_data["total_channels"]} ta</p>
            <p><b>Oxirgi yangilangan vaqt:</b> {status_data["last_update"]}</p>
            <hr style="border: 0.5px solid #334155; margin: 20px 0;">
            <a href="/pl.m3u8" target="_blank">📥 M3U Playlist (/pl.m3u8)</a>
            <a href="/playlist.json" target="_blank" style="color: #94a3b8; font-size: 14px;">📄 JSON ni ko'rish (/playlist.json)</a>
        </div>
    </body>
    </html>
    """

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/proxy")
def proxy_channel(cmd: str):
    """Универсальный прокси для создания ссылки через Stalker-портал"""
    try:
        clean_cmd = cmd.strip()
        for prefix in ["ffrt ", "ffmpeg ", "ffrt%20", "ffmpeg%20"]:
            if clean_cmd.startswith(prefix):
                clean_cmd = clean_cmd[len(prefix) :].strip()

        session = create_fresh_session()
        link_url = f"{PORTAL_URL}?type=itv&action=create_link&cmd={requests.utils.quote(clean_cmd)}&forced_storage=on&JsHttpRequest=1-xml"
        
        res = session.get(link_url, timeout=8)
        link_res = res.json()

        stream_cmd = None
        if isinstance(link_res, dict):
            if "js" in link_res and isinstance(link_res["js"], dict):
                stream_cmd = link_res["js"].get("cmd")
            if not stream_cmd:
                stream_cmd = link_res.get("cmd") or link_res.get("url")

        if not stream_cmd:
            stream_cmd = clean_cmd

        if stream_cmd:
            for prefix in ["ffrt ", "ffmpeg "]:
                if stream_cmd.startswith(prefix):
                    stream_cmd = stream_cmd[len(prefix) :].strip()
            return RedirectResponse(url=stream_cmd, status_code=302)
        else:
            return PlainTextResponse(f"Xatolik: Portal oqim bermadi.", status_code=500)
    except Exception as e:
        return PlainTextResponse(f"Proxy xatoligi: {str(e)}", status_code=500)

@app.get("/playlist.json")
def download_json():
    if os.path.exists(JSON_FILE_PATH):
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            content = json.load(f)
        return content
    return {"error": "Hali playlist tayyor emas!"}, 404

@app.get("/pl.m3u8", response_class=PlainTextResponse)
def download_m3u8(request: Request):
    if not os.path.exists(JSON_FILE_PATH):
        return "#EXTM3U\n# Xatolik: Playlist hali tayyorlanmadi"

    try:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            channels = json.load(f)
    except Exception:
        return "#EXTM3U\n# Xatolik: Playlistni o'qib bo'lmadi"

    m3u_lines = ["#EXTM3U"]
    for ch in channels:
        name = ch.get("name", "Kanal")
        cmd = ch.get("cmd", "")

        clean_cmd = cmd.strip()
        for prefix in ["ffrt ", "ffmpeg "]:
            if clean_cmd.startswith(prefix):
                clean_cmd = clean_cmd[len(prefix) :].strip()

        encoded_cmd = requests.utils.quote(clean_cmd)
        proxy_url = f"{BASE_HF_URL}/proxy?cmd={encoded_cmd}"

        m3u_lines.append(f"#EXTINF:-1,{name}")
        m3u_lines.append(proxy_url)

    return "\n".join(m3u_lines)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(content=b"", media_type="image/vnd.microsoft.icon")
