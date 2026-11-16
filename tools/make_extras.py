import io
import os
import struct
from PIL import Image, ImageDraw, ImageFont

BACKUP_SAF = "ThaiPatch/backup/FFArchive.saf"
TTF_PATH = "LINE_Seed_Sans_TH_V1.003/Game/TTF/LINESeedSansTH_G_Bd.ttf"
OUT_DIR = "ThaiPatch/evidence/extras_th"


def read_saf_entry(target: str) -> bytes:
    with open(BACKUP_SAF, "rb") as f:
        magic, ver, idx_off = struct.unpack("<4sII", f.read(12))
        f.seek(idx_off + 20)
        count, = struct.unpack("<I", f.read(4))
        for _ in range(count):
            off, size = struct.unpack("<II", f.read(8))
            _ = f.read(16)
            nlen, = struct.unpack("<H", f.read(2))
            name = f.read(nlen).rstrip(b"\x00").decode("ascii")
            if name.lower() == target.lower():
                f.seek(off)
                return f.read(size)
    raise FileNotFoundError(target)


def make_andy_button_and_mask(raw_jpg: bytes, raw_mask: bytes):
    im = Image.open(io.BytesIO(raw_jpg)).convert("RGB")
    mask = Image.open(io.BytesIO(raw_mask)).convert("RGBA")
    w, h = im.size
    px = im.load()
    mpx = mask.load()

    # Erase "Andy" in y=0..27, x=24..88 in both JPG and alpha mask
    for y in range(0, 27):
        for x in range(24, 88):
            r, g, b = px[x, y]
            if r > 45 or g > 80 or b > 120:
                px[x, y] = px[8, y]
            # Erase white text silhouette outside the circle in mask
            mr, mg, mb, ma = mpx[x, y]
            if ma > 0 and y < 18:
                # Keep circle rim only if below text; clear top text overhang
                mpx[x, y] = (0, 0, 0, 0)

    font = ImageFont.truetype(TTF_PATH, 19)
    label = "แอนดี้"
    draw_tmp = ImageDraw.Draw(im)
    bb = draw_tmp.textbbox((0, 0), label, font=font)
    tw = bb[2] - bb[0]
    tx = (w - tw) / 2.0 - bb[0]
    ty = 2 - bb[1]

    draw = ImageDraw.Draw(im)
    draw.text((tx + 1, ty + 1), label, font=font, fill=(5, 18, 40))
    draw.text((tx, ty), label, font=font, fill=(255, 255, 255))

    # Draw crisp white mask for both shadow and text on _andybutton.png
    mdraw = ImageDraw.Draw(mask)
    mdraw.text((tx + 1, ty + 1), label, font=font, fill=(255, 255, 255, 255))
    mdraw.text((tx, ty), label, font=font, fill=(255, 255, 255, 255))

    buf_jpg = io.BytesIO()
    im.save(buf_jpg, format="JPEG", quality=95)
    buf_png = io.BytesIO()
    mask.save(buf_png, format="PNG")
    return buf_jpg.getvalue(), buf_png.getvalue()


def make_ability_meter(raw: bytes) -> bytes:
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = im.size
    px = im.load()
    # Clean left label area (x=0..65, y=0..h-4) using clean teal column at x=2
    for y in range(0, h - 3):
        bg = px[2, y]
        for x in range(0, 65):
            px[x, y] = bg
    font = ImageFont.truetype(TTF_PATH, 14)
    draw = ImageDraw.Draw(im)
    label = "พลัง"
    bb = draw.textbbox((0, 0), label, font=font)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]
    tx = (62 - tw) / 2.0 - bb[0]
    ty = (h - 4 - th) / 2.0 - bb[1]
    draw.text((tx + 1, ty + 1), label, font=font, fill=(25, 55, 55))
    draw.text((tx, ty), label, font=font, fill=(240, 245, 210))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def make_hud_bg(raw: bytes) -> bytes:
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = im.size
    px = im.load()

    def clear_box(x0, y0, x1, y1):
        # Sample clean teal strip at x=340..364 (clean across all y=12..76)
        for y in range(y0, y1):
            for x in range(x0, x1):
                sx = 340 + ((x - x0) % 24)
                px[x, y] = px[sx, y]

    clear_box(12, 12, 62, 42)     # MENU
    clear_box(8, 48, 74, 76)      # GROWTH
    clear_box(370, 12, 424, 42)   # SCORE
    clear_box(366, 48, 424, 76)   # ABILITY

    font = ImageFont.truetype(TTF_PATH, 16)
    draw = ImageDraw.Draw(im)

    def draw_lbl(cx, cy, text):
        bb = draw.textbbox((0, 0), text, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        tx = cx - tw / 2.0 - bb[0]
        ty = cy - th / 2.0 - bb[1]
        draw.text((tx + 1, ty + 1), text, font=font, fill=(20, 48, 48))
        draw.text((tx, ty), text, font=font, fill=(240, 245, 210))

    draw_lbl(36, 27, "เมนู")
    draw_lbl(40, 62, "เติบโต")
    draw_lbl(396, 27, "คะแนน")
    draw_lbl(395, 62, "พลัง")

    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def make_thought_bubble(raw: bytes, label: str, y_min: int, y_max: int, x_min: int, x_max: int, font_size: int) -> bytes:
    im = Image.open(io.BytesIO(raw)).convert("RGBA")
    px = im.load()
    # Sample clean interior fill pixel from upper-center of bubble
    bg = px[im.width // 2, im.height // 3]
    for y in range(y_min, y_max):
        for x in range(x_min, x_max):
            r, g, b, a = px[x, y]
            # Replace dark text pixels with interior fill
            if a > 100 and r < 140 and g < 140 and b < 140:
                px[x, y] = bg

    font = ImageFont.truetype(TTF_PATH, font_size)
    draw = ImageDraw.Draw(im)
    bb = draw.textbbox((0, 0), label, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    cx = (x_min + x_max) / 2.0
    cy = (y_min + y_max) / 2.0
    tx = cx - tw / 2.0 - bb[0]
    ty = cy - th / 2.0 - bb[1]
    draw.text((tx, ty), label, font=font, fill=(15, 15, 15, 255))

    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    andy_jpg, andy_png = make_andy_button_and_mask(
        read_saf_entry("resources/menus/screenextras/andybutton.jpg"),
        read_saf_entry("resources/menus/screenextras/_andybutton.png"),
    )
    abil = make_ability_meter(read_saf_entry("resources/menus/screenextras/abilitymeter.jpg"))
    hud = make_hud_bg(read_saf_entry("resources/hud/hudbg.jpg"))
    yummy = make_thought_bubble(read_saf_entry("resources/hud/playerbubblegreen.png"), "น่ากิน!", 56, 77, 18, 82, 16)
    run_b = make_thought_bubble(read_saf_entry("resources/hud/playerbubblered.png"), "หนีเร็ว!", 36, 58, 28, 72, 14)

    open(os.path.join(OUT_DIR, "andybutton.jpg"), "wb").write(andy_jpg)
    open(os.path.join(OUT_DIR, "_andybutton.png"), "wb").write(andy_png)
    open(os.path.join(OUT_DIR, "abilitymeter.jpg"), "wb").write(abil)
    open(os.path.join(OUT_DIR, "hudbg.jpg"), "wb").write(hud)
    open(os.path.join(OUT_DIR, "playerbubblegreen.png"), "wb").write(yummy)
    open(os.path.join(OUT_DIR, "playerbubblered.png"), "wb").write(run_b)
    print("Generated Thai screenextras + hudbg + thought bubbles")
