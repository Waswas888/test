import json
import time
import requests
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, PlainTextResponse

PORTAL_URL = "http://pon.access.ly/stalker_portal/server/load.php"
MAC_BASE = "00:1A:79:5C:B3:A3"
PROXY_PREFIX = "https://www.ipservice.tv/api/stream/?url="

app = FastAPI()

def create_verified_session():
    """Создает сессию, повторяющую успешную последовательность авторизации"""
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

    # 1. Запрос статики портала
    try:
        session.get("http://pon.access.ly/stalker_portal/c/", timeout=5)
        session.get("http://pon.access.ly/stalker_portal/c/xpcom.common.js", timeout=5)
        session.get("http://pon.access.ly/stalker_portal/c/version.js", timeout=5)
    except Exception:
        pass

    # 2. Handshake
    token = ""
    try:
        hs_url = f"{PORTAL_URL}?type=stb&action=handshake&token=&JsHttpRequest=1-xml"
        r = session.get(hs_url, timeout=5).json()
        token = r.get("js", {}).get("token", "")
        if token:
            session.cookies.set("token", token, domain="pon.access.ly")
            session.headers.update({"Authorization": f"Bearer {token}"})
    except Exception as e:
        print(f"Handshake error: {e}")

    # 3. Profile full
    current_timestamp = int(time.time())
    random_str = "bca85bfa90893c72d6e916be097b9e5f501ee211"
    
    metrics_data = json.dumps({
        "type": "stb",
        "model": "MAG254",
        "mac": MAC_BASE,
        "sn": "3F100914EEAF3",
        "uid": "2E858D27FD71853972013E6456B2DE4A3F228BA5241843CD292943E4F6D9507B",
        "random": random_str
    })
    
    token_param = f"&token={token}" if token else ""
    prof_url = (
        f"{PORTAL_URL}?type=stb&action=get_profile&JsHttpRequest=1-xml&hd=1"
        f"{token_param}"
        "&ver=ImageDescription: 0.2.18-r23-250; ImageDate: Thu Sep 13 11:31:16 EEST 2018; PORTAL version: 5.3.0; API Version: JS API version: 343; STB API version: 146; Player Engine version: 0x58c"
        "&num_banks=2&sn=3F100914EEAF3&stb_type=MAG250&client_type=STB&image_version=218&video_out=hdmi"
        "&device_id=B6CA12E4100838EF6A18271EE7C5683F75438ADC28793E5A21AE776C483069A3"
        "&device_id2=B6CA12E4100838EF6A18271EE7C5683F75438ADC28793E5A21AE776C483069A3"
        "&signature=D2CC6F6C14D72DFD01CCB620188EF0449296615237E89BA9CABA8F881A68AA7A"
        "&auth_second_step=1&hw_version=1.7-BD-00&not_valid_token=0"
        f"&metrics={metrics_data}"
        f"&hw_version_2=d02e388e47ad401804696dd8814fc68736b6d150&timestamp={current_timestamp}&api_signature=262&prehash=feffc7137a73f1719a634ea6042075c89ee5d6a7"
    )
    
    try:
        session.get(prof_url, timeout=6)
        session.get(f"{PORTAL_URL}?type=account_info&action=get_main_info&JsHttpRequest=1-xml", timeout=6)
    except Exception:
        pass

    return session

@app.get("/", response_class=HTMLResponse)
def admin_panel():
    return """
    <!DOCTYPE html>
    <html lang="uz">
    <head>
        <meta charset="UTF-8">
        <title>IPTV Direct Panel</title>
        <style>
            body { font-family: Arial, sans-serif; background: #0f172a; color: #f8fafc; text-align: center; padding: 50px; }
            .card { background: #1e293b; padding: 30px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
            a { color: #38bdf8; text-decoration: none; display: block; margin-top: 15px; font-size: 18px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🚀 IPTV Direct Playlist</h2>
            <a href="/pl.m3u8" target="_blank">📥 M3U Playlist (/pl.m3u8)</a>
        </div>
    </body>
    </html>
    """

@app.get("/pl.m3u8", response_class=PlainTextResponse)
def download_m3u8():
    """Генерирует плейлист с проксированием через ipservice.tv"""
    try:
        session = create_verified_session()
        
        channels_url = f"{PORTAL_URL}?type=itv&action=get_all_channels&JsHttpRequest=1-xml"
        res = session.get(channels_url, timeout=10)
        
        raw_text = res.text.strip()
        if not raw_text.startswith("{"):
            return f"#EXTM3U\n# Xatolik: Portal JSON o'rniga matn qaytardi: {raw_text[:100]}"

        res_json = res.json()
        channels = res_json.get("js", {}).get("data", [])
        
        if not channels:
            alt_url = f"{PORTAL_URL}?type=itv&action=get_ordered_list&JsHttpRequest=1-xml"
            res_alt = session.get(alt_url, timeout=10).json()
            channels = res_alt.get("js", {}).get("data", []) or res_alt.get("js", [])

        if not channels or not isinstance(channels, list):
            return "#EXTM3U\n# Kanallar topilmadi"

        m3u_lines = ["#EXTM3U"]
        for idx, target_channel in enumerate(channels):
            ch_name = target_channel.get("name", f"Kanal {idx}")
            cmd = target_channel.get("cmd", "").strip()

            if not cmd:
                continue

            for prefix in ["ffrt ", "ffmpeg ", "ffrt%20", "ffmpeg%20"]:
                if cmd.startswith(prefix):
                    cmd = cmd[len(prefix):].strip()

            # Оборачиваем ссылку в ваш прокси-сервис
            proxied_url = f"{PROXY_PREFIX}{requests.utils.quote(cmd)}"

            m3u_lines.append(f"#EXTINF:-1,{ch_name}")
            m3u_lines.append(proxied_url)

        return "\n".join(m3u_lines)

    except Exception as e:
        return f"#EXTM3U\n# Xatolik: {str(e)}"

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(content=b"", media_type="image/vnd.microsoft.icon")
