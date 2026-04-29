import tkinter as tk
from tkinter import messagebox
import os
import time
import pymem
import pymem.process
import threading
import ctypes
import sys
from enum import IntEnum
from math import cos, sin, tan, radians, degrees, atan, sqrt, fabs
from win32gui import FindWindow, GetClientRect, ClientToScreen, ScreenToClient
import win32api
import win32con
import keyboard
import psutil
import cv2
import numpy as np
import win32gui
import pytesseract
import re
import bisect

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ─── Konstanta Game ───────────────────────────────────────────
PROCESS_NAME                = "gunbound.exe"
BASE_ADDRESS_PLAYER         = 0x482A58
PLAYER_OFFSET               = 0x18
MOBILE_ID_ADDRESS_OFFSET    = 0x497368
SCREEN_CENTER_X_OFFSET      = 0x4E98D4
SCREEN_CENTER_Y_OFFSET      = 0x4E98D8
WIND_DIRECTION_OFFSET       = 0x1235
WIND_SPEED_OFFSET           = 0x1234
BASE_ADDRESS_A              = 0x87053c
BASE_ADDRESS_B_OFFSET       = 0x870140
PLAYER_INDEX_ADDRESS_OFFSET = 0x4F3929
DEFAULT_ROTATED_OFFSET_X    = 20
DEFAULT_ROTATED_OFFSET_Y    = 25
OFFSET_Y                    = -40
TARGET_LOCK_OFFSET_X        = -1  # <-- geser X titik target (+ kanan, - kiri)
TARGET_LOCK_OFFSET_Y        = -18  # <-- geser Y titik target (+ bawah, - atas)
NUM_PLAYERS                 = 8
TARGET_HIGHLIGHT_RADIUS     = 15
TARGET_DETECTION_THRESHOLD  = 50

SCREEN_WIDTH_PIXELS     = 800
SCREEN_HEIGHT_PIXELS    = 600
PARTS_PER_SCREEN_WIDTH  = 8
PARTS_PER_SCREEN_HEIGHT = 6
PIXELS_PER_PART_WIDTH   = SCREEN_WIDTH_PIXELS  / PARTS_PER_SCREEN_WIDTH
PIXELS_PER_PART_HEIGHT  = SCREEN_HEIGHT_PIXELS / PARTS_PER_SCREEN_HEIGHT

POWER_BAR_WIDTH    = 400
POWER_BAR_X_OFFSET = 241
POWER_BAR_Y_OFFSET = SCREEN_HEIGHT_PIXELS - 15
POWER_BAR_MAX      = 4.0
POWER_BAR_SCALE    = POWER_BAR_WIDTH / POWER_BAR_MAX

GAME_GUI_HEIGHT = 85   # pixel GUI game dari bawah — kurva dipotong di sini

# ─── File database konstanta mobile ──────────────────────────
BARREL_OFFSET_FILE    = "barrel_offsets.txt"
MOBILE_CONSTANTS_FILE = "mobile_constants.txt"

def load_barrel_offsets() -> dict:
    """Load barrel offsets dari file. Format: MobileName x y"""
    data = {}
    if not os.path.exists(BARREL_OFFSET_FILE):
        return data
    try:
        with open(BARREL_OFFSET_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) == 3:
                    data[parts[0]] = (int(float(parts[1])), int(float(parts[2])))
    except Exception:
        pass
    return data

def save_barrel_offsets(data: dict):
    try:
        with open(BARREL_OFFSET_FILE, 'w') as f:
            f.write("# Barrel Offsets per Mobile\n")
            f.write("# Format: MobileName x y\n")
            f.write("# x: + kanan, - kiri (relatif arah tembak)\n")
            f.write("# y: + bawah, - atas\n")
            for name, (x, y) in sorted(data.items()):
                f.write(f"{name} {x} {y}\n")
    except Exception:
        pass


DEFAULT_GRAVEDAD = 0.608
DEFAULT_MASA     = 168.0

def load_mobile_constants() -> dict:
    data = {}
    if not os.path.exists(MOBILE_CONSTANTS_FILE):
        _create_default_constants_file()
    try:
        with open(MOBILE_CONSTANTS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) == 3:
                    name, g, m = parts[0], float(parts[1]), float(parts[2])
                    data[name] = (g, m)
    except Exception:
        pass
    return data

def save_mobile_constants(data: dict):
    try:
        with open(MOBILE_CONSTANTS_FILE, 'w') as f:
            f.write("# Mobile Physics Constants\n")
            f.write("# Format: MobileName gravedad masa\n")
            f.write("# Default proven: Ice 0.608 168.0\n")
            f.write("#\n")
            for name, (g, m) in sorted(data.items()):
                f.write(f"{name} {g} {m}\n")
    except Exception:
        pass

def _create_default_constants_file():
    # ICE engine: pakai DEFAULT_GRAVEDAD / DEFAULT_MASA
    # ICO engine: default G=0.677, M=105.6 (bisa dikalibrasi sendiri)
    ice_mobiles = ["Ice", "JD", "Aduka"]
    ico_mobiles = ["Armor","Mage","Lightning","Grub","Kalsiddon","ASate",
                   "Knight","Raon","Nak","BigFoot","Boomer","JFrog"]
    data = {}
    for n in ice_mobiles:
        data[n] = (DEFAULT_GRAVEDAD, DEFAULT_MASA)
    for n in ico_mobiles:
        data[n] = (ICO_DEFAULT_G, ICO_DEFAULT_M)
    data["Trico"]  = (DEFAULT_GRAVEDAD, DEFAULT_MASA)  # Trico punya engine sendiri
    data["Turtle"] = (ICO_DEFAULT_G, ICO_DEFAULT_M)    # Turtle pakai ICO engine
    data["Random"] = (DEFAULT_GRAVEDAD, DEFAULT_MASA)
    save_mobile_constants(data)

# ─── Warna Tema MILITARY ──────────────────────────────────────
BG_DARK   = "#0E0F0A"
BG_CARD   = "#161810"
BG_PANEL  = "#1C1F14"
ACCENT    = "#8BA84A"
ACCENT2   = "#C0392B"
ACCENT3   = "#D4A017"
TEXT_MAIN = "#D6CEAA"
TEXT_DIM  = "#5A5C42"
BORDER    = "#2A2D1E"
SUCCESS   = "#6DBF5A"

# ─── Warna 3 spin Trico ───────────────────────────────────────
TRICO_COLORS = ["#4FC3F7", "#FFB74D", "#CE93D8"]
TRICO_SPIN_SETS = [["1","2","3"], ["2b","3b","4"]]

# ═══════════════════════════════════════════════════════════════
# TURTLE ENGINE — reverse-engineered dari TORTUGA.xlsx + turtle.xlsx
# 30 parts system. Physics (TORTUGA.xlsx):
#   g    = 0.73
#   mass = 149 - wind^2 * 0.02  (DINAMIS berdasarkan wind!)
#   dist_internal = dist_30parts / 3.75
# Default G & M untuk ICO engine
ICO_DEFAULT_G = 0.677
ICO_DEFAULT_M = 105.6

# Fork/TimeBomb: pakai T-preset (time of flight), angle dihitung dinamis.
# SkyBomb/Choose: pakai angle-preset, power dihitung dinamis.
# ═══════════════════════════════════════════════════════════════
TURTLE_G     = 0.73
TURTLE_PARTS = 30
PIXELS_PER_PART_TURTLE_W = SCREEN_WIDTH_PIXELS  / TURTLE_PARTS   # 26.667
PIXELS_PER_PART_TURTLE_H = SCREEN_HEIGHT_PIXELS / TURTLE_PARTS   # 20.0
TURTLE_DIST_FACTOR = 3.75   # konversi 30-parts ke unit internal TORTUGA

# T-preset (time of flight) dari TORTUGA.xlsx untuk tiap shot
TURTLE_T_FORK4    = 2.665
TURTLE_T_FORK5    = 3.37
TURTLE_T_FORK6    = 4.24
TURTLE_T_CONNECT  = 6.18   # Fork 7 di TORTUGA = "Connect" di overlay
TURTLE_T_TIMEBOMB = 4.98

# Overlay 1: Fork shots — format (label, T_preset, color)
TURTLE_OVERLAY1_T = [
    ("Fork 4",  TURTLE_T_FORK4,   "#4FC3F7"),
    ("Fork 5",  TURTLE_T_FORK5,   "#FFB74D"),
    ("Fork 6",  TURTLE_T_FORK6,   "#CE93D8"),
    ("Connect", TURTLE_T_CONNECT, "#6DBF5A"),
]

# Overlay 2 (CTRL): Choose angle-preset — format (label, angle_deg, color)
# SkyBomb sekarang dihitung Plan5 (terpisah), bukan di sini
TURTLE_OVERLAY2_SKY = []
# TimeBomb — format (label, T_or_angle, color); "→" menandai angle-preset
TURTLE_OVERLAY2_TIME_T = [
    ("TimeBomb", TURTLE_T_TIMEBOMB, "#64B5F6"),
]

# Warna aksen Turtle
TURTLE_COLOR_OV1  = "#4FC3F7"   # cyan header overlay 1
TURTLE_COLOR_OV2  = "#F06292"   # pink header overlay 2


def _turtle_mass(wind: float) -> float:
    """Mass Turtle bergantung wind: 149 - wind^2 * 0.02 (TORTUGA.xlsx)."""
    return 149.0 - wind * wind * 0.02


def calc_turtle_by_T(dist_30parts: float, desnivel_30parts: float,
                     fator: float, wind: float, T: float,
                     g: float = None, m: float = None):
    """
    Hitung angle dari T-preset (Turtle), power pakai turtle engine.
    """
    dist = dist_30parts / TURTLE_DIST_FACTOR
    c18  = desnivel_30parts / TURTLE_DIST_FACTOR

    if g is None: g = TURTLE_G
    mass = _turtle_mass(wind) if m is None else m

    wind_x   = cos(radians(fator)) * wind
    wind_y   = sin(radians(fator)) * wind
    g_eff    = g - wind_y / mass
    wind_eff = wind_x / mass

    denom_tan = dist - wind_eff / 2.0 * T ** 2
    if denom_tan == 0 or T == 0:
        return None, None
    tan_angle = (c18 + g_eff / 2.0 * T ** 2) / denom_tan
    angle_out = degrees(atan(tan_angle))
    cos_a = cos(radians(angle_out))
    if cos_a == 0:
        return None, None
    power = (dist - 0.5 * wind_eff * T ** 2) / (cos_a * T)
    return round(angle_out, 3), round(max(0.0, min(power, POWER_BAR_MAX)), 3)


def calc_turtle_by_angle(dist_30parts: float, desnivel_30parts: float,
                         fator: float, wind: float, angle: float,
                         g: float = None, m: float = None):
    """
    Hitung power Turtle pakai angle dari OCR, turtle engine.
    """
    dist = dist_30parts / TURTLE_DIST_FACTOR
    c18  = desnivel_30parts / TURTLE_DIST_FACTOR

    if g is None: g = TURTLE_G
    mass = _turtle_mass(wind) if m is None else m

    wind_x   = cos(radians(fator)) * wind
    wind_y   = sin(radians(fator)) * wind
    g_eff    = g - wind_y / mass
    wind_eff = wind_x / mass
    cos_a = cos(radians(angle))
    sin_a = sin(radians(angle))
    E76   = dist - c18 * tan(radians(90.0 - angle))
    denom = (2.0 * cos_a * sin_a) / g_eff + (2.0 * wind_eff * sin_a ** 2) / (g_eff ** 2)
    if denom <= 0 or E76 <= 0:
        return angle, 0.0
    E77   = sqrt(E76 / denom)
    E79   = E77 * sin_a
    T     = (2.0 * E79) / g_eff
    if T == 0 or cos_a == 0:
        return angle, 0.0
    power = (dist - 0.5 * wind_eff * T ** 2) / (cos_a * T)
    return round(angle, 3), round(max(0.0, min(power, POWER_BAR_MAX)), 3)



def calc_plan5_skybomb(dist_30parts: float, fator: float, wind: float) -> tuple:
    """
    Hitung SkyBomb angle+power pakai Plan5 engine.
    Plan5: g=390, mass=0.254, T=4.1, dist=pixel, power_bar=raw*0.004332712+0.32
    Plan5 E6 = turtle!B3 = FATOR (effective), bukan wind_dir.
    Height TIDAK dipakai (Plan5 B19 numerator=0).
    Return: (angle_deg, power_bar).
    """
    PLAN5_G    = 390.0
    PLAN5_MASS = 0.254
    PLAN5_T    = 4.1
    PLAN5_CONV = 0.004332712
    PLAN5_OFF  = 0.32

    B6  = 30
    B18 = (800.0 / B6) * dist_30parts   # dist dalam pixel

    if wind == 0:
        D20, D21 = 0.0, PLAN5_G
    else:
        # Plan5 E6=fator (turtle!B3), B14=IF(COS(fator)==1, wind, wind-1)
        E14 = cos(radians(fator))
        B14 = wind if E14 == 1 else wind - 1
        D20 = (cos(radians(fator)) * B14) / PLAN5_MASS
        D21 = PLAN5_G - (sin(radians(fator)) * B14) / PLAN5_MASS

    T   = PLAN5_T
    den = B18 - 0.5 * D20 * T ** 2
    if den <= 0:
        return None, None
    angle = degrees(atan(0.5 * D21 * T ** 2 / den))
    cos_a = cos(radians(angle))
    if cos_a == 0:
        return None, None
    pw_raw = (B18 - 0.5 * D20 * T ** 2) / (cos_a * T)
    pw_bar = pw_raw * PLAN5_CONV + PLAN5_OFF
    return round(angle, 3), round(max(0.0, min(pw_bar, POWER_BAR_MAX)), 3)

