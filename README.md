# Pixel City for Android

This folder is the complete Android app for Pixel City. You don't need Android Studio: GitHub builds the APK for you for free.

## Get the APK (about 10 minutes, one time)

1. Create a free account at https://github.com and sign in.
2. Click **+** (top right) > **New repository**. Name it `pixel-city`, choose **Public**, and click **Create repository**.
3. On the new repository page, click **uploading an existing file**.
4. Unzip `pixel-city-android.zip` on your PC. Open the `pixel-city-android` folder, select **everything inside it**, and drag it into the GitHub page. Click **Commit changes**.
5. GitHub may skip the hidden `.github` folder when you drag files. To be safe:
   - Click **Add file** > **Create new file**.
   - In the name box, type exactly: `.github/workflows/build-apk.yml`
   - Open `build-apk.yml` from the unzipped folder in Notepad, copy everything, and paste it into GitHub.
   - Click **Commit changes**.
6. Open the **Actions** tab. A run called "Build Pixel City APK" starts on its own. Wait for the green tick (about 5–8 minutes).
7. Open the **Releases** section on the right side of the repository's main page. On your phone, open that page and tap **PixelCity.apk** to download it.

## Install it on your phone

1. Open the downloaded **PixelCity.apk**.
2. If Android asks, allow your browser or Files app to **install unknown apps**.
3. Tap **Install**, then **Open**. Pixel City appears on your home screen.

To update the game later, replace `www/index.html` in the repository. GitHub builds a new APK automatically.

## Fits any screen

The app runs fullscreen in landscape on any Android phone or tablet (Samsung, Xiaomi, Pixel, OnePlus, Realme and others). It draws behind the notch or punch-hole camera, and the buttons and panels move aside so the camera never covers them. Swipe in from the edge to show the system bars when you need them.

## Controls on the phone

- **One finger:** drag to move around. Tap a person, car or building to see details.
- **Tilt the phone:** forward or back moves the camera forward or back, and left or right slides it sideways. Your starting angle is the resting position. The **Tilt to move** button turns it off.
- **Two fingers:** pinch to zoom, twist to rotate.
- **Side pad:** zoom, rotate and tilt the camera view.
- **Build:** tap a tool at the bottom, then tap or drag on the map. Tap the tool again to stop building.

## Build it yourself instead (optional)

With Node.js 22 and Android Studio installed:

```
npm install
npx cap sync android
npx cap open android
```

Then in Android Studio: **Build > Build App Bundle(s) / APK(s) > Build APK(s)**.
