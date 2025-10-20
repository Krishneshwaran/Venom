# 📱 Quick Start: Venom AI Mobile App

## TL;DR - Will It Work?

**YES! ✅** Your Venom AI frontend will work as a mobile APK with these requirements:

### Requirements:
1. ✅ Phone and PC on **SAME WiFi network**
2. ✅ Python backend **running on PC** (`core.py`)
3. ✅ PC's **IP address** configured in app
4. ✅ **Windows Firewall** allows Python

## 🚀 Quick Setup (5 minutes)

### 1. Run Setup Script
```powershell
cd "d:\Vijay TV\Venom\animated-face"
.\setup-mobile.ps1
```

This will:
- Install Capacitor
- Detect your PC's IP
- Create `.env.local` config
- Guide you through initialization

### 2. Get Your PC's IP
```powershell
ipconfig
```
Look for **IPv4 Address** (e.g., `192.168.1.100`)

### 3. Install Capacitor Packages
```bash
npm install @capacitor/core @capacitor/cli @capacitor/android
```

### 4. Initialize Capacitor
```bash
npx cap init
```
- App name: `Venom AI`
- Package ID: `com.venomvoice.ai`
- Web directory: `out`

### 5. Build for Mobile
```bash
npm run build
npx cap add android
npx cap sync android
```

### 6. Open in Android Studio
```bash
npx cap open android
```

### 7. Build APK
In Android Studio:
**Build → Build Bundle(s) / APK(s) → Build APK(s)**

## 🧪 Test Before Building

### Test 1: Check Backend API
Start backend:
```bash
cd ..\diy_help\new_method
python core.py
```

Visit in **phone browser**:
```
http://YOUR_PC_IP:5000/api/state
```

Should show JSON data ✅

### Test 2: Test Frontend
```bash
npm run dev
```

Visit in **phone browser**:
```
http://YOUR_PC_IP:3000
```

Eyes should respond to voice activation ✅

## 🎯 How It Works

```
You say "hey venom"
    ↓
PC microphone picks it up
    ↓
Python updates API state (is_active: true)
    ↓
Mobile app polls API every 500ms
    ↓
Detects is_active: true
    ↓
Eyes OPEN! 👀
```

## 📡 Network Flow

```
[Phone] ←──WiFi──→ [Router] ←──WiFi──→ [PC]
                                        ↓
                                   Flask API :5000
                                        ↓
                                   Venom AI Backend
```

## ⚠️ Important Notes

### What's Already Done ✅
- API server configured to accept external connections (`host='0.0.0.0'`)
- Frontend updated to use environment variable for API URL
- Next.js configured for static export
- CORS enabled on backend

### What You Need to Do 📝
1. Run setup script or install Capacitor manually
2. Configure your PC's IP in `.env.local`
3. Ensure phone and PC on same WiFi
4. Allow Python through Windows Firewall
5. Keep backend running while using app

### Limitations ⚠️
- **Requires PC running**: Backend must be active
- **Same network only**: Phone must be on same WiFi as PC
- **IP changes**: If PC's IP changes, rebuild app with new IP

## 🌐 Alternative: Cloud Deployment

To make the app work **without PC running**:

### Deploy Backend to Cloud:
1. **Heroku** (free tier)
2. **Railway** (free tier)
3. **Render** (free tier)
4. **PythonAnywhere** (free tier)

Update `.env.local`:
```bash
NEXT_PUBLIC_API_URL=https://your-app.herokuapp.com
```

Then the app works **anywhere**, no PC needed! 🌍

## 🐛 Troubleshooting

### Can't connect from phone
- Check PC IP: `ipconfig`
- Visit `http://PC_IP:5000/api/health` in phone browser
- Verify same WiFi network
- Check Windows Firewall

### Build errors
- Install Java JDK 17+
- Update Android Studio
- Run `.\gradlew clean` in `android/` folder

### Eyes don't animate
- Check API is responding
- Open Chrome DevTools on phone (USB debugging)
- Check console logs

## 📖 Full Documentation

See `MOBILE_BUILD_GUIDE.md` for complete step-by-step instructions.

## Summary

**YES, it works perfectly with Capacitor!** The mobile app will:
- 👀 Open eyes when you say "hey venom" on PC
- 😴 Close eyes when Venom deactivates
- 📱 Show real-time status of Venom AI
- 🔄 Update every 500ms via API polling

The only requirement is keeping your PC's backend running and both devices on the same WiFi network.

For a truly standalone mobile experience, deploy the backend to a cloud service! 🚀
