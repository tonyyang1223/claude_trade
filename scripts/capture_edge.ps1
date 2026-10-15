Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
    
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    
    [DllImport("user32.dll")]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left, Top, Right, Bottom;
    }
}
"@

# 找 Edge 窗口
$edgeWindow = [Win32]::FindWindow("Chrome_WidgetWin_1", $null)
if ($edgeWindow -eq [IntPtr]::Zero) {
    Write-Output "没找到 Edge 窗口"
    exit
}

# 激活 Edge 窗口
[Win32]::SetForegroundWindow($edgeWindow) | Out-Null
Start-Sleep -Seconds 1

# 获取窗口位置
$rect = New-Object Win32+RECT
[Win32]::GetWindowRect($edgeWindow, [ref]$rect) | Out-Null

$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top

Write-Output "Edge 窗口位置: $($rect.Left), $($rect.Top) - $($rect.Right), $($rect.Bottom)"
Write-Output "尺寸: ${width}x${height}"

# 截取窗口
$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)

# 保存截图
$savePath = "D:\gitpro\claude_trading\reports\edge_screenshot.png"
$bitmap.Save($savePath, [System.Drawing.Imaging.ImageFormat]::Png)

Write-Output "截图已保存到: $savePath"

$graphics.Dispose()
$bitmap.Dispose()
