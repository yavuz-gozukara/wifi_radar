# core/esp32_arayuz.py — ESP32 Gerçek Veri Arayüzü
#
# Bu modül ESP32 fiziksel cihazı geldiğinde devreye girecek.
# Şu an simülasyon modunda çalışan sistem buraya geçiş yaptığında
# main.py'de sadece tek satır değiştirilecek:
#   - SIMÜLASYON: H = csi.hesapla(nesneler)
#   - GERÇEK:     H = esp32.oku()

import numpy as np
import struct
import time
from config import WiFiConfig

try:
    import serial        # pip install pyserial
    SERIAL_VAR = True
except ImportError:
    SERIAL_VAR = False

try:
    import socket
    SOCKET_VAR = True
except ImportError:
    SOCKET_VAR = False


class ESP32ArayuzBase:
    """
    Tüm ESP32 arayüzlerinin temel sınıfı.
    CSI matrisini (n_anten × n_subcarrier) karmaşık değer olarak döner.
    """

    def __init__(self):
        self.n_anten = WiFiConfig.ANTEN_SAYISI
        self.n_sub   = WiFiConfig.SUBCARRIER_SAYISI
        self._frame_sayac = 0
        self._baslangic   = time.time()

    def oku(self):
        """
        Bir frame CSI verisi döner: np.ndarray(n_anten, n_sub, dtype=complex)
        Alt sınıflar override etmeli.
        """
        raise NotImplementedError

    def kapat(self):
        pass

    def _bos_h(self):
        return np.zeros((self.n_anten, self.n_sub), dtype=complex)

    def fps(self):
        """Anlık FPS"""
        gecen = time.time() - self._baslangic
        if gecen < 1e-6:
            return 0.0
        return self._frame_sayac / gecen


class ESP32SerialArayuz(ESP32ArayuzBase):
    """
    ESP32'den USB Serial üzerinden CSI okur.

    ESP32 firmware beklenen paket formatı (her frame):
        [MAGIC: 2 byte = 0xAB 0xCD]
        [n_anten: 1 byte]
        [n_sub: 1 byte]
        [data: n_anten * n_sub * 2 * 4 byte]  (float32 reel + imaj çiftleri)
        [CHECKSUM: 1 byte]

    Bağlantı için:
        esp = ESP32SerialArayuz(port="COM3", baud=921600)
        H = esp.oku()
    """

    MAGIC = bytes([0xAB, 0xCD])

    def __init__(self, port="COM3", baud=921600, timeout=2.0):
        super().__init__()
        if not SERIAL_VAR:
            raise ImportError("pyserial kurulu değil: pip install pyserial")

        self.port   = port
        self.baud   = baud
        self.ser    = None
        self.timeout = timeout
        self._baglan()

    def _baglan(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
            print(f"[ESP32] {self.port} bağlandı @ {self.baud} baud")
        except Exception as e:
            print(f"[ESP32] HATA: {e}")
            self.ser = None

    def oku(self):
        if self.ser is None or not self.ser.is_open:
            return self._bos_h()

        try:
            # Magic byte ara
            buf = b""
            while True:
                byte = self.ser.read(1)
                if not byte:
                    return self._bos_h()
                buf += byte
                if len(buf) >= 2 and buf[-2:] == self.MAGIC:
                    break

            # Header
            header = self.ser.read(2)
            if len(header) < 2:
                return self._bos_h()
            n_ant, n_sub = header[0], header[1]

            # Veri
            nbytes = n_ant * n_sub * 2 * 4  # float32 x reel+imaj
            data = self.ser.read(nbytes)
            if len(data) < nbytes:
                return self._bos_h()

            # Checksum (basit XOR)
            chk = self.ser.read(1)
            beklenen = 0
            for b in data:
                beklenen ^= b
            if chk and chk[0] != beklenen:
                print("[ESP32] Checksum hatası — frame atlandı")
                return self._bos_h()

            # Float32 parse
            floats = struct.unpack(f"{n_ant * n_sub * 2}f", data)
            H = np.array(floats[0::2]) + 1j * np.array(floats[1::2])
            H = H.reshape(n_ant, n_sub)

            self._frame_sayac += 1
            return H

        except Exception as e:
            print(f"[ESP32] Okuma hatası: {e}")
            return self._bos_h()

    def kapat(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[ESP32] Serial bağlantı kapatıldı.")


class ESP32UDPArayuz(ESP32ArayuzBase):
    """
    ESP32'den Wi-Fi UDP üzerinden CSI okur.
    ESP32'nin IP adresi ve port ile dinleme yapar.

    Kullanım:
        esp = ESP32UDPArayuz(host="0.0.0.0", port=5005)
        H = esp.oku()
    """

    def __init__(self, host="0.0.0.0", port=5005, timeout=0.1):
        super().__init__()
        if not SOCKET_VAR:
            raise ImportError("socket modülü bulunamadı")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        self.sock.settimeout(timeout)
        print(f"[ESP32-UDP] {host}:{port} dinleniyor...")

    def oku(self):
        try:
            data, addr = self.sock.recvfrom(8192)
            n_ant  = data[0]
            n_sub  = data[1]
            nbytes = n_ant * n_sub * 2 * 4
            if len(data) < 2 + nbytes:
                return self._bos_h()

            floats = struct.unpack(f"{n_ant * n_sub * 2}f", data[2:2+nbytes])
            H = np.array(floats[0::2]) + 1j * np.array(floats[1::2])
            H = H.reshape(n_ant, n_sub)
            self._frame_sayac += 1
            return H
        except socket.timeout:
            return self._bos_h()
        except Exception as e:
            print(f"[ESP32-UDP] Okuma hatası: {e}")
            return self._bos_h()

    def kapat(self):
        self.sock.close()
        print("[ESP32-UDP] Bağlantı kapatıldı.")


class SimulasyonArayuz(ESP32ArayuzBase):
    """
    ESP32 yokken kullanılan simülasyon modu.
    CSIHesaplayici ile aynı arayüzü sağlar.
    ESP32 gelince bu sınıf doğrudan değiştirilebilir.
    """

    def __init__(self, csi_hesaplayici, nesneler_ref):
        super().__init__()
        self._csi  = csi_hesaplayici
        self._ref  = nesneler_ref  # Ana döngüdeki nesne listesine referans

    def oku(self):
        H = self._csi.hesapla(self._ref)
        self._frame_sayac += 1
        return H
