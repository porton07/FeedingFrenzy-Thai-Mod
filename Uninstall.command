#!/usr/bin/env bash
set -euo pipefail
MOD_DIR="$(cd "$(dirname "$0")" && pwd)"
for cand in "$MOD_DIR" "$(dirname "$MOD_DIR")" "$(dirname "$(dirname "$MOD_DIR")")" "$MOD_DIR/Contents/Resources/Data"; do
  if [ -d "$cand/FeedingFrenzyThai_Backup" ]; then
    [ -f "$cand/FeedingFrenzyThai_Backup/FFArchive.saf" ] && cp -f "$cand/FeedingFrenzyThai_Backup/FFArchive.saf" "$cand/FFArchive.saf"
    [ -f "$cand/FeedingFrenzyThai_Backup/gameSplash.jpg" ] && cp -f "$cand/FeedingFrenzyThai_Backup/gameSplash.jpg" "$cand/resources/splash/gameSplash.jpg"
    echo "ถอนการติดตั้งม็อดภาษาไทยเรียบร้อยแล้ว (Credit: porton007)"
    exit 0
  fi
done
echo "ไม่พบโฟลเดอร์สำรอง FeedingFrenzyThai_Backup"
exit 1
