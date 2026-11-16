import io
import math
import os
import struct
from PIL import Image, ImageDraw, ImageFont

BACKUP_SAF = "ThaiPatch/backup/FFArchive.saf"
TTF_PATH = "LINE_Seed_Sans_TH_V1.003/Game/TTF/LINESeedSansTH_G_Bd.ttf"

BUTTON_SPECS = [
    ("resources/menus/mainnewnormal.png", "เริ่มเกม\nใหม่", 24),
    ("resources/menus/mainnewhigh.png", "เริ่มเกม\nใหม่", 24),
    ("resources/menus/maintimenormal.png", "โหมด\nแข่งเวลา!", 22),
    ("resources/menus/maintimehigh.png", "โหมด\nแข่งเวลา!", 22),
    ("resources/menus/mainoptionsnormal.png", "ตั้งค่า\nเกม", 20),
    ("resources/menus/mainoptionshigh.png", "ตั้งค่า\nเกม", 20),
    ("resources/menus/mainhighscorenormal.png", "คะแนน\nสูงสุด", 19),
    ("resources/menus/mainhighscorehigh.png", "คะแนน\nสูงสุด", 19),
    ("resources/menus/mainquitnormal.png", "ออก", 22),
    ("resources/menus/mainquithigh.png", "ออก", 22),
]


def read_saf_map(path: str):
    out = {}
    with open(path, "rb") as f:
        magic, ver, idx_off = struct.unpack("<4sII", f.read(12))
        f.seek(idx_off + 20)
        count, = struct.unpack("<I", f.read(4))
        for _ in range(count):
            off, size = struct.unpack("<II", f.read(8))
            _ = f.read(16)
            nlen, = struct.unpack("<H", f.read(2))
            name = f.read(nlen).rstrip(b"\x00").decode("ascii")
            pos = f.tell()
            f.seek(off)
            out[name.lower()] = f.read(size)
            f.seek(pos)
    return out


def make_thai_bubble(orig_png: bytes, label: str, font_size: int, is_high: bool) -> bytes:
    im = Image.open(io.BytesIO(orig_png)).convert("RGBA")
    w, h = im.size
    cx, cy = w / 2.0, h / 2.0
    # Preserve outer ~24% of radius (bubble rim + hover glow)
    r_max = min(w, h) * 0.5
    r_clean = r_max * 0.72

    px = im.load()
    base_tint = (165, 185, 185, 78) if is_high else (142, 160, 159, 55)
    for y in range(h):
        for x in range(w):
            dist = math.hypot(x - cx, y - cy)
            if dist < r_clean:
                px[x, y] = base_tint
            elif dist < r_clean + 4.0:
                t = (dist - r_clean) / 4.0
                orig = px[x, y]
                px[x, y] = tuple(int(base_tint[i] * (1 - t) + orig[i] * t) for i in range(4))

    font = ImageFont.truetype(TTF_PATH, font_size)
    draw = ImageDraw.Draw(im)
    lines = label.split("\n")
    line_heights = []
    line_widths = []
    for ln in lines:
        bb = draw.textbbox((0, 0), ln, font=font)
        line_widths.append(bb[2] - bb[0])
        line_heights.append(bb[3] - bb[1])

    spacing = 2
    total_h = sum(line_heights) + spacing * (len(lines) - 1)
    cur_y = cy - total_h / 2.0 - 2
    for ln, lw, lh in zip(lines, line_widths, line_heights):
        bb = draw.textbbox((0, 0), ln, font=font)
        tx = cx - lw / 2.0 - bb[0]
        ty = cur_y - bb[1]
        # Shadow
        draw.text((tx + 1, ty + 2), ln, font=font, fill=(12, 35, 55, 200))
        # Main fill
        fill = (245, 255, 252, 245) if is_high else (222, 242, 238, 235)
        draw.text((tx, ty), ln, font=font, fill=fill)
        cur_y += lh + spacing

    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


if __name__ == "__main__":
    os.makedirs("ThaiPatch/evidence/buttons", exist_ok=True)
    saf = read_saf_map(BACKUP_SAF)
    for path, label, fsize in BUTTON_SPECS:
        is_high = path.endswith("high.png")
        data = make_thai_bubble(saf[path], label, fsize, is_high)
        out_p = os.path.join("ThaiPatch/evidence/buttons", os.path.basename(path))
        with open(out_p, "wb") as f:
            f.write(data)
    print("Generated 10 Thai menu button PNGs in ThaiPatch/evidence/buttons/")
