param(
    [ValidateSet("Install", "Uninstall")]
    [string]$Mode = "Install"
)

$ErrorActionPreference = "Stop"

$ModRoot = $PSScriptRoot
$Manifest = Get-Content (Join-Path $ModRoot "manifest.json") -Raw -Encoding UTF8 | ConvertFrom-Json

# Locate game root (either current folder or parent folder)
$GameRoot = $null
foreach ($cand in @($ModRoot, (Split-Path $ModRoot -Parent), (Split-Path (Split-Path $ModRoot -Parent) -Parent))) {
    if ($cand -and (Test-Path (Join-Path $cand "FFArchive.saf"))) {
        $GameRoot = $cand
        break
    }
}
if (-not $GameRoot) {
    throw "ไม่พบไฟล์ FFArchive.saf กรุณาวางโฟลเดอร์ม็อดไว้ในโฟลเดอร์เกม Feeding Frenzy"
}

$BackupDir = Join-Path $GameRoot "FeedingFrenzyThai_Backup"
$SafPath = Join-Path $GameRoot "FFArchive.saf"
$SplashPath = Join-Path $GameRoot "resources\splash\gameSplash.jpg"

function Get-Sha256($Path) {
    return (Get-FileHash -Path $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

if ($Mode -eq "Uninstall") {
    $SafBak = Join-Path $BackupDir "FFArchive.saf"
    $SplashBak = Join-Path $BackupDir "gameSplash.jpg"
    if (Test-Path $SafBak) {
        Copy-Item $SafBak $SafPath -Force
        Write-Host "Restored FFArchive.saf"
    }
    if (Test-Path $SplashBak) {
        Copy-Item $SplashBak $SplashPath -Force
        Write-Host "Restored resources/splash/gameSplash.jpg"
    }
    Write-Host "ถอนการติดตั้งม็อดภาษาไทยเรียบร้อยแล้ว (Credit: porton007)" -ForegroundColor Green
    exit 0
}

# Install mode
$SafMeta = $Manifest.targets."FFArchive.saf"
$SplashMeta = $Manifest.targets."resources/splash/gameSplash.jpg"

$CurSafHash = Get-Sha256 $SafPath
if ($CurSafHash -eq $SafMeta.mod_sha256) {
    Write-Host "ติดตั้งม็อดภาษาไทยไว้เรียบร้อยแล้ว" -ForegroundColor Yellow
    exit 0
}
if ($CurSafHash -ne $SafMeta.orig_sha256) {
    throw "SHA-256 ของ FFArchive.saf ไม่ตรงกับต้นฉบับที่รองรับ ($CurSafHash)"
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
$SafBak = Join-Path $BackupDir "FFArchive.saf"
$SplashBak = Join-Path $BackupDir "gameSplash.jpg"
if (-not (Test-Path $SafBak)) { Copy-Item $SafPath $SafBak }
if ((Test-Path $SplashPath) -and (-not (Test-Path $SplashBak))) { Copy-Item $SplashPath $SplashBak }

# Apply RITH GZip binary delta to FFArchive.saf
$DeltaGz = Join-Path $ModRoot $SafMeta.delta
$TmpSaf = "$SafPath.tmp"
try {
    $srcBytes = [System.IO.File]::ReadAllBytes($SafBak)
    $fsIn = [System.IO.File]::OpenRead($DeltaGz)
    $gz = New-Object System.IO.Compression.GZipStream($fsIn, [System.IO.Compression.CompressionMode]::Decompress)
    $br = New-Object System.IO.BinaryReader($gz)
    $magic = [System.Text.Encoding]::ASCII.GetString($br.ReadBytes(4))
    if ($magic -ne "RITH") { throw "Invalid delta header: $magic" }

    $fsOut = [System.IO.File]::Create($TmpSaf)
    try {
        while ($true) {
            $op = $br.ReadByte()
            if ($op -eq 0) { break }
            elseif ($op -eq 1) {
                $off = $br.ReadUInt32()
                $len = $br.ReadUInt32()
                $fsOut.Write($srcBytes, [int]$off, [int]$len)
            }
            elseif ($op -eq 2) {
                $len = $br.ReadUInt32()
                $lit = $br.ReadBytes([int]$len)
                $fsOut.Write($lit, 0, $lit.Length)
            }
            else { throw "Unknown delta op: $op" }
        }
    } finally {
        $fsOut.Dispose()
        $br.Dispose()
        $gz.Dispose()
        $fsIn.Dispose()
    }

    $NewHash = Get-Sha256 $TmpSaf
    if ($NewHash -ne $SafMeta.mod_sha256) {
        throw "Verification failed: expected $($SafMeta.mod_sha256), got $NewHash"
    }
    Move-Item $TmpSaf $SafPath -Force

    $ModSplashSrc = Join-Path $ModRoot $SplashMeta.file
    if ((Test-Path $ModSplashSrc) -and (Test-Path (Split-Path $SplashPath -Parent))) {
        Copy-Item $ModSplashSrc $SplashPath -Force
    }
    Write-Host "ติดตั้งม็อดภาษาไทย Feeding Frenzy สำเร็จแล้ว! (แปลภาษาไทยโดย porton007)" -ForegroundColor Green
} catch {
    if (Test-Path $TmpSaf) { Remove-Item $TmpSaf -Force }
    throw
}
