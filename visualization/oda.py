# visualization/oda.py — Oda çerçevesi

import open3d as o3d
from config import OdaConfig

class OdaGorunumu:
    def __init__(self):
        self.cizgi_seti = self._olustur()

    def _olustur(self):
        x = OdaConfig.GENISLIK
        y = OdaConfig.DERINLIK
        z = OdaConfig.YUKSEKLIK

        noktalar = [
            [0,0,0],[x,0,0],[x,y,0],[0,y,0],
            [0,0,z],[x,0,z],[x,y,z],[0,y,z]
        ]
        cizgiler = [
            [0,1],[1,2],[2,3],[3,0],
            [4,5],[5,6],[6,7],[7,4],
            [0,4],[1,5],[2,6],[3,7]
        ]
        renkler = [[0.3, 0.3, 0.4]] * len(cizgiler)

        cs = o3d.geometry.LineSet()
        cs.points = o3d.utility.Vector3dVector(noktalar)
        cs.lines = o3d.utility.Vector2iVector(cizgiler)
        cs.colors = o3d.utility.Vector3dVector(renkler)
        return cs

    def geometri(self):
        return self.cizgi_seti
