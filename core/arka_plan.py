# core/arka_plan.py — EMA arka plan çıkarma

import numpy as np
from config import SimulasyonConfig, WiFiConfig

class ArkaplanCikarici:
    """
    EMA (Exponential Moving Average) ile statik arka planı öğrenir.
    Hareket eden nesneler arka plandan çıkarılarak tespit edilir.
    """

    def __init__(self):
        self.arka_plan = None
        self.alfa = SimulasyonConfig.EMA_ALFA
        self.kalibrasyonda = True
        self.kalibrasyon_sayac = 0
        self.kalibrasyon_hedef = 30  # 30 frame kalibrasyon

    def guncelle(self, H):
        """
        H: (n_anten, n_subcarrier) karmaşık CSI matrisi
        Döner: fark matrisi (hareket = yüksek değer)
        """
        genlik = np.abs(H)

        if self.arka_plan is None:
            self.arka_plan = genlik.copy()
            return np.zeros_like(genlik)

        # Kalibrasyon aşaması — arka planı hızlı öğren
        if self.kalibrasyonda:
            self.arka_plan = 0.7 * self.arka_plan + 0.3 * genlik
            self.kalibrasyon_sayac += 1
            if self.kalibrasyon_sayac >= self.kalibrasyon_hedef:
                self.kalibrasyonda = False
                print("\n[Radar] Kalibrasyon tamamlandı — tarama başlıyor.")
            return np.zeros_like(genlik)

        # Normal çalışma — yavaş EMA güncelleme
        fark = np.abs(genlik - self.arka_plan)
        self.arka_plan = (1 - self.alfa) * self.arka_plan + self.alfa * genlik
        return fark

    def hareket_skoru(self, H):
        """Tek sayısal hareket skoru — ne kadar değişim var?"""
        fark = self.guncelle(H)
        return float(np.mean(fark))

    def sifirla(self):
        self.arka_plan = None
        self.kalibrasyonda = True
        self.kalibrasyon_sayac = 0
        print("[Radar] Arka plan sıfırlandı.")
