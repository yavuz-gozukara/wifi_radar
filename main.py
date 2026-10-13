# main.py — Wi-Fi CSI 3D Radar Ana Döngü
# Pipeline: CSI → EMA Arka Plan → MUSIC → CNN → Kalman → Open3D + Web + HUD
#
# ESP32 bağlantı değiştirme rehberi:
#   Simülasyon → ESP32 Serial:  kaynak = ESP32SerialArayuz(port="COM3")
#   Simülasyon → ESP32 UDP:     kaynak = ESP32UDPArayuz(port=5005)
#
# Web arayüzü: http://localhost:8765  (otomatik açılır)
# CNN eğitimi: python -m core.cnn_tahminci --egit

import time

from config import SimulasyonConfig

from core.nesne        import Nesne
from core.csi          import CSIHesaplayici
from core.arka_plan    import ArkaplanCikarici
from core.music        import MUSICTahminci
from core.kalman       import CokluIzleyici
from core.cnn_tahminci import CNNTahminci
from core.esp32_arayuz import SimulasyonArayuz

from visualization.oda     import OdaGorunumu
from visualization.radar3d import Radar3D
from visualization.hud     import HUD

from server.http_server import CSISunucu


def nesneleri_olustur():
    """Simülasyon nesnelerini oluşturur — gerçek ESP32 verisi gelince kullanılmaz."""
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

    # ── Simülasyon nesneleri ──────────────────────────────────────
    nesneler = nesneleri_olustur()
    nesneler[-1].durdur()   # Masa durağan

    # ── Veri kaynağı ─────────────────────────────────────────────
    # Simülasyon modu — ESP32 gelince bu satırı değiştir:
    csi    = CSIHesaplayici()
    kaynak = SimulasyonArayuz(csi, nesneler)
    # kaynak = ESP32SerialArayuz(port="COM3", baud=921600)
    # kaynak = ESP32UDPArayuz(port=5005)

    # ── İşleme pipeline ──────────────────────────────────────────
    arka_plan = ArkaplanCikarici()
    music     = MUSICTahminci(n_kaynak=len(nesneler))
    izleyici  = CokluIzleyici(maks_izleyici=8)
    cnn       = CNNTahminci()               # model varsa yükler, yoksa sessiz devam

    # ── Görselleştirme (Open3D) ───────────────────────────────────
    oda   = OdaGorunumu()
    radar = Radar3D(oda.geometri())
    hud   = HUD()

    # ── Web Sunucu (SSE) ──────────────────────────────────────────
    sunucu = CSISunucu(port=8765)
    sunucu.baslat()   # arka plan thread, bloklamaz

    # ── Döngü parametreleri ───────────────────────────────────────
    MUSIC_ARALIK = 5    # Her N frame'de bir MUSIC çalıştır
    CNN_ARALIK   = 3    # Her N frame'de bir CNN çalıştır (daha hızlı)
    WEB_ARALIK   = 2    # Her N frame'de web'e gönder (bant genişliğini azaltır)

    frame        = 0
    music_sonuc  = []
    cnn_sonuc    = []

    print("\n[Radar] Başlatıldı.")
    print("  Open3D penceresi: aktif")
    print("  Web arayüzü:      http://localhost:8765")
    if cnn.hazir:
        print("  CNN modeli:       yüklendi ✓")
    else:
        print("  CNN modeli:       yok (eğitmek için: python -m core.cnn_tahminci --egit)")
    print("\nKapatmak için Open3D penceresini kapatın veya Ctrl+C\n")

    try:
        while True:
            frame += 1

            # 1) Simülasyon: nesneleri hareket ettir
            #    (ESP32 modunda bu adım atlanır — gerçek veri kaynak'tan gelir)
            for nesne in nesneler:
                nesne.hareket_et()

            # 2) Veri kaynağından CSI matrisi al
            H = kaynak.oku()

            # 3) EMA arka plan çıkarma → hareket skoru
            hareket_sk = arka_plan.hareket_skoru(H)

            # 4) MUSIC açı/mesafe tahmini (her MUSIC_ARALIK frame'de)
            if frame % MUSIC_ARALIK == 0:
                try:
                    music_sonuc = music.tahmin_et(H)
                except Exception:
                    music_sonuc = []

            # 5) CNN konum tahmini (her CNN_ARALIK frame'de)
            if frame % CNN_ARALIK == 0 and cnn.hazir:
                try:
                    cnn_sonuc = cnn.tahmin_et(H)
                except Exception:
                    cnn_sonuc = []

            # 6) Kalman filtresi ile izleme (MUSIC çıktısını pürüzsüzleştirir)
            izleyici.guncelle(music_sonuc)

            # 7) Open3D görselleştirme
            radar.guncelle(nesneler)

            # 8) Web arayüzüne gönder (her WEB_ARALIK frame'de)
            if frame % WEB_ARALIK == 0:
                sunucu.guncelle(
                    nesneler       = nesneler,
                    music_konumlar = music_sonuc,
                    cnn_konumlar   = cnn_sonuc,
                    hareket_skoru  = hareket_sk,
                    frame          = frame,
                )

            # 9) Terminal HUD
            hud.guncelle(nesneler, hareket_skoru=hareket_sk, music_konumlar=music_sonuc)

            # 10) Open3D event loop
            if not radar.calis():
                break

            # FPS sınırlama
            time.sleep(max(0, 1.0 / SimulasyonConfig.FPS_HEDEF - 0.005))

    except KeyboardInterrupt:
        print("\n\n[Radar] Kullanıcı tarafından durduruldu (Ctrl+C).")

    finally:
        kaynak.kapat()
        sunucu.durdur()
        radar.kapat()
        hud.kapat()
        print("[Radar] Sistem kapatıldı.")


if __name__ == "__main__":
    main()
