# main.py — Wi-Fi CSI 3D Radar Ana Döngü
# Tüm modülleri bir araya getirir: CSI → Arka Plan → MUSIC → Görselleştirme

import sys
import time
import numpy as np

from config import OdaConfig, SimulasyonConfig

from core.nesne import Nesne
from core.csi import CSIHesaplayici
from core.arka_plan import ArkaplanCikarici
from core.music import MUSICTahminci

from visualization.oda import OdaGorunumu
from visualization.radar3d import Radar3D
from visualization.hud import HUD


def nesneleri_olustur():
    """Simülasyon nesnelerini oluşturur — gerçek ESP32 verisi gelince bu kısım kaldırılır."""
    return [
        Nesne(1.0, 1.0, 1.0, [1.0, 0.2, 0.2], "Öğrenci-1", hiz_carpani=1.0),
        Nesne(5.0, 1.0, 1.0, [0.2, 0.5, 1.0], "Öğrenci-2", hiz_carpani=0.8),
        Nesne(1.0, 4.0, 1.0, [0.2, 1.0, 0.4], "Öğrenci-3", hiz_carpani=1.2),
        Nesne(5.0, 4.0, 1.0, [1.0, 0.9, 0.1], "Öğrenci-4", hiz_carpani=0.9),
        Nesne(3.0, 2.5, 0.5, [0.8, 0.4, 0.1], "Masa",       hiz_carpani=0.0),
    ]


def main():
    print("=" * 60)
    print("  Wi-Fi CSI 3D Radar — Başlatılıyor")
    print("=" * 60)

    # Modül başlatma
    nesneler    = nesneleri_olustur()
    csi         = CSIHesaplayici()
    arka_plan   = ArkaplanCikarici()
    music       = MUSICTahminci(n_kaynak=len(nesneler))
    oda         = OdaGorunumu()
    radar       = Radar3D(oda.geometri())
    hud         = HUD()

    # Masa başlangıçta durağan
    nesneler[-1].durdur()

    # MUSIC kaç frame'de bir çalışsın (hesaplamalı yük — her 5 frame'de bir)
    MUSIC_ARALIK = 5
    frame_sayac  = 0
    music_sonuc  = []

    print("\n[Radar] Simülasyon başlatıldı. Kapatmak için Open3D penceresini kapatın.\n")

    try:
        while True:
            frame_sayac += 1

            # 1) Nesneleri hareket ettir
            for nesne in nesneler:
                nesne.hareket_et()

            # 2) CSI hesapla
            H = csi.hesapla(nesneler)

            # 3) Arka plan çıkarma — hareket skoru
            hareket_sk = arka_plan.hareket_skoru(H)

            # 4) MUSIC tahmini — her MUSIC_ARALIK frame'de
            if frame_sayac % MUSIC_ARALIK == 0:
                try:
                    music_sonuc = music.tahmin_et(H)
                except Exception:
                    music_sonuc = []

            # 5) Görselleştirme güncelle
            radar.guncelle(nesneler)

            # 6) HUD güncelle
            hud.guncelle(nesneler, hareket_skoru=hareket_sk, music_konumlar=music_sonuc)

            # 7) Open3D event loop — pencere kapatılırsa False döner
            if not radar.calis():
                break

            # FPS sınırlama
            time.sleep(max(0, 1.0 / SimulasyonConfig.FPS_HEDEF - 0.005))

    except KeyboardInterrupt:
        print("\n\n[Radar] Kullanıcı tarafından durduruldu (Ctrl+C).")

    finally:
        radar.kapat()
        hud.kapat()
        print("[Radar] Sistem kapatıldı.")


if __name__ == "__main__":
    main()
