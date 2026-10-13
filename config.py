# config.py — Tüm sistem parametreleri

class OdaConfig:
    GENISLIK = 6.0      # X ekseni (metre)
    DERINLIK = 5.0      # Y ekseni (metre)
    YUKSEKLIK = 3.0     # Z ekseni (metre)

class WiFiConfig:
    MERKEZ_FREKANS = 2.4e9
    BANT_GENISLIGI = 20e6
    SUBCARRIER_SAYISI = 64
    ANTEN_SAYISI = 3
    ISIK_HIZI = 3e8
    SUBCARRIER_ARALIK = BANT_GENISLIGI / SUBCARRIER_SAYISI  # 312500 Hz

    ROUTER_KONUM = [0.0, 0.0, 2.5]
    ANTEN_KONUMLAR = [
        [OdaConfig.GENISLIK, 0.0, 2.5],
        [OdaConfig.GENISLIK, OdaConfig.DERINLIK / 2, 2.5],
        [OdaConfig.GENISLIK, OdaConfig.DERINLIK, 2.5],
    ]

class SimulasyonConfig:
    FPS_HEDEF = 30
    IZ_UZUNLUGU = 80
    GURULTU_CARPANI = 0.01
    EMA_ALFA = 0.01

class GoruntuConfig:
    PENCERE_GENISLIK = 1280
    PENCERE_YUKSEKLIK = 720
    ARKA_PLAN = [0.02, 0.02, 0.05]
    NOKTA_BOYUTU = 4.0
    NOKTA_YOGUNLUGU = 60
