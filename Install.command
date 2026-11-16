#!/usr/bin/env bash
set -euo pipefail
MOD_DIR="$(cd "$(dirname "$0")" && pwd)"
GAME_DIR=""
for cand in "$MOD_DIR" "$(dirname "$MOD_DIR")" "$(dirname "$(dirname "$MOD_DIR")")" "$MOD_DIR/Contents/Resources/Data"; do
  if [ -f "$cand/FFArchive.saf" ]; then
    GAME_DIR="$cand"
    break
  fi
done
if [ -z "$GAME_DIR" ]; then
  echo "ไม่พบ FFArchive.saf กรุณาวางโฟลเดอร์ม็อดไว้ในโฟลเดอร์เกม (หรือ Contents/Resources/Data บน macOS)"
  exit 1
fi
python3 - "$MOD_DIR" "$GAME_DIR" <<'PY'
import gzip, hashlib, json, os, shutil, struct, sys
mod_dir, game_dir = sys.argv[1], sys.argv[2]
manifest = json.load(open(os.path.join(mod_dir, "manifest.json"), encoding="utf-8"))
saf_meta = manifest["targets"]["FFArchive.saf"]
saf_path = os.path.join(game_dir, "FFArchive.saf")
bak_dir = os.path.join(game_dir, "FeedingFrenzyThai_Backup")
os.makedirs(bak_dir, exist_ok=True)
saf_bak = os.path.join(bak_dir, "FFArchive.saf")
if not os.path.exists(saf_bak):
    shutil.copy2(saf_path, saf_bak)
src = open(saf_bak, "rb").read()
tmp = saf_path + ".tmp"
with gzip.open(os.path.join(mod_dir, saf_meta["delta"]), "rb") as gz, open(tmp, "wb") as out:
    assert gz.read(4) == b"RITH"
    while True:
        op = gz.read(1)[0]
        if op == 0: break
        elif op == 1:
            off, length = struct.unpack("<II", gz.read(8))
            out.write(src[off:off+length])
        elif op == 2:
            length, = struct.unpack("<I", gz.read(4))
            out.write(gz.read(length))
        else: raise RuntimeError(f"Bad op {op}")
assert hashlib.sha256(open(tmp, "rb").read()).hexdigest() == saf_meta["mod_sha256"]
shutil.move(tmp, saf_path)
splash_dst = os.path.join(game_dir, "resources", "splash", "gameSplash.jpg")
if os.path.exists(splash_dst):
    splash_bak = os.path.join(bak_dir, "gameSplash.jpg")
    if not os.path.exists(splash_bak): shutil.copy2(splash_dst, splash_bak)
    shutil.copy2(os.path.join(mod_dir, manifest["targets"]["resources/splash/gameSplash.jpg"]["file"]), splash_dst)
print("ติดตั้งม็อดภาษาไทยสำเร็จ! (Credit: porton007)")
PY
