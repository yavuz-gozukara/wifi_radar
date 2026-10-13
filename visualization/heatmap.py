# visualization/heatmap.py — Range-Azimuth Heatmap
#
# CSI matrisinden 2D FFT ile Range-Azimuth yoğunluk haritası üretir.
# matplotlib kullanır — Open3D'den bağımsız olarak ayrı pencerede açılır.
# Gerçek ESP32 verisi gelince bu modül direkt çalışacak.

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from config import WiFiConfig, OdaConfig


class RangeAzimuthHeatmap:
    """
    CSI H matrisinden (n_anten × n_subcarrier) 2D heatmap oluşturur.

    - Sütun FFT: range (mesafe) eksenini verir
    - Satır FFT: azimuth (açı) eksenini verir
    - fftshift ile sıfır-frekans merkeze alınır
    """

    def __init__(self):
        self.n_anten = WiFiConfig.ANTEN_SAYISI
        self.n_sub   = WiFiConfig.SUBCARRIER_SAYISI

        # Mesafe ekseni
        c   = WiFiConfig.ISIK_HIZI
        bw  = WiFiConfig.BANT_GENISLIGI
        df  = WiFiConfig.SUBCARRIER_ARALIK
        maks_mesafe = c / (2 * df)                          # ~480 m teorik
        maks_goster  = max(OdaConfig.GENISLIK, OdaConfig.DERINLIK) + 1.0
        maks_mesafe  = min(maks_mesafe, 20.0)               # Ekran için kırp

        self.mesafe_ekseni = np.linspace(0, maks_mesafe, self.n_sub)
        self.azimuth_ekseni = np.linspace(-90, 90, self.n_anten * 8)  # interpolasyon

        # Matplotlib figür
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.fig.patch.set_facecolor('#050510')
        self.ax.set_facecolor('#050510')

        # Boş heatmap
        self._im_data = np.zeros((self.n_anten * 8, self.n_sub))
        self.im = self.ax.imshow(
            self._im_data,
            aspect='auto',
            origin='lower',
            cmap='hot',
            interpolation='bilinear',
            vmin=0, vmax=1,
            extent=[0, maks_mesafe, -90, 90]
        )

        self.ax.set_xlabel("Mesafe (m)", color='white')
        self.ax.set_ylabel("Azimuth (°)", color='white')
        self.ax.set_title("Range-Azimuth Heatmap (Wi-Fi CSI)", color='cyan', fontsize=13)
        self.ax.tick_params(colors='gray')
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#333')

        cbar = self.fig.colorbar(self.im, ax=self.ax)
        cbar.set_label("Normalize Güç", color='white')
        cbar.ax.yaxis.set_tick_params(color='gray')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='gray')

        plt.tight_layout()

    def _hesapla(self, H):
        """H (n_anten × n_sub) → 2D güç haritası"""
        # Zero-pad azimuth ekseni (daha iyi açı çözünürlüğü)
        n_azimuth_fft = self.n_anten * 8
        H_pad = np.zeros((n_azimuth_fft, self.n_sub), dtype=complex)
        H_pad[:self.n_anten, :] = H

        # 2D FFT
        F = np.fft.fft2(H_pad)
        F = np.fft.fftshift(F, axes=0)   # Azimuth sıfır merkeze

        # Güç ve normalize
        guc = np.abs(F) ** 2
        if guc.max() > 0:
            guc = guc / guc.max()

        # Sadece yarı mesafe (gerçek alan)
        guc = guc[:, :self.n_sub // 2]
        return guc

    def guncelle(self, H):
        """Heatmap'i yeni CSI ile güncelle"""
        guc = self._hesapla(H)
        # Görüntü boyutuna uyacak şekilde sütun sayısını eşleştir
        w = min(guc.shape[1], self._im_data.shape[1])
        self._im_data[:, :w] = guc[:, :w]
        self.im.set_data(self._im_data)
        self.im.set_clim(0, max(self._im_data.max(), 1e-6))

    def goster(self):
        """Non-blocking draw"""
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()

    def kapat(self):
        plt.close(self.fig)


def heatmap_demosu(csi_hesaplayici, nesneler, n_frame=200):
    """
    Bağımsız demo: heatmap animasyonu.
    Kullanım: from visualization.heatmap import heatmap_demosu
    """
    import time
    hm = RangeAzimuthHeatmap()
    plt.ion()
    plt.show()

    for _ in range(n_frame):
        for nesne in nesneler:
            nesne.hareket_et()
        H = csi_hesaplayici.hesapla(nesneler)
        hm.guncelle(H)
        hm.goster()
        time.sleep(1.0 / 30.0)

    plt.ioff()
    plt.show()
