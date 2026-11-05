# PowerShell script to create icon file
# Run: powershell -ExecutionPolicy Bypass -File create_icon.ps1

Add-Type -AssemblyName System.Drawing

# Create a bitmap
$bmp = New-Object System.Drawing.Bitmap(256, 256)
$graphics = [System.Drawing.Graphics]::FromImage($bmp)
$graphics.Clear([System.Drawing.Color]::FromArgb(0, 120, 215))

# Draw text
$font = New-Object System.Drawing.Font("Arial", 36, [System.Drawing.FontStyle]::Bold)
$brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
$graphics.DrawString("BTC", $font, $brush, 80, 100)

$fontSmall = New-Object System.Drawing.Font("Arial", 18, [System.Drawing.FontStyle]::Regular)
$graphics.DrawString("Bybit", $fontSmall, $brush, 95, 160)

# Save as icon
$icon = [System.Drawing.Icon]::FromHandle($bmp.GetHicon())
$fileStream = New-Object System.IO.FileStream("icon.ico", [System.IO.FileMode]::Create)
$icon.Save($fileStream)
$fileStream.Close()

Write-Host "Icon created: icon.ico" -ForegroundColor Green