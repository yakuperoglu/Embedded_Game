# -*- coding: utf-8 -*-
"""
entities.py
Oyun nesneleri: Ship, Bullet, Meteor, Particle.

Tum nesneler delta-time tabanlidir (update(dt)) ve yalnizca pygame.draw
primitifleriyle cizilir (disaridan asset YOK).

Koordinat sistemi: EKRAN-GLOBAL. Clamp/spawn arena.rect ile yapilir, cizim
set_clip ile arenaya kirpilir, carpisma pygame.Rect.colliderect ile dogrudan
calisir.

Bagimlilik: yalnizca settings.py; input_source.InputState'i "ordek tipi"
(duck typing) olarak alir (move_x/move_y/fire alanlari yeterli) -> import
zorunlu degil ama tip ipucu icin import edilebilir.
"""

from __future__ import annotations

import math
import random

import pygame

import settings


# =====================================================================
# Ship: oyuncu uzay araci
# =====================================================================
class Ship:
    """Oyuncu uzay araci. Ucgen govde olarak cizilir.

    Hareket 2 eksenli ve arena_rect icinde clamp'lenir. Ates niyeti
    (InputState.fire) cooldown ile mermiye cevrilir. Vurulunca kisa
    sureli dokunulmazlik + yanip sonme.
    """

    def __init__(self, arena_rect: pygame.Rect, color, x: float, y: float):
        self.arena_rect = arena_rect
        self.color = color
        self.x = float(x)
        self.y = float(y)
        # Boyut cozunurluge gore olceklenir (1080p referans * SCALE).
        self.size = settings.scaled(settings.SHIP_SIZE)

        self._fire_timer = 0.0       # ates cooldown sayaci (>0 ise atilamaz)
        self._wants_fire = False     # bu kare ates niyeti var mi
        self.invuln_timer = 0.0      # dokunulmazlik suresi (>0 ise dokunulmaz)
        self._blink_t = 0.0          # yanip sonme zamanlayicisi

    # --- Carpisma/cizim icin gemi dikdortgeni ---
    @property
    def rect(self) -> pygame.Rect:
        s = self.size
        # Govde yaklasik kareye yakin; carpisma icin biraz dar tutuldu.
        r = pygame.Rect(0, 0, int(s * 1.2), int(s * 1.3))
        r.center = (int(self.x), int(self.y))
        return r

    @property
    def invulnerable(self) -> bool:
        return self.invuln_timer > 0.0

    def update(self, dt: float, input_state) -> None:
        """Hareket + clamp + cooldown/dokunulmazlik zamanlayicilari."""
        # --- Hareket (piksel/sn * dt, cozunurluge gore olcekli) ---
        speed = settings.scaled(settings.SHIP_SPEED)
        self.x += input_state.move_x * speed * dt
        self.y += input_state.move_y * speed * dt
        self._clamp_to_arena()

        # --- Cooldown ---
        if self._fire_timer > 0.0:
            self._fire_timer -= dt
            if self._fire_timer < 0.0:
                self._fire_timer = 0.0

        # --- Dokunulmazlik / yanip sonme ---
        if self.invuln_timer > 0.0:
            self.invuln_timer -= dt
            self._blink_t += dt
            if self.invuln_timer < 0.0:
                self.invuln_timer = 0.0

    def _clamp_to_arena(self) -> None:
        """Gemiyi kendi arena dikdortgeni icinde tutar."""
        half_w = self.size * 0.6
        half_h = self.size * 0.65
        if self.x - half_w < self.arena_rect.left:
            self.x = self.arena_rect.left + half_w
        if self.x + half_w > self.arena_rect.right:
            self.x = self.arena_rect.right - half_w
        if self.y - half_h < self.arena_rect.top:
            self.y = self.arena_rect.top + half_h
        if self.y + half_h > self.arena_rect.bottom:
            self.y = self.arena_rect.bottom - half_h

    def try_fire(self) -> bool:
        """OTOMATIK ates: cooldown dolduysa True doner + cooldown baslatir.

        Artik butona basmaya gerek yok; ates her cooldown'da kendiliginden
        atilir. Buton (InputState.fire) ozel guc icin kullanilir (Arena'da).
        Mermi olusturma sorumlulugu cagirana (Arena) aittir.
        """
        if self._fire_timer <= 0.0:
            self._fire_timer = settings.FIRE_COOLDOWN
            return True
        return False

    def hit(self) -> bool:
        """Gemi vuruldu. Dokunulmaz degilse can kaybi tetiklenir (True doner).

        Dokunulmazsa False doner (hasar yok). Hasar alindiysa dokunulmazlik
        baslatilir. GEMI-METEOR carpismasi icin kullanilir (dokunulmazlik korur).
        """
        if self.invulnerable:
            return False
        self.invuln_timer = settings.INVULN_TIME
        self._blink_t = 0.0
        return True

    def force_hit(self) -> None:
        """Dokunulmazligi YOK SAYAN ceza (dibe ulasan meteor icin).

        Savunmayi gecip arena dibine inen meteor mutlak cezadir; dokunulmazlik
        (gemi carpismasindan kalan) bunu engellemez. Yine de dokunulmazlik
        suresini yeniler ki oyuncu standart toparlanma penceresine sahip olsun.
        """
        self.invuln_timer = settings.INVULN_TIME
        self._blink_t = 0.0

    @property
    def nose_pos(self) -> tuple:
        """Merminin cikacagi burun noktasi (gemi ucu)."""
        return (self.x, self.y - self.size * 0.75)

    def draw(self, surf: pygame.Surface) -> None:
        # Dokunulmazlik sirasinda yanip sonme: yari periyotta gizle.
        if self.invulnerable:
            phase = math.sin(self._blink_t * settings.BLINK_HZ * math.pi)
            if phase < 0:
                return  # bu kare gizli (yanip sonme efekti)

        s = self.size
        cx, cy = self.x, self.y
        # Yukari bakan ucgen govde noktalari (burun ust, taban alt).
        points = [
            (cx, cy - s * 0.85),            # burun
            (cx - s * 0.7, cy + s * 0.7),   # sol taban
            (cx, cy + s * 0.35),            # govde alt centik
            (cx + s * 0.7, cy + s * 0.7),   # sag taban
        ]
        pygame.draw.polygon(surf, self.color, points)
        pygame.draw.polygon(surf, settings.SHIP_OUTLINE, points, 2)
        # Kucuk motor parlamasi (alt orta)
        pygame.draw.circle(surf, settings.BULLET_COLOR,
                           (int(cx), int(cy + s * 0.55)), max(2, int(s * 0.12)))


