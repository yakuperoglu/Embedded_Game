# Split-Screen Uzay Atari (2 Oyunculu)

Universite gomulu sistem projesi. Tek ekranda, dikey bir cizgiyle ikiye
bolunmus (split-screen), 2 oyunculu bir uzay atari oyunu. Oyuncu gemileri
`assets/ship_p1.png` / `assets/ship_p2.png` sprite'lariyla cizilir (Aseprite'tan
uretildi); meteor/mermi/rakip/efektler `pygame.draw` primitifleriyle cizilir.
Sprite dosyalari yoksa gemiler otomatik olarak ucgen govdeye duser (oyun yine
calisir). Ses dosyasi kullanilmaz.

Hedef platform: **Windows, Python 3.10.7, pygame 2.5.2**.

---

## Kurulum

```bash
pip install -r requirements.txt
```

`requirements.txt` yalnizca `pygame==2.5.2` icerir. `pyserial` su an
kullanilmaz (gelecekteki ESP/joystick entegrasyonu icin yorum satiri olarak
tutulur).

---

## Calistirma

Proje kokunden:

```bash
python main.py
```

Oyun **tam ekran** acilir: surec Windows'ta DPI-aware yapilir ve ekran
masaustu (fiziksel) cozunurluginde `set_mode((0,0), FULLSCREEN)` ile acilir,
boylece ekrani TAM kaplar (ekran olcekleme/DPI scaling yuzunden sag/alt
bosluk olmaz). Konumlar sabit piksel hardcode edilmez; her sey guncel
genislik/yukseklikten ve `SCALE = yukseklik/1080`'den hesaplanir.

### Headless dogrulama (selftest)

Ekransiz/otomatik ortamda oyunun bastan sona calistigini dogrulamak icin:

```bash
python main.py --selftest
```

Bu modda SDL dummy video/audio surucusu otomatik secilir, ~120 kare sentetik
girisle (rastgele hareket + ates + meteor dogus + carpisma) gercek
`update`/`collision` mantigi calistirilir ve program **cikis kodu 0** ile
temiz sekilde kapanir. Pencere acmaz, insan girisi beklemez.

---

## Kontroller

| Islem            | Oyuncu 1 (SOL)      | Oyuncu 2 (SAG)                     |
|------------------|---------------------|------------------------------------|
| Hareket          | `W` `A` `S` `D`     | Yon tuslari (`<- -> ^ v`)          |
| Ates             | **OTOMATIK**        | **OTOMATIK**                       |
| Ozel guc (kullan)| `SPACE`             | `ENTER` (hem ana hem numpad Enter) |

> Ates artik **otomatik**tir (butona basmaya gerek yok). Buton (joystickte SW,
> klavyede SPACE/ENTER) **ozel gucu** tetikler.

| Global tus | Islev                          |
|------------|--------------------------------|
| `ESC`      | Cikis (temiz kapanis)          |
| `P`        | Duraklat / Devam                |
| `R`        | Oyun bitince yeniden basla      |
| `F11`      | Tam ekran / pencere gecisi      |

Hareket 2 eksenlidir (yatay + dikey) ve her oyuncu kendi yarisinin sinirlari
icinde tutulur (clamp). Eksenler `-1..1` araliginda analog degerdir; bu sayede
ileride analog joystick birebir uyumlu calisir.

---

## Oyun Kurallari

- Ekran dikey bir cizgiyle ikiye bolunur: **sol yari = Oyuncu 1**,
  **sag yari = Oyuncu 2**. Her yari bagimsiz bir arenadir ve cizimi kendi
  dikdortgenine kirpilir (tasma olmaz).
- Her oyuncunun araci kendi yarisinin **alt ortasinda** baslar.
- Meteorlar arenanin ustunden **rastgele x konumunda**, rastgele boyut ve
  hizla dogup asagi duser.
- **Zorluk zamanla GLOBAL artar**: meteor dusus hizi ve dogma sikligi giderek
  artar, ancak makul bir **tavanla** sinirlidir (aniden imkansiz olmaz).
  HUD'da ortada bir **SEVIYE** gostergesi bulunur.
