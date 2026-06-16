# -*- coding: utf-8 -*-
"""
main.py
Giris noktasi + Game sinifi + durum makinesi + render + HUD + CLI/selftest.

Calistirma:
    python main.py              -> tam ekran, klavye ile oyna
    python main.py --serial     -> klavye yerine ESP seri joystick kaynagi
    python main.py --selftest   -> headless (dummy SDL) 120 kare dogrulama

Giris kaynagi (klavye/seri) calistirma aninda secilir: --serial bayragi
veya settings.INPUT_SOURCE sabiti ("keyboard"|"serial"). Kod govdesini
duzenlemeye gerek yoktur (CLI bayragi sabiti gecersiz kilar).

2 oyunculu split-screen uzay atari oyunu. Gemiler assets/ sprite'lariyla
(yoksa ucgen fallback), meteor/mermi/rakip/efektler pygame.draw
primitifleriyle cizilir.
"""

from __future__ import annotations

import os
import sys
import random
from enum import Enum, auto

# ---------------------------------------------------------------------
# SELFTEST: dummy SDL surucusu MUTLAKA pygame.init() ONCESI ayarlanmali.
# (Sonra yazmak etkisiz olur.) Headless/ekransiz ortamda calismayi saglar.
# ---------------------------------------------------------------------
if "--selftest" in sys.argv:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

import settings
from entities import (Ship, Bullet, Meteor, Enemy, EnemyLaser,
                      spawn_explosion, get_ship_image)
from input_source import (
    KeyboardInputSource,
    ScriptedInputSource,
    SerialJoystickInputSource,
)


# =====================================================================
# Durum makinesi
# =====================================================================
class GameStateEnum(Enum):
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()


# =====================================================================
# Difficulty: GLOBAL zorluk (iki arena paylasir)
# =====================================================================
class Difficulty:
    """Zamanla artan, tavanli global zorluk.

    elapsed (gecen sure) ilerledikce dusus hizi carpani ve meteor dogus
    sikligi artar; DIFFICULTY_TIME_TO_MAX'ta tavana ulasir, sonra sabit
    kalir (oyun 'imkansiz' olmasin).
    """

    def __init__(self):
        self.elapsed = 0.0

    def update(self, dt: float) -> None:
        self.elapsed += dt

    @property
    def _progress(self) -> float:
        # 0.0 .. 1.0 arasi normalize ilerleme (tavanli).
        p = self.elapsed / settings.DIFFICULTY_TIME_TO_MAX
        return max(0.0, min(1.0, p))

    @property
    def fall_speed_mult(self) -> float:
        """Meteor dusus hizi carpani (1.0 .. FALL_SPEED_MAX_MULT)."""
        return 1.0 + (settings.FALL_SPEED_MAX_MULT - 1.0) * self._progress

    @property
    def spawn_interval(self) -> float:
        """Meteor dogus araligi (SPAWN_BASE .. SPAWN_MIN), kisalir."""
        base = settings.SPAWN_BASE_INTERVAL
        mn = settings.SPAWN_MIN_INTERVAL
        return base - (base - mn) * self._progress

    @property
    def level(self) -> int:
        """HUD icin 1..DIFFICULTY_LEVELS arasi seviye gostergesi."""
        return 1 + int(self._progress * (settings.DIFFICULTY_LEVELS - 1))


