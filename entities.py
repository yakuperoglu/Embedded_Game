# -*- coding: utf-8 -*-
"""
entities.py
Oyun nesneleri: Ship, Bullet, Meteor, Particle, Enemy, EnemyLaser.

Tum nesneler delta-time tabanlidir (update(dt)). Cizim cogunlukla
pygame.draw primitifleriyledir; Ship istisna olarak assets/ sprite'i
kullanir (yoksa ucgen fallback'e duser).

Koordinat sistemi: EKRAN-GLOBAL. Clamp/spawn arena.rect ile yapilir, cizim
set_clip ile arenaya kirpilir, carpisma pygame.Rect.colliderect ile dogrudan
calisir.

Bagimlilik: yalnizca settings.py; input_source.InputState'i "ordek tipi"
(duck typing) olarak alir (move_x/move_y/fire alanlari yeterli) -> import
zorunlu degil ama tip ipucu icin import edilebilir.
"""

from __future__ import annotations

import math
import os
import random

import pygame

import settings


# =====================================================================
# Gemi sprite'lari (assets/) - bir kez yuklenir, OPSIYONEL
# =====================================================================
# Resim yoksa/yuklenemezse get_ship_image None doner ve Ship ucgen govdeye
# duser (oyun yine calisir). pygame.display ayarlandiktan SONRA cagrilmali
# (convert_alpha gerektirir).
_SHIP_IMAGES = {}
_SHIP_LOADED = False
_SHIP_FILES = {1: "ship_p1.png", 2: "ship_p2.png"}


def get_ship_image(player_id: int):
    """Oyuncunun gemi sprite'ini dondurur (ilk cagrida yukler + cache'ler)."""
    global _SHIP_LOADED
    if not _SHIP_LOADED:
        _SHIP_LOADED = True
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        for pid, name in _SHIP_FILES.items():
            path = os.path.join(base, name)
            try:
                _SHIP_IMAGES[pid] = pygame.image.load(path).convert_alpha()
            except Exception as exc:   # dosya yok / yuklenemedi -> ucgen fallback
                print("[assets] '%s' yuklenemedi (%s); ucgen govde kullanilacak."
                      % (name, exc))
                _SHIP_IMAGES[pid] = None
    return _SHIP_IMAGES.get(player_id)