# =====================================================================
# Bullet: yukari giden mermi
# =====================================================================
class Bullet:
    """Yukari dogru hareket eden mermi (dikey dikdortgen)."""

    def __init__(self, x: float, y: float, vy: float = None):
        self.x = float(x)
        self.y = float(y)
        # vy negatif = yukari. Varsayilan settings'ten (cozunurluge gore olcekli).
        self.vy = vy if vy is not None else -settings.scaled(settings.BULLET_SPEED)
        # Boyutlari spawn aninda olceklenmis sabitle (cozunurluk tutarli).
        self.w = max(1, int(settings.scaled(settings.BULLET_W)))
        self.h = max(1, int(settings.scaled(settings.BULLET_H)))

    def update(self, dt: float) -> None:
        self.y += self.vy * dt

    @property
    def rect(self) -> pygame.Rect:
        r = pygame.Rect(0, 0, self.w, self.h)
        r.center = (int(self.x), int(self.y))
        return r

    def is_offscreen(self, arena_rect: pygame.Rect) -> bool:
        # Mermi yukari ciktiysa (veya arena disina) temizlenir.
        return self.y + self.h < arena_rect.top

    def draw(self, surf: pygame.Surface) -> None:
        pygame.draw.rect(surf, settings.BULLET_COLOR, self.rect, border_radius=2)


