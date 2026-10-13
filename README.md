# Wi-Fi CSI 3D Radar

Wi-Fi CSI (Channel State Information) sinyalleri kullanarak bir odadaki nesneleri ve hareketleri gerçek zamanlı 3D olarak görselleştiren sistem.

## Proje Yapısı

```
wifi_radar/
├── main.py                  # Giriş noktası
├── config.py                # Tüm sistem parametreleri
├── core/
│   ├── nesne.py             # Nesne sınıfı (konum, hareket, iz)
│   └── csi.py               # CSI hesaplama ve sinyal işleme
├── visualization/
│   ├── oda.py               # 3D oda çerçevesi
│   └── radar3d.py           # Open3D gerçek zamanlı görselleştirme
└── data/                    # Kaydedilen CSI verileri
```

## Kurulum

```bash
pip install numpy scipy matplotlib torch torchvision open3d
```

## Çalıştırma

```bash
python main.py
```

## Aşamalar

- [x] Aşama 1 — Simülasyon: OOP mimarisi, 3D görselleştirme
- [ ] Aşama 2 — Gerçek Donanım: ESP32 + CSI veri akışı
- [ ] Aşama 3 — CNN Modeli: Konum tahmini
- [ ] Aşama 4 — Sunum Sistemi: Gerçek zamanlı demo
