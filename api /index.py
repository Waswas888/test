from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI()

@app.get("/")
def root():
    return PlainTextResponse("OK! FastAPI ishlamoqda!")

@app.get("/pl.m3u8")
def playlist():
    return PlainTextResponse("#EXTM3U\n# Test ishlayapti")
