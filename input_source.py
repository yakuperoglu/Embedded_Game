# -*- coding: utf-8 -*-
"""
input_source.py
Giris soyutlama katmani.

Amac: Oyun cekirdegi (Ship.update, collision) yalnizca soyut InputState
ile konussun. Boylece giris kaynagi (klavye / ESP-seri joystick) degisse
bile oyun mantigi DEGISMEZ. Kaynak secimi calistirma aninda yapilir:
'python main.py --serial' bayragi veya settings.INPUT_SOURCE sabiti (main()
secip Game'e input_source olarak gecirir).

Bagimlilik: yalnizca settings.py'ye bagimlidir; entities.py'yi BILMEZ.
"""

from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass

import pygame

import settings


# =====================================================================
# InputState: tek bir oyuncunun o kareki giris durumu
# =====================================================================
@dataclass
class InputState:
    """Bir oyuncunun o kareki giris durumu.

    move_x / move_y: -1.0 .. 1.0 arasi analog eksen degeri.
        Klavyede yalnizca -1 / 0 / 1 uretilir; analog joystickte ara
        degerler de gelir. Bu sayede imza her iki kaynak icin de aynidir.
    fire: o an ates istegi var mi (bool). Cooldown mantigi Ship icinde;
        burada yalnizca 'niyet' tasinir.
    """
    move_x: float = 0.0
    move_y: float = 0.0
    fire: bool = False


# =====================================================================
# InputSource: tum giris kaynaklarinin taban sinifi (ABC)
# =====================================================================
class InputSource(ABC):
    """Tum giris kaynaklari icin soyut taban sinif."""

    @abstractmethod
    def poll(self, events: list, keys) -> dict:
        """O karenin giris durumunu dondurur.

        Args:
            events: pygame.event.get() ile alinmis event listesi.
            keys: pygame.key.get_pressed() sonucu (basili tuslar).

        Returns:
            {1: InputState, 2: InputState} -> anahtar = oyuncu id (1/2).
        """
        raise NotImplementedError


# =====================================================================
# KeyboardInputSource: su an kullanilan klavye kaynagi
# =====================================================================
class KeyboardInputSource(InputSource):
    """Klavye girisini iki oyuncunun InputState'ine cevirir.

    Oyuncu 1 (sol): W/A/S/D hareket, SPACE ates.
    Oyuncu 2 (sag): ok tuslari hareket, ENTER (K_RETURN ve K_KP_ENTER) ates.
    """

    def poll(self, events: list, keys) -> dict:
        # --- Oyuncu 1: WASD + SPACE ---
        p1_x = (1.0 if keys[pygame.K_d] else 0.0) - (1.0 if keys[pygame.K_a] else 0.0)
        p1_y = (1.0 if keys[pygame.K_s] else 0.0) - (1.0 if keys[pygame.K_w] else 0.0)
        p1_fire = keys[pygame.K_SPACE]

        # --- Oyuncu 2: ok tuslari + ENTER (hem ana hem numpad) ---
        p2_x = (1.0 if keys[pygame.K_RIGHT] else 0.0) - (1.0 if keys[pygame.K_LEFT] else 0.0)
        p2_y = (1.0 if keys[pygame.K_DOWN] else 0.0) - (1.0 if keys[pygame.K_UP] else 0.0)
        # K_KP_ENTER tuzagi: numpad Enter ayri keycode; her ikisini de kabul et.
        p2_fire = keys[pygame.K_RETURN] or keys[pygame.K_KP_ENTER]

        # Klavyede capraz hareket vektor uzunlugu ~1.41 olabilir; >1 ise
        # normalize ederek capraz "daha hizli" gitmesini onleriz.
        p1 = InputState(*_normalized(p1_x, p1_y), bool(p1_fire))
        p2 = InputState(*_normalized(p2_x, p2_y), bool(p2_fire))
        return {1: p1, 2: p2}


