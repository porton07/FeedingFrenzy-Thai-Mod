param(
    [string]$MenuOutput = "ThaiPatch\evidence\thai_menu_test.png",
    [string]$OptionsOutput = "ThaiPatch\evidence\thai_options_test.png",
    [int]$WaitSeconds = 6
)

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinCap {
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr hWnd, ref POINT lpPoint);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint nFlags);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, int dx, int dy, uint dwData, IntPtr dwExtraInfo);
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
}
"@

function Capture-Hwnd($hwnd, $path) {
    $rect = New-Object WinCap+RECT
    [WinCap]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
    $w = $rect.Right - $rect.Left
    $h = $rect.Bottom - $rect.Top
    $bmp = New-Object System.Drawing.Bitmap $w, $h
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $g.GetHdc()
    [WinCap]::PrintWindow($hwnd, $hdc, 2) | Out-Null
    $g.ReleaseHdc($hdc)
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose()
    $bmp.Dispose()
    Write-Output "Captured ${w}x${h} to $path"
}

$proc = Start-Process -FilePath ".\FeedingFrenzy.exe" -PassThru
Start-Sleep -Seconds $WaitSeconds

$script:targetHwnd = [IntPtr]::Zero
$cb = [WinCap+EnumWindowsProc]{
    param($hwnd, $lp)
    [uint32]$pidOut = 0
    [WinCap]::GetWindowThreadProcessId($hwnd, [ref]$pidOut) | Out-Null
    if ($pidOut -eq $proc.Id -and [WinCap]::IsWindowVisible($hwnd)) {
        $r = New-Object WinCap+RECT
        [WinCap]::GetWindowRect($hwnd, [ref]$r) | Out-Null
        if (($r.Right - $r.Left) -gt 200) {
            $script:targetHwnd = $hwnd
            return $false
        }
    }
    return $true
}
[WinCap]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null

if ($script:targetHwnd -ne [IntPtr]::Zero) {
    [WinCap]::SetForegroundWindow($script:targetHwnd) | Out-Null
    # Hover over New Game (252, 164) to show helper text
    $pt = New-Object WinCap+POINT
    $pt.X = 252; $pt.Y = 164
    [WinCap]::ClientToScreen($script:targetHwnd, [ref]$pt) | Out-Null
    [WinCap]::SetCursorPos($pt.X, $pt.Y) | Out-Null
    Start-Sleep -Milliseconds 700
    Capture-Hwnd $script:targetHwnd $MenuOutput

    # Click Game Options (257, 324)
    $pt2 = New-Object WinCap+POINT
    $pt2.X = 257; $pt2.Y = 324
    [WinCap]::ClientToScreen($script:targetHwnd, [ref]$pt2) | Out-Null
    [WinCap]::SetCursorPos($pt2.X, $pt2.Y) | Out-Null
    Start-Sleep -Milliseconds 300
    [WinCap]::mouse_event(0x0002, 0, 0, 0, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [WinCap]::mouse_event(0x0004, 0, 0, 0, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 800
    Capture-Hwnd $script:targetHwnd $OptionsOutput
} else {
    Write-Output "Window not found (exited=$($proc.HasExited))"
}

if (-not $proc.HasExited) {
    Stop-Process -Id $proc.Id -Force
}
