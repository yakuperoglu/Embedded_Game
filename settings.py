# -*- coding: utf-8 -*-
"""
settings.py
Tum ayarlanabilir sabitlerin tek kaynagi (single source of truth).
Renkler, hizlar, zorluk olcekleme, FPS, can sayisi vb. burada toplanir.
Yorumlar Turkce, tanimlayicilar Ingilizce.
"""

# =====================================================================
# GENEL OYUN AYARLARI
# =====================================================================
FPS = 60                      # Hedef kare hizi (clock.tick parametresi)
MAX_DT = 0.05                 # dt tavani (sn). Odak kaybi/pencere surukleme
                              # aninda dt cok buyumesin -> tunneling onlenir.
START_LIVES = 3               # Her oyuncunun baslangic can sayisi

# =====================================================================
# RENKLER (RGB veya RGBA tuple)
# =====================================================================
SPACE_BG = (8, 10, 24)              # Uzay arka plani (koyu lacivert)
STAR_COLOR = (180, 190, 220)        # Yildiz noktalari
DIVIDER_COLOR = (90, 120, 200)      # Ortadaki ayirici cizgi

SHIP_P1_COLOR = (80, 220, 120)      # Oyuncu 1 gemi rengi (yesil)
SHIP_P2_COLOR = (90, 170, 255)      # Oyuncu 2 gemi rengi (mavi)
SHIP_OUTLINE = (240, 240, 255)      # Gemi kenar cizgisi

BULLET_COLOR = (255, 230, 120)      # Mermi rengi (sari)

# Meteor renkleri (boyuta gore degisken; rastgele secilir)
METEOR_COLORS = [
    (150, 110, 90),
    (170, 130, 100),
    (120, 100, 95),
    (190, 150, 120),
]
METEOR_OUTLINE = (60, 45, 40)       # Meteor kenar/detay cizgisi

# Patlama partikul renkleri
PARTICLE_COLORS = [
    (255, 200, 80),
    (255, 140, 50),
    (255, 90, 40),
    (255, 240, 180),
]

HUD_COLOR = (230, 235, 255)         # HUD yazi rengi
HUD_ACCENT = (255, 210, 90)         # HUD vurgu rengi (skor/seviye)
DEAD_OVERLAY = (10, 0, 0, 150)      # Olu arena karartma overlay (RGBA)
PAUSE_OVERLAY = (0, 0, 0, 160)      # Duraklatma overlay (RGBA)
GAMEOVER_OVERLAY = (0, 0, 0, 200)   # Oyun bitti overlay (RGBA)

# =====================================================================
# COZUNURLUK OLCEKLEME (runtime)
# =====================================================================
# Asagidaki BOYUT ve HIZ sabitleri 1080p (REFERENCE_HEIGHT) referans
# alinarak tanimlanmistir. Farkli cozunurlukte (orn. 4K) varlik boyutlari,
# fontlar ve hizlar ayni "oyun hissini" korusun diye runtime'da SCALE ile
# carpilir. SCALE = ekran_yuksekligi / REFERENCE_HEIGHT.
#
# Hizlar da olceklenir: mesafe (arena yuksekligi) H ile, hiz da H ile
# buyudugunden meteorun tepeden dibe dusus SURESI cozunurlukten bagimsiz
# sabit kalir -> ayni seviyede zorluk her monitorde aynidir.
#
# SCALE varsayilani 1.0; gercek deger Game baslarken/rescale'da set_scale()
# ile guncellenir. Entity'ler ve render bu carpani scaled_* yardimcilari
# (veya dogrudan SCALE) uzerinden okur.
REFERENCE_HEIGHT = 1080.0     # Boyut/hiz sabitlerinin tanimlandigi referans
SCALE = 1.0                   # Runtime olcek katsayisi (set_scale ile guncellenir)


def set_scale(screen_height: int) -> float:
    """Ekran yuksekligine gore global SCALE'i gunceller ve dondurur.

    Asiri kucuk/buyuk degerlere karsi makul bir aralikta sinirlanir
    (cok kucuk ekranda varliklar gorunmez olmasin).
    """
    global SCALE
    s = screen_height / REFERENCE_HEIGHT
    SCALE = max(0.4, min(4.0, s))
    return SCALE


def scaled(value: float) -> float:
    """Bir referans (1080p) degerini guncel SCALE ile olcekler."""
    return value * SCALE


# =====================================================================
# DUZEN / BOYUT  (1080p referans; runtime'da SCALE ile carpilir)
# =====================================================================
SHIP_SIZE = 26                # Gemi temel boyutu (piksel @1080p)
SHIP_MARGIN = 60              # Gemi baslangicta arena dibinden bu kadar yukarida
BULLET_W = 4                  # Mermi genisligi
BULLET_H = 14                 # Mermi yuksekligi
METEOR_MIN_RADIUS = 14        # En kucuk meteor yaricapi
METEOR_MAX_RADIUS = 42        # En buyuk meteor yaricapi

# Font temel boyutlari (@1080p; runtime'da SCALE ile carpilir)
FONT_SMALL_SIZE = 22
FONT_MED_SIZE = 34
FONT_BIG_SIZE = 72

# =====================================================================
# HIZLAR (piksel / saniye @1080p) -> delta-time tabanli hareket
# Runtime'da SCALE ile carpilir (dusus suresi cozunurlukten bagimsiz kalir).
# =====================================================================
SHIP_SPEED = 360.0                  # Gemi hareket hizi
BULLET_SPEED = 620.0                # Mermi hizi (yukari)
METEOR_BASE_FALL_SPEED = 120.0      # Meteor temel dusus hizi (zorlukla artar)