- **Ates (OTOMATIK)**: arac yukari mermiyi kendiliginden atar (`FIRE_COOLDOWN`
  araliginda). Butona basmaya gerek yok.
- **Rakip gemiler**: arada bir (asteroidlerden NADIR, `ENEMY_SPAWN_MIN..MAX`
  sn) GLOBAL bir zamanlayiciyla **iki arenaya da AYNI ANDA** (adil) rakip gemi
  dogar. Rakipler arenanin **ust bandinda** (`ENEMY_BAND_TOP..BOTTOM`) yatay
  devriye yapar, **asagi inmez**, ve periyodik olarak (`ENEMY_FIRE_INTERVAL`)
  hedef geminin **o anki konumuna** dogru duz giden bir **lazer** atar. Lazer
  oyuncuya carparsa o oyuncu sabit **15 HP** (`LASER_DAMAGE`) kaybeder
  (dokunulmazlik korunur). Rakip gemi `ENEMY_HP` mermiyle (varsayilan 3) yok
  olur -> `ENEMY_SCORE` puan + ozel guc dolumu.
  Arena basina en fazla `ENEMY_MAX_PER_ARENA` rakip bulunur.
- **Ozel guc**: her **`SPECIAL_KILLS_REQUIRED`** (varsayilan 15) asteroid veya
  rakip gemiyi *mermiyle* vurunca ozel guc DOLAR (HUD'da "OZEL: n/15" + ilerleme cubugu;
  dolunca "HAZIR!"). Buton (joystick SW / SPACE / ENTER) ile kullanildiginda
  o oyuncunun arenasindaki **TUM tehditler** (meteorlar + rakip gemiler + rakip
  lazerleri) yok olur (puan + patlama + kisa ekran flashi), sayac sifirlanir.
  Iki oyuncunun ozel gucu birbirinden bagimsizdir.
- **Can (100 uzerinden HP)**: her oyuncu **100 can** ile baslar. Hasar
  kaynaklari:
  - **Meteor** (dibe ulasir veya araca carpar): **boyuta gore** hasar
    (`METEOR_DAMAGE_SMALL/MEDIUM/LARGE` = 8/15/25).
  - **Rakip lazeri**: **sabit 15** (`LASER_DAMAGE`).
  - **Rakip gemiye toslama**: `ENEMY_CRASH_DAMAGE` (30).
  - Vurus sonrasi kisa **i-frame** (`INVULN_TIME`) + yanip sonme; bu pencerede
    ek hasar alinmaz (ust uste carpisma 'melt' yapmaz). Can **0** olunca elenir.
- **Carpismalar**:
  - Mermi-meteor: meteor yok olur, skor artar (buyuk meteor daha cok puan),
    ozel guc dolumu +1.
  - Mermi-rakip gemi: rakip `ENEMY_HP` vurusta yok olur (skor + ozel dolum).
  - (En kucuk asteroid, vurmasi kolaylassin diye buyutuldu.)
- **Hasar efekti (kirmizi)**: can gidince o oyuncunun yarisinda **anlik kirmizi
  flash** parlar; ayrica **kalici bir kirmizi tint** can azaldikca artar
  (`HURT_*` ayarlari). Boylece dusuk canda ekran giderek kizarir (tehlike hissi).
- **HUD**: P1 skor + can (renk: yesil>sari>kirmizi) + ozel guc SOL UST,
  P2 ayni sekilde SAG UST, ortada zorluk seviyesi.
- **Oyun bitisi**: bir oyuncunun cani 0 olunca o yari donar/karartilir
  ("ELENDI"). **Her iki** oyuncu da olunce tam ekran "OYUN BITTI" ekrani
  cikar: ortada kazanan (yuksek skor; esitse berabere). `R` ile yeniden,
  `ESC` ile cikis.
