import io
import json
import math
import os
import re
import struct
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

BACKUP_SAF = "ThaiPatch/backup/FFArchive.saf"
OUTPUT_SAF = "FFArchive.saf"
TTF_PATH = "LINE_Seed_Sans_TH_V1.003/Game/TTF/LINESeedSansTH_G_Bd.ttf"
BUTTONS_DIR = "ThaiPatch/evidence/buttons"

# Seeded MD5 used by FeedingFrenzy.exe (FUN_0045e2e0 / FUN_0045e330 / FUN_0045e430)
S = [7, 12, 17, 22] * 4 + [5, 9, 14, 20] * 4 + [4, 11, 16, 23] * 4 + [6, 10, 15, 21] * 4
K = [int(abs(math.sin(i + 1)) * 2**32) & 0xFFFFFFFF for i in range(64)]


def seeded_md5(data: bytes, seed: int = 0x53414646) -> bytes:
    a0 = (seed * 0xB + 0x67452301) & 0xFFFFFFFF
    b0 = (seed * 0x47 + 0xEFCDAB89) & 0xFFFFFFFF
    c0 = (seed * 0x25 + 0x98BADCFE) & 0xFFFFFFFF
    d0 = (seed * 0x61 + 0x10325476) & 0xFFFFFFFF
    orig_len_bits = (len(data) * 8) & 0xFFFFFFFFFFFFFFFF
    msg = bytearray(data)
    msg.append(0x80)
    while len(msg) % 64 != 56:
        msg.append(0)
    msg += struct.pack("<Q", orig_len_bits)
    for chunk_off in range(0, len(msg), 64):
        M = struct.unpack("<16I", msg[chunk_off : chunk_off + 64])
        A, B, C, D = a0, b0, c0, d0
        for i in range(64):
            if i < 16:
                F = (B & C) | ((~B) & D)
                g = i
            elif i < 32:
                F = (D & B) | ((~D) & C)
                g = (5 * i + 1) % 16
            elif i < 48:
                F = B ^ C ^ D
                g = (3 * i + 5) % 16
            else:
                F = C ^ (B | (~D))
                g = (7 * i) % 16
            F = (F + A + K[i] + M[g]) & 0xFFFFFFFF
            A, D, C, B = D, C, B, (B + (((F << S[i]) | (F >> (32 - S[i]))) & 0xFFFFFFFF)) & 0xFFFFFFFF
        a0 = (a0 + A) & 0xFFFFFFFF
        b0 = (b0 + B) & 0xFFFFFFFF
        c0 = (c0 + C) & 0xFFFFFFFF
        d0 = (d0 + D) & 0xFFFFFFFF
    return struct.pack("<4I", a0, b0, c0, d0)


def read_saf_all(path: str):
    with open(path, "rb") as f:
        magic, ver, idx_off = struct.unpack("<4sII", f.read(12))
        assert magic == b"FFAS" and ver == 1
        f.seek(idx_off + 20)
        count, = struct.unpack("<I", f.read(4))
        files = []
        for _ in range(count):
            off, size = struct.unpack("<II", f.read(8))
            h = f.read(16)
            nlen, = struct.unpack("<H", f.read(2))
            name = f.read(nlen).rstrip(b"\x00").decode("ascii")
            pos = f.tell()
            f.seek(off)
            data = f.read(size)
            f.seek(pos)
            files.append([name, data, h])
    return files


def write_saf_all(path: str, files):
    with open(path, "wb") as f:
        f.write(b"FFAS")
        f.write(struct.pack("<II", 1, 0))
        toc_entries = []
        for name, data, _ in files:
            off = f.tell()
            f.write(data)
            h = seeded_md5(data)
            toc_entries.append((name, off, len(data), h))

        idx_off = f.tell()
        toc_buf = bytearray()
        toc_buf += struct.pack("<I", len(toc_entries))
        for name, off, size, h in toc_entries:
            name_b = name.encode("ascii") + b"\x00"
            toc_buf += struct.pack("<II", off, size)
            toc_buf += h
            toc_buf += struct.pack("<H", len(name_b))
            toc_buf += name_b

        toc_hash = seeded_md5(bytes(toc_buf))
        f.write(struct.pack("<I", 1))
        f.write(toc_hash)
        f.write(toc_buf)

        f.seek(8)
        f.write(struct.pack("<I", idx_off))


CP874_CODES = []
for b in range(0xA1, 0xFC):
    try:
        ch = bytes([b]).decode("cp874")
        CP874_CODES.append((b, ch))
    except UnicodeDecodeError:
        pass