# =====================================================================
# Ship: oyuncu uzay araci
# =====================================================================
class Ship:
    """Oyuncu uzay araci.

    Resim (assets/ship_pN.png) varsa onunla, yoksa ucgen govde ile cizilir.
    Hareket 2 eksenli ve arena_rect icinde clamp'lenir (tum sprite iceride
    kalir). Ates otomatik. Vurulunca kisa i-frame + yanip sonme.
    """

    def __init__(self, arena_rect: pygame.Rect, color, x: float, y: float,
                 image=None):
        self.arena_rect = arena_rect
        self.color = color
        self.x = float(x)
        self.y = float(y)
        # Boyut cozunurluge gore olceklenir (1080p referans * SCALE).
        self.size = settings.scaled(settings.SHIP_SIZE)

        # Gemi sprite'i (varsa). None ise ucgen govdeye dusulur.
        self.image = image
        self._scaled_img = None      # guncel boyuta olceklenmis resim (cache)
        self._scaled_for = -1        # _scaled_img hangi hedef genislik icin

        self._fire_timer = 0.0       # ates cooldown sayaci (>0 ise atilamaz)
        self.invuln_timer = 0.0      # i-frame suresi (>0 ise yeni hasar almaz)
        self._blink_t = 0.0          # yanip sonme zamanlayicisi

    def _display_size(self) -> tuple:
        """Resimli gemide ekranda kaplanan (genislik, yukseklik)."""
        w = self.size * settings.SHIP_IMG_SCALE
        iw, ih = self.image.get_size()
        return w, w * ih / iw

    # --- Carpisma/cizim icin gemi dikdortgeni ---
    @property
    def rect(self) -> pygame.Rect:
        if self.image is not None:
            dw, dh = self._display_size()
            # Hitbox sprite'tan biraz kucuk (forgiving), ama orantili.
            r = pygame.Rect(0, 0, int(dw * settings.SHIP_HITBOX_SCALE),
                            int(dh * settings.SHIP_HITBOX_SCALE))
        else:
            s = self.size
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
        """Gemiyi kendi arena dikdortgeni icinde tutar (tum sprite iceride)."""
        if self.image is not None:
            dw, dh = self._display_size()
            half_w, half_h = dw * 0.5, dh * 0.5
        else:
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

    def start_invuln(self) -> None:
        """Vurus sonrasi kisa i-frame + yanip sonme baslatir.

        Hasar MIKTARI ve uygulamasi Arena._take_damage'da yonetilir; bu metot
        yalnizca dokunulmazlik penceresini ve gorsel blink'i baslatir.
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

        # --- Resim varsa onu ciz (yukari bakan gemi sprite'i) ---
        if self.image is not None:
            target_w = max(1, int(self.size * settings.SHIP_IMG_SCALE))
            if self._scaled_for != target_w:   # boyut degisince yeniden olcekle
                iw, ih = self.image.get_size()
                target_h = max(1, int(round(target_w * ih / iw)))
                self._scaled_img = pygame.transform.smoothscale(
                    self.image, (target_w, target_h))
                self._scaled_for = target_w
            rect = self._scaled_img.get_rect(center=(int(self.x), int(self.y)))
            surf.blit(self._scaled_img, rect)
            return

        # --- Resim yoksa: ucgen govde (fallback) ---
        s = self.size
        cx, cy = self.x, self.y
        points = [
            (cx, cy - s * 0.85),            # burun
            (cx - s * 0.7, cy + s * 0.7),   # sol taban
            (cx, cy + s * 0.35),            # govde alt centik
            (cx + s * 0.7, cy + s * 0.7),   # sag taban
        ]
        pygame.draw.polygon(surf, self.color, points)
        pygame.draw.polygon(surf, settings.SHIP_OUTLINE, points, 2)
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
        # Her meteorun yuzey detay cizgileri icin BIR KEZ secilen rastgele
        # acilar (omur boyu sabit kalir; tohumlanmamis).
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

    @property
    def damage(self) -> int:
        """Boyuta gore verdigi hasar (puanla AYNI boyut-siniflandirmasi)."""
        th = settings.METEOR_SIZE_THRESHOLDS
        if self.radius < settings.scaled(th["small_max"]):
            return settings.METEOR_DAMAGE_SMALL
        if self.radius < settings.scaled(th["medium_max"]):
            return settings.METEOR_DAMAGE_MEDIUM
        return settings.METEOR_DAMAGE_LARGE

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
        radius = max(1, int(settings.PARTICLE_MAX_RADIUS * frac + 1))
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


# =====================================================================
# Enemy: rakip uzay gemisi (ust bantta devriye, lazer atar)
# =====================================================================
class Enemy:
    """Rakip uzay gemisi.

    Arenanin USTUNDE belirli bir bant icinde YATAY devriye yapar (asagi inmez),
    kenarlarda seker. Periyodik olarak, atildigi ANDAKI hedef gemi konumuna
    dogru duz giden bir lazer atar (want_fire True donunce cagiran spawn eder).
    Oyuncu mermisiyle ENEMY_HP vurusta yok olur.
    """

    def __init__(self, arena_rect: pygame.Rect, x: float, y: float):
        self.arena_rect = arena_rect
        self.x = float(x)
        self.y = float(y)
        self.size = settings.scaled(settings.ENEMY_SIZE)
        # Devriye yonu rastgele (sol/sag)
        self.vx = settings.scaled(settings.ENEMY_PATROL_SPEED)
        if random.random() < 0.5:
            self.vx = -self.vx
        self.hp = settings.ENEMY_HP
        self.max_hp = settings.ENEMY_HP
        # Ilk ates biraz gecikmeli (hemen ust uste atmasin)
        self._fire_timer = settings.ENEMY_FIRE_INTERVAL * random.uniform(0.5, 1.0)

    @property
    def rect(self) -> pygame.Rect:
        s = self.size
        r = pygame.Rect(0, 0, int(s * 1.5), int(s * 1.1))
        r.center = (int(self.x), int(self.y))
        return r

    @property
    def muzzle(self) -> tuple:
        """Lazerin cikacagi nokta (gemi alti)."""
        return (self.x, self.y + self.size * 0.5)

    def update(self, dt: float) -> None:
        """Yatay devriye; arena kenarlarinda sek (asagi/yukari hareket yok)."""
        self.x += self.vx * dt
        half = self.size * 0.75
        if self.x - half < self.arena_rect.left:
            self.x = self.arena_rect.left + half
            self.vx = abs(self.vx)
        elif self.x + half > self.arena_rect.right:
            self.x = self.arena_rect.right - half
            self.vx = -abs(self.vx)

    def want_fire(self, dt: float) -> bool:
        """Ates cooldown'u dolduysa True doner + cooldown'u sifirlar."""
        self._fire_timer -= dt
        if self._fire_timer <= 0.0:
            self._fire_timer = settings.ENEMY_FIRE_INTERVAL
            return True
        return False

    def hit(self) -> bool:
        """Mermi isabeti: HP azalt. HP 0'a indiyse True (gemi yok olur)."""
        self.hp -= 1
        return self.hp <= 0

    def draw(self, surf: pygame.Surface) -> None:
        s = self.size
        cx, cy = self.x, self.y
        # Asagi bakan dusman gemisi (ters ucgen + kabin)
        points = [
            (cx, cy + s * 0.85),            # burun asagi (oyuncuya bakar)
            (cx - s * 0.85, cy - s * 0.5),  # sol ust
            (cx + s * 0.85, cy - s * 0.5),  # sag ust
        ]
        pygame.draw.polygon(surf, settings.ENEMY_COLOR, points)
        pygame.draw.polygon(surf, settings.ENEMY_OUTLINE, points, 2)
        pygame.draw.circle(surf, settings.ENEMY_OUTLINE,
                           (int(cx), int(cy - s * 0.15)), max(2, int(s * 0.2)))
        # Kucuk HP cubugu (geminin ustunde) - kac vurus kaldigini gosterir
        if self.max_hp > 1:
            bw = int(s * 1.6)
            bh = max(2, int(s * 0.14))
            bx = int(cx - bw / 2)
            by = int(cy - s * 0.8)
            frac = max(0.0, self.hp / self.max_hp)
            pygame.draw.rect(surf, settings.ENEMY_HP_BAR_BG, (bx, by, bw, bh))
            pygame.draw.rect(surf, settings.ENEMY_HP_BAR_COLOR,
                             (bx, by, int(bw * frac), bh))


