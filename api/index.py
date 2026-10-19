import json
import os
import time
import requests
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

PORTAL_URL = "http://178.63.13.164:88/stalker_portal/server/load.php"
MAC_BASE = "00:1A:79:4D:63:44"

app = FastAPI()

@app.get("/pl.m3u8", response_class=PlainTextResponse)
def debug_playlist(request: Request):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Referer": "http://178.63.13.164:88/stalker_portal/c/index.html",
    })
    session.cookies.set("mac", MAC_BASE, domain="178.63.13.164")

    # 1. Handshake
    hs_url = f"{PORTAL_URL}?type=stb&action=handshake&token=&JsHttpRequest=1-xml"
    try:
        hs_resp = session.get(hs_url, timeout=5).json()
        token = hs_resp.get("js", {}).get("token", "")
        if token:
            session.cookies.set("token", token, domain="178.63.13.164")
            session.headers.update({"Authorization": f"Bearer {token}"})
    except Exception as e:
        return f"#EXTM3U\n# Handshake Error: {str(e)}"

    # 2. Попытка запросить каналы и показать чистый ответ сервера
    ch_url = f"{PORTAL_URL}?type=itv&action=get_ordered_list&JsHttpRequest=1-xml"
    try:
        resp = session.get(ch_url, timeout=8)
        # Возвращаем в виде текста первые 500 символов ответа от сервера для анализа
        return f"#EXTM3U\n# DEBUG SERVER RESPONSE:\n# {resp.text[:800]}"
    except Exception as e:
        return f"#EXTM3U\n# Request Error: {str(e)}"
