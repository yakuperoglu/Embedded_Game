# -*- coding: utf-8 -*-
"""
settings.py
Tum ayarlanabilir sabitlerin tek kaynagi (single source of truth).
Renkler, hizlar, zorluk olcekleme, FPS, baslangic cani (HP) vb. burada toplanir.
Yorumlar Turkce, tanimlayicilar Ingilizce.
"""

# =====================================================================
# GENEL OYUN AYARLARI
# =====================================================================
FPS = 60                      # Hedef kare hizi (clock.tick parametresi)
MAX_DT = 0.05                 # dt tavani (sn). Odak kaybi/pencere surukleme
                              # aninda dt cok buyumesin -> tunneling onlenir.
START_HEALTH = 100            # Her oyuncunun baslangic cani (0-100)

# =====================================================================
# RENKLER (RGB veya RGBA tuple)
# =====================================================================
SPACE_BG = (8, 10, 24)              # Uzay arka plani (koyu lacivert)
DIVIDER_COLOR = (90, 120, 200)      # Ortadaki ayirici cizgi

SHIP_P1_COLOR = (80, 220, 120)      # Oyuncu 1 ucgen FALLBACK rengi (sprite yoksa; sprite kirmizi)
SHIP_P2_COLOR = (90, 170, 255)      # Oyuncu 2 ucgen FALLBACK rengi (sprite yoksa; sprite mor)
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
# Can durum renkleri (HUD'da cana gore degisir) + esik kesirleri
HUD_HP_GOOD = (120, 230, 130)       # yuksek can (frac > HP_WARN_FRAC)
HUD_HP_WARN = (255, 210, 90)        # orta can (frac > HP_LOW_FRAC)
HUD_HP_LOW = (255, 90, 90)          # dusuk can (esik altinda) + "OYUN BITTI" basligi
HP_WARN_FRAC = 0.5                  # bu kesrin ustunde "iyi" rengi
HP_LOW_FRAC = 0.25                  # bu kesrin ustunde "uyari" rengi
DEAD_TEXT_COLOR = (255, 120, 120)   # "ELENDI" yazisi rengi
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
SHIP_IMG_SCALE = 2.6          # Gemi sprite'inin ekran genisligi = ship.size * bu
                              # (assets/ship_pN.png varsa).
SHIP_HITBOX_SCALE = 0.62      # Hitbox sprite'in SHIP_HITBOX_SCALE kadari (forgiving)
SHIP_MARGIN = 60              # Gemi baslangicta arena dibinden bu kadar yukarida
BULLET_W = 4                  # Mermi genisligi
BULLET_H = 14                 # Mermi yuksekligi
METEOR_MIN_RADIUS = 20        # En kucuk meteor yaricapi (vurmasi kolaylassin diye buyutuldu)
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
INVULN_TIME = 0.7             # Vurus sonrasi kisa i-frame (sn): bu pencerede EK
                              # hasar alinmaz -> ust uste carpisma 'melt' yapmaz.
BLINK_HZ = 8.0                # Vurus sonrasi yanip sonme frekansi (gorsel)

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
# Yaricap esikleri: r < SMALL_MAX -> kucuk, < MEDIUM_MAX -> orta, digeri buyuk.
# Esikler METEOR_MIN/MAX_RADIUS ([20,42]) araligina gore secildi: uc sinif
# kabaca esit dagilsin (~%32/%32/%36). Onceki [22,32] esikleri MIN 14->20
# buyutulunce 'kucuk' sinifini neredeyse yok ediyordu (yalniz [20,22) kalir).
METEOR_SIZE_THRESHOLDS = {
    "small_max": 27,
    "medium_max": 34,
}

# =====================================================================
# HASAR (can 100 uzerinden)
# =====================================================================
# Meteorlar BOYUTA gore hasar verir (puanlamayla ayni boyut-sinifi),
# rakip lazeri SABIT hasar, rakibe toslama sabit hasar.
METEOR_DAMAGE_SMALL = 8        # kucuk meteor hasari
METEOR_DAMAGE_MEDIUM = 15      # orta meteor hasari
METEOR_DAMAGE_LARGE = 25       # buyuk meteor hasari
LASER_DAMAGE = 15             # rakip lazeri (sabit)
ENEMY_CRASH_DAMAGE = 30       # rakip gemiye toslama hasari