# =====================================================================
# ATES
# =====================================================================
FIRE_COOLDOWN = 0.28          # Iki ates arasi minimum sure (sn)

# =====================================================================
# DOKUNULMAZLIK (can kaybinda)
# =====================================================================
INVULN_TIME = 1.6             # Vurulduktan sonra dokunulmazlik suresi (sn)
BLINK_HZ = 8.0                # Dokunulmazlik sirasinda yanip sonme frekansi

# =====================================================================
# ZORLUK OLCEKLEME (GLOBAL - iki arena paylasir)
# =====================================================================
# Zorluk zamanla artar ama tavanla sinirli (imkansiz olmasin).
DIFFICULTY_TIME_TO_MAX = 90.0       # Bu surede (sn) tavana ulasilir
SPAWN_BASE_INTERVAL = 1.30          # Baslangic meteor dogus araligi (sn)
SPAWN_MIN_INTERVAL = 0.35           # En sik dogus araligi (tavan)
FALL_SPEED_MAX_MULT = 2.6           # Dusus hizi maksimum carpani (tavan)
DIFFICULTY_LEVELS = 10              # HUD'da gosterilen seviye sayisi (1..N)

# =====================================================================
# SKOR (meteor boyutuna gore puan)
# =====================================================================
SCORE_SMALL = 10
SCORE_MEDIUM = 20
SCORE_LARGE = 40
# Yaricap esikleri: r < SMALL_MAX -> kucuk, < MEDIUM_MAX -> orta, digeri buyuk
METEOR_SIZE_THRESHOLDS = {
    "small_max": 22,
    "medium_max": 32,
}

# =====================================================================
# OZEL GUC (special power)
# =====================================================================
# Ates artik OTOMATIK. Buton (joystick SW / SPACE / ENTER) ozel gucu tetikler.
# Her SPECIAL_KILLS_REQUIRED asteroid (mermiyle) vurulunca ozel guc DOLAR;
# doluyken butona basinca o oyuncunun arenasindaki TUM meteorlar yok olur.
SPECIAL_KILLS_REQUIRED = 15        # Kac asteroid vurunca ozel guc dolar
SPECIAL_FLASH_TIME = 0.35          # Kullaninca arena flash suresi (sn)
SPECIAL_COLOR = (120, 200, 255)    # Dolum cubugu/yazi (henuz dolmamis)
SPECIAL_READY_COLOR = (120, 255, 160)  # "HAZIR" rengi (dolu)

# =====================================================================
# PARTIKULLER (patlama efekti)
# =====================================================================
EXPLOSION_PARTICLE_COUNT = 16       # Patlama basina partikul sayisi
PARTICLE_LIFETIME = 0.55            # Partikul yasam suresi (sn)
PARTICLE_SPEED = 220.0              # Partikul saciliminin temel hizi (px/sn @1080p)

# =====================================================================
# GIRIS KAYNAGI SECIMI (klavye <-> ESP seri joystick)
# =====================================================================
# Calistirma aninda secim:
#   - Kod degistirmeden: 'python main.py --serial' (CLI bayragi)
#   - Veya bu sabiti degistir: "keyboard" | "serial"
# CLI bayragi varsa bu sabiti gecersiz kilar (oncelik CLI'dadir).
INPUT_SOURCE = "keyboard"     # "keyboard" | "serial"

# =====================================================================
# SERI / ESP JOYSTICK (gelecekteki entegrasyon - simdi kullanilmaz)
# =====================================================================
SERIAL_PORT = "COM11"         # ESP'nin Windows COM portu (CH343, Aygit Yoneticisi'nden bak)
SERIAL_BAUD = 115200          # Baud hizi (ESP firmware ile AYNI olmali)
ADC_MAX = 4095                # ESP ADC ham deger tavani (12-bit -> analogReadResolution(12))
ADC_DEADZONE = 0.08           # Olu bolge (merkez titremesini yutar, -1..1 olcek)

# Joystick ekseni ekran yonuyle ters ise burayi degistir (oyunda test edip ayarla):
#   - Arac sola giderken sen saga ittiysen JOY_INVERT_X = True yap.
#   - Arac asagi giderken sen yukari ittiysen JOY_INVERT_Y = True yap.
# Bu montajda iki eksen de ters geldi -> ikisi de duzeltildi (test edildi).
JOY_INVERT_X = True
JOY_INVERT_Y = False

# =====================================================================
# YILDIZ ALANI (deterministik arka plan)
# =====================================================================
STAR_COUNT = 140              # Yildiz sayisi
STAR_SEED = 1337              # Deterministik uretim icin sabit tohum

# =====================================================================
# SELFTEST (headless dogrulama)
# =====================================================================
SELFTEST_FRAMES = 120         # Simule edilecek kare sayisi
SELFTEST_DT = 1.0 / 60.0      # Selftest sabit delta-time

# ---------------------------------------------------------------------
# Guvenlik dogrulamasi: sifira bolme paydalarinin runtime'da 0 olmamasi.
# (Import aninda erken hata vermek, oyunun ortasinda crash'ten iyidir.)
# ---------------------------------------------------------------------
assert DIFFICULTY_TIME_TO_MAX > 0, "DIFFICULTY_TIME_TO_MAX 0 olamaz (bolme)"
assert ADC_MAX > 0, "ADC_MAX 0 olamaz (eksen map'leme bolmesi)"
assert FPS > 0, "FPS 0 olamaz"
assert METEOR_MAX_RADIUS >= METEOR_MIN_RADIUS, "Meteor yaricap araligi gecersiz"
