# 🎯 GunBound Power Calculator — Bot W8 v79

> **Real-time power & angle calculator for GunBound (Softnyx) with memory reading, trajectory overlay, wind correction, and multi-mobile physics engine support.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows)](https://www.microsoft.com/windows)
[![Game](https://img.shields.io/badge/Game-GunBound%20Classic-green)](http://www.gunbound.net)

---

## 📺 Demo Video

[![GunBound Power Calculator Demo](https://img.youtube.com/vi/Z4Pn2U8c1HI/maxresdefault.jpg)](https://youtu.be/Z4Pn2U8c1HI?si=8ih7dpSv0qjiA4Jq)

▶️ **[Tonton di YouTube](https://youtu.be/Z4Pn2U8c1HI?si=8ih7dpSv0qjiA4Jq)**

---

## ✨ Fitur Utama

- **Memory Reading** — Membaca posisi pemain, kamera, arah & kecepatan angin langsung dari proses `gunbound.exe` secara real-time.
- **Multi-Mobile Physics Engine** — Mendukung 3 engine fisika berbeda:
  - `ICE Engine` — untuk Ice, JD, Aduka
  - `ICO Engine` — untuk Armor, Mage, Lightning, Grub, Kalsiddon, ASate, Knight, Raon, Nak, BigFoot, Boomer, JFrog
  - `TRICO Engine` — untuk Trico (dengan spin mode 1 & 2)
  - `TURTLE Engine` — khusus Turtle dengan sistem 30-parts & mass dinamis berbasis wind
- **Trajectory Overlay** — Menampilkan kurva lintasan peluru langsung di atas jendela game.
- **Kalibrasi Barrel Offset** — Offset titik awal kurva per mobile dapat dikonfigurasi via file `barrel_offsets.txt`.
- **Kalibrasi Physics Constants** — Gravity & mass per mobile dapat dikustomisasi via file `mobile_constants.txt`.
- **OCR Power Bar Reader** — Membaca nilai power bar dari screen menggunakan Tesseract OCR + OpenCV.
- **Target Lock** — Lock target ke player terdekat atau posisi mouse di game world.
- **Hotkey Support** — Kontrol cepat via keyboard shortcut tanpa harus klik UI.
- **Military-theme GUI** — Tampilan dark mode bertema militer berbasis Tkinter.

---

## 🗂️ Daftar Mobile yang Didukung

| Mobile     | Engine  | Keterangan                          |
|------------|---------|-------------------------------------|
| Ice        | ICE     | Default g=0.608, m=168.0            |
| JD         | ICE     | Same as Ice engine                  |
| Aduka      | ICE     | T2 shot support                     |
| Trico      | TRICO   | Spin Mode 1 & 2, wind lookup table  |
| Turtle     | TURTLE  | 30-parts, mass dinamis (wind²×0.02) |
| Armor      | ICO     | g=0.677, m=105.6 (default)          |
| Mage       | ICO     | Kalibrasi bebas via file            |
| Lightning  | ICO     | Kalibrasi bebas via file            |
| Grub       | ICO     | Kalibrasi bebas via file            |
| Kalsiddon  | ICO     | Kalibrasi bebas via file            |
| ASate      | ICO     | Kalibrasi bebas via file            |
| Knight     | ICO     | Kalibrasi bebas via file            |
| Raon       | ICO     | Kalibrasi bebas via file            |
| Nak        | ICO     | T2 shot support                     |
| BigFoot    | ICO     | Kalibrasi bebas via file            |
| Boomer     | ICO     | Kalibrasi bebas via file            |
| JFrog      | ICO     | Kalibrasi bebas via file            |

---

## 🖥️ Requirements

- **OS**: Windows (wajib — menggunakan Win32 API)
- **Python**: 3.8+
- **Tesseract OCR**: Install dari [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki), default path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- **Jalankan sebagai Administrator** (wajib untuk membaca memory proses)

### Python Dependencies

```
pip install pymem pywin32 keyboard psutil opencv-python numpy pytesseract
```

Atau jika ada `requirements.txt`:

```
pip install -r requirements.txt
```

---

## 🚀 Cara Penggunaan

1. **Install semua dependencies** (lihat bagian Requirements).
2. **Jalankan GunBound** terlebih dahulu.
3. **Jalankan script sebagai Administrator**:
   ```bash
   python bot_w8_v79.py
   ```
4. Klik **`>> START`** di GUI untuk mulai membaca memory game.
5. Pilih **source player** (karakter kamu) dan **target player**.
6. Pilih **mobile** yang sedang digunakan.
7. Tekan **`Right Shift`** untuk menghitung power.
8. Kurva lintasan akan muncul di overlay game.

---

## ⌨️ Hotkeys

| Hotkey         | Fungsi                                                                 |
|----------------|------------------------------------------------------------------------|
| `Right Shift`  | Hitung power & tampilkan trajectory                                    |
| `ALT`          | Lock target ke posisi mouse (koordinat game) — non-Turtle              |
| `ALT`          | Lock target ke player terdekat (Turtle mode)                           |
| `ALT + SHIFT`  | Lock target ke player terdekat + offset dari mouse — non-Turtle        |
| `ALT + SHIFT`  | Lock target ke posisi mouse (Turtle mode)                              |
| `CTRL`         | Cycling Trico spin mode (1↔2) / Turtle overlay mode (FORK→SKY→REGULAR)|
| `CTRL + SHIFT` | Toggle canvas overlay / Toggle Turtle panel kotak atas                 |

---

## 📁 File Konfigurasi

### `barrel_offsets.txt`
Mengatur offset titik awal kurva per mobile (dalam pixel).
```
# Format: MobileName x y
# x: + kanan, - kiri (relatif arah tembak)
# y: + bawah, - atas
Ice 0 0
Turtle 0 0
```

### `mobile_constants.txt`
Mengatur konstanta fisika (gravity & mass) per mobile.
```
# Format: MobileName gravedad masa
Ice 0.608 168.0
Armor 0.677 105.6
```

---

## 🐢 Turtle Engine — Detail Teknis

Turtle menggunakan sistem koordinat 30-parts dengan mass dinamis:

```
mass = 149 - wind² × 0.02
```

**Overlay Mode (CTRL cycling):**
| Mode     | Isi                                              |
|----------|--------------------------------------------------|
| FORK     | Fork4, Fork5, Fork6, Connect (T-preset)          |
| SKY/TIME | SkyBomb (Plan5 engine), TimeBomb (ICO engine)    |
| REGULAR  | Mode tembak biasa                                |

---

## ⚠️ Disclaimer

> Tool ini dibuat untuk keperluan **edukasi** dan pemahaman fisika balistik dalam game.
> Penggunaan sepenuhnya menjadi tanggung jawab pengguna.
> Tidak berafiliasi dengan Softnyx Co., Ltd.

---

## 📜 License

MIT License — bebas digunakan dan dimodifikasi dengan atribusi.