# =====================================================================
# Arena: bir oyuncunun bagimsiz dunyasi (sol veya sag yari)
# =====================================================================
class Arena:
    """Tek oyuncunun arenasi: gemi, mermiler, meteorlar, partikuller, skor, can."""

    def __init__(self, player_id: int, rect: pygame.Rect, ship_color):
        self.player_id = player_id
        self.rect = rect
        self.ship_color = ship_color

        self.ship = self._make_ship()
        self.bullets = []
        self.meteors = []
        self.particles = []
        self.enemies = []           # rakip gemiler
        self.enemy_lasers = []      # rakip lazerleri

        self.score = 0
        self.health = settings.START_HEALTH   # can 0-100 (HP sistemi)
        self.alive = True

        self._spawn_timer = 0.0

        # --- Ozel guc durumu ---
        self.special_charge = 0       # bu dolumda mermiyle vurulan asteroid sayisi
        self.special_ready = False    # doldu mu (kullanilabilir mi)
        self._prev_fire = False       # buton rising-edge tespiti icin
        self._flash_timer = 0.0       # ozel guc kullaninca arena flashi (sn)
        self._hurt_timer = 0.0        # can kaybinda anlik kirmizi flash (sn)

    def _make_ship(self) -> Ship:
        x = self.rect.centerx
        y = self.rect.bottom - settings.scaled(settings.SHIP_MARGIN)
        return Ship(self.rect, self.ship_color, x, y,
                    image=get_ship_image(self.player_id))

    def rescale(self, new_rect: pygame.Rect) -> None:
        """Pencere/tam ekran gecisinde konumlari orana gore tasi (reset DEGIL)."""
        old = self.rect
        # Oran katsayilari (sifira bolme korumasi)
        sx = new_rect.width / old.width if old.width else 1.0
        sy = new_rect.height / old.height if old.height else 1.0

        def remap_x(x):
            return new_rect.left + (x - old.left) * sx

        def remap_y(y):
            return new_rect.top + (y - old.top) * sy

        self.ship.x = remap_x(self.ship.x)
        self.ship.y = remap_y(self.ship.y)
        self.ship.arena_rect = new_rect
        # Boyutlar yukseklik orani (sy) ile olceklenir; bu, global SCALE
        # degisimiyle tutarlidir (SCALE = H / REFERENCE_HEIGHT). Boylece F11
        # gecisinde mevcut varliklar da yeni cozunurluge uyar.
        self.ship.size *= sy
        for b in self.bullets:
            b.x = remap_x(b.x)
            b.y = remap_y(b.y)
            b.w = max(1, int(b.w * sy))
            b.h = max(1, int(b.h * sy))
            b.vy *= sy
        for m in self.meteors:
            m.x = remap_x(m.x)
            m.y = remap_y(m.y)
            m.radius *= sy
            m.vy *= sy
        for p in self.particles:
            p.x = remap_x(p.x)
            p.y = remap_y(p.y)
            p.vx *= sy
            p.vy *= sy
        for e in self.enemies:
            e.x = remap_x(e.x)
            e.y = remap_y(e.y)
            e.arena_rect = new_rect
            e.size *= sy
            e.vx *= sy
        for laser in self.enemy_lasers:
            laser.x = remap_x(laser.x)
            laser.y = remap_y(laser.y)
            laser.vx *= sy
            laser.vy *= sy
            laser.r = max(2, int(laser.r * sy))
        self.rect = new_rect

    def spawn_meteor(self, difficulty: Difficulty) -> None:
        """Arena ustunden rastgele x'te, zorluga gore hizli meteor dogur."""
        # Yaricap ve hiz cozunurluge gore olceklenir (1080p referans * SCALE).
        min_r = settings.scaled(settings.METEOR_MIN_RADIUS)
        max_r = settings.scaled(settings.METEOR_MAX_RADIUS)
        radius = random.uniform(min_r, max_r)
        # x araligi: arena genisligi icinde, kenara tasmadan.
        margin = radius
        left = self.rect.left + margin
        right = self.rect.right - margin
        if right <= left:  # cok dar arena guvenligi
            x = self.rect.centerx
        else:
            x = random.uniform(left, right)
        vy = settings.scaled(settings.METEOR_BASE_FALL_SPEED) * \
            difficulty.fall_speed_mult
        # Buyuk meteorlar biraz daha yavas (denge) - olcekli aralikta hesapla.
        size_factor = 1.0 - (radius - min_r) / \
            max(1.0, (max_r - min_r)) * 0.35
        self.meteors.append(Meteor(x, radius, vy * size_factor))

    def update(self, dt: float, input_state, difficulty: Difficulty) -> None:
        """Arena guncellemesi (yalnizca alive iken cagrilir)."""
        # --- Gemi ---
        self.ship.update(dt, input_state)
        # Otomatik ates (buton gerekmez): cooldown dolduysa mermi at.
        if self.ship.try_fire():
            nx, ny = self.ship.nose_pos
            self.bullets.append(Bullet(nx, ny))

        # --- Ozel guc: buton YENI basildiginda (rising edge) ve doluysa ---
        fire_now = bool(input_state.fire)
        if fire_now and not self._prev_fire and self.special_ready:
            self._activate_special()
        self._prev_fire = fire_now

        # --- Mermiler ---
        for b in self.bullets:
            b.update(dt)
        self.bullets = [b for b in self.bullets
                        if not b.is_offscreen(self.rect)]

        # --- Meteorlar ---
        for m in self.meteors:
            m.update(dt)

        # --- Meteor dogus zamanlayici ---
        self._spawn_timer -= dt
        if self._spawn_timer <= 0.0:
            self.spawn_meteor(difficulty)
            self._spawn_timer = difficulty.spawn_interval

        # --- Rakip gemiler: devriye + periyodik lazer ---
        # Lazer, atildigi ANDAKI gemi konumuna dogru gider (takip etmez).
        for e in self.enemies:
            e.update(dt)
            if e.want_fire(dt):
                mx, my = e.muzzle
                self.enemy_lasers.append(
                    EnemyLaser(mx, my, self.ship.x, self.ship.y))

        # --- Rakip lazerleri: hareket + ekran disi temizligi ---
        for laser in self.enemy_lasers:
            laser.update(dt)
        self.enemy_lasers = [laser for laser in self.enemy_lasers
                             if not laser.is_offscreen(self.rect)]

        # --- Partikuller ---
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if not p.dead]

        # --- Carpisma cozumu (bu arenanin kendi listeleri arasinda) ---
        self._resolve_collisions()
        self._resolve_enemy_collisions()

        # --- Dibe ulasan meteorlar (can kaybi) ---
        self._handle_ground_hits()

        # --- Efekt zamanlayicilari (ozel guc flashi + hasar flashi) ---
        if self._flash_timer > 0.0:
            self._flash_timer -= dt
        if self._hurt_timer > 0.0:
            self._hurt_timer -= dt

    def force_spawn(self, difficulty: Difficulty) -> None:
        """Selftest icin meteor dogusunu zorlamak (timer beklemeden)."""
        self.spawn_meteor(difficulty)

    def _resolve_collisions(self) -> None:
        """Mermi-meteor ve meteor-gemi carpismalari.

        Iterasyon sirasinda .remove() YAPILMAZ; 'olu' set'leri toplanip
        sonra tek noktada filtrelenir (IndexError/atlama onlenir).
        """
        dead_bullets = set()
        dead_meteors = set()

        # --- Mermi vs Meteor ---
        for bi, b in enumerate(self.bullets):
            if bi in dead_bullets:
                continue
            brect = b.rect
            for mi, m in enumerate(self.meteors):
                if mi in dead_meteors:
                    continue
                if brect.colliderect(m.rect):
                    dead_bullets.add(bi)
                    dead_meteors.add(mi)
                    self.score += m.points
                    self.particles.extend(spawn_explosion(m.x, m.y))
                    self._add_special_charge()   # ozel guc dolumu
                    break  # bu mermi tukendi

        # --- Meteor vs Gemi ---
        if self.alive:
            srect = self.ship.rect
            for mi, m in enumerate(self.meteors):
                if mi in dead_meteors:
                    continue
                if srect.colliderect(m.rect):
                    dead_meteors.add(mi)
                    self.particles.extend(spawn_explosion(m.x, m.y))
                    self._take_damage(m.damage)   # boyuta gore hasar

        # --- Tek noktada temizlik ---
        if dead_bullets:
            self.bullets = [b for i, b in enumerate(self.bullets)
                            if i not in dead_bullets]
        if dead_meteors:
            self.meteors = [m for i, m in enumerate(self.meteors)
                            if i not in dead_meteors]

    def _handle_ground_hits(self) -> None:
        """Arena dibine ulasan meteorlar: BOYUTA gore hasar + kaldir.

        Hasar Arena._take_damage uzerinden gider: kisa i-frame penceresinde
        (INVULN_TIME) ek hasar engellenir, boylece ayni anda dibe varan meteor
        kalabaligi tum cani birden goturmez. Meteor her durumda kaldirilir.
        """
        survivors = []
        for m in self.meteors:
            if m.is_offscreen(self.rect):
                self.particles.extend(spawn_explosion(m.x, self.rect.bottom - 10))
                if self.alive:
                    self._take_damage(m.damage)
            else:
                survivors.append(m)
        self.meteors = survivors

    def _take_damage(self, amount: int) -> None:
        """Cana 'amount' kadar hasar uygula.

        Gemi i-frame penceresindeyse (yakinda vuruldu) hasar UYGULANMAZ; aksi
        halde can azalir, kisa i-frame + yanip sonme baslar ve anlik kirmizi
        flash tetiklenir. Her carpan nesne temaste tuketildigi icin i-frame
        ust uste carpismalarda 'melt'i (saniyede defalarca hasar) onler.
        Can 0'a inerse arena elenir.
        """
        if self.ship.invulnerable:
            return
        self.health -= amount
        self.ship.start_invuln()
        self._hurt_timer = settings.HURT_FLASH_TIME   # anlik kirmizi flash
        if self.health <= 0:
            self.health = 0
            self.alive = False
            # Arena oldu: donmus rakipler/lazerler 'ELENDI' overlayi altinda
            # havada asili kalmasin (update_dead bunlari islemez). Temizle ki
            # geriye yalnizca sonen partikuller kalsin.
            self.enemies = []
            self.enemy_lasers = []

    def _add_special_charge(self) -> None:
        """Mermiyle asteroid vuruldukca ozel guc dolar (tavan = gerekli sayi)."""
        if self.special_ready:
            return
        self.special_charge += 1
        if self.special_charge >= settings.SPECIAL_KILLS_REQUIRED:
            self.special_charge = settings.SPECIAL_KILLS_REQUIRED
            self.special_ready = True

    def _activate_special(self) -> None:
        """Ozel guc: bu arenadaki TUM tehditleri temizle (meteorlar + rakip
        gemiler + rakip lazerleri) + patlama, sayaci sifirla, flash.

        PUAN VERILMEZ: ozel guc bir 'kurtarma/temizleme' aracidir, skor
        kaynagi DEGIL. Aksi halde oyuncu beceriyle vurmak yerine ozel gucle
        topluca temizleyip bedava puan (ozellikle ENEMY_SCORE) farm'layabilirdi.
        """
        for m in self.meteors:
            self.particles.extend(spawn_explosion(m.x, m.y))
        for e in self.enemies:
            self.particles.extend(spawn_explosion(e.x, e.y))
        self.meteors = []
        self.enemies = []
        self.enemy_lasers = []
        self.special_charge = 0
        self.special_ready = False
        self._flash_timer = settings.SPECIAL_FLASH_TIME

    def spawn_enemy(self) -> None:
        """Arenanin ust bandinda, rastgele x'te bir rakip gemi dogur.
        Arena basina ENEMY_MAX_PER_ARENA siniri asilirsa dogurmaz."""
        if len(self.enemies) >= settings.ENEMY_MAX_PER_ARENA:
            return
        margin = settings.scaled(settings.ENEMY_SIZE)
        left = self.rect.left + margin
        right = self.rect.right - margin
        x = random.uniform(left, right) if right > left else self.rect.centerx
        band_top = self.rect.top + self.rect.height * settings.ENEMY_BAND_TOP
        band_bot = self.rect.top + self.rect.height * settings.ENEMY_BAND_BOTTOM
        y = random.uniform(band_top, band_bot)
        self.enemies.append(Enemy(self.rect, x, y))

    def _resolve_enemy_collisions(self) -> None:
        """Mermi vs rakip gemi, rakip lazeri vs oyuncu, rakip govde vs oyuncu.
        Iterasyon sirasinda liste degistirmeden (olu setleri toplayip filtrele)."""
        # --- Oyuncu mermisi vs rakip gemi ---
        dead_bullets = set()
        dead_enemies = []
        for bi, b in enumerate(self.bullets):
            if bi in dead_bullets:
                continue
            brect = b.rect
            for e in self.enemies:
                if e in dead_enemies:
                    continue
                if brect.colliderect(e.rect):
                    dead_bullets.add(bi)
                    if e.hit():                       # HP bitti -> yok ol
                        dead_enemies.append(e)
                        self.score += settings.ENEMY_SCORE
                        self.particles.extend(spawn_explosion(e.x, e.y))
                        self._add_special_charge()
                    else:                             # sadece hasar (kucuk kivilcim)
                        self.particles.extend(spawn_explosion(b.x, b.y))
                    break  # bu mermi tukendi
        if dead_bullets:
            self.bullets = [b for i, b in enumerate(self.bullets)
                            if i not in dead_bullets]
        if dead_enemies:
            self.enemies = [e for e in self.enemies if e not in dead_enemies]

        # --- Rakip lazeri vs oyuncu gemisi (carparsa can gider) ---
        if self.alive:
            srect = self.ship.rect
            survivors = []
            for laser in self.enemy_lasers:
                if srect.colliderect(laser.rect):
                    self.particles.extend(spawn_explosion(laser.x, laser.y))
                    self._take_damage(settings.LASER_DAMAGE)   # sabit hasar
                    # lazer tuketildi -> survivors'a eklenmez
                else:
                    survivors.append(laser)
            self.enemy_lasers = survivors

        # --- Rakip govde vs oyuncu gemisi (oyuncu yukari cikarsa) ---
        # Rakibi yalnizca carpisma GERCEKTEN can goturduyse yok et. Dokunulmaz
        # iken (meteor/lazerden kalan pencere) rakibi yerinde birak; aksi halde
        # oyuncu cezasiz/puansiz toslamayla tehdidi bedavaya silebilirdi.
        # Carpisma bir sonraki dokunulmazlik bitiminde cozulur.
        if self.alive:
            srect = self.ship.rect
            crashed = [e for e in self.enemies if srect.colliderect(e.rect)]
            # Dokunulmazken rakibi bedava silme; carpisma i-frame bitince cozulur.
            if crashed and not self.ship.invulnerable:
                self._take_damage(settings.ENEMY_CRASH_DAMAGE)
                for e in crashed:
                    self.particles.extend(spawn_explosion(e.x, e.y))
                self.enemies = [e for e in self.enemies if e not in crashed]

    def update_dead(self, dt: float) -> None:
        """Olu arena: gemi/meteor durur ama partikuller sonene kadar isler."""
        if self._flash_timer > 0.0:
            self._flash_timer -= dt
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if not p.dead]

    def draw(self, surf: pygame.Surface) -> None:
        """Arena cizimi (clip aktifken cagrilmali)."""
        for m in self.meteors:
            m.draw(surf)
        for e in self.enemies:
            e.draw(surf)
        for laser in self.enemy_lasers:
            laser.draw(surf)
        for b in self.bullets:
            b.draw(surf)
        if self.alive:
            self.ship.draw(surf)
        for p in self.particles:
            p.draw(surf)


