# 🎯 GunBound Power Calculator — Bot W8 v79

> **Real-time power & angle calculator for GunBound (Softnyx) with memory reading, trajectory overlay, wind correction, and multi-mobile physics engine support.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows)](https://www.microsoft.com/windows)
[![Game](https://img.shields.io/badge/Game-GunBound%20Classic-green)](http://www.gunbound.net)

---

## 📺 Demo Video

[![GunBound Power Calculator Demo](https://img.youtube.com/vi/Z4Pn2U8c1HI/maxresdefault.jpg)](https://youtu.be/Z4Pn2U8c1HI?si=8ih7dpSv0qjiA4Jq)

▶️ **[Watch on YouTube](https://youtu.be/Z4Pn2U8c1HI?si=8ih7dpSv0qjiA4Jq)**

---

## ✨ Features

- **Memory Reading** — Reads player positions, camera, wind direction & speed directly from the `gunbound.exe` process in real-time.
- **Multi-Mobile Physics Engine** — Supports 3 distinct physics engines:
  - `ICE Engine` — for Ice, JD, Aduka
  - `ICO Engine` — for Armor, Mage, Lightning, Grub, Kalsiddon, ASate, Knight, Raon, Nak, BigFoot, Boomer, JFrog
  - `TRICO Engine` — for Trico (with Spin Mode 1 & 2)
  - `TURTLE Engine` — specialized for Turtle with a 30-parts coordinate system and dynamic wind-based mass
- **Trajectory Overlay** — Renders a real-time projectile curve directly on top of the game window.
- **Barrel Offset Calibration** — Per-mobile curve origin offset configurable via `barrel_offsets.txt`.
- **Physics Constant Calibration** — Gravity & mass per mobile customizable via `mobile_constants.txt`.
- **OCR Power Bar Reader** — Reads the in-game power bar value using Tesseract OCR + OpenCV.
- **Target Lock** — Lock onto the nearest player or any position in the game world using the mouse.
- **Hotkey Support** — Fast controls via keyboard shortcuts without touching the UI.
- **Military-theme GUI** — Dark mode military-style interface built with Tkinter.

---

## 🗂️ Supported Mobiles

| Mobile     | Engine  | Notes                               |
|------------|---------|-------------------------------------|
| Ice        | ICE     | Default g=0.608, m=168.0            |
| JD         | ICE     | Same as Ice engine                  |
| Aduka      | ICE     | T2 shot support                     |
| Trico      | TRICO   | Spin Mode 1 & 2, wind lookup table  |
| Turtle     | TURTLE  | 30-parts, dynamic mass (wind²×0.02) |
| Armor      | ICO     | g=0.677, m=105.6 (default)          |
| Mage       | ICO     | Freely calibrated via config file   |
| Lightning  | ICO     | Freely calibrated via config file   |
| Grub       | ICO     | Freely calibrated via config file   |
| Kalsiddon  | ICO     | Freely calibrated via config file   |
| ASate      | ICO     | Freely calibrated via config file   |
| Knight     | ICO     | Freely calibrated via config file   |
| Raon       | ICO     | Freely calibrated via config file   |
| Nak        | ICO     | T2 shot support                     |
| BigFoot    | ICO     | Freely calibrated via config file   |
| Boomer     | ICO     | Freely calibrated via config file   |
| JFrog      | ICO     | Freely calibrated via config file   |

---

## 🖥️ Requirements

- **OS**: Windows (required — uses Win32 API)
- **Python**: 3.8+
- **Tesseract OCR**: Install from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki), default path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- **Run as Administrator** (required for reading game process memory)

> ⚠️ **GunBound must be running in Windowed Mode at 800×600 resolution without a title bar.** The overlay and OCR features will not work correctly in any other display mode.

### Python Dependencies

```bash
pip install pymem pywin32 keyboard psutil opencv-python numpy pytesseract
```

---

## 🚀 Getting Started

1. **Install all dependencies** (see Requirements above).
2. **Launch GunBound** first.
3. **Run the script as Administrator**:
   ```bash
   python bot_w8_v79.py
   ```
4. Click **`>> START`** in the GUI to begin reading game memory.
5. Select your **source player** (your character) and **target player**.
6. Select the **mobile** you are currently using.
7. Press **`Right Shift`** to calculate the power.
8. The trajectory curve will appear on the game overlay.

---

## ⌨️ Hotkeys

| Hotkey         | Action                                                                      |
|----------------|-----------------------------------------------------------------------------|
| `Right Shift`  | Calculate power & display trajectory                                        |
| `ALT`          | Lock target to current mouse position (game coords) — non-Turtle            |
| `ALT`          | Lock target to nearest player — Turtle mode                                 |
| `ALT + SHIFT`  | Lock target to nearest player with mouse offset — non-Turtle                |
| `ALT + SHIFT`  | Lock target to mouse position — Turtle mode                                 |
| `CTRL`         | Cycle Trico spin mode (1↔2) / Turtle overlay mode (FORK → SKY → REGULAR)   |
| `CTRL + SHIFT` | Toggle canvas overlay / Toggle Turtle top panel                             |

---

## 📁 Configuration Files

### `barrel_offsets.txt`
Sets the curve origin offset per mobile (in pixels).
```
# Format: MobileName x y
# x: + right, - left (relative to shooting direction)
# y: + down, - up
Ice 0 0
Turtle 0 0
```

### `mobile_constants.txt`
Sets physics constants (gravity & mass) per mobile.
```
# Format: MobileName gravity mass
Ice 0.608 168.0
Armor 0.677 105.6
```

---

## 🐢 Turtle Engine — Technical Details

Turtle uses a 30-parts coordinate system with dynamic mass based on wind:

```
mass = 149 - wind² × 0.02
```

**Overlay Modes (cycle with CTRL):**

| Mode     | Contents                                            |
|----------|-----------------------------------------------------|
| FORK     | Fork4, Fork5, Fork6, Connect (T-preset shots)       |
| SKY/TIME | SkyBomb (Plan5 engine), TimeBomb (ICO engine)       |
| REGULAR  | Standard shooting mode                              |

---

## ⚠️ Disclaimer

> This tool is made for **educational purposes** and to understand ballistic physics within the game.
> Use it at your own risk.
> Not affiliated with Softnyx Co., Ltd.

---

## 📜 License

MIT License — free to use and modify with attribution.
