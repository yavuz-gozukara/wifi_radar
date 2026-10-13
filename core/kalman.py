# core/kalman.py — Kalman Filtresi ile Nesne İzleme

import numpy as np

class KalmanIzleyici:
    """
    Tek nesne için 3B Kalman filtresi.
    Durum vektörü: [x, y, z, vx, vy, vz]  (6 boyutlu)
    Ölçüm: [x, y, z]  (3 boyutlu — MUSIC çıktısı)
    """

    def __init__(self, x0, y0, z0, dt=1.0/30.0):
        self.dt = dt

        # Durum vektörü — başlangıç konumu, sıfır hız
        self.x = np.array([x0, y0, z0, 0.0, 0.0, 0.0], dtype=float)

        # Durum geçiş matrisi F (sabit hız modeli)
        self.F = np.eye(6)
        self.F[0, 3] = dt
        self.F[1, 4] = dt
        self.F[2, 5] = dt

        # Ölçüm matrisi H (sadece konum gözlemlenir)
        self.H = np.zeros((3, 6))
        self.H[0, 0] = 1.0
        self.H[1, 1] = 1.0
        self.H[2, 2] = 1.0

        # Süreç gürültüsü kovaryansı Q
        q = 0.001
        self.Q = np.eye(6) * q
        self.Q[3:, 3:] *= 10  # Hız bileşenleri daha gürültülü

        # Ölçüm gürültüsü kovaryansı R
        self.R = np.eye(3) * 0.05

        # Hata kovaryans matrisi P
        self.P = np.eye(6) * 1.0

        # İz geçmişi
        self.iz = []
        self.iz_max = 40
        self._guncelleme_sayac = 0
        self.aktif = True
        self._kayip_sayac = 0  # Kaç frame ölçüm yok

    def tahmin_et(self):
        """Kalman tahmin adımı — her frame çağrılır"""
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x[:3].copy()

    def guncelle(self, olcum):
        """
        Kalman güncelleme adımı.
        olcum: [x, y, z] — MUSIC çıktısı
        """
        z = np.array(olcum[:3], dtype=float)
        y = z - self.H @ self.x                          # Yenilik
        S = self.H @ self.P @ self.H.T + self.R         # Yenilik kovaryansı
        K = self.P @ self.H.T @ np.linalg.inv(S)        # Kalman kazancı
        self.x = self.x + K @ y
        self.P = (np.eye(6) - K @ self.H) @ self.P

        self._guncelleme_sayac += 1
        self._kayip_sayac = 0

        # İz güncelle
        self.iz.append(self.x[:3].copy())
        if len(self.iz) > self.iz_max:
            self.iz.pop(0)

    def kayip_bildir(self):
        """Ölçüm gelmediğinde çağrılır — sadece tahmin adımı ilerler"""
        self._kayip_sayac += 1
        if self._kayip_sayac > 30:  # 30 frame ölçüm gelmezse pasif
            self.aktif = False

    def konum(self):
        return self.x[:3].copy()

    def hiz(self):
        return self.x[3:].copy()


class CokluIzleyici:
    """
    MUSIC çıktısından gelen birden fazla noktayı izler.
    Yeni noktalar mevcut izleyicilere en yakın eşleştirme ile atanır.
    """

    def __init__(self, maks_izleyici=8, dt=1.0/30.0):
        self.izleyiciler = []
        self.maks_izleyici = maks_izleyici
        self.dt = dt
        self._eslestirme_esigi = 1.5  # metre — bu mesafenin üstü yeni nesne

    def guncelle(self, music_konumlar):
        """
        music_konumlar: list of (x, y, z, guc) — MUSICTahminci.tahmin_et() çıktısı
        Döner: list of KalmanIzleyici
        """
        # Önce tüm izleyicileri tahmin adımı ile ilerlet
        for iz in self.izleyiciler:
            iz.tahmin_et()

        if not music_konumlar:
            for iz in self.izleyiciler:
                iz.kayip_bildir()
        else:
            atanmis = set()
            for (mx, my, mz, guc) in music_konumlar:
                nokta = np.array([mx, my, mz])
                en_yakin_iz = None
                en_kisa_mesafe = self._eslestirme_esigi

                for i, iz in enumerate(self.izleyiciler):
                    if i in atanmis or not iz.aktif:
                        continue
                    mesafe = np.linalg.norm(nokta - iz.konum())
                    if mesafe < en_kisa_mesafe:
                        en_kisa_mesafe = mesafe
                        en_yakin_iz = i

                if en_yakin_iz is not None:
                    self.izleyiciler[en_yakin_iz].guncelle([mx, my, mz])
                    atanmis.add(en_yakin_iz)
                else:
                    # Yeni nesne — yeni izleyici aç
                    if len(self.izleyiciler) < self.maks_izleyici:
                        yeni = KalmanIzleyici(mx, my, mz, dt=self.dt)
                        yeni.guncelle([mx, my, mz])
                        self.izleyiciler.append(yeni)

            # Ölçüm almayan izleyicilere kayıp bildir
            for i, iz in enumerate(self.izleyiciler):
                if i not in atanmis:
                    iz.kayip_bildir()

        # Pasif izleyicileri listeden çıkar
        self.izleyiciler = [iz for iz in self.izleyiciler if iz.aktif]
        return self.izleyiciler

    def aktif_konumlar(self):
        """Aktif izleyicilerin filtreli konumlarını döner"""
        return [iz.konum() for iz in self.izleyiciler if iz.aktif]