# =====================================================================
# Meteor: asagi dusen meteor
# =====================================================================
class Meteor:
    """Yukaridan asagi dusen meteor (daire + detay cizgileri)."""

    def __init__(self, x: float, radius: float, vy: float):
        self.x = float(x)
        self.y = float(-radius)          # ekran ustunden basla
        self.radius = float(radius)
        self.vy = float(vy)
        self.color = random.choice(settings.METEOR_COLORS)
        # Yuzeyde sabit detay cizgileri icin rastgele acilar (deterministik degil)
        self._seed_angles = [random.uniform(0, math.tau) for _ in range(3)]

    def update(self, dt: float) -> None:
        self.y += self.vy * dt

    @property
    def rect(self) -> pygame.Rect:
        d = int(self.radius * 2)
        r = pygame.Rect(0, 0, d, d)
        r.center = (int(self.x), int(self.y))
        return r

    def is_offscreen(self, arena_rect: pygame.Rect) -> bool:
        # Meteor arena dibine ulastiysa (alt sinir) True.
        return self.y - self.radius > arena_rect.bottom

    @property
    def points(self) -> int:
        """Boyuta gore puan degeri.

        Yaricap cozunurlukle olceklendigi icin esikler de ayni SCALE ile
        karsilastirilir (puanlama her cozunurlukte ayni boyut-sinifi verir).
        """
        th = settings.METEOR_SIZE_THRESHOLDS
        if self.radius < settings.scaled(th["small_max"]):
            return settings.SCORE_SMALL
        if self.radius < settings.scaled(th["medium_max"]):
            return settings.SCORE_MEDIUM
        return settings.SCORE_LARGE

    def draw(self, surf: pygame.Surface) -> None:
        cx, cy, r = int(self.x), int(self.y), int(self.radius)
        pygame.draw.circle(surf, self.color, (cx, cy), r)
        pygame.draw.circle(surf, settings.METEOR_OUTLINE, (cx, cy), r, 2)
        # Krater/detay cizgileri (yuzey hissi)
        for ang in self._seed_angles:
            ex = cx + int(math.cos(ang) * r * 0.5)
            ey = cy + int(math.sin(ang) * r * 0.5)
            pygame.draw.line(surf, settings.METEOR_OUTLINE, (cx, cy), (ex, ey), 2)


# =====================================================================
# Particle: patlama partikulu
# =====================================================================
class Particle:
    """Patlama partikulu: yasam suresi azaldikca kuculen daire."""

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 life: float, color):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.life = float(life)
        self.max_life = float(life)
        self.color = color

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        # Hafif surtunme (saciliminin yavaslamasi)
        self.vx *= (1.0 - 1.5 * dt)
        self.vy *= (1.0 - 1.5 * dt)
        self.life -= dt

    @property
    def dead(self) -> bool:
        return self.life <= 0.0

    def draw(self, surf: pygame.Surface) -> None:
        if self.dead:
            return
        frac = max(0.0, self.life / self.max_life)
        radius = max(1, int(4 * frac + 1))
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), radius)


# =====================================================================
# Yardimci: patlama partikulleri uret
# =====================================================================
def spawn_explosion(x: float, y: float) -> list:
    """Verilen konumda patlama partikul listesi uretir."""
    particles = []
    count = settings.EXPLOSION_PARTICLE_COUNT
    for i in range(count):
        ang = random.uniform(0, math.tau)
        speed = random.uniform(0.4, 1.0) * settings.scaled(settings.PARTICLE_SPEED)
        vx = math.cos(ang) * speed
        vy = math.sin(ang) * speed
        life = random.uniform(0.5, 1.0) * settings.PARTICLE_LIFETIME
        color = random.choice(settings.PARTICLE_COLORS)
        particles.append(Particle(x, y, vx, vy, life, color))
    return particles