# =====================================================================
# OZEL GUC (special power)
# =====================================================================
# Ates artik OTOMATIK. Buton (joystick SW / SPACE / ENTER) ozel gucu tetikler.
# Her SPECIAL_KILLS_REQUIRED asteroid (mermiyle) vurulunca ozel guc DOLAR;
# doluyken butona basinca o oyuncunun arenasindaki TUM tehditler
# (meteorlar + rakip gemiler + rakip lazerleri) yok olur.
SPECIAL_KILLS_REQUIRED = 15        # Kac asteroid vurunca ozel guc dolar
SPECIAL_FLASH_TIME = 0.35          # Kullaninca arena flash suresi (sn)
SPECIAL_FLASH_ALPHA = 170          # Ozel guc flashi en yuksek saydamlik (0-255)
SPECIAL_COLOR = (120, 200, 255)    # Dolum cubugu/yazi (henuz dolmamis)
SPECIAL_READY_COLOR = (120, 255, 160)  # "HAZIR" rengi (dolu)
SPECIAL_BAR_W = 160                # Ozel guc ilerleme cubugu genisligi (@1080p)
SPECIAL_BAR_H = 10                 # Ozel guc ilerleme cubugu yuksekligi (@1080p)
SPECIAL_BAR_BG = (50, 50, 70)      # Ilerleme cubugu arka plan rengi

# =====================================================================
# HASAR EFEKTI (can kaybinda kirmizi)
# =====================================================================
# Can gidince o oyuncunun arenasinda kirmizi efekt:
#   - anlik FLASH: vurus aninda parlar, hizla soner.
#   - KALICI tint: can azaldikca artar (tehlike hissi); can=0'a yaklasinca en koyu.
HURT_COLOR = (200, 30, 30)         # kirmizi efekt rengi
HURT_FLASH_TIME = 0.45             # anlik flash suresi (sn)
HURT_FLASH_ALPHA = 150             # anlik flash en yuksek saydamlik (0-255)
HURT_PERSIST_MAX_ALPHA = 90        # kalici tint en yuksek alpha (can dustukce yaklasilir)

# =====================================================================
# RAKIP GEMILER (enemy ships) + LAZER
# =====================================================================
# Rakip gemiler arenanin USTUNDE bir bantta yatay devriye yapar (asagi inmez),
# periyodik olarak hedef geminin O ANKI konumuna lazer atar. Oyuncu mermisiyle
# ENEMY_HP vurusta yok olur. Dogus GLOBAL ve iki arenaya AYNI ANDA (adil),
# asteroidlerden NADIR.
ENEMY_COLOR = (235, 80, 90)          # rakip gemi govdesi (kirmizi)
ENEMY_OUTLINE = (255, 205, 205)      # kenar cizgisi
ENEMY_LASER_COLOR = (255, 70, 70)    # lazer rengi
ENEMY_HP_BAR_COLOR = (255, 230, 120) # rakip can cubugu
ENEMY_HP_BAR_BG = (60, 30, 30)       # rakip can cubugu arka plani
ENEMY_LASER_RADIUS = 5               # lazer yaricapi (@1080p, SCALE ile)

ENEMY_SIZE = 24                      # rakip gemi boyutu (@1080p, SCALE ile)
ENEMY_HP = 3                         # kac mermiyle yok olur
ENEMY_SCORE = 60                     # yok edince puan (asteroidden cok)
ENEMY_PATROL_SPEED = 130.0           # yatay devriye hizi (px/sn @1080p)
ENEMY_BAND_TOP = 0.10                # ust bant: arena yuksekliginin %10'undan
ENEMY_BAND_BOTTOM = 0.32             #           %32'sine kadar (bu araliki gecmez)
ENEMY_FIRE_INTERVAL = 1.8            # kac saniyede bir lazer atar
ENEMY_LASER_SPEED = 430.0            # lazer hizi (px/sn @1080p)
ENEMY_MAX_PER_ARENA = 2              # arena basina ayni anda max rakip

# Rakip dogus araligi (GLOBAL timer; bu sure rastgele secilir). Meteordan uzun.
ENEMY_SPAWN_MIN = 6.0                # min saniye
ENEMY_SPAWN_MAX = 11.0               # max saniye

# =====================================================================
# PARTIKULLER (patlama efekti)
# =====================================================================
EXPLOSION_PARTICLE_COUNT = 16       # Patlama basina partikul sayisi
PARTICLE_MAX_RADIUS = 4             # Partikul yaricap tabani (omur kesriyle olceklenir)
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

# Joystick ekseni ekran yonuyle ters ise burayi degistir (oyunda test edip ayarla).
# Iki joystick FARKLI yonde monte edildigi icin ayar OYUNCU BASINA ayridir:
#   - Arac sola giderken sen saga ittiysen ilgili oyuncunun INVERT_X'ini cevir.
#   - Arac asagi giderken sen yukari ittiysen ilgili oyuncunun INVERT_Y'sini cevir.
# (P2 dogru calisiyordu; P1 tam ters geldigi icin P1 iki eksende de ters cevrildi.)
P1_INVERT_X = False
P1_INVERT_Y = True
P2_INVERT_X = True
P2_INVERT_Y = False

# =====================================================================
# YILDIZ ALANI (deterministik arka plan)
# =====================================================================
STAR_COUNT = 140              # Yildiz sayisi
STAR_SEED = 1337              # Deterministik uretim icin sabit tohum
STAR_BLUE_BOOST = 30          # Yildiza katilan mavi ton ofseti (parlaklik uzeri)

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
