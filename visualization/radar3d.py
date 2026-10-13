# visualization/radar3d.py — Open3D gerçek zamanlı görselleştirme

import open3d as o3d
import numpy as np
import time
from config import GoruntuConfig, SimulasyonConfig, WiFiConfig

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

        # Router göstergesi
        self._router_ekle()

        # Anten göstergeleri
        self._antenler_ekle()

        # Ana nokta bulutu
        self.pcd = o3d.geometry.PointCloud()
        self.vis.add_geometry(self.pcd)

        ctrl = self.vis.get_view_control()
        ctrl.set_zoom(0.55)
        ctrl.set_front([0.6, -0.75, 0.4])
        ctrl.set_up([0, 0, 1])
        ctrl.set_lookat([3.0, 2.5, 1.5])

        self._fps_sayac = 0
        self._t0 = time.time()
        self._fps = 0.0

    def _router_ekle(self):
        router = o3d.geometry.TriangleMesh.create_sphere(radius=0.12)
        router.translate(WiFiConfig.ROUTER_KONUM)
        router.paint_uniform_color([1.0, 1.0, 0.0])
        self.vis.add_geometry(router)

    def _antenler_ekle(self):
        for ant_pos in WiFiConfig.ANTEN_KONUMLAR:
            ant = o3d.geometry.TriangleMesh.create_sphere(radius=0.08)
            ant.translate(ant_pos)
            ant.paint_uniform_color([1.0, 0.5, 0.0])
            self.vis.add_geometry(ant)

    def guncelle(self, nesneler):
        noktalar, renkler = [], []

        for nesne in nesneler:
            # Ana parlak nokta kümesi — Gaussian dağılım
            for _ in range(GoruntuConfig.NOKTA_YOGUNLUGU):
                g = np.random.randn(3) * 0.10
                g[2] *= 0.4  # Z ekseninde daha sıkışık
                noktalar.append(nesne.pos + g)
                yogunluk = max(0.5, 1.0 - np.linalg.norm(g) / 0.35)
                renkler.append(np.clip(nesne.renk * yogunluk, 0, 1))

            # İz — soluklaşan kuyruk
            iz_len = max(len(nesne.iz), 1)
            for i, iz_pos in enumerate(nesne.iz):
                alfa = (i / iz_len) ** 1.5 * 0.7
                for _ in range(3):
                    g = np.random.randn(3) * 0.03
                    noktalar.append(iz_pos + g)
                    renkler.append(np.clip(nesne.renk * alfa, 0, 1))

        self.pcd.points = o3d.utility.Vector3dVector(np.array(noktalar))
        self.pcd.colors = o3d.utility.Vector3dVector(np.array(renkler))
        self.vis.update_geometry(self.pcd)

        self._fps_sayac += 1
        if self._fps_sayac % 20 == 0:
            self._fps = 20 / (time.time() - self._t0)
            print(f"\r[Wi-Fi Radar] FPS: {self._fps:.1f} | Nesne: {len(nesneler)} | Durum: TARAMA", end="")
            self._t0 = time.time()

    def calis(self):
        if not self.vis.poll_events():
            return False
        self.vis.update_renderer()
        return True

    def kapat(self):
        self.vis.destroy_window()
