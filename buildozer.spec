[app]
# Uygulama başlığı ve paket adı
title = Basketbol Mac Programi
package.name = basketbolmac
package.domain = com.basketfaul

# Ana dosya (uzantısız)
source.dir = .
source.include_exts = py,png,jpg,kv,atlas

# Uygulama versiyonu
version = 1.0

# Gerekli Python paketleri
requirements = python3,kivy,requests,beautifulsoup4,certifi,charset-normalizer,urllib3,idna

# Android izinleri
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# Android API
android.minapi = 21
android.api = 33
android.ndk = 25b
android.ndk_api = 21

# Yön: portrait (dikey)
orientation = portrait

# Android mimarileri (arm64-v8a = modern telefonlar)
android.archs = arm64-v8a, armeabi-v7a

# Tam ekran uygulama
fullscreen = 0

# İkon (isteğe bağlı - ikon.png koyabilirsiniz)
# icon.filename = %(source.dir)s/icon.png

# Android bootstrap
android.bootstrap = sdl2

# Log seviyesi (0=sessiz, 2=debug)
log_level = 2

[buildozer]
# Buildozer çalışma dizini
buildozer.warn_on_root = 1
