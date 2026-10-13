# core/cnn_tahminci.py — Wi-Fi CSI 3D Radar
# PyTorch CNN: CSI genliği → (x, y, z) konum tahmini
# MUSIC algoritmasına paralel çalışır; daha düşük gecikme, öğrenme tabanlı tahmin.
#
# Eğitim:   python -m core.cnn_tahminci --egit
# Kullanım: CNNTahminci.tahmin_et(H) → (x, y, z, guc) listesi

from __future__ import annotations

import os
import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    TORCH_MEVCUT = True
except ImportError:
    TORCH_MEVCUT = False

from config import SimulasyonConfig

# ── Sabitler ─────────────────────────────────────────────────────────────────
MODEL_YOLU  = os.path.join(os.path.dirname(__file__), "..", "models", "cnn_konum.pth")
GIRIS_H     = SimulasyonConfig.N_ANTEN       # 3 anten (satır)
GIRIS_W     = SimulasyonConfig.N_SUBCARRIER  # 64 subcarrier (sütun)
ODA_X       = SimulasyonConfig.ODA_X         # 10.0 m
ODA_Y       = SimulasyonConfig.ODA_Y         # 6.0 m
ODA_Z       = 3.0                            # tavan yüksekliği


# ── Model Mimarisi ────────────────────────────────────────────────────────────
class _CSIKonumNet(nn.Module if TORCH_MEVCUT else object):
    """
    Girdi : (batch, 1, N_anten, N_subcarrier) — normalize genlik
    Çıktı : (batch, 3) — [x_norm, y_norm, z_norm] in [0, 1]
    """
    def __init__(self):
        if not TORCH_MEVCUT:
            return
        super().__init__()

        self.ozellik = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),                          # → (16, H/2, W/2)

            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),                          # → (32, H/4, W/4)

            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((2, 4)),             # → (64, 2, 4) her zaman sabit
        )

        self.regresyon = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 2 * 4, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.4),
            nn.Linear(256, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, 3),
            nn.Sigmoid(),                             # çıktı [0, 1]
        )

    def forward(self, x):
        return self.regresyon(self.ozellik(x))


# ── Veri Seti ─────────────────────────────────────────────────────────────────
class _CSIVeriSeti(Dataset if TORCH_MEVCUT else object):
    """Simülasyon tabanlı eğitim verisi üretir."""

    def __init__(self, n_ornek: int = 2000):
        if not TORCH_MEVCUT:
            return
        super().__init__()
        # Geç import — csi modülü sadece eğitimde lazım
        from core.csi import CSIHesaplayici
        from core.nesne import Nesne

        csi_hesap = CSIHesaplayici()
        self.girisler: list[torch.Tensor] = []
        self.etiketler: list[torch.Tensor] = []

        rng = np.random.default_rng(42)
        for _ in range(n_ornek):
            # Rastgele konum
            ox = rng.uniform(0.5, ODA_X - 0.5)
            oy = rng.uniform(0.5, ODA_Y - 0.5)
            oz = rng.uniform(0.3, ODA_Z - 0.3)

            nesne = Nesne(ox, oy, oz, [1, 0, 0], "tmp", hiz_carpani=0.0)
            H = csi_hesap.hesapla([nesne])      # (N_ant, N_sub) complex

            amp = np.abs(H).astype(np.float32)
            dmin, dmax = amp.min(), amp.max()
            if dmax - dmin > 1e-9:
                amp = (amp - dmin) / (dmax - dmin)

            # (1, H, W) tensor
            t_giris  = torch.from_numpy(amp).unsqueeze(0)
            t_etiket = torch.tensor(
                [ox / ODA_X, oy / ODA_Y, oz / ODA_Z], dtype=torch.float32
            )
            self.girisler.append(t_giris)
            self.etiketler.append(t_etiket)

    def __len__(self):
        return len(self.girisler)

    def __getitem__(self, idx):
        return self.girisler[idx], self.etiketler[idx]


