# core/music.py — MUSIC (Multiple Signal Classification) algoritması

import numpy as np
from config import WiFiConfig, OdaConfig

class MUSICTahminci:
    """
    MUSIC algoritması ile CSI'dan nesne açısı ve menzilini tahmin eder.

    Notebook Gün 18'deki MUSIC beamforming'i tam implementasyon.
    Gerçek ESP32 verisi gelince bu sınıf doğrudan kullanılacak.
    """

    def __init__(self, n_kaynak=5):
        self.n_anten = WiFiConfig.ANTEN_SAYISI
        self.n_subcarrier = WiFiConfig.SUBCARRIER_SAYISI
        self.n_kaynak = n_kaynak  # Odadaki tahmin edilen nesne sayısı
        self.dalga_boyu = WiFiConfig.ISIK_HIZI / WiFiConfig.MERKEZ_FREKANS
        self.anten_araligi = self.dalga_boyu / 2  # λ/2 anten dizisi

        # Tarama açıları (-90° ile +90° arası)
        self.acilar = np.linspace(-np.pi/2, np.pi/2, 360)
        # Tarama mesafeleri
        self.mesafeler = np.linspace(0.5, max(OdaConfig.GENISLIK, OdaConfig.DERINLIK), 100)

    def _yon_vektoru(self, aci):
        """Belirli bir açı için anten dizi yön vektörü"""
        d = self.anten_araligi
        n = np.arange(self.n_anten)
        return np.exp(-1j * 2 * np.pi * d * np.sin(aci) * n / self.dalga_boyu)

    def _kovaryans_matrisi(self, H):
        """CSI matrisinden uzamsal kovaryans matrisi hesapla"""
        # H: (n_anten, n_subcarrier)
        # Her subcarrier'dan kovaryans al ve ortala
        R = np.zeros((self.n_anten, self.n_anten), dtype=complex)
        for k in range(self.n_subcarrier):
            h = H[:, k:k+1]
            R += h @ h.conj().T
        return R / self.n_subcarrier

    def _music_spektrumu(self, R):
        """MUSIC pseudo-spektrumu hesapla"""
        # Özdeğer ayrışımı
        eigenvalues, eigenvectors = np.linalg.eigh(R)

        # Gürültü alt uzayı — en küçük (n_anten - n_kaynak) özvektör
        n_gurultu = self.n_anten - min(self.n_kaynak, self.n_anten - 1)
        En = eigenvectors[:, :n_gurultu]  # Gürültü alt uzayı

        # Her açı için MUSIC skoru
        spektrum = np.zeros(len(self.acilar))
        for i, aci in enumerate(self.acilar):
            a = self._yon_vektoru(aci)
            En_proj = En.conj().T @ a
            deger = np.real(a.conj() @ a) / (np.real(En_proj.conj() @ En_proj) + 1e-10)
            spektrum[i] = deger

        return spektrum

    def tahmin_et(self, H):
        """
        CSI matrisinden nesne konumlarını tahmin et.

        Döner: list of (x, y, z) tahmin konumları
        """
        R = self._kovaryans_matrisi(H)
        spektrum = self._music_spektrumu(R)

        # Tepe noktalarını bul
        tepe_idxler = self._tepe_bul(spektrum, n_tepe=self.n_kaynak)

        konumlar = []
        for idx in tepe_idxler:
            aci = self.acilar[idx]
            guc = spektrum[idx]

            # Açıdan menzil tahmini — subcarrier faz farkı kullan
            faz_egimi = np.unwrap(np.angle(H[0]))
            faz_fark = np.diff(faz_egimi)
            ort_faz_fark = np.abs(np.mean(faz_fark))
            mesafe = (ort_faz_fark * WiFiConfig.ISIK_HIZI /
                     (2 * np.pi * WiFiConfig.SUBCARRIER_ARALIK))
            mesafe = np.clip(mesafe * 3.0, 0.5, OdaConfig.GENISLIK - 0.5)

            # Polar → Kartezyen
            x = mesafe * np.cos(aci) + OdaConfig.GENISLIK / 2
            y = mesafe * np.sin(aci) + OdaConfig.DERINLIK / 2
            z = 1.0  # Sabit yükseklik (3D anten dizisi olmadan)

            x = np.clip(x, 0.3, OdaConfig.GENISLIK - 0.3)
            y = np.clip(y, 0.3, OdaConfig.DERINLIK - 0.3)

            konumlar.append((float(x), float(y), float(z), float(guc)))

        return konumlar

    def _tepe_bul(self, spektrum, n_tepe=5):
        """Spektrumdaki en yüksek n_tepe noktasını bul"""
        # Minimum mesafe aralığı — birbirine çok yakın tepeleri ele
        min_aralik = 15
        tepeler = []
        kopyalanan = spektrum.copy()

        for _ in range(n_tepe):
            idx = np.argmax(kopyalanan)
            tepeler.append(idx)
            # Etrafını sıfırla
            baslangic = max(0, idx - min_aralik)
            bitis = min(len(kopyalanan), idx + min_aralik)
            kopyalanan[baslangic:bitis] = 0

        return tepeler
