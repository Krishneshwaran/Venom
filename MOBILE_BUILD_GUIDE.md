# 📱 Building Venom AI Mobile App with Capacitor

## Prerequisites
- Node.js installed
- Android Studio (for Android APK)
- Java JDK 17+ installed

## Step-by-Step Setup

### 1. Install Capacitor

```bash
cd "d:\Vijay TV\Venom\animated-face"
npm install @capacitor/core @capacitor/cli
npm install @capacitor/android
```

### 2. Initialize Capacitor

```bash
npx cap init
```

When prompted:
- **App name**: `Venom AI`
- **App package ID**: `com.venomvoice.ai` (or your preference)
- **Web directory**: `out` (for Next.js static export)

### 3. Configure Next.js for Static Export

Update `next.config.mjs`:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: {
    unoptimized: true,
  },
  trailingSlash: true,
}

export default nextConfig
```

### 4. Update package.json Scripts

Add these scripts:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "build:mobile": "next build && npx cap sync",
    "android": "npx cap open android",
    "sync": "npx cap sync"
  }
}
```

### 5. Get Your PC's IP Address

**Windows PowerShell:**
```powershell
ipconfig
```

Look for **"Wireless LAN adapter Wi-Fi"** or **"Ethernet adapter"**:
```
IPv4 Address. . . . . . . . . . . : 192.168.1.100
```

**That's your IP!** (Example: `192.168.1.100`)

### 6. Configure API URL

Edit `.env.local`:
```bash
# Replace with YOUR PC's IP address
NEXT_PUBLIC_API_URL=http://192.168.1.100:5000
```

### 7. Update Backend to Accept External Connections

The Flask server needs to accept connections from your phone.

**It's already configured!** In `api_server.py`:
```python
app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
```

`host='0.0.0.0'` means it accepts connections from any device on your network.

### 8. Configure Windows Firewall

Allow Python through Windows Firewall:

**Option A: Automatic (when prompted)**
- When you run `core.py`, Windows may ask for permission
- Click "Allow access"

**Option B: Manual**
1. Windows Security → Firewall & network protection
2. Allow an app through firewall
3. Find Python or add it manually
4. Check both "Private" and "Public" networks

### 9. Build and Sync

```bash
# Build Next.js app
npm run build

# Add Android platform (first time only)
npx cap add android

# Sync changes
npx cap sync android
```

### 10. Configure Android App

Edit `android/app/src/main/AndroidManifest.xml` to add internet permission:

```xml
<manifest>
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <!-- other permissions -->
</manifest>
```

### 11. Open in Android Studio

```bash
npx cap open android
```

Android Studio will open the project.

### 12. Build APK

In Android Studio:
1. **Build** → **Build Bundle(s) / APK(s)** → **Build APK(s)**
2. Wait for build to complete
3. Click **"locate"** to find the APK
4. Transfer APK to your phone and install

Or use command line:
```bash
cd android
.\gradlew assembleDebug
```

APK location: `android/app/build/outputs/apk/debug/app-debug.apk`

## 🔥 Important: Network Setup

### **Requirements:**
1. ✅ **Phone and PC on SAME WiFi network**
2. ✅ **PC's IP address in `.env.local`**
3. ✅ **Python backend running** (`core.py`)
4. ✅ **Windows Firewall allows Python**

### **Test Before Building:**

**Test 1: Check PC IP**
```powershell
ipconfig
# Note your IPv4 Address
```

**Test 2: Start Backend**
```bash
cd "d:\Vijay TV\Venom\diy_help\new_method"
python core.py
# Should show: 🌐 API Server started on http://0.0.0.0:5000
```

**Test 3: Test from Phone Browser**
Open your phone's browser and visit:
```
http://YOUR_PC_IP:5000/api/state
```

If you see JSON data, it's working! ✅

**Test 4: Test Next.js Dev on Phone**
```bash
cd animated-face
npm run dev
```

Visit on phone browser:
```
http://YOUR_PC_IP:3000
```

If eyes work, you're ready to build! ✅

## 📦 Alternative: Standalone Mobile App

If you want the app to work **without the PC running**, you have two options:

### Option A: Deploy Backend to Cloud
1. Deploy Flask API to:
   - **Heroku** (free tier)
   - **Railway** (free tier)
   - **Render** (free tier)
   - **PythonAnywhere** (free tier)

2. Update `.env.local`:
```bash
NEXT_PUBLIC_API_URL=https://your-app.herokuapp.com
```

### Option B: Run Everything on Phone (Advanced)
Use **Termux** + **Python** to run the backend on Android itself. Complex but possible.

## 🎯 Final Checklist

Before building APK:

- [ ] Installed Capacitor packages
- [ ] Configured Next.js for static export (`output: 'export'`)
- [ ] Got PC's IP address from `ipconfig`
- [ ] Updated `.env.local` with PC's IP
- [ ] Tested API from phone browser (`http://YOUR_IP:5000/api/state`)
- [ ] Phone and PC on same WiFi
- [ ] Windows Firewall allows Python
- [ ] Backend is running (`python core.py`)
- [ ] Built Next.js (`npm run build`)
- [ ] Synced with Capacitor (`npx cap sync android`)
- [ ] Android Studio installed
- [ ] Java JDK 17+ installed

## 🐛 Troubleshooting

### "Can't connect to API" on phone
1. Verify PC IP: `ipconfig`
2. Verify backend running: Visit `http://PC_IP:5000/api/health` on PC browser
3. Test from phone browser first
4. Check Windows Firewall
5. Ensure same WiFi network

### "CORS Error" on mobile
- Should be fixed (Flask-CORS installed)
- If persists, check `api_server.py` has `CORS(app)`

### "Build failed" in Android Studio
- Check Java version: `java -version` (need 17+)
- Update Android Studio and SDK tools
- Run `.\gradlew clean` in `android/` folder

### Eyes don't animate
- Check console logs in Chrome DevTools (connected device)
- Enable USB debugging on phone
- Use `chrome://inspect` on PC to debug mobile app

## 📱 Development Workflow

1. **Make changes** to Next.js code
2. **Build**: `npm run build`
3. **Sync**: `npx cap sync android`
4. **Reload** app on phone or rebuild

## 🚀 Production Build

For release APK (smaller, optimized):

```bash
cd android
.\gradlew assembleRelease
```

You'll need to sign it with a keystore for publishing to Play Store.

## Summary

**YES, it will work!** But you need:
1. PC and phone on same WiFi
2. PC's IP address in config
3. Backend running on PC
4. Proper network/firewall setup

The app will communicate with your PC over local network and control the animated eyes when you speak to Venom! 🎉