- Hareket **delta-time** tabanlidir (hizlar saniye basina; `clock.tick(60)`
  ile dt hesaplanir) -> cozunurluk/FPS bagimsiz. Ekran disina cikan
  mermi/meteorlar listeden temizlenir (bellek sizdirmaz).

---

## Mimari (kisa)

Asagidan yukariya 4 katman, tek yonlu bagimlilik:

```
settings.py  <-  input_source.py / entities.py  <-  main.py
```

- **settings.py**: tum ayarlanabilir sabitlerin tek kaynagi (renkler, hizlar,
  zorluk olcekleme, FPS, can, cooldown, tavanlar, seri/ADC ayarlari).
- **input_source.py**: giris soyutlama katmani. `InputState` veri sinifi,
  `InputSource` (ABC), `KeyboardInputSource` (su an kullanilan),
  `SerialJoystickInputSource` (gelecekteki ESP stub'i),
  `ScriptedInputSource` (selftest).
- **entities.py**: `Ship`, `Bullet`, `Meteor`, `Enemy`, `EnemyLaser`,
  `Particle` -> hepsi dt tabanli. Gemi sprite'i `get_ship_image()` ile
  `assets/`'ten yuklenir (yoksa ucgen fallback), gerisi pygame primitifi.
- **main.py**: giris noktasi, `Game` (durum makinesi: PLAYING/PAUSED/
  GAME_OVER), `Arena`, `Difficulty`, render/HUD, CLI ve selftest.
- **assets/**: `ship_p1.png` (P1), `ship_p2.png` (P2) gemi sprite'lari.
- **tools/aseprite_to_png.py**: `Photos/Sprite-000{1,2}.aseprite` -> `assets/`
  PNG donusturucu. Aseprite'ta gemiyi duzenleyip kaydettikten sonra
  `python tools/aseprite_to_png.py` calistir, sprite'lar guncellensin.

Oyun cekirdegi dis dunyaya yalnizca `InputState` uzerinden bakar; klavye veya
ESP-seri kaynak degistiginde cekirdek **degismez**.

---

## ESP32-S3 + Analog Joystick (Donanim) Entegrasyonu

Klavye yerine **ESP32-S3 + 2x Deneyap Kumanda Kolu (analog joystick)** kullanmak
icin gereken her sey hazir. ESP, iki joystickin eksenlerini ve butonlarini okuyup
USB seri porttan satir-bazli yollar; oyun bunu `SerialJoystickInputSource` ile okur.
**Oyun cekirdegi degismez** (yalnizca giris kaynagi degisir).

### 1) Kablolama (Deneyap Kumanda Kolu -> ESP32-S3)

Deneyap Kumanda Kolu (M26) **3.3V** calisir. Sol header'da `3V3, RES, X, Y, SW`,
sag (I2C) header'da `GND, SDA, SCL, SWIM, NC` bulunur. Biz **analog modda**
kullaniyoruz; I2C/SDA/SCL/SWIM/RES/NC **bos kalir**. (Modulde silkscreen
etiketlerine gore bagla.)

| Joystick pini | Oyuncu 1 -> ESP32-S3 | Oyuncu 2 -> ESP32-S3 |
|---------------|----------------------|----------------------|
| `3V3`         | **3V3**              | **3V3**              |
| `GND` (I2C tarafinda) | **GND**      | **GND**              |
| `X`           | **GPIO4**            | **GPIO7**            |
| `Y`           | **GPIO5**            | **GPIO8**            |
| `SW` (buton)  | **GPIO6**            | **GPIO9**            |

Tum sinyaller **GPIO4-9** araliginda: bunlar kartin AYNI uzun kenarinda toplanir
ve hepsi **ADC1** (GPIO1-10; WiFi'dan etkilenmez). Boylece dar kenardaki
GPIO1/GPIO2'ye gerek kalmaz. Strapping pinlerden (GPIO0/3/45/46) ve USB
pinlerinden (GPIO19/20) kacinildi.

> **Breadboard ipucu:** Her satirda (orta kanalin bir yarisinda) 5 delik
> elektriksel olarak birdir. Bir pine ulasmak icin o pinin sirasindaki **bos
> bir deligi** kullan -- **asla kenardaki `+`/`-` guc rayini sinyal icin
> kullanma** (ray sadece besleme/GND icindir; sinyali oraya takmak kisa devre
> yapar). Kart genis ve ortada degilse, pinlerin yaninda bos delik kalmasi icin
> **karti orta kanala simetrik otur**. Guc icin: ESP `3V3` -> `+` ray,
> ESP `GND` -> `-` ray; iki joystickin `3V3`/`GND`'si de bu raylara. Eger iki
> uzun kenardaki raylari kullaniyorsan, ayni isimli raylari (`-` ile `-`,
> `+` ile `+`) birer jumper'la kopru yap ki ortak olsunlar.

> Pin degistirmek istersen `firmware/src/main.cpp` tepesindeki pin
> sabitlerini guncelle (oyun tarafi etkilenmez).

### 2) ESP firmware (PlatformIO)

Firmware bir PlatformIO projesidir: `firmware/` (`platformio.ini` + `src/main.cpp`).
Kart `esp32-s3-devkitc-1`; Serial yerlesik USB-C portundan akar
(`ARDUINO_USB_CDC_ON_BOOT=1`).

**VS Code (PlatformIO eklentisi) ile:** `firmware` klasorunu ac (File > Open
Folder > firmware), alt cubuktan **Build** (✓) ve sonra **Upload** (→).

**Komut satiri ile** (proje koku disindan da calisir):

```bash
pio run -d firmware                  # derle (dogrula)
pio run -d firmware -t upload        # ESP'ye yukle (takiliyken)
```

Upload "Connecting…"de takilirsa: karttaki **BOOT** tusunu basili tut, **RST**'ye
bir kez bas, birak; tekrar dene.

Firmware her ~15 ms'de `x1,y1,b1,x2,y2,b2\n` yollar (115200 baud).
Ornek: `2048,3900,1,2050,150,0`. Ham eksenler `0..4095`, buton `1=basili`.

### 3) PC / oyun tarafi

```bash
pip install pyserial
```

`settings.py` icinde `SERIAL_PORT`'u ESP'nin COM portuna ayarla (Aygit
Yoneticisi > Baglanti Noktalari). Once ham veriyi test et:

```bash
python serial_test.py          # joystigi oynat: x/y degismeli, butona bas: b=1
```

Veri akiyorsa oyunu seri kaynakla baslat:

```bash
python main.py --serial        # veya settings.py: INPUT_SOURCE = "serial"
```

### 4) Kalibrasyon / ince ayar (settings.py)

- **Eksen ters donuyorsa**: ilgili oyuncunun `P1_INVERT_X/Y` veya `P2_INVERT_X/Y`
  degerini degistir. Iki joystick farkli yonde monte edilebilir; ayar OYUNCU
  BASINA ayridir (orn. P2 dogruyken P1 ters gelebilir).
- **Merkezde kayma/titreme**: `ADC_DEADZONE`'u buyut (orn. 0.12).
- **Buton ters calisiyorsa** (basili degilken ozel guc tetikleniyor / basinca
  tetiklenmiyor): firmware'de `b1/b2` satirindaki `HIGH` <-> `LOW` mantigini cevir.

> Not: `pyserial` opsiyoneldir (`import serial` lazy, sinif icinde). Kurulu
> olmasa veya port acilamasa bile oyun **cokmez**; uyari basip notr girisle
> devam eder. Klavye modu (`python main.py`) her zaman calisir.

---

## Ayarlar (ozellestirme)

Tum dengeleme degerleri `settings.py` icinde merkezidir: hizlar, baslangic cani (HP),
ates cooldown, zorluk tavanlari, meteor boyut/puan esikleri, partikul sayisi,
seri port/baud/ADC degerleri, yildiz sayisi vb. Oyunu degistirmek icin
yalnizca bu dosyayi duzenlemek yeterlidir.
