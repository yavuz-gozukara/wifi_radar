# visualization/hud.py — Terminal tabanlı HUD (Heads-Up Display)
# Open3D penceresi üzerinde metin overlay desteklemediğinden
# terminal çıktısı olarak detaylı sistem durumu gösterilir.

import time
import numpy as np
from config import WiFiConfig, OdaConfig

class HUD:
    """
    Sistem durumunu terminal'de gerçek zamanlı gösterir.
    Open3D'nin metin overlay kısıtlaması nedeniyle terminal tabanlıdır.
    """

    def __init__(self):
        self._baslangic = time.time()
        self._frame = 0
        self._fps = 0.0
        self._fps_t0 = time.time()
        self._fps_pencere = 30   # Her 30 frame'de bir FPS hesapla
        self._son_gosterim = 0.0
        self._gosterim_aralik = 1.0  # Saniyede bir tam tablo göster

        # Sistem genişliği
        self._w = 60

    def guncelle(self, nesneler, hareket_skoru=0.0, music_konumlar=None):
        """
        Her frame çağrılır. FPS hesaplar, periyodik olarak terminal'i günceller.
        """
        self._frame += 1

        # FPS hesapla
        if self._frame % self._fps_pencere == 0:
            gecen = time.time() - self._fps_t0
            self._fps = self._fps_pencere / max(gecen, 1e-6)
            self._fps_t0 = time.time()

        # Hızlı satır — her frame
        aktif_n = sum(1 for n in nesneler if n.aktif)
        print(f"\r  FPS: {self._fps:5.1f} | Nesne: {len(nesneler)} aktif({aktif_n}) "
              f"| Hareket: {hareket_skoru:.4f} | Frame: {self._frame:6d}  ", end="", flush=True)

        # Tam tablo — saniyede bir
        su_an = time.time()
        if su_an - self._son_gosterim >= self._gosterim_aralik:
            self._son_gosterim = su_an
            self._tam_tablo_yaz(nesneler, hareket_skoru, music_konumlar)

    def _tam_tablo_yaz(self, nesneler, hareket_skoru, music_konumlar):
        """Detaylı sistem tablosu yazar — her saniye bir kez"""
        cizgi = "─" * self._w
        calisma_suresi = time.time() - self._baslangic
        saat = int(calisma_suresi // 3600)
        dakika = int((calisma_suresi % 3600) // 60)
        saniye = int(calisma_suresi % 60)

        satirlar = [
            "\n",
            f"┌{cizgi}┐",
            f"│  {'Wi-Fi CSI 3D RADAR — SİSTEM DURUMU':^{self._w-2}}  │",
            f"├{cizgi}┤",
            f"│  Çalışma Süresi : {saat:02d}:{dakika:02d}:{saniye:02d}{'':>33}│",
            f"│  FPS            : {self._fps:.1f}{'':>43}│",
            f"│  Toplam Frame   : {self._frame}{'':>42}│",
            f"│  Hareket Skoru  : {hareket_skoru:.6f}{'':>35}│",
            f"├{cizgi}┤",
            f"│  {'NESNE KONUMLARI':^{self._w-2}}  │",
        ]

        for nesne in nesneler:
            p = nesne.pos
            durum = "AKTIF" if nesne.aktif else "DUR  "
            satir = f"│  [{durum}] {nesne.isim:<12} X:{p[0]:5.2f} Y:{p[1]:5.2f} Z:{p[2]:4.2f}  │"
            satirlar.append(satir)

        if music_konumlar:
            satirlar.append(f"├{cizgi}┤")
            satirlar.append(f"│  {'MUSIC TAHMİN KONUMLARI':^{self._w-2}}  │")
            for i, (mx, my, mz, guc) in enumerate(music_konumlar[:3]):
                satir = f"│  Kaynak {i+1}: X:{mx:5.2f} Y:{my:5.2f} Z:{mz:4.2f}  Güç:{guc:.1f}  │"
                satirlar.append(satir)

        satirlar.append(f"├{cizgi}┤")
        satirlar.append(f"│  {'SİSTEM BİLGİSİ':^{self._w-2}}  │")
        satirlar.append(f"│  Oda         : {OdaConfig.GENISLIK}m x {OdaConfig.DERINLIK}m x {OdaConfig.YUKSEKLIK}m{'':>28}│")
        satirlar.append(f"│  Anten Sayısı: {WiFiConfig.ANTEN_SAYISI}{'':>45}│")
        satirlar.append(f"│  Subcarrier  : {WiFiConfig.SUBCARRIER_SAYISI}{'':>45}│")
        satirlar.append(f"│  Frekans     : {WiFiConfig.MERKEZ_FREKANS/1e9:.1f} GHz{'':>42}│")
        satirlar.append(f"└{cizgi}┘")

        print("\n".join(satirlar))

    def kapat(self):
        toplam = time.time() - self._baslangic
        print(f"\n\n[HUD] Oturum sona erdi. Toplam süre: {toplam:.1f}s, {self._frame} frame işlendi.")