def calc_turtle_overlay2(dist_30parts: float, desnivel_30parts: float,
                         fator: float, wind: float,
                         g: float = ICO_DEFAULT_G, m: float = ICO_DEFAULT_M) -> list:
    """
    Hitung overlay 2: Plan5 SkyBomb + Choose angle-preset + TimeBomb.
    wind_dir: arah angin asli game (untuk Plan5 SkyBomb).
    Return: [(label, angle, power, color), ...]
    """
    results = []
    # ── SkyBomb: Plan5 engine (dinamis, bukan hardcoded) ──
    ang_sky, pw_sky = calc_plan5_skybomb(dist_30parts, fator, wind)
    if ang_sky is None:
        ang_sky, pw_sky = 0.0, 0.0
    results.append(("Sky★P5",  ang_sky, pw_sky, "#F06292"))
    # ── Choose angle-preset (ICO engine) ──
    for label, angle, color in TURTLE_OVERLAY2_SKY:
        actual_angle = float(label.split("→")[1]) if "→" in label else angle
        ang, pw = calc_turtle_by_angle(dist_30parts, desnivel_30parts, fator, wind, actual_angle, g, m)
        results.append((label, ang, pw, color))
    # ── TimeBomb (ICO engine) ──
    for label, val, color in TURTLE_OVERLAY2_TIME_T:
        if "→" in label:
            ang, pw = calc_turtle_by_angle(dist_30parts, desnivel_30parts,
                                           fator, wind, float(label.split("→")[1]), g, m)
        else:
            ang, pw = calc_turtle_by_T(dist_30parts, desnivel_30parts, fator, wind, val, g, m)
            if ang is None:
                ang, pw = 0.0, 0.0
        results.append((label, ang, pw, color))
    return results


def calc_turtle_set(dist_30parts: float, desnivel_30parts: float,
                    fator: float, wind: float,
                    shot_list: list,
                    g: float = ICO_DEFAULT_G, m: float = ICO_DEFAULT_M) -> list:
    """
    Wrapper untuk overlay 1 (T-preset list).
    shot_list: [(label, T_preset, color), ...]
    Return: [(label, angle, power, color), ...]
    """
    results = []
    for label, T, color in shot_list:
        ang, pw = calc_turtle_by_T(dist_30parts, desnivel_30parts, fator, wind, T, g, m)
        if ang is None:
            ang, pw = 0.0, 0.0
        results.append((label, ang, pw, color))
    return results


# ─── Peta engine per mobile ───────────────────────────────────
# "ico" = ICO engine: rumus Trico tanpa spin, G & M bisa diatur bebas
MOBILE_ENGINE = {
    "Ice":       "ice",
    "Trico":     "trico",
    "JD":        "ice",
    "Aduka":     "ice",
    "Turtle":    "turtle",
    "Armor":     "ico",
    "Mage":      "ico",
    "Lightning": "ico",
    "Grub":      "ico",
    "Kalsiddon": "ico",
    "ASate":     "ico",
    "Knight":    "ico",
    "Raon":      "ico",
    "Nak":       "ico",
    "BigFoot":   "ico",
    "Boomer":    "ico",
    "JFrog":     "ico",
}

# ─── Offset titik awal kurva per mobile (pixel) ───────────────
# Adjust x dan y sampai pangkal kurva tepat di ujung laras
# x: + = kanan, - = kiri (relatif ke arah tembak)
# y: + = bawah, - = atas
MOBILE_BARREL_OFFSET = {
    "Ice":       (0,  0),
    "JD":        (0,  0),
    "Aduka":     (0,  0),   # Aduka pakai T2, offset ini tidak dipakai
    "Nak":       (0,  0),   # Nak pakai T2, offset ini tidak dipakai
    "Trico":     (0,  0),
    "Turtle":    (0,  0),
    "Armor":     (0,  0),
    "Mage":      (0,  0),
    "Lightning": (0,  0),
    "Grub":      (0,  0),
    "Kalsiddon": (0,  0),
    "ASate":     (0,  0),
    "Knight":    (0,  0),
    "Raon":      (0,  0),
    "BigFoot":   (0,  0),
    "Boomer":    (0,  0),
    "JFrog":     (0,  0),
}


# ═══════════════════════════════════════════════════════════════
# ICE ENGINE
# ═══════════════════════════════════════════════════════════════
def calc_power_ice(distance: float, desnivel: float,
                   fator: float, wind: float, angle: float,
                   g: float = DEFAULT_GRAVEDAD,
                   m: float = DEFAULT_MASA) -> float:
    wind_cos = cos(radians(fator)) * wind
    wind_sin = sin(radians(fator)) * wind
    c46 = g - wind_sin / m
    c45 = wind_cos / m
    altura = desnivel
    cos_a = cos(radians(angle))
    sin_a = sin(radians(angle))
    d44 = distance - altura * tan(radians(90.0 - angle))
    denom = (2.0 * cos_a * sin_a) / c46 + (2.0 * c45 * sin_a ** 2) / (c46 ** 2)
    if denom == 0 or d44 == 0:
        return 0.0
    if (d44 / denom) < 0:
        return 0.0
    d45 = sqrt(d44 / denom)
    d47 = d45 * sin_a
    d48 = (2.0 * d47) / c46
    b45_denom = distance - c45 / 2.0 * d48 ** 2
    if b45_denom == 0 or d48 == 0:
        return 0.0
    b45    = (altura + c46 / 2.0 * d48 ** 2) / b45_denom
    b46    = degrees(atan(b45))
    cos_b46 = cos(radians(b46))
    if cos_b46 == 0:
        return 0.0
    return (distance - 0.5 * c45 * d48 ** 2) / (cos_b46 * d48)


# ═══════════════════════════════════════════════════════════════
# ICO ENGINE — Trico physics tanpa spin, G & M bebas diatur
# Rumus identik dengan ICE engine, tapi G & M diambil dari
# mobile_constants.txt (bisa dikalibrasi sendiri per mobile)
# ═══════════════════════════════════════════════════════════════
def calc_power_ico(distance: float, desnivel: float,
                   fator: float, wind: float, angle: float,
                   g: float, m: float) -> float:
    wind_cos = cos(radians(fator)) * wind
    wind_sin = sin(radians(fator)) * wind
    g_eff = g - wind_sin / m      # gravitasi efektif terkoreksi angin vertikal
    a_w   = wind_cos / m          # akselerasi horizontal dari angin
    cos_a = cos(radians(angle))
    sin_a = sin(radians(angle))
    d44 = distance - desnivel * tan(radians(90.0 - angle))
    denom = (2.0 * cos_a * sin_a) / g_eff + (2.0 * a_w * sin_a ** 2) / (g_eff ** 2)
    if denom == 0 or d44 == 0:
        return 0.0
    if (d44 / denom) < 0:
        return 0.0
    d45 = sqrt(d44 / denom)
    d47 = d45 * sin_a
    T   = (2.0 * d47) / g_eff    # time of flight analitik
    b45_denom = distance - a_w / 2.0 * T ** 2
    if b45_denom == 0 or T == 0:
        return 0.0
    b45     = (desnivel + g_eff / 2.0 * T ** 2) / b45_denom
    b46     = degrees(atan(b45))
    cos_b46 = cos(radians(b46))
    if cos_b46 == 0:
        return 0.0
    return (distance - 0.5 * a_w * T ** 2) / (cos_b46 * T)


# ═══════════════════════════════════════════════════════════════
# TRICO ENGINE
# ═══════════════════════════════════════════════════════════════
_TRICO_WIND_TABLE = [
    (0,0),(1,0),(2,1.1),(3,0.4),(4,3.5),(5,4.4),(6,5.1),(7,6.4),
    (8,7.4),(9,8.7),(10,9.5),(11,10.8),(12,11.9),(13,12.7),(14,13.8),
    (15,15.1),(16,15.8),(17,17.2),(18,18.3),(19,18.9),(20,20.4),
    (21,21.6),(22,22.5),(23,23.2),(24,24.8),(25,25.9),(26,26.5),
]
_T_SPIN1 = [
    (1.0,4.28),(1.25,4.28),(1.5,3.94516),(1.75,3.8888),(2.0,3.79605),
    (2.5,3.62789),(3.0,3.500389),(3.5,3.45816),(4.0,3.3),(4.5,3.20534),
    (5.0,3.0073),(5.5,2.6825),(6.0,2.59081),(6.5,2.52952),(7.0,2.50803),
    (7.5,2.470333),(8.0,2.45167),(8.5,2.4204),(9.0,2.41),(9.5,2.4),
    (10.0,2.4),(10.5,2.39),
]
_T_SPIN2 = [
    (-5.0,6.6),(-4.0,6.64),(-3.0,6.66),(-2.0,6.68),(-1.0,6.69899),
    (0.0,6.69899),(0.5,6.65289),(1.0,6.60801),(1.5,6.56905),(2.0,6.55108),
    (2.5,6.50744),(3.0,6.38468),(3.5,6.30844),(4.0,6.24688),(4.5,6.17333),
    (5.0,6.16468),(5.5,6.18695),(6.0,6.12046),(6.5,6.05818),(7.0,5.99844),
    (7.5,5.8769),(8.0,5.885),(8.5,5.823606),(9.0,5.764311),(9.5,5.703603),
    (10.0,5.641059),(10.5,5.626185),(11.0,5.606823),(11.5,5.534493),
    (12.0,5.459355),(12.5,5.475447),(13.0,5.487208),(13.5,5.399736),
    (14.0,5.308666),(14.5,5.307422),(15.0,5.302335),(15.5,5.293494),
    (16.0,5.28098),
]
_T_SPIN3 = [
    (-9.0,8.92),(-8.0,8.96),(-7.0,9.02),(-6.0,9.02),(-5.0,9.02),
    (-4.0,9.05),(-3.0,9.04),(-2.0,9.03),(-1.0,9.04),(0.0,9.0),
    (0.5,8.98),(1.0,8.96),(1.5,8.94),(2.0,8.92),(2.5,8.9),
    (3.0,8.88),(3.5,8.86),(4.0,8.84),(4.5,8.82),(5.0,8.81),
    (5.5,8.8),(6.0,8.795),(6.5,8.79),(7.0,8.78),(7.5,8.77),
    (8.0,8.7666),(8.5,8.71),(9.0,8.67051),(9.5,8.62),(10.0,8.58586),
    (10.5,8.54),(11.0,8.50815),(11.5,8.53),(12.0,8.56401),(12.5,8.46),
    (13.0,8.3628),(13.5,8.32),(14.0,8.22),(14.5,8.25),(15.0,8.22016),
    (15.5,8.18),(16.0,8.14727),(16.5,8.095),(17.0,8.05),(17.5,8.0),
    (18.0,7.96),(18.5,7.91),(19.0,7.86),(19.5,7.81),(20.0,7.76),
]
_T_SPIN2B = [
    (-4.0,5.22),(-3.0,5.32),(-2.0,5.36),(-1.0,5.37),(0.0,5.36554),
    (0.5,5.345),(1.0,5.32408),(1.5,5.27),(2.0,5.22562),(2.5,5.16),
    (3.0,5.1),(3.5,5.04),(4.0,4.99589),(4.5,4.86),(5.0,4.74591),
    (5.5,4.7),(6.0,4.65),(6.5,4.6),(7.0,4.55),(7.5,4.5),
    (8.0,4.45449),(8.5,4.35),(9.0,4.25304),(9.5,4.17),(10.0,4.09529),
    (10.5,4.03),(11.0,3.97883),(11.5,3.934),(12.0,3.90931),(12.5,3.865),
    (13.0,3.83),(13.5,3.8),(14.0,3.77278),(14.5,3.73),(15.0,3.7),
]
_T_SPIN3B = [
    (-6.0,7.842),(-5.0,7.882),(-4.0,7.902),(-3.0,7.93),(-2.0,7.96),
    (-1.0,7.962),(0.0,7.962),(0.5,7.89699),(1.0,7.87776),(1.5,7.8635),
    (2.0,7.85416),(2.5,7.83209),(3.0,7.80325),(3.5,7.76773),(4.0,7.73418),
    (4.5,7.70346),(5.0,7.67264),(5.5,7.63833),(6.0,7.59268),(6.5,7.548475),
    (7.0,7.493191),(7.5,7.442112),(8.0,7.406419),(8.5,7.32896),(9.0,7.3038),
    (9.5,7.2517),(10.0,7.20534),(10.5,7.18698),(11.0,7.166716),(11.5,7.159454),
    (12.0,7.152),(12.5,7.1371),(13.0,7.108608),(13.5,7.078348),(14.0,7.033237),
    (14.5,6.935934),(15.0,6.827754),(15.5,6.780937),(16.0,6.772),
]
_TRICO_SPIN_CFG = {
    "1":  (_T_SPIN1,  0.987),
    "2":  (_T_SPIN2,  1.0),
    "3":  (_T_SPIN3,  1.0),
    "2b": (_T_SPIN2B, 0.99),
    "3b": (_T_SPIN3B, 1.0),
    "4":  (_T_SPIN3B, 1.0),
}

def _trico_vlookup(val: float, table: list) -> float:
    keys = [r[0] for r in table]
    i    = bisect.bisect_right(keys, val) - 1
    i    = max(0, min(i, len(table) - 1))
    return table[i][1]

def calc_trico(dist, desnivel, fator, wind, spin_key):
    G, M = 0.835, 124.0
    W_corr = _trico_vlookup(wind, _TRICO_WIND_TABLE)
    W_x    = cos(radians(fator)) * W_corr
    W_y    = sin(radians(fator)) * W_corr
    g_eff  = G - W_y / M
    a_w    = W_x / M
    table, mult = _TRICO_SPIN_CFG[spin_key]
    T = _trico_vlookup(dist, table)
    denom_b = dist - a_w / 2.0 * T ** 2
    if denom_b == 0 or T == 0:
        return None, None
    tan_b   = (desnivel + g_eff / 2.0 * T ** 2) / denom_b
    angle_r = degrees(atan(tan_b))
    cos_b   = cos(radians(angle_r))
    if cos_b == 0:
        return None, None
    power = (dist - 0.5 * a_w * T ** 2) / (cos_b * T)
    power *= mult
    if spin_key == "4":
        ang3b, pw3b = calc_trico(dist, desnivel, fator, wind, "3b")
        ang3,  pw3  = calc_trico(dist, desnivel, fator, wind, "3")
        ang2,  pw2  = calc_trico(dist, desnivel, fator, wind, "2")
        if ang3b is not None and ang3 is not None and pw2 is not None:
            delta_ang = ang3  - ang3b
            delta_pw  = pw3   - pw2
            power     = pw3b + delta_pw
            angle_r   = ang3b + delta_ang
            return round(angle_r, 1), round(power, 3)
    power = min(power, POWER_BAR_MAX)
    return round(angle_r, 1), round(power, 3)

def calc_trico_set(dist, desnivel, fator, wind, spin_keys):
    results = []
    label_map = {"1":"1 spin","2":"2 spin","3":"3 spin",
                 "2b":"2 spin","3b":"3 spin","4":"4 spin"}
    for sk in spin_keys:
        ang, pw = calc_trico(dist, desnivel, fator, wind, sk)
        if ang is not None:
            results.append((label_map.get(sk, sk), ang, pw))
    return results


