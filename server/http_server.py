# server/http_server.py — Wi-Fi CSI 3D Radar
# Pipeline verilerini (konumlar, metrikler) web tarayıcısına SSE ile aktarır.
# Ayrıca web/ klasörünü statik dosya olarak serve eder.
#
# Kullanım (main.py tarafından başlatılır):
#   sunucu = CSISunucu(port=8765)
#   sunucu.baslat()   # arka plan thread — bloklamaz
#   sunucu.guncelle(nesneler, music_konumlar, cnn_konumlar, hareket_skoru, frame)
#   sunucu.durdur()

from __future__ import annotations

import json
import math
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.nesne import Nesne

# ── Paylaşımlı durum ─────────────────────────────────────────────────────────
_lock        = threading.Lock()
_son_payload: dict | None = None
_istemciler: list = []          # (response, condition) çiftleri


# ── Yardımcı: payload oluştur ─────────────────────────────────────────────────
def _nesne_listesi(nesneler: list) -> list[dict]:
    sonuc = []
    for n in nesneler:
        pos = n.konum()
        sonuc.append({
            "x": round(pos[0], 3),
            "y": round(pos[1], 3),
            "z": round(pos[2], 3),
            "ad": n.ad,
            "renk": n.renk,
            "hareketli": n.hareketli,
        })
    return sonuc


def _konum_listesi(konumlar: list) -> list[dict]:
    """MUSIC / CNN çıktısı: [(x, y, z, guc), ...]"""
    return [
        {"x": round(k[0], 3), "y": round(k[1], 3), "z": round(k[2], 3), "guc": round(k[3], 3)}
        for k in konumlar
    ]


# ── HTTP Handler ──────────────────────────────────────────────────────────────
class _Handler(BaseHTTPRequestHandler):
    """
    GET /          → web/index.html yönlendirme
    GET /web/*     → statik dosyalar
    GET /stream    → SSE veri akışı
    """

    _web_kok = os.path.join(os.path.dirname(__file__), "..", "web")

    def log_message(self, fmt, *args):
        pass   # konsol kirliliğini önler

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/") or "/"

        # Kök → index.html
        if path == "/":
            self.send_response(301)
            self.send_header("Location", "/web/index.html")
            self.end_headers()
            return

        # SSE stream
        if path == "/stream":
            self._sse_baslat()
            return

        # Statik web dosyaları
        if path.startswith("/web/"):
            dosya_adi = path[len("/web/"):]
            dosya_yol = os.path.normpath(os.path.join(self._web_kok, dosya_adi))
            # Path traversal koruması
            if not dosya_yol.startswith(os.path.normpath(self._web_kok)):
                self._404()
                return
            self._statik_sun(dosya_yol)
            return

        self._404()

    # ── SSE ──────────────────────────────────────────────────────────────────
    def _sse_baslat(self):
        global _son_payload, _istemciler

        self.send_response(200)
        self.send_header("Content-Type",  "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection",    "keep-alive")
        self.end_headers()

        kosul = threading.Condition(_lock)
        with _lock:
            _istemciler.append(kosul)

        try:
            while True:
                with kosul:
                    kosul.wait(timeout=2.0)   # en fazla 2s bekle (heartbeat)
                    payload = _son_payload

                if payload is None:
                    # heartbeat
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue

                mesaj = f"data: {json.dumps(payload)}\n\n".encode("utf-8")
                self.wfile.write(mesaj)
                self.wfile.flush()
        except Exception:
            pass
        finally:
            with _lock:
                try:
                    _istemciler.remove(kosul)
                except ValueError:
                    pass

    # ── Statik dosya ─────────────────────────────────────────────────────────
    def _statik_sun(self, yol: str):
        if not os.path.isfile(yol):
            self._404()
            return

        ext = os.path.splitext(yol)[1].lower()
        mime = {
            ".html": "text/html; charset=utf-8",
            ".js":   "application/javascript",
            ".css":  "text/css",
            ".json": "application/json",
            ".ico":  "image/x-icon",
        }.get(ext, "application/octet-stream")

        with open(yol, "rb") as f:
            icerik = f.read()

        self.send_response(200)
        self.send_header("Content-Type",   mime)
        self.send_header("Content-Length", str(len(icerik)))
        self.end_headers()
        self.wfile.write(icerik)

    def _404(self):
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"404 Not Found")


# ── CSISunucu ─────────────────────────────────────────────────────────────────
class CSISunucu:
    """
    Ana döngü tarafından kullanılan HTTP/SSE sunucu.

    Örnek:
        sunucu = CSISunucu(port=8765)
        sunucu.baslat()
        # döngüde:
        sunucu.guncelle(nesneler, music_k, cnn_k, hareket_sk, frame)
    """

    def __init__(self, port: int = 8765):
        self.port   = port
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None   = None

    def baslat(self):
        """Sunucuyu arka plan thread'de başlat."""
        self._httpd = ThreadingHTTPServer(("", self.port), _Handler)
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, daemon=True
        )
        self._thread.start()
        print(f"[Web]  http://localhost:{self.port}  — tarayıcıda aç")

    def guncelle(
        self,
        nesneler:      list,
        music_konumlar: list | None = None,
        cnn_konumlar:   list | None = None,
        hareket_skoru:  float = 0.0,
        frame:          int   = 0,
    ):
        """
        Pipeline her frame'de bu metodu çağırır.
        Payload SSE üzerinden tüm bağlı istemcilere yayınlanır.
        """
        global _son_payload

        payload = {
            "frame":         frame,
            "nesneler":      _nesne_listesi(nesneler),
            "music":         _konum_listesi(music_konumlar or []),
            "cnn":           _konum_listesi(cnn_konumlar   or []),
            "hareket_skoru": round(hareket_skoru, 4),
            "zaman_ms":      int(time.time() * 1000),
        }

        with _lock:
            _son_payload = payload
            for kosul in _istemciler:
                with kosul:
                    kosul.notify_all()

    def durdur(self):
        if self._httpd:
            self._httpd.shutdown()
