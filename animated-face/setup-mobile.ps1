# Venom AI Mobile Setup Script
# Run this to set up Capacitor for mobile build

Write-Host "🚀 Venom AI Mobile Setup" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan
Write-Host ""

# Check if in correct directory
if (-not (Test-Path "package.json")) {
    Write-Host "❌ Error: Run this script from the animated-face directory" -ForegroundColor Red
    Write-Host "   cd animated-face" -ForegroundColor Yellow
    exit 1
}

# Step 1: Get PC's IP Address
Write-Host "📡 Step 1: Getting your PC's IP address..." -ForegroundColor Green
$ipAddress = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -like "*Wi-Fi*" -or $_.InterfaceAlias -like "*Ethernet*"} | Select-Object -First 1).IPAddress

if ($ipAddress) {
    Write-Host "   Your PC's IP: $ipAddress" -ForegroundColor Cyan
} else {
    Write-Host "   ⚠️  Could not auto-detect IP. Please check manually with 'ipconfig'" -ForegroundColor Yellow
    $ipAddress = "192.168.1.100"
}

# Step 2: Install Capacitor
Write-Host ""
Write-Host "📦 Step 2: Installing Capacitor packages..." -ForegroundColor Green
npm install @capacitor/core @capacitor/cli @capacitor/android

# Step 3: Create .env.local
Write-Host ""
Write-Host "⚙️  Step 3: Creating .env.local configuration..." -ForegroundColor Green
$envContent = @"
# API Configuration for Mobile
# Your PC's IP address (update if changed)
NEXT_PUBLIC_API_URL=http://${ipAddress}:5000

# Instructions:
# 1. Make sure your phone and PC are on the SAME WiFi network
# 2. Keep the Python backend running (python core.py)
# 3. If IP changes, update this file and rebuild
"@

Set-Content -Path ".env.local" -Value $envContent
Write-Host "   ✅ Created .env.local with IP: $ipAddress" -ForegroundColor Cyan

# Step 4: Initialize Capacitor (if not already done)
if (-not (Test-Path "capacitor.config.ts")) {
    Write-Host ""
    Write-Host "🔧 Step 4: Initializing Capacitor..." -ForegroundColor Green
    Write-Host "   Please answer the prompts:" -ForegroundColor Yellow
    npx cap init
} else {
    Write-Host ""
    Write-Host "✅ Capacitor already initialized" -ForegroundColor Cyan
}

# Step 5: Update package.json scripts
Write-Host ""
Write-Host "📝 Step 5: Checking package.json scripts..." -ForegroundColor Green
Write-Host "   Make sure you have these scripts:" -ForegroundColor Yellow
Write-Host '   "build:mobile": "next build && npx cap sync"' -ForegroundColor Gray
Write-Host '   "android": "npx cap open android"' -ForegroundColor Gray

# Step 6: Instructions
Write-Host ""
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Start the Python backend:" -ForegroundColor White
Write-Host "      cd ..\diy_help\new_method" -ForegroundColor Gray
Write-Host "      python core.py" -ForegroundColor Gray
Write-Host ""
Write-Host "   2. Test on phone browser:" -ForegroundColor White
Write-Host "      http://${ipAddress}:5000/api/state" -ForegroundColor Gray
Write-Host ""
Write-Host "   3. Build the app:" -ForegroundColor White
Write-Host "      npm run build" -ForegroundColor Gray
Write-Host "      npx cap add android" -ForegroundColor Gray
Write-Host "      npx cap sync android" -ForegroundColor Gray
Write-Host ""
Write-Host "   4. Open in Android Studio:" -ForegroundColor White
Write-Host "      npx cap open android" -ForegroundColor Gray
Write-Host ""
Write-Host "   5. Build APK in Android Studio:" -ForegroundColor White
Write-Host "      Build → Build Bundle(s) / APK(s) → Build APK(s)" -ForegroundColor Gray
Write-Host ""
Write-Host "⚠️  Important:" -ForegroundColor Yellow
Write-Host "   - Phone and PC must be on SAME WiFi" -ForegroundColor White
Write-Host "   - Keep Python backend running while using app" -ForegroundColor White
Write-Host "   - Allow Python through Windows Firewall when prompted" -ForegroundColor White
Write-Host ""
Write-Host "📖 Full guide: See MOBILE_BUILD_GUIDE.md" -ForegroundColor Cyan
