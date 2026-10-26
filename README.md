# Lock Screen Changer

A tiny Android app that does one thing: replaces the photo on your lock screen.

- **Choose a photo** from your gallery, preview it, then **Set as lock screen** (or lock + home screen).
- **Remove lock screen photo** drops the lock screen picture entirely, so the lock screen shows your
  home screen wallpaper instead.
- If something on the phone is blocking wallpaper changes, the app tells you so instead of failing silently.

Needs Android 7.0 or newer. It asks for only one permission (changing the wallpaper) and has no
internet access.

> **iPhone?** iOS doesn't let any app change the lock screen, so this app can't help.
> See [iPhone](#iphone) below for the manual steps.

## Install on your phone

1. On the phone, open this repo on GitHub, go to `release/LockScreenChanger.apk` and tap **Download**
   (or open the [direct download link](https://github.com/idkwhatd/ihatethsd/raw/HEAD/release/LockScreenChanger.apk)).
2. Open the downloaded file. Android will ask you to allow installs from your browser:
   tap **Settings**, turn on **Allow from this source**, then go back.
3. Tap **Install**. If Play Protect says the app is from an unknown developer, tap
   **More details → Install anyway**. That warning shows up for any app that isn't from the Play Store.
4. Open **Lock Screen Changer**, pick a photo, tap **Set as lock screen**, then lock the phone to check.

After it works you can uninstall the app; the new lock screen stays.

## If it still won't change

The app checks for a block and tells you if it finds one. These are the usual culprits:

| What you see | Cause | Fix |
| --- | --- | --- |
| App says *"This phone blocks wallpaper changes"*, or Settings says *"Disabled by admin"* / *"Action not allowed"* | The phone is managed by a work, school or carrier device-management profile, or a parental-control app | Check **Settings → Security → Device admin apps** and **Settings → Accounts** for a work profile. Whoever set it up has to remove it; no app can override it. |
| The change works but the old photo comes back | A lock screen "story"/carousel service is drawing over the wallpaper (Glance, Samsung **Dynamic Lock Screen**, Xiaomi **Wallpaper carousel**) | Samsung: **Settings → Lock screen** (or **Lock screen and AOD**) **→ Wallpaper services → None**. Others: turn off Glance / Wallpaper carousel in **Settings → Lock screen**. |
| Wallpaper settings are greyed out on Samsung, Xiaomi, Huawei, etc. | A downloaded theme locks the wallpaper | Switch back to the default theme in the **Themes** app, then try again. |
| Something other than the stock lock screen appears | A third-party lock screen app | Uninstall it, or change the photo in that app's own settings. |

## iPhone

There's no public iOS API for setting the lock screen, so no App Store app can do this. On iOS 16 or later:

1. Unlock with Face ID / Touch ID **but stay on the lock screen**, then touch and hold it.
2. Tap the **+** button → **Photos** to make a new lock screen with a photo you choose. Tap **Add**.
3. To get rid of the old one, touch and hold the lock screen again, swipe up on the old wallpaper and tap the
   **trash** icon.

If the old photo keeps coming back, check whether that lock screen is linked to a **Focus**
(the Focus button at the bottom of the lock screen picker) or uses **Photo Shuffle**.
If you can't touch and hold to edit at all, look at the top of **Settings** for *"This iPhone is supervised"*
or under **Settings → General → VPN & Device Management** for a profile. A managed iPhone can be locked
against wallpaper changes, and only whoever manages it can lift that.

## Build from source

Needs JDK 17+ and the Android SDK (platform 35).

```sh
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```
