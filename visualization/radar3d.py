# visualization/radar3d.py — Open3D gerçek zamanlı görselleştirme

import open3d as o3d
import numpy as np
import time
from config import GoruntuConfig, SimulasyonConfig

class Radar3D:
    def __init__(self, oda_geometrisi):
        self.vis = o3d.visualization.Visualizer()
        self.vis.create_window(
            window_name="Wi-Fi CSI 3D Radar",
            width=GoruntuConfig.PENCERE_GENISLIK,
            height=GoruntuConfig.PENCERE_YUKSEKLIK
        )
        opt = self.vis.get_render_option()
        opt.background_color = np.array(GoruntuConfig.ARKA_PLAN)
        opt.point_size = GoruntuConfig.NOKTA_BOYUTU

        self.vis.add_geometry(oda_geometrisi)

        self.pcd = o3d.geometry.PointCloud()
        self.vis.add_geometry(self.pcd)

        ctrl = self.vis.get_view_control()
        ctrl.set_zoom(0.6)
        ctrl.set_front([0.5, -0.8, 0.5])
        ctrl.set_up([0, 0, 1])

        self._fps_sayac = 0
        self._t0 = time.time()

    def guncelle(self, nesneler):
        noktalar, renkler = [], []

        for nesne in nesneler:
            for _ in range(GoruntuConfig.NOKTA_YOGUNLUGU):
                g = np.random.randn(3) * 0.08
                noktalar.append(nesne.pos + g)
                y = max(0.3, 1.0 - np.linalg.norm(g) / 0.3)
                renkler.append(nesne.renk * y)

            for i, iz in enumerate(nesne.iz):
                alfa = (i / max(len(nesne.iz), 1)) * 0.5
                noktalar.append(iz)
                renkler.append(nesne.renk * alfa)

        self.pcd.points = o3d.utility.Vector3dVector(np.array(noktalar))
        self.pcd.colors = o3d.utility.Vector3dVector(np.array(renkler))
        self.vis.update_geometry(self.pcd)

        self._fps_sayac += 1
        if self._fps_sayac % 30 == 0:
            fps = 30 / (time.time() - self._t0)
            print(f"FPS: {fps:.1f} | Nesne: {len(nesneler)}")
            self._t0 = time.time()

    def calis(self):
        if not self.vis.poll_events():
            return False
        self.vis.update_renderer()
        return True

    def kapat(self):
        self.vis.destroy_window()