TOP_VOWELS = {0xD1, 0xD4, 0xD5, 0xD6, 0xD7, 0xE7, 0xEC, 0xED}
TONE_MARKS = {0xE8, 0xE9, 0xEA, 0xEB}
BOTTOM_VOWELS = {0xD8, 0xD9, 0xDA}
COMBINING_CODES = TOP_VOWELS | TONE_MARKS | BOTTOM_VOWELS


def render_thai_glyph(ch: str, code: int, font: ImageFont.FreeTypeFont, cell_h: int, ascent: int, fill_rgba):
    pad = 12
    tmp_w = cell_h * 2 + pad * 2
    tmp_h = cell_h + pad * 2
    tmp = Image.new("RGBA", (tmp_w, tmp_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tmp)

    mbbox = draw.textbbox((0, 0), "ม", font=font)
    m_top = mbbox[1]
    m_bot = mbbox[3]
    base_y = pad + ascent - m_bot

    draw.text((pad, base_y), ch, font=font, fill=fill_rgba)
    bbox = tmp.getbbox()
    if bbox is None:
        return Image.new("RGBA", (1, cell_h), (0, 0, 0, 0)), 0

    if code in TOP_VOWELS or code in TONE_MARKS or code in BOTTOM_VOWELS:
        glyph_crop = tmp.crop(bbox)
        gw, gh = glyph_crop.size
        cell = Image.new("RGBA", (gw + 2, cell_h), (0, 0, 0, 0))

        cons_top_in_cell = max(2, ascent - (m_bot - m_top))
        if code in TOP_VOWELS:
            target_y = max(1, cons_top_in_cell - gh - 1)
            min_tone_zone = max(3, int(cell_h * 0.14))
            if target_y < min_tone_zone and cons_top_in_cell - gh >= min_tone_zone:
                target_y = min_tone_zone
        elif code in TONE_MARKS:
            target_y = 0
        else:
            target_y = min(cell_h - gh, ascent + 1)

        cell.paste(glyph_crop, (1, max(0, min(cell_h - gh, target_y))), glyph_crop)
        return cell, 0
    else:
        x0 = max(0, bbox[0] - 1)
        x1 = min(tmp_w, bbox[2] + 1)
        if bbox[1] < pad:
            shift = pad - bbox[1]
            tmp2 = Image.new("RGBA", (tmp_w, tmp_h), (0, 0, 0, 0))
            draw2 = ImageDraw.Draw(tmp2)
            draw2.text((pad, base_y + min(shift, 2)), ch, font=font, fill=fill_rgba)
            tmp = tmp2
        cell = tmp.crop((x0, pad, x1, pad + cell_h))
        left_overhang = max(0, pad - x0) if code == 0xD3 else 0
        return cell, left_overhang


def extend_bitmap_font(xml_bytes: bytes, png_bytes: bytes, font_size: int, fill_rgba, make_bold_outline=False):
    xml_text = xml_bytes.decode("utf-8", errors="replace")
    root = ET.fromstring(xml_text)
    height = int(root.attrib["height"])
    gap = int(root.attrib.get("gap", "0"))
    ascent = int(root.attrib.get("ascent", str(int(height * 0.75))))

    orig_im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    img_w, img_h = orig_im.size

    cur_x = 0
    cur_y = 0
    for g in root.findall("glyph"):
        b = int(g.attrib["b"])
        if img_w < gap * 2 + b + cur_x:
            cur_x = 0
            cur_y += height + gap * 2
        cur_x += b + gap * 2

    tt_font = ImageFont.truetype(TTF_PATH, font_size)

    thai_glyphs = []
    for code, ch in CP874_CODES:
        gim, left_overhang = render_thai_glyph(ch, code, tt_font, height, ascent, fill_rgba)
        if make_bold_outline:
            out = Image.new("RGBA", (gim.width + 1, gim.height), (0, 0, 0, 0))
            alpha = gim.split()[3]
            shadow = Image.new("RGBA", gim.size, (20, 30, 50, 180))
            out.paste(shadow, (1, 1), alpha)
            out.paste(gim, (0, 0), gim)
            gim = out
        bw = gim.width
        if img_w < gap * 2 + bw + cur_x:
            cur_x = 0
            cur_y += height + gap * 2
        gx = cur_x + gap
        gy = cur_y + gap
        cur_x += bw + gap * 2

        if code in COMBINING_CODES:
            a_val = -bw
            c_val = 0
        else:
            a_val = -left_overhang
            c_val = 1
        thai_glyphs.append((code, a_val, bw, c_val, gx, gy, gim))

    needed_h = max(img_h, cur_y + height + gap * 2)
    new_im = Image.new("RGBA", (img_w, needed_h), (0, 0, 0, 0))
    new_im.paste(orig_im, (0, 0))
    for code, a_val, bw, c_val, gx, gy, gim in thai_glyphs:
        new_im.paste(gim, (gx, gy), gim)

    lines = ["   <!-- Thai cp874 -->"]
    for code, a_val, bw, c_val, gx, gy, gim in thai_glyphs:
        lines.append(f'   <glyph char="{code}" a="{a_val}" b="{bw}" c="{c_val}" />')
    insert_block = "\n".join(lines) + "\n</font>"
    new_xml = re.sub(r"</font>\s*$", insert_block, xml_text)

    out_png = io.BytesIO()
    new_im.save(out_png, format="PNG")
    return new_xml.encode("utf-8"), out_png.getvalue(), new_im


def apply_translations_to_xml(xml_bytes: bytes, mapping: dict) -> bytes:
    text = xml_bytes.decode("latin1")

    def repl_fn(match):
        orig = match.group(1)
        if orig in mapping:
            th_latin1 = mapping[orig].encode("cp874").decode("latin1")
            return f'string="{th_latin1}"'
        return match.group(0)

    new_text = re.sub(r'string\s*=\s*"([^"]*)"', repl_fn, text, flags=re.S)
    return new_text.encode("latin1")


def main():
    files = read_saf_all(BACKUP_SAF)
    file_map = {name.lower(): i for i, (name, _, _) in enumerate(files)}

    # 1. Extend all 6 game text fonts with LINE Seed Sans TH Game Bold
    font_specs = [
        ("resources/menus/menufont", 24, (255, 255, 255, 255), True),
        ("resources/menus/infotext14", 13, (255, 255, 255, 255), False),
        ("resources/hud/buttonfont", 18, (10, 68, 38, 255), False),
        ("resources/hud/textfont", 16, (255, 255, 255, 255), False),
        ("resources/hud/frenzyfontwhite", 30, (255, 255, 255, 255), True),
        ("resources/hud/hudfont", 13, (255, 255, 255, 255), False),
    ]
    for base, fsize, fill, outline in font_specs:
        xi = file_map[base + ".xml"]
        pi = file_map[base + ".png"]
        new_xml, new_png, preview_im = extend_bitmap_font(files[xi][1], files[pi][1], fsize, fill, outline)
        files[xi][1] = new_xml
        files[pi][1] = new_png
        print(f"Updated {base}: atlas={preview_im.size}")

    # 2. Replace 10 main menu bubble button PNGs + screenExtras JPGs
    if os.path.isdir(BUTTONS_DIR):
        for fn in os.listdir(BUTTONS_DIR):
            if fn.endswith(".png"):
                key = f"resources/menus/{fn.lower()}"
                if key in file_map:
                    with open(os.path.join(BUTTONS_DIR, fn), "rb") as bf:
                        files[file_map[key]][1] = bf.read()
                    print(f"Replaced button {key}")

    extras_dir = "ThaiPatch/evidence/extras_th"
    hud_names = {"hudbg.jpg", "playerbubblegreen.png", "playerbubblered.png"}
    if os.path.isdir(extras_dir):
        for fn in os.listdir(extras_dir):
            fl = fn.lower()
            if fl in hud_names and f"resources/hud/{fl}" in file_map:
                with open(os.path.join(extras_dir, fn), "rb") as ef:
                    files[file_map[f"resources/hud/{fl}"]][1] = ef.read()
                print(f"Replaced hud resources/hud/{fl}")
            elif fl.endswith(".jpg") or fl.endswith(".png"):
                key = f"resources/menus/screenextras/{fl}"
                if key in file_map:
                    with open(os.path.join(extras_dir, fn), "rb") as ef:
                        files[file_map[key]][1] = ef.read()
                    print(f"Replaced extra {key}")

    # 3. Merge and apply all 3 translation batches (65 XML files)
    all_translations = {}
    for batch_fn in ["batch1_ui_th.json", "batch2_stages_th.json", "batch3_funfacts_th.json"]:
        with open(os.path.join("ThaiPatch/source", batch_fn), "r", encoding="utf-8") as f:
            batch = json.load(f)
            for k, v in batch.items():
                all_translations[k.lower()] = v

    patched_count = 0
    for xml_path, mapping in all_translations.items():
        if xml_path in file_map:
            idx = file_map[xml_path]
            files[idx][1] = apply_translations_to_xml(files[idx][1], mapping)
            patched_count += 1
        else:
            print(f"WARNING: {xml_path} not found in FFArchive.saf")

    print(f"Patched {patched_count} XML files.")
    write_saf_all(OUTPUT_SAF, files)
    print(f"Wrote {OUTPUT_SAF} ({os.path.getsize(OUTPUT_SAF)} bytes)")


if __name__ == "__main__":
    main()
