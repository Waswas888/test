import requests
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse

# Точный адрес вашего рабочего Hugging Face Space
HF_SPACE_URL = "https://stream-tv-digital.hf.space"

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def admin_panel():
    return f"""
    <!DOCTYPE html>
    <html lang="uz">
    <head>
        <meta charset="UTF-8">
        <title>IPTV Proxy Panel</title>
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
            <h2>🚀 IPTV Vercel Proxy</h2>
            <p>Holati: <span class="badge">Ishlayapti ✅</span></p>
            <p>Bازг соҳил (Hugging Face Space) орқали уланди.</p>
            <hr style="border: 0.5px solid #334155; margin: 20px 0;">
            <a href="/pl.m3u8" target="_blank">📥 M3U Playlist (/pl.m3u8)</a>
            <a href="{HF_SPACE_URL}/playlist.json" target="_blank" style="color: #94a3b8; font-size: 14px;">📄 JSON ni ko'rish</a>
        </div>
    </body>
    </html>
    """

@app.get("/pl.m3u8", response_class=PlainTextResponse)
def get_m3u8():
    """Мгновенно забираем готовый плейлист с Hugging Face Space"""
    try:
        res = requests.get(f"{HF_SPACE_URL}/pl.m3u8", timeout=10)
        return res.text
    except Exception as e:
        return f"#EXTM3U\n# Xatolik: HF Space bilan bog'lanib bo'lmadi ({str(e)})"

@app.get("/proxy")
def proxy_channel(cmd: str):
    """Перенаправляем запрос потока на Hugging Face Space"""
    return RedirectResponse(url=f"{HF_SPACE_URL}/proxy?cmd={requests.utils.quote(cmd)}", status_code=302)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(content=b"", media_type="image/vnd.microsoft.icon")