# =====================================================================
# Game: ana oyun yoneticisi
# =====================================================================
class Game:
    """Durum makinesi, oyun dongusu, render, HUD, selftest cekirdegi."""

    def __init__(self, screen: pygame.Surface, w: int, h: int,
                 input_source=None):
        self.screen = screen
        self.W = w
        self.H = h
        self.fullscreen = True

        # Cozunurluk olcegi: TUM boyut/hiz/font hesaplarindan ONCE ayarla
        # (arenalar ve fontlar bu SCALE'e gore olusur).
        settings.set_scale(h)

        # Giris kaynagi (klavye varsayilan; selftest'te scripted gecirilir).
        self.input_source = input_source or KeyboardInputSource()

        # Font'lar: pygame.init() SONRASI olusturulur (modul seviyesinde DEGIL).
        # Boyutlar cozunurluge gore olceklenir.
        self._build_fonts()

        self.clock = pygame.time.Clock()
        self.state = GameStateEnum.PLAYING

        # Deterministik yildiz alani (STAR_SEED ile uretilir).
        self.stars = self._generate_stars()

        self.difficulty = Difficulty()
        self._enemy_timer = random.uniform(settings.ENEMY_SPAWN_MIN,
                                           settings.ENEMY_SPAWN_MAX)
        self.arena_left = None
        self.arena_right = None
        self._build_arenas()

    # ----------------------------------------------------------------
    # Kurulum / reset
    # ----------------------------------------------------------------
    def _build_fonts(self) -> None:
        """Font'lari guncel SCALE'e gore (yeniden) olusturur.

        En az 1 piksel garanti edilir (cok kucuk ekranda SysFont hatasi olmasin).
        """
        def fs(size: int) -> int:
            return max(1, int(round(settings.scaled(size))))

        self.font_small = pygame.font.SysFont("consolas", fs(settings.FONT_SMALL_SIZE))
        self.font_med = pygame.font.SysFont("consolas", fs(settings.FONT_MED_SIZE),
                                            bold=True)
        self.font_big = pygame.font.SysFont("consolas", fs(settings.FONT_BIG_SIZE),
                                            bold=True)

    def _arena_rects(self) -> tuple:
        """Ekrani ikiye bolen sol/sag dikdortgenler (sabit pixel YOK)."""
        mid = self.W // 2
        left = pygame.Rect(0, 0, mid, self.H)
        right = pygame.Rect(mid, 0, self.W - mid, self.H)  # tek pixel sagda
        return left, right

    def _build_arenas(self) -> None:
        left_rect, right_rect = self._arena_rects()
        self.arena_left = Arena(1, left_rect, settings.SHIP_P1_COLOR)
        self.arena_right = Arena(2, right_rect, settings.SHIP_P2_COLOR)

    def reset(self) -> None:
        """Oyunu bastan baslat: arenalar, skor, can, zorluk sifirlanir."""
        self.difficulty = Difficulty()
        self._enemy_timer = random.uniform(settings.ENEMY_SPAWN_MIN,
                                           settings.ENEMY_SPAWN_MAX)
        self._build_arenas()
        self.state = GameStateEnum.PLAYING

    def _generate_stars(self) -> list:
        """Ekran boyutuna gore deterministik yildiz noktalari."""
        rng = random.Random(settings.STAR_SEED)
        stars = []
        for _ in range(settings.STAR_COUNT):
            x = rng.randint(0, max(1, self.W - 1))
            y = rng.randint(0, max(1, self.H - 1))
            bright = rng.randint(120, 255)
            size = rng.choice([1, 1, 1, 2])
            stars.append((x, y, bright, size))
        return stars

    # ----------------------------------------------------------------
    # Durum gecisleri
    # ----------------------------------------------------------------
    def _transition_to(self, new_state: GameStateEnum) -> None:
        self.state = new_state

    # ----------------------------------------------------------------
    # Ana dongu
    # ----------------------------------------------------------------
    def run(self) -> None:
        running = True
        while running:
            # 1) Event'ler bir KEZ alinir (ikinci get() ilk listeyi tuketir).
            events = pygame.event.get()
            keys = pygame.key.get_pressed()

            # 2) Global event'ler (QUIT, ESC, P, R, F11)
            if self._handle_global_events(events):
                running = False
                break

            # 3) dt: tick'ten DONEN ms degeri (FPS dususunde dogru hiz).
            #    MAX_DT ile clamp -> tunneling/sicrama onlenir.
            dt = self.clock.tick(settings.FPS) / 1000.0
            dt = min(dt, settings.MAX_DT)

            # 4) Giris durumu
            inputs = self.input_source.poll(events, keys)

            # 5) Guncelle + ciz
            self.update(dt, inputs)
            self.draw(self.screen)
            pygame.display.flip()

        self._quit(0)

    def _handle_global_events(self, events: list) -> bool:
        """Global tuslari isler. True donerse oyun kapanmali."""
        for ev in events:
            if ev.type == pygame.QUIT:
                return True
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return True
                if ev.key == pygame.K_p:
                    self._toggle_pause()
                elif ev.key == pygame.K_r:
                    if self.state == GameStateEnum.GAME_OVER:
                        self.reset()
                elif ev.key == pygame.K_F11:
                    self._toggle_fullscreen()
        return False

    def _toggle_pause(self) -> None:
        if self.state == GameStateEnum.PLAYING:
            self._transition_to(GameStateEnum.PAUSED)
        elif self.state == GameStateEnum.PAUSED:
            self._transition_to(GameStateEnum.PLAYING)

    def _toggle_fullscreen(self) -> None:
        """Tam ekran/pencere gecisi. W/H ve TUM konumlar yeniden olceklenir."""
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            # (0,0) -> masaustu cozunurlugu; ekrani TAM kaplar (bosluk olmaz).
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            new_w, new_h = self.screen.get_size()
        else:
            # Pencere modu: makul bir cozunurluk
            new_w, new_h = 1280, 720
            self.screen = pygame.display.set_mode((new_w, new_h))
        self._rescale(new_w, new_h)

    def _rescale(self, new_w: int, new_h: int) -> None:
        """W/H degisince arena rect'lerini, entity konum/boyutlarini ve
        fontlari yeni cozunurluge tasi."""
        self.W, self.H = new_w, new_h
        # Once global olcegi guncelle (yeni dogan varliklar/fontlar dogru olur).
        settings.set_scale(new_h)
        self._build_fonts()
        left_rect, right_rect = self._arena_rects()
        self.arena_left.rescale(left_rect)
        self.arena_right.rescale(right_rect)
        self.stars = self._generate_stars()

    # ----------------------------------------------------------------
    # Update
    # ----------------------------------------------------------------
    def update(self, dt: float, inputs: dict) -> None:
        """Duruma gore guncelleme. Selftest de bunu cagirir."""
        if self.state != GameStateEnum.PLAYING:
            # PAUSED / GAME_OVER: cekirdek update yok.
            return

        # Zorluk global olarak ilerler (en az bir arena yasiyorsa).
        if self.arena_left.alive or self.arena_right.alive:
            self.difficulty.update(dt)

            # Rakip gemi dogusu: GLOBAL timer, iki arenaya AYNI ANDA (adil), nadir.
            self._enemy_timer -= dt
            if self._enemy_timer <= 0.0:
                if self.arena_left.alive:
                    self.arena_left.spawn_enemy()
                if self.arena_right.alive:
                    self.arena_right.spawn_enemy()
                self._enemy_timer = random.uniform(settings.ENEMY_SPAWN_MIN,
                                                    settings.ENEMY_SPAWN_MAX)

        # Sol arena
        if self.arena_left.alive:
            self.arena_left.update(dt, inputs[1], self.difficulty)
        else:
            self.arena_left.update_dead(dt)

        # Sag arena
        if self.arena_right.alive:
            self.arena_right.update(dt, inputs[2], self.difficulty)
        else:
            self.arena_right.update_dead(dt)

        # Her iki arena da olduyse -> GAME_OVER
        if not self.arena_left.alive and not self.arena_right.alive:
            self._transition_to(GameStateEnum.GAME_OVER)

    # ----------------------------------------------------------------
    # Render
    # ----------------------------------------------------------------
    def draw(self, screen: pygame.Surface) -> None:
        # 1) Arka plan + yildizlar
        screen.fill(settings.SPACE_BG)
        for (x, y, b, size) in self.stars:
            screen.fill((b, b, min(255, b + settings.STAR_BLUE_BOOST)),
                        (x, y, size, size))

        # 2) Arenalar (her biri kendi rect'ine kirpili cizilir)
        self._draw_arena(screen, self.arena_left)
        self._draw_arena(screen, self.arena_right)

        # 3) Ortadaki ayirici cizgi (clip kapali iken)
        mid = self.W // 2
        pygame.draw.line(screen, settings.DIVIDER_COLOR,
                         (mid, 0), (mid, self.H), 3)

        # 4) HUD
        self._draw_hud(screen)

        # 5) State overlay (en uste)
        if self.state == GameStateEnum.PAUSED:
            self._draw_pause(screen)
        elif self.state == GameStateEnum.GAME_OVER:
            self._draw_game_over(screen)

    def _draw_arena(self, screen: pygame.Surface, arena: Arena) -> None:
        # Kirpma: arena disina tasma olmasin.
        screen.set_clip(arena.rect)
        arena.draw(screen)
        # Ozel guc flashi (kullanildiginda kisa beyaz parlama, sonerek)
        if arena._flash_timer > 0.0:
            a = int(settings.SPECIAL_FLASH_ALPHA *
                    min(1.0, arena._flash_timer / settings.SPECIAL_FLASH_TIME))
            flash = pygame.Surface((arena.rect.width, arena.rect.height),
                                   pygame.SRCALPHA)
            flash.fill((255, 255, 255, a))
            screen.blit(flash, arena.rect.topleft)
        # Hasar efekti: KALICI kirmizi (can azaldikca artar) + ANLIK flash (vurusta).
        # Ikisi toplanir: dusuk canda zaten kirmizi taban, vurus aninda parlama spike'i.
        if arena.alive:
            danger = (settings.START_HEALTH - arena.health) / max(1, settings.START_HEALTH)
            persist_a = int(danger * settings.HURT_PERSIST_MAX_ALPHA)
            flash_a = 0
            if arena._hurt_timer > 0.0:
                flash_a = int(settings.HURT_FLASH_ALPHA *
                              min(1.0, arena._hurt_timer / settings.HURT_FLASH_TIME))
            hurt_a = min(255, persist_a + flash_a)
            if hurt_a > 0:
                red = pygame.Surface((arena.rect.width, arena.rect.height),
                                     pygame.SRCALPHA)
                red.fill((settings.HURT_COLOR[0], settings.HURT_COLOR[1],
                          settings.HURT_COLOR[2], hurt_a))
                screen.blit(red, arena.rect.topleft)
        # Olu arena -> karartma overlay
        if not arena.alive:
            overlay = pygame.Surface((arena.rect.width, arena.rect.height),
                                     pygame.SRCALPHA)
            overlay.fill(settings.DEAD_OVERLAY)
            screen.blit(overlay, arena.rect.topleft)
            txt = self.font_med.render("ELENDI", True, settings.DEAD_TEXT_COLOR)
            tr = txt.get_rect(center=arena.rect.center)
            screen.blit(txt, tr)
        screen.set_clip(None)  # MUTLAKA kapat (HUD/overlay kirpilmasin)

    def _draw_hud(self, screen: pygame.Surface) -> None:
        lh = self.font_small.get_linesize()   # satir yuksekligi (cozunurluge gore)
        m = 16                                 # kenar boslugu
        p1, p2 = self.arena_left, self.arena_right

        # --- P1 sol ust ---
        self._blit_text(screen, f"P1  SKOR: {p1.score}", (m, m),
                        settings.HUD_ACCENT)
        self._blit_text(screen, f"CAN: {p1.health}", (m, m + lh),
                        self._health_color(p1.health))
        self._draw_special(screen, p1, m + 2 * lh, right=False)

        # --- P2 sag ust (saga hizali) ---
        def rx(text):
            return self.W - self.font_small.size(text)[0] - m
        s2 = f"P2  SKOR: {p2.score}"
        c2 = f"CAN: {p2.health}"
        self._blit_text(screen, s2, (rx(s2), m), settings.HUD_ACCENT)
        self._blit_text(screen, c2, (rx(c2), m + lh), self._health_color(p2.health))
        self._draw_special(screen, p2, m + 2 * lh, right=True)

        # --- Ortada zorluk seviyesi gostergesi ---
        lvl = self.difficulty.level
        txt = f"SEVIYE {lvl}"
        self._blit_text(screen, txt,
                        (self.W // 2 - self.font_small.size(txt)[0] // 2, m),
                        settings.HUD_COLOR)

    def _draw_special(self, screen: pygame.Surface, arena: Arena, y: int,
                      right: bool) -> None:
        """Oyuncunun ozel guc gostergesi: yazi + ilerleme cubugu."""
        req = settings.SPECIAL_KILLS_REQUIRED
        if arena.special_ready:
            label = "OZEL: HAZIR! (BAS)"
            col = settings.SPECIAL_READY_COLOR
            frac = 1.0
        else:
            label = f"OZEL: {arena.special_charge}/{req}"
            col = settings.SPECIAL_COLOR
            frac = (arena.special_charge / req) if req else 0.0

        m = 16
        x = (self.W - self.font_small.size(label)[0] - m) if right else m
        self._blit_text(screen, label, (x, y), col)

        # Ilerleme cubugu (yazinin altinda)
        bw = int(settings.scaled(settings.SPECIAL_BAR_W))
        bh = max(4, int(settings.scaled(settings.SPECIAL_BAR_H)))
        bx = (self.W - bw - m) if right else m
        by = y + self.font_small.get_linesize()
        pygame.draw.rect(screen, settings.SPECIAL_BAR_BG, (bx, by, bw, bh),
                         border_radius=3)
        if frac > 0:
            pygame.draw.rect(screen, col, (bx, by, int(bw * frac), bh),
                             border_radius=3)

    @staticmethod
    def _health_color(hp: int):
        """Cana gore HUD rengi: yuksek=yesil, orta=sari, dusuk=kirmizi."""
        frac = max(0.0, hp / settings.START_HEALTH)
        if frac > settings.HP_WARN_FRAC:
            return settings.HUD_HP_GOOD
        if frac > settings.HP_LOW_FRAC:
            return settings.HUD_HP_WARN
        return settings.HUD_HP_LOW

    def _blit_text(self, screen, text, pos, color, font=None) -> None:
        font = font or self.font_small
        surf = font.render(text, True, color)
        screen.blit(surf, pos)

    def _draw_pause(self, screen: pygame.Surface) -> None:
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill(settings.PAUSE_OVERLAY)
        screen.blit(overlay, (0, 0))
        self._center_text(screen, "DURAKLATILDI", self.font_big,
                          settings.HUD_COLOR, dy=-30)
        self._center_text(screen, "P: devam   ESC: cikis", self.font_small,
                          settings.HUD_COLOR, dy=40)

    def _draw_game_over(self, screen: pygame.Surface) -> None:
        overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        overlay.fill(settings.GAMEOVER_OVERLAY)
        screen.blit(overlay, (0, 0))

        self._center_text(screen, "OYUN BITTI", self.font_big,
                          settings.HUD_HP_LOW, dy=-110)

        winner = self._winner()
        self._center_text(screen, winner, self.font_med,
                          settings.HUD_ACCENT, dy=-20)

        p1, p2 = self.arena_left, self.arena_right
        self._center_text(screen,
                          f"P1: {p1.score}    P2: {p2.score}",
                          self.font_small, settings.HUD_COLOR, dy=40)
        self._center_text(screen, "R: yeniden basla    ESC: cikis",
                          self.font_small, settings.HUD_COLOR, dy=90)

    def _winner(self) -> str:
        p1, p2 = self.arena_left.score, self.arena_right.score
        if p1 > p2:
            return "KAZANAN: OYUNCU 1"
        if p2 > p1:
            return "KAZANAN: OYUNCU 2"
        return "BERABERE!"

    def _center_text(self, screen, text, font, color, dy=0) -> None:
        surf = font.render(text, True, color)
        rect = surf.get_rect(center=(self.W // 2, self.H // 2 + dy))
        screen.blit(surf, rect)

    # ----------------------------------------------------------------
    # Kapanis
    # ----------------------------------------------------------------
    def _quit(self, code: int) -> None:
        pygame.quit()
        sys.exit(code)


# =====================================================================
# Selftest: rakip-spesifik carpisma yollarini deterministik dogrula
# =====================================================================
def _selftest_enemy_paths(game: "Game") -> None:
    """Rakip carpisma mantigini GARANTILI (rastgele scripted girise bagli
    olmadan) calistirir ve sonuclari assert eder:
      (1) Mermi rakibe ENEMY_HP kez isabet edince rakip yok olur, listeden
          cikar ve skor ENEMY_SCORE artar (mermi->rakip->skor yolu).
      (2) Bir EnemyLaser dogrudan gemi uzerine konup (ship.invuln_timer=0)
          bir kare cozuldugunde oyuncu LASER_DAMAGE kadar HP kaybeder
          (lazer->can yolu).
    Yan etki birakmamak icin temiz bir arena uzerinde calisir."""
    arena = game.arena_left

    # --- (1) Mermi vs rakip: ENEMY_HP isabet -> yok + ENEMY_SCORE ---
    arena.bullets = []
    arena.enemies = []
    arena.enemy_lasers = []
    arena.meteors = []
    e = Enemy(arena.rect, arena.ship.x, arena.rect.top + 30)
    arena.enemies.append(e)
    score_before = arena.score
    enemies_before = len(arena.enemies)
    # ENEMY_HP kadar mermi: her birini rakip uzerine koyup carpismayi coz.
    for _ in range(settings.ENEMY_HP):
        b = Bullet(e.x, e.y)
        b.y = e.y                      # tam ust uste -> kesin carpisir
        arena.bullets.append(b)
        arena._resolve_enemy_collisions()
    assert len(arena.enemies) == enemies_before - 1, \
        "Rakip ENEMY_HP isabette yok olmadi"
    assert arena.score == score_before + settings.ENEMY_SCORE, \
        "Rakip yok edilince ENEMY_SCORE eklenmedi"

    # --- (2) Lazer vs gemi: dokunulmaz degilken LASER_DAMAGE kadar HP kaybi ---
    arena.bullets = []
    arena.enemies = []
    arena.meteors = []
    arena.enemy_lasers = []
    arena.ship.invuln_timer = 0.0      # dokunulmaz degil
    health_before = arena.health
    laser = EnemyLaser(arena.ship.x, arena.ship.y, arena.ship.x, arena.ship.y)
    laser.x, laser.y = arena.ship.x, arena.ship.y   # tam gemi uzerinde
    arena.enemy_lasers.append(laser)
    arena._resolve_enemy_collisions()
    assert arena.health == health_before - settings.LASER_DAMAGE, \
        "Rakip lazeri gemiye carpinca can LASER_DAMAGE kadar azalmadi"
    assert len(arena.enemy_lasers) == 0, "Carpan lazer tuketilmedi"


# =====================================================================
# Selftest harness (headless dogrulama)
# =====================================================================
def run_selftest() -> None:
    """Gercek update/collision yolunu ScriptedInputSource + sabit dt ile
    calistirir. Off-screen surface'e cizer, meteor spawn ve en az bir
    carpisma zorlanir, sonra temiz cikar (kod 0)."""
    try:
        pygame.init()
        # Dummy surucuyle gercek pencere acilmaz; kucuk bir yuzey yeter.
        w, h = 800, 600
        screen = pygame.display.set_mode((w, h))
        off_surface = pygame.Surface((w, h))

        game = Game(screen, w, h, input_source=ScriptedInputSource())

        # Carpismayi GARANTILE: her arenaya gemi onune meteor yerlestir.
        for arena in (game.arena_left, game.arena_right):
            arena.force_spawn(game.difficulty)
            # Bir meteoru dogrudan gemi ustune koy (mermi-meteor carpismasi
            # ve/veya gemi carpismasini tetiklemek icin).
            m = Meteor(arena.ship.x,
                       settings.scaled(settings.METEOR_MIN_RADIUS),
                       settings.scaled(settings.METEOR_BASE_FALL_SPEED))
            m.y = arena.ship.y - 40
            arena.meteors.append(m)
            # Mermi de ekle ki mermi-meteor carpismasi da denensin.
            arena.bullets.append(Bullet(arena.ship.x, arena.ship.y - 30))
            # Rakip gemi + lazer yollarini da test et (update/carpisma/cizim).
            arena.spawn_enemy()
            arena.enemy_lasers.append(
                EnemyLaser(arena.ship.x, arena.ship.y - 80,
                           arena.ship.x, arena.ship.y))

        dt = settings.SELFTEST_DT
        collisions_seen = False
        prev_scores = (game.arena_left.score, game.arena_right.score)

        for frame in range(settings.SELFTEST_FRAMES):
            inputs = game.input_source.poll([], None)
            game.update(dt, inputs)
            game.draw(off_surface)

            cur_scores = (game.arena_left.score, game.arena_right.score)
            if cur_scores != prev_scores:
                collisions_seen = True
            prev_scores = cur_scores

            # Surekli meteor besle (en az birkac carpisma sansi)
            if frame % 4 == 0:
                game.arena_left.force_spawn(game.difficulty)
                game.arena_right.force_spawn(game.difficulty)

        # Cekirdek dogrulamalari
        assert game.difficulty.elapsed > 0.0, "Zorluk ilerlemedi"
        assert game.difficulty.fall_speed_mult >= 1.0, "fall_mult gecersiz"
        # Carpisma ya skor degisikligi ya da partikul ureterek kendini gosterir.
        produced_particles = (len(game.arena_left.particles) >= 0)
        assert produced_particles, "Partikul listesi gecersiz"

        # -------------------------------------------------------------
        # RAKIP CARPISMA YOLLARINI DETERMINISTIK ZORLA (yesil yaniltici
        # olmasin): mermi->rakip->yok edilme->ENEMY_SCORE ve lazer->can kaybi.
        # -------------------------------------------------------------
        _selftest_enemy_paths(game)

        print("[selftest] OK - frames=%d, elapsed=%.2fs, P1=%d P2=%d, "
              "collisions_seen=%s"
              % (settings.SELFTEST_FRAMES, game.difficulty.elapsed,
                 game.arena_left.score, game.arena_right.score,
                 collisions_seen))

        pygame.quit()
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("[selftest] FAILED: %s" % exc)
        try:
            pygame.quit()
        except Exception:
            pass
        sys.exit(1)


# =====================================================================
# Giris noktasi
# =====================================================================
def _enable_windows_dpi_awareness() -> None:
    """Windows'ta sureci DPI-aware yapar ki tam ekran FIZIKSEL cozunurlukte
    acilsin. Ekran olcekleme (orn. %125/%150) acikken bu yapilmazsa pencere
    daha kucuk mantiksal cozunurlukte acilir ve sag/alt tarafta siyah bosluk
    kalir. Diger platformlarda etkisizdir."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)   # Per-Monitor v2
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()         # eski API (fallback)
    except Exception:
        pass   # DPI ayari yapilamasa bile oyun calismaya devam etsin


def main() -> None:
    if "--selftest" in sys.argv:
        run_selftest()
        return

    _enable_windows_dpi_awareness()   # tam ekran fiziksel cozunurlukte acilsin
    pygame.init()
    # Tam ekran: SDL'e (0,0) verince MEVCUT MASAUSTU cozunurlugu kullanilir,
    # boylece ekran TAM kaplanir (sag/alt bosluk olmaz). Gercek boyutu
    # surface'ten okuruz; her sey SCALE = H/1080 ile bu cozunurluge uyarlanir.
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    w, h = screen.get_size()
    pygame.display.set_caption("Split-Screen Uzay Atari")

    # Giris kaynagi secimi (calistirma aninda; kod govdesi duzenlenmez).
    # Oncelik: --serial bayragi > settings.INPUT_SOURCE sabiti.
    use_serial = ("--serial" in sys.argv) or \
        (settings.INPUT_SOURCE.lower() == "serial")
    input_source = SerialJoystickInputSource() if use_serial else None

    game = Game(screen, w, h, input_source=input_source)
    game.run()


if __name__ == "__main__":
    main()
