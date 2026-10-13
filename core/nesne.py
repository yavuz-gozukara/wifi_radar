# core/nesne.py — Nesne sınıfı

import numpy as np
from config import OdaConfig, SimulasyonConfig

class Nesne:
    def __init__(self, x, y, z, renk, isim, hiz_carpani=1.0):
        self.pos = np.array([x, y, z], dtype=float)
        self.renk = np.array(renk, dtype=float)
        self.isim = isim
        self.hiz_carpani = hiz_carpani
        self.hiz = np.array([
            np.random.uniform(-0.04, 0.04) * hiz_carpani,
            np.random.uniform(-0.04, 0.04) * hiz_carpani,
            0.0
        ])
        self.iz = []
        self.aktif = True   # Hareket ediyor mu

    def hareket_et(self):
        if not self.aktif:
            return

        # Hafif rastgele sapma — doğal hareket
        self.hiz[0] += np.random.uniform(-0.002, 0.002)
        self.hiz[1] += np.random.uniform(-0.002, 0.002)

        # Hız sınırı
        maks_hiz = 0.06 * self.hiz_carpani
        self.hiz = np.clip(self.hiz, -maks_hiz, maks_hiz)

        self.pos += self.hiz

        # Duvar yansıması
        if self.pos[0] < 0.4 or self.pos[0] > OdaConfig.GENISLIK - 0.4:
            self.hiz[0] *= -1
        if self.pos[1] < 0.4 or self.pos[1] > OdaConfig.DERINLIK - 0.4:
            self.hiz[1] *= -1

        self.pos = np.clip(
            self.pos,
            [0.4, 0.4, 0.1],
            [OdaConfig.GENISLIK - 0.4, OdaConfig.DERINLIK - 0.4, OdaConfig.YUKSEKLIK - 0.1]
        )

        self.iz.append(self.pos.copy())
        if len(self.iz) > SimulasyonConfig.IZ_UZUNLUGU:
            self.iz.pop(0)

    def konum(self):
        return self.pos.copy()

    def durdur(self):
        self.aktif = False
        self.hiz = np.zeros(3)

    def baslat(self):
        self.aktif = True
        self.hiz = np.array([
            np.random.uniform(-0.04, 0.04) * self.hiz_carpani,
            np.random.uniform(-0.04, 0.04) * self.hiz_carpani,
            0.0
        ])
