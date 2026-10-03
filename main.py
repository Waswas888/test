import os
import time
import requests
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response, JSONResponse

app = FastAPI()

PORTAL_URL = "http://185.129.1.249:88/stalker_portal/server/load.php"
MAC = "00:1A:79:1E:AE:CA"
SN = "DF0F44459D4A7"
UID = "AC8300DB56F0CB9FE6EEEDE8DE33983101E0E001674836FBCA9F33B4F2BE0BFA"
RANDOM = "6ed621bb34dc4048a9ec86c8e0daca1775985e2a"
DEVICE_ID = "971A3E208DDDF68098245F5F4B6B8EEF2AA7871B09801557CB51022B6CFC99F6"
SIGNATURE = "E2A028C645F51F1DACC4CBF61840D910E8CD6BC4B57E18DE51F851E7C05EAB72"
HW_VERSION_2 = "985e216b34d169f6944e957d5092baf9c873834a"
TELEGRAM_GROUP = "https://t.me/+2lWVU6CKQsVkMWRi"
SECRET_KEY = "0"
STUB_VIDEO_URL = "https://raw.githubusercontent.com/Waswas777/video2/refs/heads/main/playlist.m3u8"
TOKEN_SOURCE_URL = "" # Если есть источник токенов, укажите сюда

cached_channels = []
cached_headers = None
cached_token = ""
session_time = 0
last_error = ""

def get_valid_session():
    global cached_headers, cached_token, session_time, last_error
    now = time.time() * 1000
    if cached_headers and cached_token and (now - session_time < 300000): # Сократим кэш до 5 минут
        return {"headers": cached_headers, "token": cached_token}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "X-User-Agent": "Model: MAG250; Link: WiFi",
        "Referer": "http://185.129.1.249:88/stalker_portal/c/index.html",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        "Pragma": "no-cache",
        "Cookie": f"mac={MAC}; stb_lang=en; timezone=Europe/London"
    }
    token = ""
    try:
        # 1. Handshake
        hs_url = f"{PORTAL_URL}?type=stb&action=handshake&token=&JsHttpRequest=1-xml"
        hs_res = requests.get(hs_url, headers=headers, timeout=10)
        hs_data = hs_res.json()
        token = hs_data.get("js", {}).get("token") or hs_data.get("token") or ""
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
            headers["Cookie"] = f"mac={MAC}; stb_lang=en; timezone=Europe/London; token={token}"

        timestamp = int(now / 1000)
        metrics = '{"type":"stb","model":"MAG254","mac":"' + MAC + '","sn":"' + SN + '","uid":"' + UID + '","random":"' + RANDOM + '"}'

        # 2. Обязательные шаги инициализации приставки, без которых портал сбрасывает авторизацию
        init_url = f"{PORTAL_URL}?type=stb&action=stb_init&JsHttpRequest=1-xml&token={token}"
        requests.get(init_url, headers=headers, timeout=10)

        profile_url = (
            f"{PORTAL_URL}?type=stb&action=get_profile&JsHttpRequest=1-xml&hd=1&"
            f"ver=ImageDescription: 0.2.18-r23-250; PORTAL version: 5.3.0&"
            f"sn={SN}&stb_type=MAG250&client_type=STB&device_id={DEVICE_ID}&"
            f"signature={SIGNATURE}&hw_version_2={HW_VERSION_2}&timestamp={timestamp}&token={token}"
        )
        requests.get(profile_url, headers=headers, timeout=10)
        
        cached_headers = headers
        cached_token = token
        session_time = now
    except Exception as e:
        last_error = f"Session error: {str(e)}"
    
    return {"headers": cached_headers or headers, "token": cached_token}
    
