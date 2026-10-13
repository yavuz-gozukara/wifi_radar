import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.animation as animation

# --- PARAMETRELER ---
oda_x, oda_y, oda_z = 6.0, 5.0, 3.0   # Sınıf boyutu (metre)
fs = 100          # Örnekleme frekansı (Hz)
n_subcarrier = 64 # OFDM alt taşıyıcı sayısı
n_anten = 3       # Alıcı anten sayısı
fc = 2.4e9        # Wi-Fi merkez frekansı
c = 3e8           # Işık hızı
dalga_boyu = c / fc

# --- NESNE SINIFI ---
class Nesne:
    def __init__(self, isim, x, y, z, renk):
        self.isim = isim
        self.x = x
        self.y = y
        self.z = z
        self.renk = renk
        self.vx = np.random.uniform(-0.05, 0.05)
        self.vy = np.random.uniform(-0.05, 0.05)

    def hareket_et(self):
        self.x += self.vx
        self.y += self.vy
        # Duvara çarpınca geri dön
        if self.x < 0.3 or self.x > oda_x - 0.3:
            self.vx *= -1
        if self.y < 0.3 or self.y > oda_y - 0.3:
            self.vy *= -1

# --- NESNELER (sınıftaki insanlar/masalar) ---
nesneler = [
    Nesne("Öğrenci 1", 2.0, 2.0, 1.0, 'red'),
    Nesne("Öğrenci 2", 4.0, 3.0, 1.0, 'blue'),
    Nesne("Öğrenci 3", 1.5, 4.0, 1.0, 'green'),
    Nesne("Masa",      3.0, 2.5, 0.8, 'brown'),
]

# --- ROUTER VE ANTEN KONUMLARI ---
router_pos = np.array([0.0, 0.0, 2.5])
anten_pos = np.array([
    [oda_x, 0.0, 2.5],
    [oda_x, oda_y/2, 2.5],
    [oda_x, oda_y, 2.5],
])

# --- CSI HESAPLA ---
def csi_hesapla(nesne_listesi):
    frekanslar = fc + np.arange(n_subcarrier) * 312500
    H = np.zeros((n_anten, n_subcarrier), dtype=complex)

    for ant_idx, ant in enumerate(anten_pos):
        for nesne in nesne_listesi:
            pos = np.array([nesne.x, nesne.y, nesne.z])
            dist1 = np.linalg.norm(pos - router_pos)
            dist2 = np.linalg.norm(ant - pos)
            toplam_dist = dist1 + dist2
            genlik = 0.5 / (toplam_dist ** 2 + 1e-6)
            for k, fk in enumerate(frekanslar):
                faz = 2 * np.pi * fk * toplam_dist / c
                H[ant_idx, k] += genlik * np.exp(1j * faz)

        # Gürültü ekle
        H[ant_idx] += 0.01 * (np.random.randn(n_subcarrier) +
                               1j * np.random.randn(n_subcarrier))
    return H

# --- CSI'DAN KONUM TAHMİNİ ---
def konum_tahmin(H):
    # Anten faz farklarından açı tahmini (basit beamforming)
    faz_fark_01 = np.angle(H[1] * np.conj(H[0]))
    faz_fark_12 = np.angle(H[2] * np.conj(H[1]))

    ort_faz_01 = np.mean(faz_fark_01)
    ort_faz_12 = np.mean(faz_fark_12)

    # Subcarrier farkından menzil tahmini
    faz_subcarrier = np.unwrap(np.angle(H[0]))
    menzil = np.abs(np.mean(np.diff(faz_subcarrier))) * c / (2 * np.pi * 312500)
    menzil = np.clip(menzil * 50, 0.5, oda_x - 0.5)

    azimut = np.clip(ort_faz_01 * oda_y / np.pi + oda_y/2, 0.3, oda_y - 0.3)

    return menzil, azimut

# --- GÖRSELLEŞTİRME ---
fig = plt.figure(figsize=(14, 6))
ax_gercek = fig.add_subplot(121, projection='3d')
ax_radar = fig.add_subplot(122, projection='3d')

def guncelle(frame):
    # Nesneleri hareket ettir
    for nesne in nesneler:
        nesne.hareket_et()

    # CSI hesapla
    H = csi_hesapla(nesneler)

    # --- SOL: Gerçek konum ---
    ax_gercek.cla()
    ax_gercek.set_xlim(0, oda_x)
    ax_gercek.set_ylim(0, oda_y)
    ax_gercek.set_zlim(0, oda_z)
    ax_gercek.set_title('Gerçek Konum', fontsize=12, fontweight='bold')
    ax_gercek.set_xlabel('X (m)')
    ax_gercek.set_ylabel('Y (m)')
    ax_gercek.set_zlabel('Z (m)')

    # Oda çerçevesi
    for x in [0, oda_x]:
        for y in [0, oda_y]:
            ax_gercek.plot([x,x],[y,y],[0,oda_z],'gray',alpha=0.2)

    # Router ve antenler
    ax_gercek.scatter(*router_pos, c='yellow', s=150, marker='*', label='Router')
    for i, ant in enumerate(anten_pos):
        ax_gercek.scatter(*ant, c='orange', s=80, marker='^')

    # Nesneler
    for nesne in nesneler:
        ax_gercek.scatter(nesne.x, nesne.y, nesne.z,
                         c=nesne.renk, s=200, alpha=0.9)
        ax_gercek.text(nesne.x, nesne.y, nesne.z + 0.15,
                      nesne.isim, fontsize=7)

    # --- SAĞ: Radar tahmini ---
    ax_radar.cla()
    ax_radar.set_xlim(0, oda_x)
    ax_radar.set_ylim(0, oda_y)
    ax_radar.set_zlim(0, oda_z)
    ax_radar.set_title('Wi-Fi Radar Görüntüsü', fontsize=12, fontweight='bold')
    ax_radar.set_xlabel('X (m)')
    ax_radar.set_ylabel('Y (m)')
    ax_radar.set_zlabel('Z (m)')

    # Her nesne için ayrı CSI kanalı simüle et ve tahmin yap
    for nesne in nesneler:
        H_tek = csi_hesapla([nesne])
        mx, my = konum_tahmin(H_tek)
        ax_radar.scatter(mx, my, nesne.z,
                        c=nesne.renk, s=150, alpha=0.7, marker='o')

    # Arka plan ızgarası
    ax_radar.set_facecolor('#0a0a1a')
    ax_radar.grid(True, alpha=0.3)

    plt.tight_layout()

print("Wi-Fi CSI 3D Radar Simülasyonu başlıyor...")
print("Pencereyi kapatmak için X'e bas.")

ani = animation.FuncAnimation(fig, guncelle, interval=100,
                               cache_frame_data=False)
plt.show()