# ═══════════════════════════════════════════════════════════════
# TRAJECTORY PATH COMPUTATION — untuk render jalur peluru di overlay
# Menggunakan koordinat pixel game (bukan parts), output list of (x,y) pixel
# dt kecil → kurva halus, tapi tetap render pakai line segments pendek
# ═══════════════════════════════════════════════════════════════

def compute_trajectory_ice(src_px: float, src_py: float,
                            dist_px: float, desn_px: float,
                            fator: float, wind: float,
                            angle_deg: float,
                            g: float, m: float) -> list:
    """
    Hitung jalur peluru ICE engine dalam koordinat pixel overlay.
    Simulasi dilakukan dalam satuan "parts" (sama dengan calc_power_ice),
    lalu di-scale ke pixel untuk render.
    src_px, src_py : posisi source di overlay canvas (pixel)
    dist_px        : jarak horizontal ke target dalam pixel
    desn_px        : beda ketinggian src-tgt dalam pixel (positif = target lebih rendah)
    Return: list of (canvas_x, canvas_y)
    """
    from math import cos as _c, sin as _s, atan as _a, sqrt as _sq, radians as _r, degrees as _d, tan as _t

    # Konversi ke satuan parts (sama seperti _get_power_inputs)
    distance = dist_px / PIXELS_PER_PART_WIDTH
    desnivel = desn_px / PIXELS_PER_PART_HEIGHT

    wind_cos = _c(_r(fator)) * wind
    wind_sin = _s(_r(fator)) * wind
    c46 = g - wind_sin / m     # g_eff
    c45 = wind_cos / m         # wind_eff horizontal

    cos_a = _c(_r(angle_deg))
    sin_a = _s(_r(angle_deg))
    if sin_a == 0 or c46 == 0:
        return []

    altura = desnivel
    d44 = distance - altura * _t(_r(90.0 - angle_deg))
    denom = (2.0 * cos_a * sin_a) / c46 + (2.0 * c45 * sin_a**2) / (c46**2)
    if denom == 0 or d44 == 0:
        return []
    if (d44 / denom) < 0:
        return []

    d45 = _sq(d44 / denom)
    d47 = d45 * sin_a
    d48 = (2.0 * d47) / c46    # time of flight

    b45_d = distance - c45 / 2.0 * d48**2
    if b45_d == 0 or d48 == 0:
        return []
    b45 = (altura + c46 / 2.0 * d48**2) / b45_d
    b46 = _d(_a(b45))
    cos_b46 = _c(_r(b46))
    if cos_b46 == 0:
        return []
    power = (distance - 0.5 * c45 * d48**2) / (cos_b46 * d48)

    # Simulasi dalam satuan parts, dt dalam T-unit
    dt = 0.02
    vx = power * _c(_r(b46))
    vy = power * _s(_r(b46))

    # Scale parts → pixel untuk render
    sx = PIXELS_PER_PART_WIDTH
    sy = PIXELS_PER_PART_HEIGHT

    pts = []
    x, y = 0.0, 0.0   # dalam satuan parts
    for _ in range(5000):
        # Konversi ke pixel overlay: x ke kanan, y ke atas (screen y terbalik)
        pts.append((src_px + x * sx, src_py - y * sy))
        vx += c45 * dt
        vy -= c46 * dt
        x  += vx * dt
        y  += vy * dt
        if x > distance * 1.5 or y < -(desnivel + 30):
            pts.append((src_px + x * sx, src_py - y * sy))
            break
    return pts


def compute_trajectory_turtle(src_px: float, src_py: float,
                               dist_px: float, desn_px: float,
                               fator: float, wind: float,
                               angle_deg: float) -> list:
    """
    Hitung jalur peluru Turtle engine dalam koordinat pixel overlay.
    Pakai G=TURTLE_G dan mass dinamis seperti calc_turtle_by_angle.
    """
    from math import cos as _c, sin as _s, atan as _a, sqrt as _sq, radians as _r, degrees as _d, tan as _t

    g    = TURTLE_G
    mass = _turtle_mass(wind)

    distance = dist_px / PIXELS_PER_PART_WIDTH
    desnivel = desn_px / PIXELS_PER_PART_HEIGHT

    wind_cos = _c(_r(fator)) * wind
    wind_sin = _s(_r(fator)) * wind
    g_eff    = g - wind_sin / mass
    wind_eff = wind_cos / mass

    cos_a = _c(_r(angle_deg))
    sin_a = _s(_r(angle_deg))
    if sin_a == 0 or g_eff == 0:
        return []

    E76   = distance - desnivel * _t(_r(90.0 - angle_deg))
    denom = (2.0 * cos_a * sin_a) / g_eff + (2.0 * wind_eff * sin_a**2) / (g_eff**2)
    if denom <= 0 or E76 <= 0:
        return []

    E77 = _sq(E76 / denom)
    E79 = E77 * sin_a
    T   = (2.0 * E79) / g_eff
    if T == 0 or cos_a == 0:
        return []
    power = (distance - 0.5 * wind_eff * T**2) / (cos_a * T)

    dt = 0.02
    vx = power * cos_a
    vy = power * sin_a

    sx = PIXELS_PER_PART_WIDTH
    sy = PIXELS_PER_PART_HEIGHT

    pts = []
    x, y = 0.0, 0.0
    for _ in range(5000):
        pts.append((src_px + x * sx, src_py - y * sy))
        vx += wind_eff * dt
        vy -= g_eff * dt
        x  += vx * dt
        y  += vy * dt
        if x > distance * 1.5 or y < -(desnivel + 30):
            pts.append((src_px + x * sx, src_py - y * sy))
            break
    return pts


def compute_trajectory_trico(src_px: float, src_py: float,
                              dist_px: float, desn_px: float,
                              fator: float, wind: float,
                              spin_key: str) -> list:
    """
    Hitung jalur peluru TRICO engine dalam koordinat pixel overlay.
    Simulasi dalam satuan parts, output di-scale ke pixel.
    """
    from math import cos as _c, sin as _s, atan as _a, radians as _r

    G, M = 0.835, 124.0
    W_corr = _trico_vlookup(wind, _TRICO_WIND_TABLE)
    Wx = _c(_r(fator)) * W_corr
    Wy = _s(_r(fator)) * W_corr
    g_eff = G - Wy / M
    a_w   = Wx / M

    dist_parts = dist_px / PIXELS_PER_PART_WIDTH
    desn_parts = desn_px / PIXELS_PER_PART_HEIGHT

    table, mult = _TRICO_SPIN_CFG[spin_key]
    T = _trico_vlookup(dist_parts, table)

    denom_b = dist_parts - a_w / 2.0 * T**2
    if denom_b == 0 or T == 0:
        return []
    tan_b   = (desn_parts + g_eff / 2.0 * T**2) / denom_b
    angle_r = _a(tan_b)
    cos_b   = _c(angle_r)
    if cos_b == 0:
        return []

    power = (dist_parts - 0.5 * a_w * T**2) / (cos_b * T)
    power *= mult
    power = min(max(power, 0.0), POWER_BAR_MAX)

    dt = 0.02
    vx = power * cos_b
    vy = power * _s(angle_r)

    sx = PIXELS_PER_PART_WIDTH
    sy = PIXELS_PER_PART_HEIGHT

    pts = []
    x, y = 0.0, 0.0
    for _ in range(5000):
        pts.append((src_px + x * sx, src_py - y * sy))
        vx += a_w * dt
        vy -= g_eff * dt
        x  += vx * dt
        y  += vy * dt
        if x > dist_parts * 1.5 or y < -(desn_parts + 30):
            pts.append((src_px + x * sx, src_py - y * sy))
            break
    return pts


# ─── Enums ────────────────────────────────────────────────────
class CartFacingDirection(IntEnum):
    Left  = 0
    Right = 1

class Mobile(IntEnum):
    Armor=0; Mage=1; Nak=2; Trico=3; BigFoot=4; Boomer=5
    Raon=6; Lightning=7; JD=8; ASate=9; Ice=10; Turtle=11
    Grub=12; Aduka=13; Knight=13; Kalsiddon=14; JFrog=15
    Dragon=15; Random=255

MOBILE_ID_TO_NAME = {
    0:"Armor", 1:"Mage", 2:"Nak", 3:"Trico", 4:"BigFoot",
    5:"Boomer", 6:"Raon", 7:"Lightning", 8:"JD", 9:"ASate",
    10:"Ice", 11:"Turtle", 12:"Grub", 13:"Aduka", 14:"Kalsiddon",
    15:"JFrog", 255:"Random"
}


# ─── Custom Widgets ───────────────────────────────────────────
class ToggleSwitch(tk.Canvas):
    def __init__(self, parent, variable, command=None, **kw):
        super().__init__(parent, width=44, height=22,
                         highlightthickness=0, cursor="hand2", **kw)
        self.var = variable; self._cmd = command
        self._draw()
        self.bind("<Button-1>", self._toggle)

    def _draw(self):
        self.delete("all")
        on = self.var.get()
        self.config(bg=self["bg"])
        track = ACCENT if on else "#252718"
        self.create_rounded_rect(1,1,43,21,10, fill=track,
                                 outline="#363820" if not on else "")
        kx = 32 if on else 12
        self.create_oval(kx-9,2,kx+9,20,
                         fill=TEXT_MAIN if on else "#424535", outline="")

    def create_rounded_rect(self, x1,y1,x2,y2,r,**kw):
        pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2,
               x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
        return self.create_polygon(pts, smooth=True, **kw)

    def _toggle(self, e=None):
        self.var.set(1 - self.var.get()); self._draw()
        if self._cmd: self._cmd()


class StatCard(tk.Frame):
    def __init__(self, parent, label, initial="-", color=TEXT_MAIN, **kw):
        super().__init__(parent, bg=BG_CARD, padx=10, pady=6, **kw)
        tk.Label(self, text=label, bg=BG_CARD, fg=TEXT_DIM,
                 font=("Courier", 7, "bold")).pack(anchor="w")
        self.val_var = tk.StringVar(value=initial)
        self.val_lbl = tk.Label(self, textvariable=self.val_var, bg=BG_CARD,
                                fg=color, font=("Courier", 13, "bold"))
        self.val_lbl.pack(anchor="w")

    def set(self, text, color=None):
        self.val_var.set(text)
        if color: self.val_lbl.config(fg=color)


