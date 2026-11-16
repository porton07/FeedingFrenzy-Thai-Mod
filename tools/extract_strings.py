import json
import os
import re
import struct

os.makedirs("ThaiPatch/source", exist_ok=True)

with open("ThaiPatch/backup/FFArchive.saf", "rb") as f:
    magic, ver, idx_off = struct.unpack("<4sII", f.read(12))
    f.seek(idx_off + 20)
    count, = struct.unpack("<I", f.read(4))
    extracted = {}
    total_strings = 0
    for _ in range(count):
        off, size = struct.unpack("<II", f.read(8))
        _ = f.read(16)
        nlen, = struct.unpack("<H", f.read(2))
        name = f.read(nlen).rstrip(b"\x00").decode("ascii")
        if not name.startswith("config/") or not name.endswith(".xml"):
            continue
        if name.startswith("config/fish/") or name.startswith("config/fx/") or name.startswith("config/sound/"):
            continue
        if name.endswith("stage.xml") or (name.endswith("layout.xml") and name != "config/maplayout.xml"):
            continue
        pos = f.tell()
        f.seek(off)
        text = f.read(size).decode("utf-8", errors="replace")
        f.seek(pos)

        matches = re.findall(r'string\s*=\s*"([^"]*)"', text, flags=re.S)
        cleaned = []
        for m in matches:
            s = m.strip()
            if not s or s.startswith("<<") or re.fullmatch(r"[0-9:./+-]+", s):
                continue
            cleaned.append(m)
        if cleaned:
            extracted[name] = cleaned
            total_strings += len(cleaned)

with open("ThaiPatch/source/extracted_strings.json", "w", encoding="utf-8") as out:
    json.dump(extracted, out, ensure_ascii=False, indent=2)

print(f"Files with strings: {len(extracted)}, Total string entries: {total_strings}")
for k, v in extracted.items():
    print(f"  {k}: {len(v)}")
