# core/nesne.py — Nesne sınıfı

import numpy as np
from config import OdaConfig, SimulasyonConfig

class Nesne:
    def __init__(self, x, y, z, renk, isim):
        self.pos = np.array([x, y, z], dtype=float)
        self.renk = np.array(renk, dtype=float)
        self.isim = isim
        self.hiz = np.array([
            np.random.uniform(-0.03, 0.03),
            np.random.uniform(-0.03, 0.03),
            0.0
        ])
        self.iz = []

    def hareket_et(self):
        self.pos += self.hiz

        if self.pos[0] < 0.3 or self.pos[0] > OdaConfig.GENISLIK - 0.3:
            self.hiz[0] *= -1
        if self.pos[1] < 0.3 or self.pos[1] > OdaConfig.DERINLIK - 0.3:
            self.hiz[1] *= -1

        self.pos = np.clip(
            self.pos,
            [0.3, 0.3, 0.1],
            [OdaConfig.GENISLIK - 0.3, OdaConfig.DERINLIK - 0.3, OdaConfig.YUKSEKLIK - 0.1]
        )

        self.iz.append(self.pos.copy())
        if len(self.iz) > SimulasyonConfig.IZ_UZUNLUGU:
            self.iz.pop(0)

    def konum(self):
        return self.pos.copy()