def _normalized(x: float, y: float) -> tuple:
    """Vektor uzunlugu 1'i asarsa normalize eder (sifir kontrollu).

    move_x ve move_y ikisi de 0 iken uzunluk 0 olur -> normalize ETME
    (sifira bolme tuzagi). Analog joystikte zaten <=1 gelir; bu yalnizca
    klavye capraz hareketi icin devreye girer.
    """
    length = math.hypot(x, y)
    if length > 1.0:
        return x / length, y / length
    return x, y


# =====================================================================
# SerialJoystickInputSource: GELECEKTEKI ESP entegrasyonu icin STUB
# =====================================================================
class SerialJoystickInputSource(InputSource):
    """ESP32 + analog joystick (Deneyap kumanda kolu) icin ORNEK kaynak.

    Su an VARSAYILAN OLARAK KULLANILMAZ. Klavye yerine bunu secmek icin
    KOD DEGISTIRMEYE GEREK YOKTUR; calistirma aninda secilir:
        python main.py --serial
    veya settings.INPUT_SOURCE = "serial" yapilir (CLI bayragi oncelikli).
    Oyun cekirdegi degismez (sadece kaynak degisir).

    BEKLENEN SERI PROTOKOL (satir bazli, '\\n' ile biten):
        "x1,y1,b1,x2,y2,b2\\n"
    Burada:
        x1,y1 -> Oyuncu 1 joystick ham ADC degerleri (0 .. ADC_MAX)
        b1    -> Oyuncu 1 buton (0/1)
        x2,y2 -> Oyuncu 2 joystick ham ADC degerleri (0 .. ADC_MAX)
        b2    -> Oyuncu 2 buton (0/1)

    Ham 0..ADC_MAX degeri _map_axis() ile -1..1 araligina cevrilir ve
    deadzone uygulanir.

    NOT: pyserial OPSIYONEL bir bagimliliktir; bu yuzden 'import serial'
    MODUL TEPESINDE DEGIL, __init__ ICINDE (lazy) yapilir. Boylece pyserial
    kurulu olmasa bile 'python main.py' klavye ile sorunsuz calisir.
    """

    def __init__(self, port: str = None, baud: int = None):
        # TODO (ESP entegrasyonu): port/baud degerlerini gercek donanima gore
        # ayarla. Su an settings.py'deki varsayilanlar kullaniliyor.
        self.port = port or settings.SERIAL_PORT
        self.baud = baud or settings.SERIAL_BAUD
        self._ser = None
        self._last = {
            1: InputState(),
            2: InputState(),
        }

        # --- Lazy import: pyserial yalnizca bu kaynak secilince gerekir ---
        try:
            import serial  # opsiyonel bagimlilik
            self._serial_module = serial
        except ImportError:
            # pyserial yoksa kaynak yine olusur ama poll() notr deger doner.
            print("[serial] pyserial kurulu degil -> 'pip install pyserial'. "
                  "Notr (hareketsiz) giris kullanilacak.")
            self._serial_module = None
            return

        # --- Gercek seri baglantiyi ac (ESP USB ile bagliyken) ---
        # Acilamazsa (yanlis port / kart takili degil) oyun COKMEZ; notr
        # giris ile devam eder ve kullaniciyi yonlendiren bir uyari basar.
        try:
            self._ser = self._serial_module.Serial(self.port, self.baud,
                                                    timeout=0)
            print("[serial] Baglanildi: %s @ %d baud" % (self.port, self.baud))
        except Exception as e:  # noqa: BLE001 (SerialException dahil her sey)
            print("[serial] '%s' acilamadi (%s).\n"
                  "         -> settings.SERIAL_PORT'u dogru COM portuna ayarla "
                  "(Aygit Yoneticisi > Baglanti Noktalari).\n"
                  "         Simdilik notr giris kullanilacak." % (self.port, e))
            self._ser = None

    def _map_axis(self, raw: float, invert: bool = False) -> float:
        """Ham ADC degerini (0..ADC_MAX) -1..1 araligina map'ler + deadzone.

        Merkez = ADC_MAX/2 -> 0.0. ADC_MAX != 0 settings'te garanti edilir.
        invert=True ise eksen yonu ters cevrilir (joystick fiziksel montaji
        ekran yonuyle ters ise; settings.JOY_INVERT_X/Y ile kontrol edilir).
        """
        # 0..ADC_MAX -> -1..1
        value = (raw / settings.ADC_MAX) * 2.0 - 1.0
        if invert:
            value = -value
        # Deadzone: merkeze cok yakin degerleri 0 say (titreme/sapmayi yut).
        if abs(value) < settings.ADC_DEADZONE:
            return 0.0
        # Olu bolge sonrasi kalan araligi yeniden -1..1'e ger (yumusak gecis).
        sign = 1.0 if value > 0 else -1.0
        scaled = (abs(value) - settings.ADC_DEADZONE) / (1.0 - settings.ADC_DEADZONE)
        return sign * max(0.0, min(1.0, scaled))

    def _parse_line(self, line: str) -> dict:
        """'x1,y1,b1,x2,y2,b2' satirini iki InputState'e cevirir."""
        parts = line.strip().split(",")
        if len(parts) != 6:
            # Bozuk/eksik satir -> son bilinen durumu koru.
            return self._last
        try:
            x1, y1, b1, x2, y2, b2 = (float(p) for p in parts)
        except ValueError:
            return self._last

        ix, iy = settings.JOY_INVERT_X, settings.JOY_INVERT_Y
        p1 = InputState(self._map_axis(x1, ix), self._map_axis(y1, iy), b1 > 0.5)
        p2 = InputState(self._map_axis(x2, ix), self._map_axis(y2, iy), b2 > 0.5)
        return {1: p1, 2: p2}

    def poll(self, events: list, keys) -> dict:
        """Seri porttan en son satiri okuyup InputState'lere cevirir.

        Donanim/pyserial yoksa notr (hareketsiz) durum doner; oyun yine
        calisir. Bu metot gelecekteki ESP entegrasyonu icin iskelettir.
        """
        if self._ser is None:
            # Henuz gercek baglanti yok (STUB). Notr durum.
            return {1: InputState(), 2: InputState()}

        # --- Ornek okuma dongusu (donanim hazir oldugunda aktiflesir) ---
        try:
            last_line = None
            # Tampondaki tum satirlari oku, en gunceli kullan (gecikme azalir).
            while self._ser.in_waiting:
                raw = self._ser.readline().decode("utf-8", errors="ignore")
                if raw:
                    last_line = raw
            if last_line:
                self._last = self._parse_line(last_line)
        except Exception:
            # Seri hata -> oyunu cokertme, son durumu koru.
            pass
        return self._last


# =====================================================================
# ScriptedInputSource: SELFTEST icin sentetik giris kaynagi
# =====================================================================
class ScriptedInputSource(InputSource):
    """Selftest icin deterministik/rastgele sentetik giris uretir.

    Insan girisi beklemeden update/collision yolunu calistirmak icin
    her cagrida sahte hareket + periyodik ates dondurur.
    """

    def __init__(self, seed: int = 12345):
        self._rng = random.Random(seed)
        self._frame = 0

    def poll(self, events: list, keys) -> dict:
        self._frame += 1
        # Sinuzoidal + rastgele karisik hareket (eksenler -1..1).
        t = self._frame * 0.1
        p1 = InputState(
            move_x=math.sin(t) * self._rng.uniform(0.4, 1.0),
            move_y=math.cos(t * 0.7) * self._rng.uniform(0.2, 0.8),
            fire=(self._frame % 6 == 0),   # periyodik ates
        )
        p2 = InputState(
            move_x=math.cos(t * 1.3) * self._rng.uniform(0.4, 1.0),
            move_y=math.sin(t * 0.5) * self._rng.uniform(0.2, 0.8),
            fire=(self._frame % 5 == 0),
        )
        return {1: p1, 2: p2}