# ── Ana Sınıf ─────────────────────────────────────────────────────────────────
class CNNTahminci:
    """
    Kullanım:
        tahminci = CNNTahminci()
        konumlar = tahminci.tahmin_et(H)   # [(x, y, z, guc), ...]
    """

    def __init__(self):
        self._hazir = False

        if not TORCH_MEVCUT:
            print("[CNN] Uyarı: PyTorch kurulu değil. CNN devre dışı.")
            return

        self._model = _CSIKonumNet()
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)

        if os.path.exists(MODEL_YOLU):
            try:
                sd = torch.load(MODEL_YOLU, map_location=self._device)
                self._model.load_state_dict(sd)
                self._model.eval()
                self._hazir = True
                print(f"[CNN] Model yüklendi: {MODEL_YOLU}")
            except Exception as e:
                print(f"[CNN] Model yüklenemedi ({e}). Eğitim gerekli: --egit")
        else:
            print("[CNN] Kayıtlı model yok. 'python -m core.cnn_tahminci --egit' ile eğitin.")

    # ── Tahmin ───────────────────────────────────────────────────────────────
    def tahmin_et(self, H: np.ndarray) -> list[tuple[float, float, float, float]]:
        """
        Parametreler
        ------------
        H : np.ndarray (N_ant, N_sub) complex  — anlık CSI matrisi

        Dönüş
        -----
        [(x, y, z, guc)] — tek tahmin noktası, MUSIC sonuçlarıyla birleştirilebilir
        """
        if not self._hazir:
            return []

        amp = np.abs(H).astype(np.float32)
        dmin, dmax = amp.min(), amp.max()
        if dmax - dmin < 1e-9:
            return []
        amp = (amp - dmin) / (dmax - dmin)

        with torch.no_grad():
            t = torch.from_numpy(amp).unsqueeze(0).unsqueeze(0).to(self._device)
            pred = self._model(t).cpu().numpy()[0]   # [x_norm, y_norm, z_norm]

        x = float(pred[0]) * ODA_X
        y = float(pred[1]) * ODA_Y
        z = float(pred[2]) * ODA_Z
        # "güç" — ortalama normalize genlik (görselleştirme için)
        guc = float(np.mean(amp))
        return [(x, y, z, guc)]

    @property
    def hazir(self) -> bool:
        return self._hazir


# ── Eğitim ────────────────────────────────────────────────────────────────────
def egit(n_ornek: int = 2000, epoch: int = 30, lr: float = 1e-3, batch: int = 64):
    """Modeli simülasyon verisiyle eğitir ve models/ altına kaydeder."""
    if not TORCH_MEVCUT:
        print("[CNN] PyTorch kurulu değil. Eğitim atlanıyor.")
        return

    print(f"[CNN] Eğitim başlıyor — {n_ornek} örnek, {epoch} epoch")
    os.makedirs(os.path.dirname(MODEL_YOLU), exist_ok=True)

    veri   = _CSIVeriSeti(n_ornek)
    yukl   = DataLoader(veri, batch_size=batch, shuffle=True, num_workers=0)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model  = _CSIKonumNet().to(device)
    opt    = optim.Adam(model.parameters(), lr=lr)
    kayip  = nn.MSELoss()
    sched  = optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epoch)

    for ep in range(1, epoch + 1):
        model.train()
        toplam = 0.0
        for X, y in yukl:
            X, y = X.to(device), y.to(device)
            opt.zero_grad()
            kayip(model(X), y).backward()
            opt.step()
            toplam += kayip(model(X.detach()), y.detach()).item()
        sched.step()
        ort_kayip = toplam / len(yukl)
        print(f"  Epoch {ep:3d}/{epoch} | Kayıp: {ort_kayip:.5f}")

    torch.save(model.state_dict(), MODEL_YOLU)
    print(f"[CNN] Model kaydedildi → {MODEL_YOLU}")


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if "--egit" in sys.argv:
        egit()
    else:
        print("Kullanım: python -m core.cnn_tahminci --egit")