# =====================================================================
# EnemyLaser: rakip geminin attigi lazer (duz gider, takip etmez)
# =====================================================================
class EnemyLaser:
    """Rakip lazeri. Atildigi anda hedef konuma dogru yonelir ve DUZ gider
    (sonradan takip etmez). Oyuncu gemisine carparsa can goturur."""

    def __init__(self, x: float, y: float, target_x: float, target_y: float):
        self.x = float(x)
        self.y = float(y)
        dx = target_x - x
        dy = target_y - y
        dist = math.hypot(dx, dy) or 1.0   # sifira bolme korumasi
        speed = settings.scaled(settings.ENEMY_LASER_SPEED)
        self.vx = dx / dist * speed
        self.vy = dy / dist * speed
        self.r = max(2, int(settings.scaled(settings.ENEMY_LASER_RADIUS)))

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt

    @property
    def rect(self) -> pygame.Rect:
        d = self.r * 2
        r = pygame.Rect(0, 0, d, d)
        r.center = (int(self.x), int(self.y))
        return r

    def is_offscreen(self, arena_rect: pygame.Rect) -> bool:
        return (self.y - self.r > arena_rect.bottom or
                self.y + self.r < arena_rect.top or
                self.x + self.r < arena_rect.left or
                self.x - self.r > arena_rect.right)

    def draw(self, surf: pygame.Surface) -> None:
        # Hareket yonunde kisa bir iz + parlak bas
        tail = (int(self.x - self.vx * 0.03), int(self.y - self.vy * 0.03))
        pygame.draw.line(surf, settings.ENEMY_LASER_COLOR,
                         tail, (int(self.x), int(self.y)), max(2, self.r))
        pygame.draw.circle(surf, settings.ENEMY_LASER_COLOR,
                           (int(self.x), int(self.y)), self.r)