# ═══════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════
class GunboundPowerCalculator:
    def __init__(self):
        self.pm                  = None
        self.running             = False
        self.base_address        = None
        self.locked_target_index = None
        self.root = self.overlay = self.canvas = None
        self.source_index = self.target_index  = None
        self.shot_counter     = 0
        self.current_power    = None
        self.current_angle    = 60.0
        self.prev_frame       = None
        self.last_valid_angle = None

        self.ocr_x = 218; self.ocr_y = 529
        self.ocr_w = 60;  self.ocr_h = 20
        self._ocr_drag_start = self._ocr_drag_origin = self._ocr_drag_mode = None
        self.debug_enabled = False

        self.mobile_db           = load_mobile_constants()
        self.active_mobile_name  = "Ice"
        self.active_gravedad     = DEFAULT_GRAVEDAD
        self.active_masa         = DEFAULT_MASA
        self._last_mobile_loaded = None

        # Load barrel offsets dan apply ke MOBILE_BARREL_OFFSET
        _saved_offsets = load_barrel_offsets()
        for mob, (x, y) in _saved_offsets.items():
            if mob in MOBILE_BARREL_OFFSET:
                MOBILE_BARREL_OFFSET[mob] = (x, y)

        # Mouse target mode
        self.mouse_target_mode     = False
        self.mouse_target_game_pos = None

        # Manual mobile override
        self.manual_mobile_override = False
        self.manual_mobile_name     = "Ice"

        # Player lock dengan relative offset
        self.player_lock_offset_x   = 0
        self.player_lock_offset_y   = 0
        self.player_lock_facing_ref = None

        self.is_trico            = False
        self.trico_spin_mode     = 0
        self.trico_results       = []

        # Turtle state
        self.is_turtle           = False
        self.turtle_overlay_mode = 0
        self.turtle_ov1_results  = []
        self.turtle_ov2_results  = []

        # Overlay visibility
        self.overlay_visible        = True
        self.overlay_canvas_visible = True
        self.turtle_panel_visible   = True

        self._build_gui()

    # ─── GUI ──────────────────────────────────────────────────
    def _build_gui(self):
        try:
            self.root = tk.Tk()
            self.root.title("ICE PRO 8 PART")
            self.root.geometry("330x940")
            self.root.resizable(False, False)
            self.root.configure(bg=BG_DARK)

            tk.Frame(self.root, bg=ACCENT3, height=2).pack(fill="x")
            hdr = tk.Frame(self.root, bg=BG_PANEL, pady=10)
            hdr.pack(fill="x")
            tk.Label(hdr, text="[ ICE AIMBOT ]", bg=BG_PANEL, fg=ACCENT,
                     font=("Courier", 15, "bold")).pack()
            tk.Label(hdr, text="ICE PRO  //  8 PARTS  //  BALLISTIC CALC",
                     bg=BG_PANEL, fg=TEXT_DIM, font=("Courier", 7)).pack()
            tk.Frame(self.root, bg=ACCENT, height=1).pack(fill="x")

            body = tk.Frame(self.root, bg=BG_DARK)
            body.pack(fill="both", expand=True, padx=12, pady=8)

            self.status_var = tk.StringVar(value="DISCONNECTED")
            sr = tk.Frame(body, bg=BG_CARD, pady=6, padx=10)
            sr.pack(fill="x", pady=(0,6))
            tk.Label(sr, text="// STATUS", bg=BG_CARD, fg=TEXT_DIM,
                     font=("Courier", 7, "bold")).pack(side="left")
            self.status_lbl = tk.Label(sr, textvariable=self.status_var,
                                        bg=BG_CARD, fg=ACCENT2,
                                        font=("Courier", 9, "bold"))
            self.status_lbl.pack(side="right")

            grid = tk.Frame(body, bg=BG_DARK)
            grid.pack(fill="x", pady=(0,6))
            self.wind_card   = StatCard(grid, "ANGIN",  color=ACCENT)
            self.mobile_card = StatCard(grid, "MOBILE", color=ACCENT3)
            self.player_card = StatCard(grid, "PLAYER", color=TEXT_MAIN)
            self.dist_card   = StatCard(grid, "JARAK",  color=SUCCESS)
            self.angle_card  = StatCard(grid, "SUDUT",  color=ACCENT3)
            self.power_card  = StatCard(grid, "POWER",  color=ACCENT2)
            for i, c in enumerate([self.wind_card, self.mobile_card, self.player_card,
                                    self.dist_card, self.angle_card, self.power_card]):
                c.grid(row=i//2, column=i%2, sticky="ew", padx=2, pady=2)
            grid.columnconfigure(0, weight=1)
            grid.columnconfigure(1, weight=1)

            idx_frame = tk.Frame(body, bg=BG_CARD, pady=8, padx=10)
            idx_frame.pack(fill="x", pady=(0,6))
            self.source_index = tk.IntVar(value=0)
            self.target_index = tk.IntVar(value=1)

            def _idx_row(parent, label, var):
                row = tk.Frame(parent, bg=BG_CARD)
                row.pack(fill="x", pady=2)
                tk.Label(row, text=label, bg=BG_CARD, fg=TEXT_DIM,
                         font=("Courier", 8), width=14, anchor="w").pack(side="left")
                tk.Entry(row, textvariable=var, width=4,
                         bg=BG_DARK, fg=ACCENT, insertbackground=ACCENT,
                         relief="flat", font=("Courier", 11, "bold"),
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=ACCENT).pack(side="left")

            _idx_row(idx_frame, "SRC IDX", self.source_index)
            _idx_row(idx_frame, "TGT IDX", self.target_index)

            # ── Manual Mobile Selector ────────────────────────
            mob_frame = tk.Frame(body, bg=BG_CARD, pady=8, padx=10)
            mob_frame.pack(fill="x", pady=(0,6))

            mob_hdr = tk.Frame(mob_frame, bg=BG_CARD)
            mob_hdr.pack(fill="x", pady=(0,6))
            tk.Label(mob_hdr, text=">> MOBILE MANUAL", bg=BG_CARD,
                     fg=TEXT_DIM, font=("Courier", 7, "bold")).pack(side="left")
            self.mob_override_var = tk.IntVar(value=0)
            self.mob_override_sw  = ToggleSwitch(mob_hdr, variable=self.mob_override_var,
                                                  command=self._on_mob_override_toggle,
                                                  bg=BG_CARD)
            self.mob_override_sw.pack(side="right")

            mob_sel_row = tk.Frame(mob_frame, bg=BG_CARD)
            mob_sel_row.pack(fill="x")

            import tkinter.ttk as ttk
            mobile_names = ["Armor","Mage","Nak","Trico","BigFoot","Boomer","Raon",
                            "Lightning","JD","ASate","Ice","Turtle","Grub","Aduka",
                            "Kalsiddon","JFrog"]
            self.mob_select_var = tk.StringVar(value="Ice")
            self.mob_combo = ttk.Combobox(
                mob_sel_row, textvariable=self.mob_select_var,
                values=mobile_names, state="disabled",
                font=("Courier", 9, "bold"), width=14)
            self.mob_combo.pack(side="left", padx=(0,6))
            self.mob_combo.bind("<<ComboboxSelected>>", self._on_mob_selected)

            self.mob_status_lbl = tk.Label(
                mob_sel_row, text="AUTO", bg=BG_CARD,
                fg=TEXT_DIM, font=("Courier", 7, "bold"))
            self.mob_status_lbl.pack(side="left")

            btn_row = tk.Frame(body, bg=BG_DARK)
            btn_row.pack(fill="x", pady=(0,6))

            def _btn(parent, text, cmd, color):
                b = tk.Button(parent, text=text, command=cmd,
                              bg=color, fg=BG_DARK, relief="flat",
                              font=("Courier", 9, "bold"),
                              activebackground=color, cursor="hand2",
                              padx=12, pady=7)
                b.pack(side="left", expand=True, fill="x", padx=2)
                return b

            self.toggle_btn = _btn(btn_row, ">> START", self.toggle_reading, SUCCESS)
            self.overlay_btn = _btn(btn_row, "[ OVL ON ]", self.toggle_overlay_visible, ACCENT)

            live_frame = tk.Frame(body, bg=BG_CARD, pady=5, padx=10)
            live_frame.pack(fill="x", pady=(0,6))
            live_left = tk.Frame(live_frame, bg=BG_CARD)
            live_left.pack(side="left")
            self.live_dot = tk.Label(live_left, text="●", bg=BG_CARD, fg=TEXT_DIM,
                                      font=("Courier", 10, "bold"))
            self.live_dot.pack(side="left")
            tk.Label(live_left, text=" POWER AUTO  //  real-time",
                     bg=BG_CARD, fg=TEXT_DIM, font=("Courier", 7)).pack(side="left")
            self.live_status = tk.Label(live_frame, text="WAITING", bg=BG_CARD,
                                         fg=TEXT_DIM, font=("Courier", 7, "bold"))
            self.live_status.pack(side="right")

            feat_frame = tk.Frame(body, bg=BG_CARD, pady=8, padx=10)
            feat_frame.pack(fill="x", pady=(0,6))
            self.debug_var          = tk.IntVar(value=0)
            self.reverse_facing_var = tk.IntVar(value=0)
            self.backshot_var       = tk.IntVar(value=0)
            self.tpl_angle_var      = tk.IntVar(value=1)
            self.templates          = {}

            def _toggle_row(parent, label, var, cmd, tip=""):
                row = tk.Frame(parent, bg=BG_CARD)
                row.pack(fill="x", pady=3)
                tk.Label(row, text=label, bg=BG_CARD, fg=TEXT_MAIN,
                         font=("Courier", 9), anchor="w").pack(side="left")
                if tip:
                    tk.Label(row, text=tip, bg=BG_CARD, fg=TEXT_DIM,
                             font=("Courier", 7)).pack(side="left", padx=4)
                sw = ToggleSwitch(row, variable=var, command=cmd, bg=BG_CARD)
                sw.pack(side="right")
                return sw

            _toggle_row(feat_frame, "[DBG]  Debug Log",      self.debug_var,
                        self._on_debug_toggle, tip="print + simpan crop")
            _toggle_row(feat_frame, "[BCK]  Backshot",       self.backshot_var,
                        lambda: None, tip="sudut negatif")
            _toggle_row(feat_frame, "[TPL]  Template Match", self.tpl_angle_var,
                        self._on_tpl_toggle, tip="captured_numbers/")

            const_frame = tk.Frame(body, bg=BG_CARD, pady=8, padx=10)
            const_frame.pack(fill="x", pady=(0,6))
            const_hdr = tk.Frame(const_frame, bg=BG_CARD)
            const_hdr.pack(fill="x", pady=(0,6))
            tk.Label(const_hdr, text=">> PHYSICS CONSTANTS", bg=BG_CARD,
                     fg=TEXT_DIM, font=("Courier", 7, "bold")).pack(side="left")
            self.const_mobile_lbl = tk.Label(const_hdr, text="[ Ice ]",
                                              bg=BG_CARD, fg=ACCENT,
                                              font=("Courier", 7, "bold"))
            self.const_mobile_lbl.pack(side="left", padx=6)
            self.const_engine_lbl = tk.Label(const_hdr, text="",
                                              bg=BG_CARD, fg=TEXT_DIM,
                                              font=("Courier", 7))
            self.const_engine_lbl.pack(side="right")

            entry_kw = dict(
                bg=BG_DARK, fg=ACCENT3, insertbackground=ACCENT3,
                relief="flat", font=("Courier", 10, "bold"), width=8,
                highlightthickness=1, highlightbackground=BORDER,
                highlightcolor=ACCENT3
            )

            def _const_slider_row(parent, label, var, from_, to, resolution):
                """Row dengan slider presisi + entry manual."""
                frame = tk.Frame(parent, bg=BG_CARD)
                frame.pack(fill="x", pady=3)
                tk.Label(frame, text=label, bg=BG_CARD, fg=TEXT_MAIN,
                         font=("Courier", 9), width=9, anchor="w").pack(side="left")
                # Entry manual
                e = tk.Entry(frame, textvariable=var, width=7,
                             bg=BG_DARK, fg=ACCENT3, insertbackground=ACCENT3,
                             font=("Courier", 9), relief="flat",
                             highlightthickness=1, highlightbackground=ACCENT2,
                             highlightcolor=ACCENT3)
                e.pack(side="right", padx=(4,0))
                # Slider
                dvar = tk.DoubleVar(value=float(var.get()))
                def _on_slider(v, _var=var, _dvar=dvar):
                    val = round(float(v), 4)
                    _var.set(str(val))
                def _on_entry(*args, _var=var, _dvar=dvar):
                    try:
                        _dvar.set(float(_var.get()))
                    except ValueError:
                        pass
                var.trace_add("write", _on_entry)
                sl = tk.Scale(frame, variable=dvar, from_=from_, to=to,
                              resolution=resolution, orient="horizontal",
                              bg=BG_CARD, fg=TEXT_MAIN, troughcolor=BG_DARK,
                              highlightthickness=0, showvalue=False,
                              sliderlength=10, length=120,
                              command=_on_slider)
                sl.pack(side="left", padx=(0,4))
                return e, sl, dvar

            self.gravedad_var = tk.StringVar(value=str(DEFAULT_GRAVEDAD))
            self.masa_var     = tk.StringVar(value=str(DEFAULT_MASA))

            _, self._g_slider, self._g_dvar = _const_slider_row(
                const_frame, "gravedad", self.gravedad_var, 0.3, 0.9, 0.001)
            _, self._m_slider, self._m_dvar = _const_slider_row(
                const_frame, "masa",     self.masa_var,     90.0, 200.0, 0.01)

            save_row = tk.Frame(const_frame, bg=BG_CARD)
            save_row.pack(fill="x", pady=(6,0))
            self.const_save_status = tk.Label(save_row, text="", bg=BG_CARD,
                                               fg=SUCCESS, font=("Courier", 7))
            self.const_save_status.pack(side="right")
            tk.Button(save_row, text=">> SAVE", command=self._save_constants,
                      bg=ACCENT, fg=BG_DARK, relief="flat",
                      font=("Courier", 8, "bold"), cursor="hand2",
                      padx=8, pady=3).pack(side="left")

            # ── Barrel Offset Panel ──────────────────────────────
            barrel_frame = tk.Frame(body, bg=BG_CARD, pady=8, padx=10)
            barrel_frame.pack(fill="x", pady=(0,6))

            barrel_hdr = tk.Frame(barrel_frame, bg=BG_CARD)
            barrel_hdr.pack(fill="x", pady=(0,6))
            tk.Label(barrel_hdr, text=">> BARREL OFFSET", bg=BG_CARD,
                     fg=TEXT_DIM, font=("Courier", 7, "bold")).pack(side="left")
            self.barrel_mobile_lbl = tk.Label(barrel_hdr, text=f"[ {self.active_mobile_name} ]",
                                               bg=BG_CARD, fg=ACCENT,
                                               font=("Courier", 7, "bold"))
            self.barrel_mobile_lbl.pack(side="left", padx=6)

            def _slider_row(parent, label, from_, to, var_name, init_val):
                row = tk.Frame(parent, bg=BG_CARD)
                row.pack(fill="x", pady=2)
                tk.Label(row, text=label, bg=BG_CARD, fg=TEXT_MAIN,
                         font=("Courier", 9), width=8, anchor="w").pack(side="left")
                val_lbl = tk.Label(row, text=f"{init_val:+d}", bg=BG_CARD,
                                   fg=ACCENT3, font=("Courier", 9, "bold"), width=4)
                val_lbl.pack(side="right")
                var = tk.IntVar(value=init_val)
                sl = tk.Scale(row, from_=from_, to=to, orient="horizontal",
                              variable=var, bg=BG_CARD, fg=TEXT_MAIN,
                              troughcolor=BG_DARK, highlightthickness=0,
                              showvalue=False, length=140,
                              command=lambda v, lbl=val_lbl, vn=var_name: (
                                  lbl.config(text=f"{int(float(v)):+d}"),
                                  setattr(self, vn, int(float(v))),
                                  self._apply_barrel_offset()
                              ))
                sl.pack(side="left", padx=4)
                setattr(self, f"_{var_name}_slider", sl)
                setattr(self, f"_{var_name}_lbl", val_lbl)
                setattr(self, var_name, init_val)
                return var, sl, val_lbl

            init_bx, init_by = MOBILE_BARREL_OFFSET.get(self.active_mobile_name, (0, 0))
            self._barrel_x_var, self._barrel_x_sl, self._barrel_x_lbl = \
                _slider_row(barrel_frame, "X (→)", -50, 50, "_barrel_x", init_bx)
            self._barrel_y_var, self._barrel_y_sl, self._barrel_y_lbl = \
                _slider_row(barrel_frame, "Y (↓)", -50, 50, "_barrel_y", init_by)

            barrel_save_row = tk.Frame(barrel_frame, bg=BG_CARD)
            barrel_save_row.pack(fill="x", pady=(6,0))
            self.barrel_save_status = tk.Label(barrel_save_row, text="", bg=BG_CARD,
                                                fg=SUCCESS, font=("Courier", 7))
            self.barrel_save_status.pack(side="right")
            tk.Button(barrel_save_row, text=">> SAVE", command=self._save_barrel_offsets,
                      bg=ACCENT, fg=BG_DARK, relief="flat",
                      font=("Courier", 8, "bold"), cursor="hand2",
                      padx=8, pady=3).pack(side="left")
            hint = tk.Frame(body, bg=BG_PANEL, pady=5)
            hint.pack(fill="x", pady=(0,4))

            # Mouse target mode indicator row
            mouse_row = tk.Frame(hint, bg=BG_PANEL)
            mouse_row.pack(fill="x", padx=10, pady=(0,4))
            tk.Label(mouse_row, text="TARGET MODE:", bg=BG_PANEL, fg=TEXT_DIM,
                     font=("Courier", 7, "bold")).pack(side="left")
            self.mouse_mode_lbl = tk.Label(
                mouse_row, text="● PLAYER",
                bg=BG_PANEL, fg=SUCCESS,
                font=("Courier", 7, "bold"))
            self.mouse_mode_lbl.pack(side="right")

            for key, desc in [("[ALT]",       "Lock target ke player"),
                               ("[ALT+SHIFT]", "Lock target ke posisi mouse"),
                               ("[SHFT]",      "Log shot"),
                               ("[CTRL]",      "Trico: 1·2·3 ↔ 2·3·4  |  Turtle: Fork ↔ Sky/Time")]:
                row = tk.Frame(hint, bg=BG_PANEL)
                row.pack(fill="x", padx=10, pady=1)
                tk.Label(row, text=key, bg=BORDER, fg=ACCENT3,
                         font=("Courier", 7, "bold"), padx=4).pack(side="left")
                tk.Label(row, text=f"  {desc}", bg=BG_PANEL, fg=TEXT_DIM,
                         font=("Courier", 7)).pack(side="left")

            tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")
            sb = tk.Frame(self.root, bg=BG_PANEL, pady=4)
            sb.pack(fill="x")
            tk.Label(sb, text="CLASSIFIED  //  ICE·ICO·TRICO·TURTLE  //  no-excel build",
                     bg=BG_PANEL, fg=TEXT_DIM, font=("Courier", 7)).pack()

            self.debug_panel = tk.Frame(self.root, bg=BG_CARD)
            self.debug_text  = tk.Text(self.debug_panel, bg=BG_CARD, fg=SUCCESS,
                                       font=("Courier", 7), relief="flat",
                                       height=6, state="disabled",
                                       insertbackground=SUCCESS)
            self.debug_text.pack(fill="both", expand=True, padx=4, pady=4)

            self.overlay = tk.Toplevel(self.root)
            self.overlay.overrideredirect(True)
            self.overlay.wm_attributes("-topmost", True)
            self.overlay.wm_attributes("-transparentcolor", "black")
            self.overlay.config(bg="black")
            self.canvas = tk.Canvas(self.overlay, bg="black", highlightthickness=0)
            self.canvas.pack(fill="both", expand=True)
            self.canvas.bind("<ButtonPress-1>",  self._ocr_mouse_press)
            self.canvas.bind("<B1-Motion>",       self._ocr_mouse_drag)
            self.canvas.bind("<ButtonRelease-1>", self._ocr_mouse_release)

            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        except Exception as e:
            messagebox.showerror("Error", f"Gagal inisialisasi GUI: {e}")
            if self.root: self.root.destroy()
            sys.exit(1)

    # ─── Debug ────────────────────────────────────────────────
    def _on_debug_toggle(self):
        self.debug_enabled = bool(self.debug_var.get())
        if self.debug_enabled:
            self.debug_panel.pack(fill="x")
            self.root.geometry("330x1080")
            self._log_debug("Debug ON")
        else:
            self.debug_panel.pack_forget()
            self.root.geometry("330x940")

    def _on_mob_override_toggle(self):
        self.manual_mobile_override = bool(self.mob_override_var.get())
        if self.manual_mobile_override:
            self.mob_combo.config(state="readonly")
            self.manual_mobile_name = self.mob_select_var.get()
            self.mob_status_lbl.config(text=f"MANUAL: {self.manual_mobile_name}", fg=ACCENT3)
            self._log_debug(f"Mobile manual override ON → {self.manual_mobile_name}")
        else:
            self.mob_combo.config(state="disabled")
            self.mob_status_lbl.config(text="AUTO", fg=TEXT_DIM)
            self._last_mobile_loaded = None  # force reload dari memory
            self._log_debug("Mobile manual override OFF → AUTO")

    def _on_mob_selected(self, event=None):
        if self.manual_mobile_override:
            self.manual_mobile_name = self.mob_select_var.get()
            self._last_mobile_loaded = None  # force reload constants
            self.mob_status_lbl.config(text=f"MANUAL: {self.manual_mobile_name}", fg=ACCENT3)
            self._log_debug(f"Mobile dipilih manual → {self.manual_mobile_name}")

    # ─── Mobile Constants ─────────────────────────────────────
    def _load_constants_for_mobile(self, mobile_name: str):
        if mobile_name == self._last_mobile_loaded:
            return  # sudah loaded, active_gravedad/masa dijaga oleh _save_constants
        engine = MOBILE_ENGINE.get(mobile_name, "ice")
        self.mobile_db = load_mobile_constants()
        if engine == "ico":
            g, m = self.mobile_db.get(mobile_name, (ICO_DEFAULT_G, ICO_DEFAULT_M))
        else:
            g, m = self.mobile_db.get(mobile_name, (DEFAULT_GRAVEDAD, DEFAULT_MASA))
        self.active_mobile_name  = mobile_name
        self.active_gravedad     = g
        self.active_masa         = m
        self._last_mobile_loaded = mobile_name
        self.gravedad_var.set(str(g))
        self.masa_var.set(str(m))
        self.const_mobile_lbl.config(text=f"[ {mobile_name} ]")
        self.const_save_status.config(text="")
        # Update barrel offset slider
        bx, by = MOBILE_BARREL_OFFSET.get(mobile_name, (0, 0))
        self._barrel_x = bx; self._barrel_y = by
        self._barrel_x_sl.set(bx); self._barrel_y_sl.set(by)
        self._barrel_x_lbl.config(text=f"{bx:+d}")
        self._barrel_y_lbl.config(text=f"{by:+d}")
        self.barrel_mobile_lbl.config(text=f"[ {mobile_name} ]")
        if engine == "ico":
            self.const_engine_lbl.config(
                text=f"ICO  g={g}  m={m}", fg=ACCENT3)
        elif engine == "trico":
            self.const_engine_lbl.config(text="TRICO ENGINE", fg=TRICO_COLORS[0])
        elif engine == "turtle":
            self.const_engine_lbl.config(
                text=f"TURTLE  g={TURTLE_G}  30pts", fg=TURTLE_COLOR_OV1)
            self.gravedad_var.set(str(TURTLE_G))
            self.masa_var.set(str(self.mobile_db.get("Turtle", (TURTLE_G, 149.0))[1]))
        else:
            self.const_engine_lbl.config(text="ICE ENGINE", fg=SUCCESS)
        self._log_debug(f"Constants loaded: {mobile_name} engine={engine} g={g} m={m}")

    def _apply_barrel_offset(self):
        """Apply nilai slider ke MOBILE_BARREL_OFFSET untuk mobile aktif."""
        MOBILE_BARREL_OFFSET[self.active_mobile_name] = (self._barrel_x, self._barrel_y)

    def _save_barrel_offsets(self):
        """Save semua barrel offsets ke file."""
        try:
            self._apply_barrel_offset()  # pastikan nilai slider ter-apply dulu
            save_barrel_offsets(MOBILE_BARREL_OFFSET)
            self.barrel_save_status.config(text="✓ SAVED")
            self.root.after(2000, lambda: self.barrel_save_status.config(text=""))
        except Exception as e:
            self.barrel_save_status.config(text="✗ ERR")
            self._log_debug(f"Barrel save error: {e}")

    def _save_constants(self):
        try:
            g = float(self.gravedad_var.get().strip())
            m = float(self.masa_var.get().strip())
        except ValueError:
            self.const_save_status.config(text="INVALID INPUT", fg=ACCENT2)
            return
        if g <= 0 or m <= 0:
            self.const_save_status.config(text="MUST BE > 0", fg=ACCENT2)
            return
        self.active_gravedad = g
        self.active_masa     = m
        self.mobile_db[self.active_mobile_name] = (g, m)
        save_mobile_constants(self.mobile_db)
        self.const_save_status.config(text=f"SAVED  g={g}  m={m}", fg=SUCCESS)
        self._log_debug(f"Constants saved: {self.active_mobile_name} g={g} m={m}")
        self.root.after(3000, lambda: self.const_save_status.config(text=""))

    def _log_debug(self, msg):
        if not self.debug_enabled: return
        print(f"[DEBUG] {msg}")
        try:
            self.debug_text.config(state="normal")
            self.debug_text.insert("end", f"{msg}\n")
            self.debug_text.see("end")
            if int(self.debug_text.index("end-1c").split(".")[0]) > 200:
                self.debug_text.delete("1.0", "50.0")
            self.debug_text.config(state="disabled")
        except Exception:
            pass

    def is_process_running(self, name):
        for p in psutil.process_iter(['name']):
            if p.info['name'].lower() == name.lower():
                return True
        return False

    # ─── OCR ──────────────────────────────────────────────────
    def ocr_tesseract(self, img_bgr):
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        cfg  = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
        _, th  = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY     + cv2.THRESH_OTSU)
        _, thi = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        t1 = re.sub(r'[^0-9]', '', pytesseract.image_to_string(th,  config=cfg).strip())
        t2 = re.sub(r'[^0-9]', '', pytesseract.image_to_string(thi, config=cfg).strip())
        for t in [t1, t2]:
            if t and t.isdigit() and 0 <= int(t) <= 89:
                return t
        return t1 or t2 or None

    def capture_window_region(self, hwnd, rx, ry, rw, rh):
        import win32ui, win32con as wcon
        def _grab(pw):
            l,t,r,b = win32gui.GetClientRect(hwnd)
            ww,wh = r-l, b-t
            hdc = win32gui.GetWindowDC(hwnd)
            mdc = win32ui.CreateDCFromHandle(hdc)
            sdc = mdc.CreateCompatibleDC()
            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(mdc, ww, wh)
            sdc.SelectObject(bmp)
            if pw:
                ok = ctypes.windll.user32.PrintWindow(hwnd, sdc.GetSafeHdc(), 2)
                if not ok:
                    ctypes.windll.user32.PrintWindow(hwnd, sdc.GetSafeHdc(), 1)
            else:
                sdc.BitBlt((0,0),(ww,wh),mdc,(0,0),wcon.SRCCOPY)
            info = bmp.GetInfo(); data = bmp.GetBitmapBits(True)
            img  = np.frombuffer(data, dtype=np.uint8).reshape((info['bmHeight'], info['bmWidth'], 4))
            out  = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            win32gui.DeleteObject(bmp.GetHandle())
            sdc.DeleteDC(); mdc.DeleteDC(); win32gui.ReleaseDC(hwnd, hdc)
            x1,y1 = max(0,rx), max(0,ry)
            x2,y2 = min(ww,rx+rw), min(wh,ry+rh)
            return out[y1:y2, x1:x2] if x2>x1 and y2>y1 else None
        try:
            return _grab(True)
        except Exception as e:
            self._log_debug(f"PrintWindow err: {e}")
            try:
                return _grab(False)
            except Exception as e2:
                self._log_debug(f"BitBlt fallback err: {e2}")
                return None

    def read_angle(self):
        try:
            hwnd = FindWindow('Softnyx', None)
            if not hwnd:
                self._log_debug("Window tidak ditemukan!"); return None, None
            img_bgr = self.capture_window_region(hwnd, self.ocr_x, self.ocr_y,
                                                  self.ocr_w, self.ocr_h)
            if img_bgr is None: return None, None
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            if self.prev_frame is not None and self.prev_frame.shape == gray.shape:
                if np.mean(cv2.absdiff(self.prev_frame, gray)) < 3:
                    return (str(int(self.last_valid_angle)), 1.0) if self.last_valid_angle else (None, None)
            self.prev_frame = gray
            if self.debug_enabled:
                try:
                    cv2.imwrite("debug_ocr_crop.png", img_bgr)
                except Exception:
                    pass
            if self.tpl_angle_var.get():
                label = self._match_templates(img_bgr)
                self._log_debug(f"TPL raw='{label}'")
            else:
                label = self.ocr_tesseract(img_bgr)
                self._log_debug(f"OCR raw='{label}'")
            if label and label.isdigit():
                val = int(label)
                if 0 <= val <= 89:
                    self.last_valid_angle = float(val)
                    return label, 1.0
            return (str(int(self.last_valid_angle)), 0.8) if self.last_valid_angle else (None, None)
        except Exception as e:
            self._log_debug(f"Error read_angle: {e}"); return None, None

    def _ocr_mouse_press(self, event):
        x,y = event.x, event.y
        rx,ry,rw,rh = self.ocr_x, self.ocr_y, self.ocr_w, self.ocr_h
        m = 12
        if rx+rw-m<=x<=rx+rw+m and ry+rh-m<=y<=ry+rh+m:
            self._ocr_drag_mode = 'resize'
        elif rx<=x<=rx+rw and ry<=y<=ry+rh:
            self._ocr_drag_mode = 'move'
        else:
            self._ocr_drag_mode = None; return
        self._ocr_drag_start  = (x, y)
        self._ocr_drag_origin = (rx, ry, rw, rh)

    def _ocr_mouse_drag(self, event):
        if not self._ocr_drag_mode or not self._ocr_drag_start: return
        dx = event.x - self._ocr_drag_start[0]
        dy = event.y - self._ocr_drag_start[1]
        ox,oy,ow,oh = self._ocr_drag_origin
        if self._ocr_drag_mode == 'move':
            self.ocr_x, self.ocr_y = ox+dx, oy+dy
        else:
            self.ocr_w, self.ocr_h = max(20, ow+dx), max(10, oh+dy)
        self.prev_frame = None

    def _ocr_mouse_release(self, event):
        self._ocr_drag_mode = self._ocr_drag_start = self._ocr_drag_origin = None

    # ─── Memory ───────────────────────────────────────────────
    def read_player_index(self):
        try:
            return self.pm.read_bytes(self.base_address + PLAYER_INDEX_ADDRESS_OFFSET, 1)[0]
        except Exception as e:
            self._log_debug(f"Err player_index: {e}"); return None

    def read_mobile_id(self):
        try:
            mid = self.pm.read_bytes(self.base_address + MOBILE_ID_ADDRESS_OFFSET, 1)[0]
            return MOBILE_ID_TO_NAME.get(mid, f"ID:{mid}")
        except Exception as e:
            self._log_debug(f"Err mobile_id: {e}"); return "Unknown"

    def read_camera_position(self):
        try:
            return (self.pm.read_int(self.base_address + SCREEN_CENTER_X_OFFSET),
                    self.pm.read_int(self.base_address + SCREEN_CENTER_Y_OFFSET))
        except Exception as e:
            self._log_debug(f"Err camera: {e}"); return 0, 0

    def read_player_center(self, index):
        """Baca posisi CENTER badan player (raw, tanpa ROTATED_OFFSET).
        Dipakai untuk target lock — titik tengah badan yang tidak berubah saat balik badan."""
        try:
            addr   = self.base_address + BASE_ADDRESS_PLAYER + index * PLAYER_OFFSET
            x      = self.pm.read_ushort(addr + 0x0)
            y      = self.pm.read_ushort(addr + 0x4)
            facing = self.pm.read_bytes(addr + 0xC, 1)[0]
            cx     = int(x) + TARGET_LOCK_OFFSET_X
            cy     = int(y + OFFSET_Y) + TARGET_LOCK_OFFSET_Y
            return cx, cy, facing
        except Exception as e:
            self._log_debug(f"Err center P{index}: {e}"); return None, None, None

    def read_player_position(self, index, mobile_name=None):
        try:
            addr   = self.base_address + BASE_ADDRESS_PLAYER + index * PLAYER_OFFSET
            x      = self.pm.read_ushort(addr + 0x0)   # center_x raw
            y      = self.pm.read_ushort(addr + 0x4)   # center_y raw
            facing = self.pm.read_bytes(addr + 0xC, 1)[0]
            angle  = self.pm.read_int(addr + 0x8)
            body_angle = angle

            # Offset per mobile — dari main.py
            if mobile_name == "Nak":
                rot_x = 20 if facing == CartFacingDirection.Right else 25
                rot_y = -20
            elif mobile_name == "Aduka":
                rot_x = 20 if facing == CartFacingDirection.Right else 16
                rot_y = -20
            else:
                rot_x = DEFAULT_ROTATED_OFFSET_X
                rot_y = DEFAULT_ROTATED_OFFSET_Y

            if facing == CartFacingDirection.Left:
                angle = (angle + 180) % 360

            xr = radians(angle)
            yr = radians(angle + (-90 if facing == CartFacingDirection.Left else 90))

            # T1 = titik muka (posisi normal)
            t1x = int(round(x + rot_x * cos(xr) + rot_y * cos(yr)))
            t1y = int(round(y + OFFSET_Y - rot_x * sin(xr) - rot_y * sin(yr)))

            # T2 = titik ekor = balik arah rot_x
            if mobile_name in ("Nak", "Aduka"):
                t2x = int(round(x - rot_x * cos(xr) - rot_y * cos(yr)))
                t2y = int(round(y + OFFSET_Y + rot_x * sin(xr) + rot_y * sin(yr)))
                return t2x, t2y, facing, body_angle

            return t1x, t1y, facing, body_angle
        except Exception as e:
            self._log_debug(f"Err pos P{index}: {e}"); return None, None, None, None

    def read_player_screen_positions(self):
        cx, cy = self.read_camera_position()
        result = []
        for i in range(NUM_PLAYERS):
            wx, wy, _, _ = self.read_player_position(i)
            result.append((wx-cx+400, wy-cy+300) if wx is not None else None)
        return result

    def _on_tpl_toggle(self):
        if self.tpl_angle_var.get():
            self._load_templates()

    def _load_templates(self):
        folder = "captured_numbers"
        self.templates = {}
        if not os.path.isdir(folder):
            self._log_debug(f"Folder '{folder}' tidak ditemukan")
            return
        for fname in os.listdir(folder):
            if fname.lower().endswith(".png"):
                label = os.path.splitext(fname)[0]
                path  = os.path.join(folder, fname)
                img   = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    self.templates[label] = img
        self._log_debug(f"Templates loaded: {list(self.templates.keys())}")

    def _match_templates(self, img_bgr):
        if not self.templates:
            return None
        captured_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        best_score = -1
        best_label = None
        for label, tmpl in self.templates.items():
            if tmpl.shape[0] > captured_gray.shape[0] or tmpl.shape[1] > captured_gray.shape[1]:
                continue
            res = cv2.matchTemplate(captured_gray, tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val > best_score:
                best_score = max_val
                best_label = label
        if best_label is not None and best_score > 0.7:
            return best_label
        return None

    def read_wind(self):
        try:
            a   = self.pm.read_uint(BASE_ADDRESS_A)
            b   = self.pm.read_uint(BASE_ADDRESS_B_OFFSET + a * 4)
            dir = self.pm.read_ushort(b + WIND_DIRECTION_OFFSET)
            spd = self.pm.read_bytes(b + WIND_SPEED_OFFSET, 1)[0]
            return dir, spd
        except Exception as e:
            self._log_debug(f"Err wind: {e}"); return 0, 0

    def calculate_distance(self, src_idx, tgt_idx):
        try:
            sx, _, _, _        = self.read_player_position(src_idx)
            tx, _, facing_t, _ = self.read_player_position(tgt_idx)
            if sx is None or tx is None: return None
            return fabs(tx - sx)
        except Exception as e:
            self._log_debug(f"Err distance: {e}"); return None

    # ─── KALKULASI POWER REALTIME ─────────────────────────────
    def _get_power_inputs(self):
        src_idx = self.source_index.get()

        _, src_y, src_facing, _ = self.read_player_position(src_idx, self.active_mobile_name)
        sx, _, _, _             = self.read_player_position(src_idx, self.active_mobile_name)
        if sx is None or src_y is None:
            return None, "no source"

        wind_dir, wind_spd = self.read_wind()

        effective_facing = src_facing
        if self.active_mobile_name in ("Nak", "Aduka"):
            effective_facing = (CartFacingDirection.Right
                                if src_facing == CartFacingDirection.Left
                                else CartFacingDirection.Left)
        else:
            # Auto reverse: facing selalu berlawanan dari arah target
            tgt_idx = self.target_index.get()
            tgt_cx, _, _ = self.read_player_center(tgt_idx)
            if tgt_cx is not None:
                target_is_right = tgt_cx >= sx
                facing_right = (src_facing == CartFacingDirection.Right)
                if target_is_right != facing_right:
                    effective_facing = (CartFacingDirection.Right
                                        if src_facing == CartFacingDirection.Left
                                        else CartFacingDirection.Left)

        if wind_dir in (90, 270):
            fator = wind_dir
        elif effective_facing == CartFacingDirection.Right:
            fator = wind_dir
        else:
            fator = (180 - wind_dir + 360) % 360

        engine = MOBILE_ENGINE.get(self.active_mobile_name, "ice")

        # Apply barrel offset ke src position
        bx_game, by_game = 0.0, 0.0
        if self.active_mobile_name not in ("Nak", "Aduka"):
            bx_px, by_px = MOBILE_BARREL_OFFSET.get(self.active_mobile_name, (0, 0))
            # Konversi pixel offset ke game coords
            _ppw = PIXELS_PER_PART_TURTLE_W if engine == "turtle" else PIXELS_PER_PART_WIDTH
            _pph = PIXELS_PER_PART_TURTLE_H if engine == "turtle" else PIXELS_PER_PART_HEIGHT
            going_right = True  # default, akan dikoreksi di bawah
            bx_game = bx_px  # pixel = game coords (1:1)
            by_game = by_px

        # ── Mode mouse target ──────────────────────────────────
        if self.mouse_target_mode and self.mouse_target_game_pos is not None:
            tgt_game_x, tgt_game_y = self.mouse_target_game_pos
            going_right_m = tgt_game_x >= sx
            sx_eff  = sx + (bx_game if going_right_m else -bx_game)
            src_y_eff = src_y + by_game
            dist_px = fabs(tgt_game_x - sx_eff)
            tgt_y   = tgt_game_y

            if engine == "turtle":
                distance = dist_px / PIXELS_PER_PART_TURTLE_W
                desn_px  = src_y_eff - tgt_y
                desnivel = desn_px / PIXELS_PER_PART_TURTLE_H
            else:
                distance = dist_px / PIXELS_PER_PART_WIDTH
                desn_px  = src_y_eff - tgt_y
                desnivel = desn_px / PIXELS_PER_PART_HEIGHT

            if engine not in ("trico", "turtle") and self.last_valid_angle is None:
                return None, "no angle"
            angle = self.last_valid_angle

            return {
                "dist_px":  dist_px,
                "desn_px":  src_y_eff - tgt_y,
                "distance": distance,
                "desnivel": desnivel,
                "fator":    fator,
                "wind_spd": wind_spd,
                "wind_dir": wind_dir,
                "angle":    angle,
            }, "ok"

        # ── Mode player target (default) ───────────────────────
        tgt_idx = self.target_index.get()
        tgt_cx, tgt_cy, tgt_facing = self.read_player_center(tgt_idx)
        if tgt_cx is None or tgt_cy is None:
            return None, "no target"

        # Terapkan offset facing-relative dari center badan — flip X saat balik badan
        if self.player_lock_facing_ref is not None:
            if tgt_facing == CartFacingDirection.Right:
                applied_ox = self.player_lock_offset_x
            else:
                applied_ox = -self.player_lock_offset_x
            tgt_x_final = tgt_cx + applied_ox
            tgt_y_final = tgt_cy + self.player_lock_offset_y
        else:
            tgt_x_final = tgt_cx
            tgt_y_final = tgt_cy

        going_right_p = tgt_x_final >= sx
        sx_eff  = sx + (bx_game if going_right_p else -bx_game)
        src_y_eff = src_y + by_game

        dist_px = fabs(tgt_x_final - sx_eff)
        tgt_y   = tgt_y_final

        if engine == "turtle":
            distance = dist_px / PIXELS_PER_PART_TURTLE_W
            desn_px  = src_y_eff - tgt_y
            desnivel = desn_px / PIXELS_PER_PART_TURTLE_H
        else:
            distance = dist_px / PIXELS_PER_PART_WIDTH
            desn_px  = src_y_eff - tgt_y
            desnivel = desn_px / PIXELS_PER_PART_HEIGHT

        if engine not in ("trico", "turtle") and self.last_valid_angle is None:
            return None, "no angle"
        angle = self.last_valid_angle
        if self.backshot_var.get() and angle is not None:
            angle = 180 - angle  # A1→A2: game 89° → rumus 91°

        return {
                "dist_px":  dist_px,
                "desn_px":  src_y_eff - tgt_y,
                "distance": distance,
                "desnivel": desnivel,
                "fator":    fator,
                "wind_spd": wind_spd,
                "wind_dir": wind_dir,
                "angle":    angle,
        }, "ok"

    def _update_realtime_power(self):
        engine = MOBILE_ENGINE.get(self.active_mobile_name, "ice")
        self.is_trico  = (engine == "trico")
        self.is_turtle = (engine == "turtle")

        inputs, status = self._get_power_inputs()
        if inputs is None:
            self.current_power    = None
            self.trico_results    = []
            self.turtle_ov1_results = []
            self.turtle_ov2_results = []
            self.power_card.set("-", color=TEXT_DIM)
            self.live_dot.config(fg=TEXT_DIM)
            self.live_status.config(text=status.upper(), fg=TEXT_DIM)
            return

        try:
            if engine == "turtle":
                # ── MODE TURTLE ───────────────────────────────
                self.trico_results    = []
                self.current_power    = None

                dist  = inputs["distance"]
                desn  = inputs["desnivel"]
                fator = inputs["fator"]
                wind  = inputs["wind_spd"]

                self.turtle_ov1_results = calc_turtle_set(
                    dist, desn, fator, wind, TURTLE_OVERLAY1_T,
                    g=self.active_gravedad, m=self.active_masa)
                self.turtle_ov2_results = calc_turtle_overlay2(
                    dist, desn, fator, wind,
                    g=self.active_gravedad, m=self.active_masa)

                # Mode 2: regular shot — butuh angle dari OCR
                if self.turtle_overlay_mode == 2:
                    if inputs["angle"] is not None:
                        _, pw_raw = calc_turtle_by_angle(dist, desn, fator, wind, inputs["angle"],
                                                         g=self.active_gravedad, m=self.active_masa)
                        self.current_power = pw_raw
                        self.power_card.set(f"{self.current_power:.3f}", color=ACCENT2)
                        self.live_dot.config(fg=ACCENT2)
                        self.live_status.config(text="TURTLE·REG", fg=ACCENT2)
                    else:
                        self.current_power = None
                        self.power_card.set("-", color=TEXT_DIM)
                        self.live_dot.config(fg=TEXT_DIM)
                        self.live_status.config(text="NO ANGLE", fg=TEXT_DIM)
                else:
                    self.current_power = None
                    mode_txt = "FORK" if self.turtle_overlay_mode == 0 else "SKY/TIME"
                    active   = self.turtle_ov1_results if self.turtle_overlay_mode == 0 \
                               else self.turtle_ov2_results
                    if active:
                        self.power_card.set(f"{active[0][2]:.3f}", color=TURTLE_COLOR_OV1)
                    self.live_dot.config(fg=TURTLE_COLOR_OV1)
                    self.live_status.config(text=f"TURTLE·{mode_txt}", fg=TURTLE_COLOR_OV1)
                self._log_debug(
                    f"TURTLE dist={dist:.2f} desn={desn:.2f} fator={fator} wind={wind}")

            elif engine == "trico":
                # ── MODE TRICO ────────────────────────────────
                self.turtle_ov1_results = []
                self.turtle_ov2_results = []
                spins = TRICO_SPIN_SETS[self.trico_spin_mode]
                self.trico_results = calc_trico_set(
                    inputs["distance"], inputs["desnivel"],
                    inputs["fator"],    inputs["wind_spd"],
                    spins
                )
                if self.trico_results:
                    summary = "  ".join(
                        f"↓{abs(pw):.2f}" if pw < 0 else f"{pw:.2f}"
                        for _, _, pw in self.trico_results
                    )
                    self.power_card.set(summary, color=TRICO_COLORS[0])
                self.current_power = None
                self.live_dot.config(fg=TRICO_COLORS[0])
                mode_label = "SPIN 1-2-3" if self.trico_spin_mode == 0 else "SPIN 2-3-4"
                self.live_status.config(text=mode_label, fg=TRICO_COLORS[0])

            elif engine == "ico":
                # ── MODE ICO ──────────────────────────────────
                # Rumus Trico tanpa spin, G & M dari mobile_constants.txt
                self.trico_results = []
                self.turtle_ov1_results = []
                self.turtle_ov2_results = []
                power_raw = calc_power_ico(
                    inputs["distance"],  inputs["desnivel"],
                    inputs["fator"],     inputs["wind_spd"],
                    inputs["angle"],
                    g=self.active_gravedad,
                    m=self.active_masa
                )
                self._log_debug(f"BCK angle={inputs['angle']:.1f} dist={inputs['distance']:.2f} desn={inputs['desnivel']:.2f} raw={power_raw:.4f}")
                power = min(max(abs(power_raw), 0.0), POWER_BAR_MAX)
                self.current_power = power
                self.power_card.set(f"{power:.2f}", color=ACCENT3)
                self.live_dot.config(fg=ACCENT3)
                self.live_status.config(text="LIVE·ICO", fg=ACCENT3)

            else:
                # ── MODE ICE ──────────────────────────────────
                self.trico_results = []
                self.turtle_ov1_results = []
                self.turtle_ov2_results = []
                power_raw = calc_power_ice(
                    inputs["distance"], inputs["desnivel"],
                    inputs["fator"],    inputs["wind_spd"],
                    inputs["angle"],
                    g=self.active_gravedad,
                    m=self.active_masa
                )
                power = min(max(abs(power_raw), 0.0), POWER_BAR_MAX)
                self.current_power = power
                self.power_card.set(f"{power:.2f}", color=ACCENT2)
                self.live_dot.config(fg=SUCCESS)
                self.live_status.config(text="LIVE", fg=SUCCESS)

        except Exception as e:
            self.current_power = None
            self.trico_results = []
            self.turtle_ov1_results = []
            self.turtle_ov2_results = []
            self.power_card.set("ERR", color=ACCENT2)
            self.live_dot.config(fg=ACCENT2)
            self.live_status.config(text="CALC ERR", fg=ACCENT2)
            self._log_debug(f"Err calc power: {e}")

    def hitung_power(self):
        if self.current_power is None:
            return
        inputs, status = self._get_power_inputs()
        if inputs is None:
            return
        self.shot_counter += 1
        with open(SHOT_DATA_FILE, 'a') as f:
            f.write(
                f"Shot {self.shot_counter}: "
                f"dist={inputs['distance']:.2f} desnivel={inputs['desnivel']:.2f} "
                f"fator={inputs['fator']} wind={inputs['wind_spd']} "
                f"angle={inputs['angle']} power={self.current_power:.2f}\n"
            )
        self._log_debug(f"Shot#{self.shot_counter} logged → power={self.current_power:.2f}")


    # ─── Trajectory Arc Render ────────────────────────────────
    def _draw_trajectory(self, src_screen_x, src_screen_y, inputs):
        """
        Gambar jalur peluru dari source ke target di overlay canvas.
        Pakai polyline (banyak create_line pendek) agar smooth.
        Wrapped try/except agar error di sini tidak ganggu render lain.
        """
        try:
            engine  = MOBILE_ENGINE.get(self.active_mobile_name, "ice")
            dist_px = inputs["dist_px"]   # selalu positif (fabs)
            desn_px = inputs["desn_px"]   # positif = target lebih rendah dari src
            fator   = inputs["fator"]
            wind    = inputs["wind_spd"]
            angle   = inputs["angle"]

            if dist_px <= 0:
                return

            # Tentukan arah tembak: ke kiri atau kanan di screen
            src_idx = self.source_index.get()
            sx_game, _, src_facing, src_body_angle = self.read_player_position(src_idx, self.active_mobile_name)
            if sx_game is None:
                return

            if self.mouse_target_mode and self.mouse_target_game_pos:
                tgt_game_x = self.mouse_target_game_pos[0]
            else:
                tgt_idx = self.target_index.get()
                tgt_cx, _, tgt_f = self.read_player_center(tgt_idx)
                if tgt_cx is None:
                    return
                applied_ox = 0
                if self.player_lock_facing_ref is not None:
                    if tgt_f == CartFacingDirection.Right:
                        applied_ox = self.player_lock_offset_x
                    else:
                        applied_ox = -self.player_lock_offset_x
                tgt_game_x = tgt_cx + applied_ox

            going_right = tgt_game_x >= sx_game

            traj_src_x = src_screen_x
            traj_src_y = src_screen_y
            if self.active_mobile_name not in ("Nak", "Aduka"):
                bx, by = MOBILE_BARREL_OFFSET.get(self.active_mobile_name, (0, 0))
                traj_src_x = src_screen_x + (bx if going_right else -bx)
                traj_src_y = src_screen_y + by

            def _render(pts, color, width=1):
                """Render list (x,y) sebagai polyline — flip x jika going_left."""
                if len(pts) < 2:
                    return
                if not going_right:
                    pts = [(2 * traj_src_x - px, py) for (px, py) in pts]
                for i in range(len(pts) - 1):
                    self.canvas.create_line(
                        pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                        fill=color, width=width,
                        capstyle="round", joinstyle="round")

            if engine == "trico":
                spin_keys  = TRICO_SPIN_SETS[self.trico_spin_mode]
                colors_map = {"1": "#4FC3F7", "2": "#FFB74D", "3": "#CE93D8",
                              "2b": "#FFB74D", "3b": "#CE93D8", "4": "#A5D6A7"}
                for sk in spin_keys:
                    pts = compute_trajectory_trico(
                        traj_src_x, traj_src_y,
                        dist_px, desn_px, fator, wind, sk)
                    if not pts:
                        continue
                    col = colors_map.get(sk, "#FFFFFF")
                    _render(pts, col, width=1)

            elif engine == "turtle":
                if self.turtle_overlay_mode == 2:
                    if angle is not None:
                        pts = compute_trajectory_ice(
                            traj_src_x, traj_src_y,
                            dist_px, desn_px, fator, wind, angle,
                            self.active_gravedad, self.active_masa)
                        if pts:
                            _render(pts, TURTLE_COLOR_OV1, width=1)
                else:
                    active = self.turtle_ov1_results if self.turtle_overlay_mode == 0 \
                             else self.turtle_ov2_results
                    for label, angle_t, power_t, color_t in active:
                        if angle_t == 0.0 and power_t == 0.0:
                            continue
                        pts = compute_trajectory_turtle(
                            traj_src_x, traj_src_y,
                            dist_px, desn_px, fator, wind, angle_t)
                        if pts:
                            _render(pts, color_t, width=1)

            else:
                # ICE / ICO engine — pakai compute_trajectory_ice (rumus sama)
                if angle is None:
                    return
                g = self.active_gravedad
                m = self.active_masa

                pts = compute_trajectory_ice(
                    traj_src_x, traj_src_y,
                    dist_px, desn_px, fator, wind, angle, g, m)
                if not pts:
                    return

                col_map = {
                    "Ice": "#4FC3F7", "JD": "#B39DDB", "Aduka": "#80CBC4",
                    "Grub": "#FFAB91", "Mage": "#F48FB1",
                }
                col = col_map.get(self.active_mobile_name, SUCCESS)
                _render(pts, col, width=1)

                # Titik apex
                apex = min(pts, key=lambda p: p[1])
                ax_s = apex[0]
                ay_s = apex[1]
                if not going_right:
                    ax_s = 2 * traj_src_x - ax_s
                self.canvas.create_oval(ax_s-3, ay_s-3, ax_s+3, ay_s+3,
                                        fill=col, outline="")
                self.canvas.create_text(ax_s, ay_s - 10,
                                        text=f"∠{angle:.0f}°",
                                        fill=col, font=("Courier", 7, "bold"))
        except Exception as e:
            self._log_debug(f"_draw_trajectory err: {e}")

    # ─── Turtle Overlay Render ────────────────────────────────
    def _draw_turtle_overlay(self, w, h):
        """Gambar panel Turtle di overlay canvas."""
        if self.turtle_overlay_mode == 0:
            results  = self.turtle_ov1_results
            title    = "◈ TURTLE  [FORK]  [CTRL=SKY/TIME]"
            hdr_col  = TURTLE_COLOR_OV1
        else:
            results  = self.turtle_ov2_results
            title    = "◈ TURTLE  [SKY★PLAN5·TIME]  [CTRL=REGULAR]"
            hdr_col  = TURTLE_COLOR_OV2

        if not results:
            return

        # Power bar markers — kotak + sudut, stacked ke atas biar ga overlap
        BOX_W   = 26   # lebar kotak label
        BOX_H   = 13   # tinggi kotak
        TICK_H  = 8    # tinggi garis tick di bawah kotak
        BASE_Y  = POWER_BAR_Y_OFFSET   # = 585

        # Hitung posisi x semua marker dulu, lalu stack yang overlap
        markers = []
        for label, angle, pw, color in results:
            if pw <= 0:
                continue
            markers.append((POWER_BAR_X_OFFSET + pw * POWER_BAR_SCALE, angle, pw, color, label))

        # Sort by x agar stacking rapi
        markers.sort(key=lambda m: m[0])

        # Assign level (0=langsung di atas bar, 1=satu tingkat lagi, dst)
        # Kalau jarak x < BOX_W+2, naikkan level
        levels = []
        for idx, (mx, ang, pw, col, lbl) in enumerate(markers):
            lv = 0
            for prev_idx in range(idx):
                px2, _, _, _, _ = markers[prev_idx]
                if abs(mx - px2) < BOX_W + 2 and levels[prev_idx] == lv:
                    lv += 1
            levels.append(lv)

        for (mx, ang, pw, col, lbl), lv in zip(markers, levels):
            # Tick garis dari power bar ke kotak
            tick_top  = BASE_Y - TICK_H - (BOX_H + 1) * lv - BOX_H
            tick_bot  = BASE_Y
            self.canvas.create_line(
                mx, tick_bot,
                mx, tick_top + BOX_H,
                fill=col, width=2)

            # Kotak kecil
            bx1 = mx - BOX_W // 2
            bx2 = mx + BOX_W // 2
            by1 = tick_top - BOX_H
            by2 = tick_top
            self.canvas.create_rectangle(
                bx1, by1, bx2, by2,
                fill="#0D0F09", outline=col, width=1)

            # Angka sudut di dalam kotak
            self.canvas.create_text(
                mx, (by1 + by2) // 2,
                text=f"{ang:.1f}",
                fill=col, font=("Courier", 7, "bold"), anchor="center")

        # Panel pojok kanan atas
        if not self.turtle_panel_visible:
            return
        row_h    = 22
        header_h = 20
        total_h  = header_h + len(results) * row_h + 10
        panel_w  = 210
        px = w - 120
        py = 10

        self.canvas.create_rectangle(
            px - panel_w, py, px, py + total_h,
            fill="#0A0C06", outline=hdr_col, width=1)

        # Header
        self.canvas.create_text(
            px - panel_w // 2, py + 10,
            text=title,
            fill=hdr_col, font=("Courier", 7, "bold"), anchor="center")

        # Separator
        self.canvas.create_line(
            px - panel_w + 4, py + header_h,
            px - 4,           py + header_h,
            fill="#2A2D1E", width=1)

        col_label = px - panel_w + 10
        col_angle = px - panel_w + 88
        col_power = px - panel_w + 155

        for i, (label, angle, pw, color) in enumerate(results):
            ry = py + header_h + 6 + i * row_h

            # Dot warna
            self.canvas.create_oval(
                col_label - 2, ry + 4,
                col_label + 6, ry + 12,
                fill=color, outline="")

            # Label
            self.canvas.create_text(
                col_label + 10, ry + 8,
                text=label, fill=color,
                font=("Courier", 8, "bold"), anchor="w")

            # Sudut
            self.canvas.create_text(
                col_angle, ry + 8,
                text=f"∠ {angle:.1f}°", fill="#D6CEAA",
                font=("Courier", 9, "bold"), anchor="w")

            # Power
            pw_col = ACCENT2 if pw <= 0 else color
            self.canvas.create_text(
                col_power, ry + 8,
                text=f"⚡{pw:.3f}", fill=pw_col,
                font=("Courier", 9, "bold"), anchor="w")

    # ─── Overlay ──────────────────────────────────────────────
    def update_overlay(self):
        if not self.running: return
        try:
            hwnd = FindWindow('Softnyx', None)
            if hwnd:
                l,t,r,b = GetClientRect(hwnd)
                sx,sy   = ClientToScreen(hwnd, (0,0))
                w, h    = r-l, b-t
                self.overlay.geometry(f"{w}x{h}+{sx}+{sy}")
                self.canvas.config(width=w, height=h)
                self.canvas.delete("all")

                if not self.overlay_visible:
                    # Overlay disembunyiin, tapi tetap update stat cards
                    self.read_angle()
                    self.current_angle = self.last_valid_angle
                    if self.current_angle is not None:
                        self.angle_card.set(f"{self.current_angle:.0f}°", color=ACCENT3)
                    else:
                        self.angle_card.set("-")
                    self._update_realtime_power()
                    d, s = self.read_wind()
                    self.wind_card.set(f"{d}°  spd {s}", color=ACCENT)
                    if self.manual_mobile_override:
                        mobile_name = self.manual_mobile_name
                    else:
                        mobile_name = self.read_mobile_id()
                    self.mobile_card.set(mobile_name, color=ACCENT3)
                    self._load_constants_for_mobile(mobile_name)
                    mi = self.read_player_index()
                    if mi is not None:
                        self.source_index.set(mi)
                        self.player_card.set(f"P{mi}", color=TEXT_MAIN)
                    self.root.after(33, self.update_overlay)
                    return

                # Player positions
                for idx, pos in enumerate(self.read_player_screen_positions()):
                    if pos:
                        px, py = pos
                        col = ACCENT2 if (idx == self.locked_target_index and not self.mouse_target_mode) else ACCENT3
                        self.canvas.create_text(px, py, text=f"P{idx}",
                                                fill=col, font=("Courier", 8, "bold"))
                        if idx == self.locked_target_index and not self.mouse_target_mode:
                            tgt_cx, tgt_cy, tf = self.read_player_center(idx)
                            if tgt_cx is not None:
                                camera_x, camera_y = self.read_camera_position()
                                if self.player_lock_facing_ref is not None:
                                    if tf == CartFacingDirection.Right:
                                        applied_ox = self.player_lock_offset_x
                                    else:
                                        applied_ox = -self.player_lock_offset_x
                                    applied_oy = self.player_lock_offset_y
                                else:
                                    applied_ox = 0
                                    applied_oy = 0
                                cx_circle = (tgt_cx + applied_ox) - camera_x + 400
                                cy_circle = (tgt_cy + applied_oy) - camera_y + 300
                                self.canvas.create_oval(
                                    cx_circle - TARGET_HIGHLIGHT_RADIUS, cy_circle - TARGET_HIGHLIGHT_RADIUS,
                                    cx_circle + TARGET_HIGHLIGHT_RADIUS, cy_circle + TARGET_HIGHLIGHT_RADIUS,
                                    outline=ACCENT2, width=2)

                # Mouse target circle
                if self.mouse_target_mode and self.mouse_target_game_pos is not None:
                    camera_x, camera_y = self.read_camera_position()
                    gx, gy = self.mouse_target_game_pos
                    # Konversi game coords → screen pixel di dalam overlay
                    scr_x = gx - camera_x + 400
                    scr_y = gy - camera_y + 300
                    R = TARGET_HIGHLIGHT_RADIUS
                    # Lingkaran luar (kuning/orange = beda dari player)
                    self.canvas.create_oval(
                        scr_x - R, scr_y - R,
                        scr_x + R, scr_y + R,
                        outline=ACCENT3, width=2)
                    # Crosshair kecil di tengah
                    self.canvas.create_line(
                        scr_x - R//2, scr_y,
                        scr_x + R//2, scr_y,
                        fill=ACCENT3, width=1)
                    self.canvas.create_line(
                        scr_x, scr_y - R//2,
                        scr_x, scr_y + R//2,
                        fill=ACCENT3, width=1)
                    # Label
                    self.canvas.create_text(
                        scr_x, scr_y - R - 6,
                        text="★ MOUSE", fill=ACCENT3,
                        font=("Courier", 7, "bold"), anchor="s")

                # Angle — OCR atau Template
                self.read_angle()
                self.current_angle = self.last_valid_angle
                if self.current_angle is not None:
                    self.angle_card.set(f"{self.current_angle:.0f}°", color=ACCENT3)
                    self.canvas.create_text(153, h-114,
                                            text=f"Sudut: {self.current_angle:.0f}",
                                            fill=SUCCESS,
                                            font=("Courier", 10, "bold"), anchor="nw")
                else:
                    self.angle_card.set("-")

                # Power calc
                self._update_realtime_power()

                # ── Render trajectory arc ─────────────────────
                inputs, _status = self._get_power_inputs()
                if inputs is not None:
                    src_idx = self.source_index.get()
                    src_gx, src_gy, _, _ = self.read_player_position(src_idx, self.active_mobile_name)
                    camera_x, camera_y = self.read_camera_position()
                    if src_gx is not None:
                        src_scr_x = src_gx - camera_x + 400
                        src_scr_y = src_gy - camera_y + 300
                        self._draw_trajectory(src_scr_x, src_scr_y, inputs)

                # ── Render Turtle overlay ─────────────────────
                if self.is_turtle:
                    if self.turtle_overlay_mode == 2:
                        # Regular shot — 1 marker + power text kayak Ice
                        if self.current_power is not None:
                            px_bar = POWER_BAR_X_OFFSET + self.current_power * POWER_BAR_SCALE
                            self.canvas.create_line(px_bar, POWER_BAR_Y_OFFSET - 20,
                                                    px_bar, POWER_BAR_Y_OFFSET,
                                                    fill=ACCENT2, width=2)
                            self.canvas.create_text(
                                228, h - 100,
                                text=f"Power: {self.current_power:.3f}",
                                fill=ACCENT3, font=("Courier", 10, "bold"), anchor="ne")
                        # Label mode di pojok kanan atas
                        self.canvas.create_text(
                            w - 8, 14, anchor="ne",
                            text="◈ TURTLE  [REGULAR]  [CTRL=FORK]",
                            fill=ACCENT2, font=("Courier", 7, "bold"))
                    else:
                        self._draw_turtle_overlay(w, h)

                # ── Render Trico overlay ──────────────────────
                elif self.is_trico and self.trico_results:
                    _trico_markers = []
                    for i, (label, ang, pw) in enumerate(self.trico_results):
                        col     = TRICO_COLORS[i % len(TRICO_COLORS)]
                        pw_disp = abs(pw)
                        bar_col = ACCENT2 if pw < 0 else col
                        _trico_markers.append((POWER_BAR_X_OFFSET + pw_disp * POWER_BAR_SCALE, ang, bar_col))
                    _trico_markers.sort(key=lambda m: m[0])
                    _trico_lvls = []
                    for _ti, (_tmx,_,_) in enumerate(_trico_markers):
                        _lv=0
                        for _tj in range(_ti):
                            if abs(_tmx-_trico_markers[_tj][0])<28 and _trico_lvls[_tj]==_lv: _lv+=1
                        _trico_lvls.append(_lv)
                    for (_tmx,_tang,_tcol),_tlv in zip(_trico_markers,_trico_lvls):
                        _ttop=POWER_BAR_Y_OFFSET-8-(14)*_tlv-13
                        self.canvas.create_line(_tmx,POWER_BAR_Y_OFFSET,_tmx,_ttop+13,fill=_tcol,width=2)
                        self.canvas.create_rectangle(_tmx-13,_ttop-13,_tmx+13,_ttop,fill="#0D0F09",outline=_tcol,width=1)
                        self.canvas.create_text(_tmx,_ttop-6,text=f"{_tang:.0f}°",fill=_tcol,font=("Courier",7,"bold"),anchor="center")

                    # Panah arah spin di tengah atas (ganti seluruh panel data)
                    arrow_txt = "→→→" if self.trico_spin_mode == 0 else "←←←"
                    self.canvas.create_text(
                        w // 2, 8, anchor="n",
                        text=arrow_txt,
                        fill=TRICO_COLORS[0], font=("Courier", 48, "bold"))

                elif self.current_power is not None:
                    px_bar = POWER_BAR_X_OFFSET + self.current_power * POWER_BAR_SCALE
                    self.canvas.create_line(px_bar, POWER_BAR_Y_OFFSET - 20,
                                            px_bar, POWER_BAR_Y_OFFSET,
                                            fill=SUCCESS, width=2)
                    self.canvas.create_text(
                        228, h - 100,
                        text=f"Power: {self.current_power:.2f}",
                        fill=ACCENT3, font=("Courier", 10, "bold"), anchor="ne")
                    self.power_card.set(f"{self.current_power:.2f}", color=ACCENT2)

                # OCR bounding box
                rx,ry,rw,rh = self.ocr_x, self.ocr_y, self.ocr_w, self.ocr_h
                oc = ACCENT
                self.canvas.create_rectangle(rx,ry,rx+rw,ry+rh,outline=oc,width=2,dash=(4,2))
                for a_,b_ in [((rx,ry+8),(rx,ry)),((rx,ry),(rx+8,ry)),
                               ((rx+rw-8,ry),(rx+rw,ry)),((rx+rw,ry),(rx+rw,ry+8)),
                               ((rx,ry+rh-8),(rx,ry+rh)),((rx,ry+rh),(rx+8,ry+rh))]:
                    self.canvas.create_line(*a_,*b_,fill=oc,width=2)
                self.canvas.create_polygon(
                    rx+rw-10,ry+rh,rx+rw,ry+rh,rx+rw,ry+rh-10,
                    fill=ACCENT3,outline=ACCENT3)

                # Stat cards
                d, s = self.read_wind()
                self.wind_card.set(f"{d}°  spd {s}", color=ACCENT)
                if self.manual_mobile_override:
                    mobile_name = self.manual_mobile_name
                else:
                    mobile_name = self.read_mobile_id()
                self.mobile_card.set(mobile_name, color=ACCENT3)
                self._load_constants_for_mobile(mobile_name)
                mi = self.read_player_index()
                if mi is not None:
                    self.source_index.set(mi)
                    self.player_card.set(f"P{mi}", color=TEXT_MAIN)
                if self.mouse_target_mode and self.mouse_target_game_pos is not None:
                    sx, _, _, _ = self.read_player_position(self.source_index.get())
                    if sx is not None:
                        dist = fabs(self.mouse_target_game_pos[0] - sx)
                    else:
                        dist = None
                else:
                    tgt_cx, _, tgt_f = self.read_player_center(self.target_index.get())
                    src_x, _, _, _   = self.read_player_position(self.source_index.get(), self.active_mobile_name)
                    if tgt_cx is not None and src_x is not None:
                        if self.player_lock_facing_ref is not None:
                            if tgt_f == CartFacingDirection.Right:
                                applied_ox = self.player_lock_offset_x
                            else:
                                applied_ox = -self.player_lock_offset_x
                        else:
                            applied_ox = 0
                        dist = fabs((tgt_cx + applied_ox) - src_x)
                    else:
                        dist = None
                self.dist_card.set(
                    f"{dist/PIXELS_PER_PART_WIDTH:.2f} pts" if dist else "-",
                    color=SUCCESS)

        except Exception as e:
            self._log_debug(f"Error overlay: {e}")

        self.root.after(33, self.update_overlay)

    # ─── Toggle Overlay Visibility ────────────────────────────
    def toggle_overlay_visible(self):
        self.overlay_visible = not self.overlay_visible
        if self.overlay_visible:
            self.overlay.deiconify()
            self.overlay_btn.config(text="[ OVL ON ]",  bg=ACCENT)
            self._log_debug("Overlay ON")
        else:
            self.overlay.withdraw()
            self.overlay_btn.config(text="[ OVL OFF ]", bg=TEXT_DIM)
            self._log_debug("Overlay OFF")

    def toggle_canvas_overlay(self):
        """CTRL+SHIFT: turtle → toggle panel kotak atas. Mobile lain → toggle canvas."""
        if self.is_turtle:
            self.turtle_panel_visible = not self.turtle_panel_visible
            self._log_debug(f"Turtle panel {'ON' if self.turtle_panel_visible else 'OFF'}")
        else:
            self.overlay_canvas_visible = not self.overlay_canvas_visible
            if self.overlay_canvas_visible:
                self.canvas.pack(fill="both", expand=True)
            else:
                self.canvas.pack_forget()
            self._log_debug(f"Canvas overlay {'ON' if self.overlay_canvas_visible else 'OFF'}")

    # ─── Start/Stop ───────────────────────────────────────────
    def toggle_reading(self):
        if not self.running:
            if not self.is_process_running(PROCESS_NAME):
                messagebox.showerror("Error", f"{PROCESS_NAME} tidak berjalan.")
                return
            try:
                self.pm           = pymem.Pymem(PROCESS_NAME)
                self.base_address = self.pm.base_address
                self.running      = True
                self.status_var.set(f"PID {self.pm.process_id}")
                self.status_lbl.config(fg=SUCCESS)
                self.toggle_btn.config(text="[] STOP", bg=ACCENT2)
                self._load_templates()
                self.update_overlay()
                threading.Thread(target=self.start_hotkey_listener, daemon=True).start()
                self._log_debug(f"Terhubung PID={self.pm.process_id}")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal terhubung: {e}")
        else:
            self.running = False
            self.status_var.set("DISCONNECTED")
            self.status_lbl.config(fg=ACCENT2)
            self.toggle_btn.config(text=">> START", bg=SUCCESS)
            self.player_lock_facing_ref = None
            self.player_lock_offset_x   = 0
            self.player_lock_offset_y   = 0
            self._log_debug("Dihentikan.")

    # ─── Hotkeys ──────────────────────────────────────────────
    def on_alt_pressed(self):
        """ALT: Lock target ke posisi mouse saat ini (game coordinates)."""
        hwnd = FindWindow('Softnyx', None)
        if not hwnd: return
        try:
            mx, my = win32api.GetCursorPos()
            lx, ly = ScreenToClient(hwnd, (mx, my))
            cx, cy = self.read_camera_position()
            # Konversi screen pixel → game coordinates
            game_x = cx - 400 + lx
            game_y = cy - 300 + ly
            self.mouse_target_game_pos = (game_x, game_y)
            self.mouse_target_mode = True
            self._update_mouse_mode_label()
            self._log_debug(f"Mouse target locked → game({game_x}, {game_y}) screen({lx}, {ly})")
        except Exception as e:
            self._log_debug(f"Err alt: {e}")

    def on_alt_shift_pressed(self):
        """ALT+SHIFT: Lock target ke player terdekat, offset relatif dari posisi mouse."""
        hwnd = FindWindow('Softnyx', None)
        if not hwnd: return
        try:
            mx, my = win32api.GetCursorPos()
            lx, ly = ScreenToClient(hwnd, (mx, my))
            cx, cy = self.read_camera_position()

            # Posisi mouse dalam game coords
            mouse_game_x = cx - 400 + lx
            mouse_game_y = cy - 300 + ly

            # Cari player terdekat di screen
            best, best_d = None, TARGET_DETECTION_THRESHOLD * 5  # threshold lebih lebar untuk player lock
            for idx, pos in enumerate(self.read_player_screen_positions()):
                if pos:
                    d = sqrt((lx - pos[0])**2 + (ly - pos[1])**2)
                    if d < best_d:
                        best_d, best = d, idx

            if best is not None:
                tgt_cx, tgt_cy, tgt_facing = self.read_player_center(best)
                if tgt_cx is not None:
                    # Target fixed ke center badan — tidak pakai offset mouse
                    self.player_lock_offset_x   = 0
                    self.player_lock_offset_y   = 0
                    self.player_lock_facing_ref = tgt_facing

                    self.target_index.set(best)
                    self.locked_target_index = best
                    self.mouse_target_mode = False
                    self.mouse_target_game_pos = None
                    self._update_mouse_mode_label()
                    self._log_debug(
                        f"Player lock P{best} | offset facing-rel=({self.player_lock_offset_x:.0f}, {self.player_lock_offset_y:.0f}) | facing={'R' if tgt_facing==CartFacingDirection.Right else 'L'}")
        except Exception as e:
            self._log_debug(f"Err alt+shift: {e}")

    def _update_mouse_mode_label(self):
        """Update label indikator mode target di UI."""
        try:
            if self.mouse_target_mode and self.mouse_target_game_pos:
                gx, gy = self.mouse_target_game_pos
                self.mouse_mode_lbl.config(
                    text=f"● MOUSE ({gx},{gy})",
                    fg=ACCENT3)
            else:
                self.mouse_mode_lbl.config(text="● PLAYER", fg=SUCCESS)
        except Exception:
            pass

    def _on_ctrl_hotkey(self):
        """CTRL: cycling Trico spin mode ATAU Turtle overlay mode (0→1→2→0)."""
        if self.is_turtle:
            self.turtle_overlay_mode = (self.turtle_overlay_mode + 1) % 3
            mode_txt = ["FORK", "SKY/TIME", "REGULAR"][self.turtle_overlay_mode]
            self._log_debug(f"Turtle overlay mode → {mode_txt}")
        elif self.is_trico:
            self.trico_spin_mode = 1 - self.trico_spin_mode
            self._log_debug(f"Trico spin mode → {TRICO_SPIN_SETS[self.trico_spin_mode]}")

    def start_hotkey_listener(self):
        def _alt():
            if self.is_turtle:
                self.root.after(0, self.on_alt_pressed)
            else:
                self.root.after(0, self.on_alt_shift_pressed)

        def _alt_shift():
            if self.is_turtle:
                self.root.after(0, self.on_alt_shift_pressed)
            else:
                self.root.after(0, self.on_alt_pressed)

        keyboard.add_hotkey('alt+shift', _alt_shift)
        keyboard.add_hotkey('alt', _alt)
        keyboard.add_hotkey('right shift', lambda: self.root.after(0, self.hitung_power))
        keyboard.add_hotkey('ctrl', lambda: self.root.after(0, self._on_ctrl_hotkey))
        keyboard.add_hotkey('ctrl+shift', lambda: self.root.after(0, self.toggle_canvas_overlay))

    def on_closing(self):
        self.running = False
        if self.pm: self.pm.close_process()
        if self.root: self.root.destroy()

    def run(self):
        if self.root: self.root.mainloop()


# ─── Entry ────────────────────────────────────────────────────
if __name__ == "__main__":
    if not ctypes.windll.shell32.IsUserAnAdmin():
        messagebox.showerror("Error", "Jalankan sebagai Administrator.")
        sys.exit(1)
    GunboundPowerCalculator().run()
