# main.py — Giriş noktası

from core.nesne import Nesne
from core.csi import CSIHesaplayici
from visualization.oda import OdaGorunumu
from visualization.radar3d import Radar3D

def nesneleri_olustur():
    return [
        Nesne(1.5, 1.5, 1.0, [1.0, 0.2, 0.2], "Öğrenci 1"),
        Nesne(4.0, 1.5, 1.0, [0.2, 0.5, 1.0], "Öğrenci 2"),
        Nesne(2.5, 3.5, 1.0, [0.2, 1.0, 0.4], "Öğrenci 3"),
        Nesne(4.5, 3.5, 1.0, [1.0, 0.8, 0.1], "Öğrenci 4"),
        Nesne(3.0, 2.5, 0.8, [0.7, 0.4, 0.2], "Masa"),
    ]

def main():
    print("Wi-Fi CSI 3D Radar başlıyor...")
    print("Fareyle döndür | Scroll zoom | Q çık")

    nesneler = nesneleri_olustur()
    csi = CSIHesaplayici()
    oda = OdaGorunumu()
    radar = Radar3D(oda.geometri())

    while True:
        for nesne in nesneler:
            nesne.hareket_et()

        H = csi.hesapla(nesneler)
        radar.guncelle(nesneler)

        if not radar.calis():
            break

    radar.kapat()

if __name__ == "__main__":
    main()
