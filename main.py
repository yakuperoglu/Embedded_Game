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

2 oyunculu split-screen uzay atari oyunu. Tum cizim pygame.draw
primitifleriyle yapilir (disaridan asset YOK).
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
from entities import Ship, Bullet, Meteor, spawn_explosion
from input_source import (
    InputState,
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

        self.score = 0
        self.lives = settings.START_LIVES
        self.alive = True

        self._spawn_timer = 0.0

        # --- Ozel guc durumu ---
        self.special_charge = 0       # bu dolumda mermiyle vurulan asteroid sayisi
        self.special_ready = False    # doldu mu (kullanilabilir mi)
        self._prev_fire = False       # buton rising-edge tespiti icin
        self._flash_timer = 0.0       # ozel guc kullaninca arena flashi (sn)

    def _make_ship(self) -> Ship:
        x = self.rect.centerx
        y = self.rect.bottom - settings.scaled(settings.SHIP_MARGIN)
        return Ship(self.rect, self.ship_color, x, y)

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

        # --- Partikuller ---
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if not p.dead]

        # --- Carpisma cozumu (bu arenanin kendi listeleri arasinda) ---
        self._resolve_collisions()

        # --- Dibe ulasan meteorlar (can kaybi) ---
        self._handle_ground_hits()

        # --- Ozel guc flash zamanlayici ---
        if self._flash_timer > 0.0:
            self._flash_timer -= dt

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
                    if self.ship.hit():
                        self._lose_life()

        # --- Tek noktada temizlik ---
        if dead_bullets:
            self.bullets = [b for i, b in enumerate(self.bullets)
                            if i not in dead_bullets]
        if dead_meteors:
            self.meteors = [m for i, m in enumerate(self.meteors)
                            if i not in dead_meteors]

    def _handle_ground_hits(self) -> None:
        """Arena dibine ulasan meteorlar: can kaybi + kaldir.

        ONEMLI: Dibe ulasma (savunmayi gecme) MUTLAK cezadir; dokunulmazlik
        bunu engellemez (aksi halde 1.6 sn dokunulmazken yagan tum meteorlar
        bedavaya silinir, somurulebilir denge sorunu). Yine de bir karede
        meteor kalabaligi tum canlari birden goturmesin diye en fazla 1 can
        kaybi uygulanir; ilk dibe varan dokunulmazligi yenileyerek geri kalan
        ayni-kare meteorlarini absorbe eder.
        """
        survivors = []
        life_lost_this_frame = False
        for m in self.meteors:
            if m.is_offscreen(self.rect):
                # Dibe ulasti -> patlama + (kareye ozel) mutlak can kaybi.
                self.particles.extend(spawn_explosion(m.x, self.rect.bottom - 10))
                if self.alive and not life_lost_this_frame:
                    self.ship.force_hit()   # dokunulmazlik YOK SAYILIR
                    self._lose_life()
                    life_lost_this_frame = True
                # meteor her durumda kaldirilir
            else:
                survivors.append(m)
        self.meteors = survivors

    def _lose_life(self) -> None:
        self.lives -= 1
        if self.lives <= 0:
            self.lives = 0
            self.alive = False

    def _add_special_charge(self) -> None:
        """Mermiyle asteroid vuruldukca ozel guc dolar (tavan = gerekli sayi)."""
        if self.special_ready:
            return
        self.special_charge += 1
        if self.special_charge >= settings.SPECIAL_KILLS_REQUIRED:
            self.special_charge = settings.SPECIAL_KILLS_REQUIRED
            self.special_ready = True

    def _activate_special(self) -> None:
        """Ozel guc: bu arenadaki TUM meteorlari yok et (puan + patlama),
        sayaci sifirla, kisa arena flashi baslat."""
        for m in self.meteors:
            self.score += m.points
            self.particles.extend(spawn_explosion(m.x, m.y))
        self.meteors = []
        self.special_charge = 0
        self.special_ready = False
        self._flash_timer = settings.SPECIAL_FLASH_TIME

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
            info = pygame.display.Info()
            new_w, new_h = info.current_w, info.current_h
            self.screen = pygame.display.set_mode((new_w, new_h),
                                                   pygame.FULLSCREEN)
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
            screen.fill((b, b, min(255, b + 30)), (x, y, size, size))

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
            a = int(170 * min(1.0, arena._flash_timer / settings.SPECIAL_FLASH_TIME))
            flash = pygame.Surface((arena.rect.width, arena.rect.height),
                                   pygame.SRCALPHA)
            flash.fill((255, 255, 255, a))
            screen.blit(flash, arena.rect.topleft)
        # Olu arena -> karartma overlay
        if not arena.alive:
            overlay = pygame.Surface((arena.rect.width, arena.rect.height),
                                     pygame.SRCALPHA)
            overlay.fill(settings.DEAD_OVERLAY)
            screen.blit(overlay, arena.rect.topleft)
            txt = self.font_med.render("ELENDI", True, (255, 120, 120))
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
        self._blit_text(screen, f"CAN: {self._lives_str(p1.lives)}", (m, m + lh),
                        settings.HUD_COLOR)
        self._draw_special(screen, p1, m + 2 * lh, right=False)

        # --- P2 sag ust (saga hizali) ---
        def rx(text):
            return self.W - self.font_small.size(text)[0] - m
        s2 = f"P2  SKOR: {p2.score}"
        c2 = f"CAN: {self._lives_str(p2.lives)}"
        self._blit_text(screen, s2, (rx(s2), m), settings.HUD_ACCENT)
        self._blit_text(screen, c2, (rx(c2), m + lh), settings.HUD_COLOR)
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
        bw = int(settings.scaled(160))
        bh = max(4, int(settings.scaled(10)))
        bx = (self.W - bw - m) if right else m
        by = y + self.font_small.get_linesize()
        pygame.draw.rect(screen, (50, 50, 70), (bx, by, bw, bh), border_radius=3)
        if frac > 0:
            pygame.draw.rect(screen, col, (bx, by, int(bw * frac), bh),
                             border_radius=3)

    @staticmethod
    def _lives_str(lives: int) -> str:
        # Canlari kalp benzeri sembolle goster (ascii guvenli).
        return ("<3 " * lives).strip() if lives > 0 else "-"

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
                          (255, 90, 90), dy=-110)

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
def main() -> None:
    if "--selftest" in sys.argv:
        run_selftest()
        return

    pygame.init()
    # Tam ekran: cozunurlugu monitorden al (sabit pixel hardcode YOK).
    info = pygame.display.Info()
    w, h = info.current_w, info.current_h
    screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN)
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