def update_channels_list():
    global cached_channels, last_error
    try:
        session = get_valid_session()
        token = session["token"]
        headers = session["headers"]
        
        genres_url = f"{PORTAL_URL}?type=itv&action=get_genres&JsHttpRequest=1-xml&token={token}"
        genres_res = requests.get(genres_url, headers=headers, timeout=10)
        genres_map = {}
        try:
            genres_json = genres_res.json()
            genres_data = genres_json.get("js") or genres_json
            if isinstance(genres_data, list):
                for g in genres_data:
                    genres_map[g.get("id")] = g.get("title") or g.get("name") or "Общие"
        except Exception:
            pass

        # Пробуем запросить каналы без указания genre=* (иногда это вызывает ошибку на сервере)
        channels_url = f"{PORTAL_URL}?type=itv&action=get_all_channels&JsHttpRequest=1-xml&token={token}"
        res = requests.get(channels_url, headers=headers, timeout=10)
        text = res.text
        
        # Запишем сырой ответ в lastError, чтобы увидеть, что именно отвечает портал
        last_error = f"RAW: {text[:100]}"

        if not text.strip().startswith("<") and not text.startswith("Authorization"):
            res_json = res.json()
            js_data = res_json.get("js")
            data = []
            if isinstance(js_data, list):
                data = js_data
            elif isinstance(js_data, dict):
                data = js_data.get("data") or js_data.get("channels") or []
            elif isinstance(res_json.get("data"), list):
                data = res_json.get("data")
            
            if data:
                cached_channels = []
                for ch in data:
                    genre_id = ch.get("tv_genre_id") or ch.get("genre_id")
                    cached_channels.append({
                        "name": ch.get("name") or ch.get("title") or "Kanal",
                        "cmd": ch.get("cmd"),
                        "group_title": genres_map.get(genre_id, "Общие")
                    })
                last_error = ""
    except Exception as e:
        last_error = f"Update channels error: {str(e)}"
@app.get("/")
def root_redirect():
    return RedirectResponse(TELEGRAM_GROUP, status_code=302)

@app.get("/debug")
def debug_page():
    if not cached_channels:
        update_channels_list()
    return JSONResponse({
        "channelsCount": len(cached_channels),
        "lastError": last_error,
        "token": "EXISTS" if cached_token else "EMPTY"
    })

@app.get(f"/{SECRET_KEY}.m3u8")
@app.get(f"/{SECRET_KEY}")
def get_main_playlist(request: Request):
    if not cached_channels:
        update_channels_list()
    
    worker_domain = f"{request.url.scheme}://{request.url.netloc}"
    updated_lines = ["#EXTM3U"]
    
    for idx, ch in enumerate(cached_channels):
        clean_link = f"{worker_domain}/ch{idx}/stream.m3u8?key={SECRET_KEY}"
        updated_lines.append(f"#EXTINF:-1 group-title=\"{ch['group_title']}\",{ch['name']}")
        updated_lines.append(clean_link)
        
    return Response("\n".join(updated_lines), media_type="audio/x-mpegurl; charset=utf-8")

@app.get("/ch{idx}/{stream_type}")
def handle_stream(idx: int, stream_type: str, request: Request, key: str = ""):
    if key != SECRET_KEY and stream_type != "stream.m3u8":
        return RedirectResponse(STUB_VIDEO_URL, status_code=302)
        
    if not cached_channels or idx >= len(cached_channels):
        update_channels_list()
        
    if idx < 0 or idx >= len(cached_channels):
        return RedirectResponse(STUB_VIDEO_URL, status_code=302)
        
    target = cached_channels[idx]
    target_stream_url = ""
    
    try:
        session = get_valid_session()
        link_url = f"{PORTAL_URL}?type=itv&action=create_link&cmd={requests.utils.quote(target['cmd'])}&JsHttpRequest=1-xml&token={session['token']}"
        link_res = requests.get(link_url, headers=session['headers'], timeout=10)
        link_text = link_res.text
        
        if "Authorization" in link_text or "error" in link_text or link_text.strip().startswith("<"):
            global cached_token, cached_headers
            cached_token = ""
            cached_headers = None
            session = get_valid_session()
            link_url = f"{PORTAL_URL}?type=itv&action=create_link&cmd={requests.utils.quote(target['cmd'])}&JsHttpRequest=1-xml&token={session['token']}"
            link_res = requests.get(link_url, headers=session['headers'], timeout=10)
            link_text = link_res.text
            
        link_data = link_res.json()
        js_obj = link_data.get("js", {})
        stream_cmd = js_obj.get("cmd") or js_obj.get("url") or link_data.get("cmd") or ""
        
        import re
        stream_cmd = re.sub(r"^(ffmpeg|ch:ffrt|ffrt2|ffrt|ch:)\s*", "", stream_cmd).strip()
        
        if stream_cmd.startswith("http://") or stream_cmd.startswith("https://"):
            target_stream_url = stream_cmd
        elif stream_cmd.startswith("/"):
            portal_obj = requests.utils.urlparse(PORTAL_URL)
            target_stream_url = f"{portal_obj.scheme}://{portal_obj.netloc}{stream_cmd}"
    except Exception:
        pass
        
    if not target_stream_url:
        return RedirectResponse(STUB_VIDEO_URL, status_code=302)
        
    if stream_type == "stream.m3u8":
        return RedirectResponse(target_stream_url, status_code=302)
        
    return RedirectResponse(target_stream_url, status_code=302)
