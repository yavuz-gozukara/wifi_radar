# core/csi.py — CSI hesaplama ve sinyal işleme

import numpy as np
from config import WiFiConfig, SimulasyonConfig

class CSIHesaplayici:
    def __init__(self):
        self.router = np.array(WiFiConfig.ROUTER_KONUM)
        self.antenler = np.array(WiFiConfig.ANTEN_KONUMLAR)
        self.frekanslar = (WiFiConfig.MERKEZ_FREKANS +
                           np.arange(WiFiConfig.SUBCARRIER_SAYISI) *
                           WiFiConfig.SUBCARRIER_ARALIK)

    def hesapla(self, nesneler):
        H = np.zeros(
            (WiFiConfig.ANTEN_SAYISI, WiFiConfig.SUBCARRIER_SAYISI),
            dtype=complex
        )

        for ant_idx, ant in enumerate(self.antenler):
            for nesne in nesneler:
                pos = nesne.konum()
                dist1 = np.linalg.norm(pos - self.router)
                dist2 = np.linalg.norm(ant - pos)
                toplam = dist1 + dist2
                genlik = 0.5 / (toplam ** 2 + 1e-6)

                faz = 2 * np.pi * self.frekanslar * toplam / WiFiConfig.ISIK_HIZI
                H[ant_idx] += genlik * np.exp(1j * faz)

            H[ant_idx] += SimulasyonConfig.GURULTU_CARPANI * (
                np.random.randn(WiFiConfig.SUBCARRIER_SAYISI) +
                1j * np.random.randn(WiFiConfig.SUBCARRIER_SAYISI)
            )
        return H

    def range_azimuth(self, H):
        harita = np.abs(np.fft.fft2(H))
        harita = np.fft.fftshift(harita)
        return harita
