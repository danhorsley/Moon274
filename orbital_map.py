import pygame
import math
import random

# Colors
BG         = (0, 0, 0)
SATURN     = (180, 160, 100)
RING_COLOR = (120, 110, 70, 80)
MOON_DOT   = (0, 100, 0)
MOON_HOVER = (0, 220, 0)
PLAYER_MOON = (0, 255, 100)
RIVAL_BLIP = (255, 80, 80)
TOURIST_BLIP = (100, 160, 255)
ROUTE_LINE = (0, 220, 220, 120)
ROUTE_DRAG = (255, 200, 0)
DIM        = (0, 60, 0)
WHITE      = (200, 200, 200)

NUM_VISIBLE_MOONS = 40  # We show a subset of 274 moons for readability


class MoonPos:
    """Precomputed position for a moon on the orbital map."""
    def __init__(self, moon_id, x, y, orbit_ring):
        self.id = moon_id
        self.x = x
        self.y = y
        self.ring = orbit_ring


class OrbitalMap:
    def __init__(self, rect, font):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.cx = self.rect.x + self.rect.width // 2
        self.cy = self.rect.y + self.rect.height // 2
        self.moons = {}  # moon_id -> MoonPos
        self.hovered_moon = None
        self.tooltip = None
        self.drag_start = None   # moon_id
        self.drag_end = None     # moon_id
        self.drag_mouse = None   # (x,y) current mouse pos during drag
        self._generate_positions()

    def _generate_positions(self):
        """Place moons in orbital rings around Saturn."""
        rng = random.Random(274)  # deterministic layout
        # 5 orbital rings
        radii = [60, 95, 130, 165, 200]
        moons_per_ring = [6, 8, 10, 8, 8]

        # Always include key moons: 274 (player), plus some named ones
        key_moons = [274, 42, 188, 7, 1, 50, 100, 150, 200, 250]

        moon_ids = list(key_moons)
        # Fill rest randomly
        all_ids = set(range(1, 275))
        all_ids -= set(key_moons)
        remaining = rng.sample(sorted(all_ids), NUM_VISIBLE_MOONS - len(key_moons))
        moon_ids.extend(remaining)
        moon_ids.sort()

        idx = 0
        for ring_i, (radius, count) in enumerate(zip(radii, moons_per_ring)):
            for j in range(count):
                if idx >= len(moon_ids):
                    break
                angle = (2 * math.pi * j / count) + ring_i * 0.3
                # Add slight jitter
                angle += rng.uniform(-0.1, 0.1)
                x = self.cx + int(radius * math.cos(angle))
                y = self.cy + int(radius * math.sin(angle))
                mid = moon_ids[idx]
                self.moons[mid] = MoonPos(mid, x, y, ring_i)
                idx += 1

    def get_moon_pos(self, moon_id):
        """Get (x,y) for a moon, or approximate for unlisted moons."""
        if moon_id in self.moons:
            m = self.moons[moon_id]
            return (m.x, m.y)
        # For moons not on the visible map, place them on the outer edge
        angle = (moon_id / 274.0) * 2 * math.pi
        r = 210
        return (self.cx + int(r * math.cos(angle)),
                self.cy + int(r * math.sin(angle)))

    def _moon_at_pos(self, mx, my):
        """Find moon under mouse position (within 8px)."""
        best = None
        best_dist = 64  # 8px squared threshold
        for mid, m in self.moons.items():
            dx = mx - m.x
            dy = my - m.y
            d2 = dx * dx + dy * dy
            if d2 < best_dist:
                best_dist = d2
                best = mid
        return best

    def handle_event(self, event, game_state):
        """Handle mouse events. Returns clicked moon_id or None."""
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hovered_moon = self._moon_at_pos(mx, my)
            if self.drag_start is not None:
                self.drag_mouse = (mx, my)
                self.drag_end = self._moon_at_pos(mx, my)
            self._build_tooltip(game_state)
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            moon = self._moon_at_pos(mx, my)
            if moon is not None:
                self.drag_start = moon
                self.drag_mouse = (mx, my)
                return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            result = None
            if self.drag_start is not None and self.drag_end is not None:
                if self.drag_start != self.drag_end:
                    result = ("route", self.drag_start, self.drag_end)
                else:
                    result = ("click", self.drag_start)
            elif self.drag_start is not None:
                result = ("click", self.drag_start)
            self.drag_start = None
            self.drag_end = None
            self.drag_mouse = None
            return result

        return None

    def _build_tooltip(self, game_state):
        """Build tooltip text for hovered moon."""
        if self.hovered_moon is None:
            self.tooltip = None
            return

        mid = self.hovered_moon
        lines = [f"Moon {mid}"]

        if mid == 274:
            lines.append(">> YOUR MOON <<")

        # Check if any rivals are here
        for r_name, r_pos in game_state.get("rival_positions", []):
            if r_pos == mid:
                lines.append(f"Rival: {r_name}")

        # Check tourists
        for t_name, t_pos in game_state.get("tourist_positions", []):
            if t_pos == mid:
                lines.append(f"Tourist: {t_name}")

        self.tooltip = lines

    def draw(self, surface, game_state):
        """Draw the orbital map."""
        # Border
        pygame.draw.rect(surface, DIM, self.rect, 1)

        # Saturn (center blob with ring)
        pygame.draw.circle(surface, SATURN, (self.cx, self.cy), 18)
        pygame.draw.ellipse(surface, (120, 110, 70), (self.cx - 30, self.cy - 6, 60, 12), 1)

        # Orbital ring guides
        for r in [60, 95, 130, 165, 200]:
            pygame.draw.circle(surface, (0, 30, 0), (self.cx, self.cy), r, 1)

        # Tourist routes (faint lines)
        t_positions = game_state.get("tourist_routes", [])
        for route in t_positions:
            pts = [self.get_moon_pos(m) for m in route]
            if len(pts) > 1:
                pygame.draw.lines(surface, (30, 60, 80), False, pts, 1)

        # Moon dots
        for mid, m in self.moons.items():
            if mid == 274:
                pygame.draw.circle(surface, PLAYER_MOON, (m.x, m.y), 5)
                pygame.draw.circle(surface, (0, 255, 100), (m.x, m.y), 7, 1)
            elif mid == self.hovered_moon:
                pygame.draw.circle(surface, MOON_HOVER, (m.x, m.y), 4)
            else:
                pygame.draw.circle(surface, MOON_DOT, (m.x, m.y), 3)

        # Rival blips
        for r_name, r_pos in game_state.get("rival_positions", []):
            rx, ry = self.get_moon_pos(r_pos)
            pygame.draw.circle(surface, RIVAL_BLIP, (rx, ry), 5, 2)

        # Tourist blips
        for t_name, t_pos in game_state.get("tourist_positions", []):
            tx, ty = self.get_moon_pos(t_pos)
            pygame.draw.polygon(surface, TOURIST_BLIP,
                                [(tx, ty - 5), (tx - 4, ty + 3), (tx + 4, ty + 3)])

        # Drag route preview
        if self.drag_start is not None and self.drag_mouse is not None:
            start_pos = self.get_moon_pos(self.drag_start)
            pygame.draw.line(surface, ROUTE_DRAG, start_pos, self.drag_mouse, 2)
            if self.drag_end is not None and self.drag_end != self.drag_start:
                end_pos = self.get_moon_pos(self.drag_end)
                pygame.draw.circle(surface, ROUTE_DRAG, end_pos, 6, 2)

        # Tooltip
        if self.tooltip and self.hovered_moon is not None:
            m = self.moons.get(self.hovered_moon)
            if m:
                tx, ty = m.x + 10, m.y - 10
                for i, line in enumerate(self.tooltip):
                    bg_surf = self.font.render(line, True, WHITE)
                    # Dark background for readability
                    bg_rect = bg_surf.get_rect(topleft=(tx, ty + i * 13))
                    bg_rect.inflate_ip(4, 2)
                    pygame.draw.rect(surface, (0, 0, 0), bg_rect)
                    pygame.draw.rect(surface, DIM, bg_rect, 1)
                    surface.blit(bg_surf, (tx, ty + i * 13))

        # Map label
        surface.blit(self.font.render("SATURN ORBITAL MAP", True, (0, 120, 0)),
                     (self.rect.x + 4, self.rect.y + 2))
