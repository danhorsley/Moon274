import pygame
import random
from lattice import TAGS

# Colors
BG        = (0, 0, 0)
GREEN     = (0, 200, 0)
DIM_GREEN = (0, 120, 0)
DARK_GREEN = (0, 60, 0)
HIGHLIGHT = (255, 200, 0)
WARN_RED  = (255, 80, 80)
COOL_BLUE = (100, 160, 255)
WHITE     = (200, 200, 200)
CYAN      = (0, 220, 220)

# Tag family colors (match archetype colors on map)
FAMILY_COLORS = {
    "commerce": (0, 220, 220),    # cyan — matches hub
    "warfare":  (255, 80, 80),    # red — matches military
    "science":  (220, 220, 0),    # yellow — matches compute
}

# ── Command definitions ─────────────────────────────────────────────
# Each: (description, eq_action, lattice_tags_injected)
COMMANDS = {
    "TRADE":      ("Open trade channel with nearest rival",        "trade",      []),
    "HEIST":      ("Raid a rival moon for resources",              "heist",      []),
    "PROTECT":    ("Fortify Moon 274 defenses",                    "protect",    []),
    "TRADE_IDEA": ("Exchange research with visiting Tourist",      "trade_idea", []),
    "EAVESDROP":  ("Tap rival comms for intel",                    "eavesdrop",  ["cyber"]),
    "SABOTAGE":   ("Sabotage rival infrastructure",                "sabotage",   ["cyber", "nano"]),
    "DIPLOMACY":  ("Send diplomatic envoy to rival",               "diplomacy",  []),
    "SMUGGLE":    ("Smuggle contraband for profit",                "smuggle",    ["carbon"]),
    "RESEARCH":   ("Direct research at a tech field (eg RESEARCH QUANTUM)", "research", []),
    "BROADCAST":  ("Broadcast cultural signal across moons",       "broadcast",  ["optics"]),
    "BUILD":      ("Build infrastructure (DRONES/CLUSTERS/LEISURE)",  "build",     []),
}

SIMULATE_RUNS = 50  # Monte Carlo preview count


def parse_command(raw):
    """Parse a raw input string into (command, args) or (None, error_msg)."""
    parts = raw.strip().upper().split()
    if not parts:
        return None, ""

    cmd = parts[0]

    # SIMULATE <ACTION> [MOON-N] or SIMULATE ALL
    if cmd == "SIMULATE" and len(parts) >= 2:
        action = parts[1]
        if action == "ALL":
            return ("SIMULATE_ALL", None), ""
        target = parts[2] if len(parts) > 2 else None
        if action in COMMANDS:
            return ("SIMULATE", (action, target)), ""
        return None, f"Unknown action to simulate: {action}"

    if cmd in COMMANDS:
        # For RESEARCH, the arg is a tech tag (lowercase), not a rival name
        if cmd == "RESEARCH":
            tag = parts[1].lower() if len(parts) > 1 else None
            return (cmd, tag), ""
        # For BUILD, the arg is an upgrade type (lowercase)
        if cmd == "BUILD":
            upgrade = parts[1].lower() if len(parts) > 1 else None
            return (cmd, upgrade), ""
        target = parts[1] if len(parts) > 1 else None
        return (cmd, target), ""

    # HELP / STATUS / RESPOND / BOUNTIES
    if cmd == "HELP":
        return ("HELP", None), ""
    if cmd == "STATUS":
        # STATUS <target> — pass remaining text as target
        target = " ".join(parts[1:]) if len(parts) > 1 else None
        return ("STATUS", target), ""
    if cmd == "RESPOND":
        arg = parts[1] if len(parts) > 1 else None
        return ("RESPOND", arg), ""
    if cmd == "BOUNTIES":
        return ("BOUNTIES", None), ""

    return None, f"Unknown command: {cmd}"


def run_simulate_all(lattice, market, equilibrium, rivals, player=None, tourists=None):
    """Compact Monte Carlo summary of ALL actions. Returns list of lines."""
    from equilibrium import ACTION_IMPACTS
    from player import ACTION_ABILITIES, BASE_DIFFICULTY
    from lattice import TAG_FAMILIES

    lines = [f"SIMULATE ALL ({SIMULATE_RUNS} runs each):"]
    lines.append(f"  {'ACTION':<13} {'SUCCESS':>7}  {'CRIT':>5}  {'EQ':>6}  NOTES")
    lines.append(f"  {'─' * 55}")

    # Synergy bonus (same for all actions, computed once per source)
    synergy_cache = {}
    if tourists:
        for cmd_name in COMMANDS:
            eq_act = COMMANDS[cmd_name][1]
            synergy_cache[eq_act] = tourists.get_synergy_bonus(eq_act)

    results = []
    for cmd_name, (desc, eq_action, chaos_tags) in COMMANDS.items():
        if eq_action == "build":
            continue  # BUILD isn't simulatable

        delta = ACTION_IMPACTS.get(eq_action, 0.0)
        primary, secondary = ACTION_ABILITIES.get(eq_action, ("influence", "extraction"))
        base_diff = BASE_DIFFICULTY.get(eq_action, 0.30)
        syn = synergy_cache.get(eq_action, 0.0)

        successes = 0
        crit_fails = 0
        for _ in range(SIMULATE_RUNS):
            if player:
                ability_bonus = player.abilities[primary] * 0.12 + player.abilities[secondary] * 0.06
                eff_diff = max(0.05, base_diff - ability_bonus - syn
                              + (player.notoriety * 0.15
                                 if eq_action in ("heist", "eavesdrop", "sabotage", "smuggle")
                                 else 0))
            else:
                eff_diff = base_diff
            roll = random.random()
            if roll > eff_diff:
                successes += 1
            elif roll < eff_diff * 0.10:
                crit_fails += 1

        success_pct = (successes / SIMULATE_RUNS) * 100
        crit_pct = (crit_fails / SIMULATE_RUNS) * 100

        notes = []
        if syn > 0:
            notes.append(f"syn-{syn:.0%}")
        if eq_action in ("heist", "eavesdrop", "sabotage", "smuggle") and player and player.notoriety > 0.1:
            notes.append(f"noto")
        notes_str = " ".join(notes)

        results.append((cmd_name, success_pct, crit_pct, delta, notes_str))

    # Sort by success rate descending
    results.sort(key=lambda x: x[1], reverse=True)

    for cmd_name, spct, cpct, delta, notes_str in results:
        bar = "█" * int(spct / 10) + "·" * (10 - int(spct / 10))
        lines.append(f"  {cmd_name:<13} {spct:5.0f}%  {cpct:4.0f}%  {delta:+5.2f}  {bar} {notes_str}")

    lines.append(f"  {'─' * 55}")
    lines.append(f"  Sorted by success rate. SIMULATE <ACTION> for details.")
    return lines


def run_simulate(action, lattice, market, equilibrium, rivals, player=None, tag=None,
                  tourists=None):
    """Run N Monte Carlo previews of an action, return summary string."""
    from equilibrium import ACTION_IMPACTS
    from player import ACTION_ABILITIES, BASE_DIFFICULTY
    delta = ACTION_IMPACTS.get(COMMANDS[action][1], 0.0)
    tags = COMMANDS[action][2]
    eq_action = COMMANDS[action][1]

    # Calculate synergy bonus from tourists/residents
    synergy_bonus = 0.0
    synergy_sources = []
    if tourists:
        synergy_bonus = tourists.get_synergy_bonus(eq_action)
        synergy_sources = tourists.get_synergy_sources(eq_action)

    # Calculate success rate via Monte Carlo
    successes = 0
    crit_fails = 0
    total_eq_shift = 0.0

    primary, secondary = ACTION_ABILITIES.get(eq_action, ("influence", "extraction"))
    base_diff = BASE_DIFFICULTY.get(eq_action, 0.30)

    for _ in range(SIMULATE_RUNS):
        if player:
            ability_bonus = player.abilities[primary] * 0.12 + player.abilities[secondary] * 0.06
            eff_diff = max(0.05, base_diff - ability_bonus - synergy_bonus
                          + (player.notoriety * 0.15
                             if eq_action in ("heist", "eavesdrop", "sabotage", "smuggle")
                             else 0))
        else:
            eff_diff = base_diff

        roll = random.random()
        if roll > eff_diff:
            successes += 1
        elif roll < eff_diff * 0.10:
            crit_fails += 1
        total_eq_shift += delta

    success_pct = (successes / SIMULATE_RUNS) * 100
    crit_pct = (crit_fails / SIMULATE_RUNS) * 100

    lines = [
        f"SIMULATE {action} ({SIMULATE_RUNS} runs):",
        f"  Success rate: {success_pct:.0f}%  |  Crit fail: {crit_pct:.0f}%",
        f"  Eq shift: {delta:+.2f} per action",
    ]

    # Ability factors
    if player:
        lines.append(f"  Using: {primary}={player.abilities[primary]:.2f} "
                     f"+ {secondary}={player.abilities[secondary]:.2f}")
        if eq_action in ("heist", "eavesdrop", "sabotage", "smuggle"):
            lines.append(f"  Notoriety penalty: +{player.notoriety * 0.15:.2f} difficulty")

    # Synergy factors
    if synergy_sources:
        for name, bonus in synergy_sources:
            lines.append(f"  Synergy: {name} (-{bonus:.0%} difficulty)")
    elif tourists:
        lines.append(f"  No synergy active for this action")

    # Factor breakdown
    if tags:
        tag_weights = lattice.get_tags()
        for t in tags:
            w = tag_weights.get(t, 0)
            lines.append(f"  Lattice '{t}': weight={w:.0f}" +
                         (" (GOLDEN AGE active)" if t in lattice.golden_ages else ""))

    # Rival factor
    if action in ("HEIST", "SABOTAGE", "EAVESDROP"):
        avg_aggro = sum(r.aggressive for r in rivals.rivals) / len(rivals.rivals)
        lines.append(f"  Rival avg aggression: {avg_aggro:.2f} (retaliation risk)")

    # Research tag info
    if action == "RESEARCH" and tag:
        from lattice import TAG_FAMILIES, FAMILY_NAMES
        fam = TAG_FAMILIES.get(tag, "science")
        fam_label = FAMILY_NAMES.get(fam, "Science")
        archetype_map = {"commerce": "Hub", "warfare": "Military", "science": "Compute"}
        status = lattice.get_tag_status(tag)
        if status:
            lines.append(f"  --- '{tag}' ({fam_label} / {archetype_map[fam]} synergy) ---")
            lines.append(f"  Nodes: {status['node_count']}  |  Avg maturity: {status['avg_maturity']:.0f}%")
            lines.append(f"  Lead node: {status['closest_name']} ({status['closest_maturity']:.0f}%)")
            if status["closest_flagged_name"]:
                gap = 70 - status["closest_flagged_maturity"]
                if gap > 0:
                    lines.append(f"  Golden Age via: {status['closest_flagged_name']} "
                                 f"({status['closest_flagged_maturity']:.0f}%) — {gap:.0f}% to go")
                else:
                    lines.append(f"  Golden Age: ALREADY TRIGGERED by {status['closest_flagged_name']}")
            else:
                lines.append(f"  No flagged nodes — Golden Age not possible via this tag alone")
            if status["golden_age_active"]:
                lines.append(f"  GOLDEN AGE ACTIVE: {status['golden_age_remaining']}t remaining")
        else:
            lines.append(f"  Unknown tag: '{tag}'")
    elif action == "RESEARCH" and not tag:
        from lattice import get_tags_by_family
        lines.append(f"  Tip: RESEARCH <TAG> to target a field (e.g. RESEARCH QUANTUM)")
        families = get_tags_by_family()
        for fam, label in [("commerce", "Commerce [H]"), ("warfare", "Warfare [M]"), ("science", "Science [C]")]:
            tags_str = ", ".join(t.upper() for t in families[fam])
            lines.append(f"    {label}: {tags_str}")

    return lines


# ── UI Panel Classes ────────────────────────────────────────────────

class TerminalLog:
    """Scrollable text log on the left side."""
    def __init__(self, rect, font):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.lines = []       # (text, color)
        self.scroll = 0       # lines scrolled up from bottom
        self.line_h = 14

    def add(self, text, color=GREEN):
        self.lines.append((text, color))
        if len(self.lines) > 500:
            del self.lines[:200]
        self.scroll = 0  # snap to bottom on new content

    def scroll_up(self):
        max_scroll = max(0, len(self.lines) - self.visible_count())
        self.scroll = min(self.scroll + 3, max_scroll)

    def scroll_down(self):
        self.scroll = max(0, self.scroll - 3)

    def visible_count(self):
        return (self.rect.height - 20) // self.line_h

    def draw(self, surface):
        pygame.draw.rect(surface, DARK_GREEN, self.rect, 1)
        self.font_big = self.font  # reuse
        clip = surface.subsurface(self.rect)
        clip.fill(BG)

        visible = self.visible_count()
        end = len(self.lines) - self.scroll
        start = max(0, end - visible)
        y = 4
        for text, color in self.lines[start:end]:
            clip.blit(self.font.render(text, True, color), (4, y))
            y += self.line_h

        # Scroll indicator
        if self.scroll > 0:
            clip.blit(self.font.render(f"  [{self.scroll} more below]", True, DIM_GREEN),
                      (4, self.rect.height - 14))


class MarketTicker:
    """Right panel: scrolling price ticker."""
    def __init__(self, rect, font):
        self.rect = pygame.Rect(rect)
        self.font = font

    def draw(self, surface, market):
        pygame.draw.rect(surface, DARK_GREEN, self.rect, 1)
        clip = surface.subsurface(self.rect)
        clip.fill(BG)

        clip.blit(self.font.render("MARKET TICKER", True, GREEN), (4, 2))
        y = 18
        for g in market.goods:
            delta = ((g["price"] - g["base"]) / g["base"]) * 100
            if delta > 10:
                color = WARN_RED
            elif delta < -10:
                color = COOL_BLUE
            else:
                color = GREEN
            line = f"{g['name']:<14} {g['price']:>7.0f} ({delta:+.0f}%)"
            clip.blit(self.font.render(line, True, color), (4, y))
            y += 14


class EquilibriumBar:
    """Visual equilibrium meter."""
    def __init__(self, rect, font):
        self.rect = pygame.Rect(rect)
        self.font = font

    def draw(self, surface, eq):
        pygame.draw.rect(surface, DARK_GREEN, self.rect, 1)
        clip = surface.subsurface(self.rect)
        clip.fill(BG)

        clip.blit(self.font.render(f"EQUILIBRIUM: {eq.value:+.3f}", True, GREEN), (4, 2))

        # Bar
        bar_x, bar_y = 4, 20
        bar_w = self.rect.width - 8
        bar_h = 16
        pygame.draw.rect(clip, DIM_GREEN, (bar_x, bar_y, bar_w, bar_h), 1)

        mid = bar_x + bar_w // 2
        fill_w = int(eq.value * (bar_w // 2))

        # Danger zone markers at ±0.7
        mark_70 = int(0.7 * (bar_w // 2))
        pygame.draw.line(clip, WARN_RED, (mid - mark_70, bar_y), (mid - mark_70, bar_y + bar_h))
        pygame.draw.line(clip, WARN_RED, (mid + mark_70, bar_y), (mid + mark_70, bar_y + bar_h))

        if fill_w > 0:
            color = HIGHLIGHT if eq.value < 0.7 else WARN_RED
            pygame.draw.rect(clip, color, (mid, bar_y + 1, fill_w, bar_h - 2))
        elif fill_w < 0:
            color = COOL_BLUE if eq.value > -0.7 else WARN_RED
            pygame.draw.rect(clip, color, (mid + fill_w, bar_y + 1, -fill_w, bar_h - 2))

        # Center tick
        pygame.draw.line(clip, WHITE, (mid, bar_y), (mid, bar_y + bar_h))

        # Status text
        status = ""
        if abs(eq.value) >= 0.7:
            status = "!! DANGER ZONE !!"
        elif abs(eq.value) >= 0.5:
            status = "~ Unstable ~"
        clip.blit(self.font.render(status, True, WARN_RED if status.startswith("!") else HIGHLIGHT),
                  (4, bar_y + bar_h + 4))


class MessagePanel:
    """Right panel: comms/bounties + rival/tourist status + golden ages."""
    def __init__(self, rect, font):
        self.rect = pygame.Rect(rect)
        self.font = font

    def draw(self, surface, rivals, tourists, lattice, comms=None):
        pygame.draw.rect(surface, DARK_GREEN, self.rect, 1)
        clip = surface.subsurface(self.rect)
        clip.fill(BG)
        y = 2

        # Active proposals (urgent — show first)
        if comms:
            active_props = comms.get_active_proposals()
            active_bounties = comms.get_active_bounties()
            if active_props or active_bounties:
                clip.blit(self.font.render("COMMS", True, HIGHLIGHT), (4, y))
                y += 14
                for p in active_props:
                    timer_color = WARN_RED if p.timer <= 2 else HIGHLIGHT
                    clip.blit(self.font.render(
                        f" [{p.timer}t] {p.text[:32]}", True, timer_color), (4, y))
                    y += 13
                for b in active_bounties:
                    timer_color = WARN_RED if b.timer <= 3 else HIGHLIGHT
                    clip.blit(self.font.render(
                        f" B[{b.timer}t] ${b.reward} {b.action_required[:6]}", True, timer_color), (4, y))
                    y += 13
                y += 2

        # Golden Ages
        clip.blit(self.font.render("GOLDEN AGES", True, HIGHLIGHT), (4, y))
        y += 14
        if lattice.golden_ages:
            for tag, turns in lattice.golden_ages.items():
                clip.blit(self.font.render(f"  {tag:<10} {turns}t left", True, HIGHLIGHT), (4, y))
                y += 13
        else:
            clip.blit(self.font.render("  (none)", True, DIM_GREEN), (4, y))
            y += 13

        # Rivals (compact)
        y += 2
        clip.blit(self.font.render("RIVALS", True, WARN_RED), (4, y))
        y += 14
        for name, action, rep in rivals.get_status():
            clip.blit(self.font.render(f"  {name[:14]:<14} {action:<7}", True, GREEN), (4, y))
            y += 13

        # Tourists (compact)
        y += 2
        clip.blit(self.font.render("TOURISTS", True, COOL_BLUE), (4, y))
        y += 14
        for name, pos, pers in tourists.get_status():
            here = "*" if pos == 274 else " "
            clip.blit(self.font.render(f" {here}{name[:13]:<13} M{pos:<3}", True,
                                       CYAN if pos == 274 else GREEN), (4, y))
            y += 13


class CommandInput:
    """Text input bar at the bottom."""
    def __init__(self, rect, font):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.text = ""
        self.cursor_visible = True
        self.cursor_timer = 0

    def handle_key(self, event):
        """Process a KEYDOWN event. Returns completed command string or None."""
        if event.key == pygame.K_RETURN:
            cmd = self.text
            self.text = ""
            return cmd
        elif event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        elif event.key == pygame.K_TAB:
            # Tab completion
            partial = self.text.strip().upper()
            matches = [c for c in list(COMMANDS) + ["SIMULATE", "HELP"] if c.startswith(partial)]
            if len(matches) == 1:
                self.text = matches[0] + " "
        elif event.unicode and event.unicode.isprintable():
            self.text += event.unicode
        return None

    def draw(self, surface):
        pygame.draw.rect(surface, DARK_GREEN, self.rect, 1)
        clip = surface.subsurface(self.rect)
        clip.fill((0, 10, 0))

        self.cursor_timer += 1
        cursor = "_" if (self.cursor_timer // 5) % 2 == 0 else " "
        prompt = f"> {self.text}{cursor}"
        clip.blit(self.font.render(prompt, True, GREEN), (4, 4))

        # Hint
        hint = "Type command (HELP for list) | TAB to complete | ENTER to run"
        clip.blit(self.font.render(hint, True, DIM_GREEN), (4, 20))


class SpeedControl:
    """Cassette-style playback controls: pause, step, 1x, 3x, 10x."""

    SPEEDS = [
        ("||",  "PAUSED", 0),       # paused
        ("|>",  "STEP",   0),       # advance one tick then pause
        (">",   "1x",     600),     # normal
        (">>",  "3x",     200),     # fast
        (">>>", "10x",    60),      # very fast
    ]

    def __init__(self, rect, font):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.mode = 0  # start paused
        self.step_pending = False
        self.btn_rects = []  # computed in draw
        self._build_btn_rects()

    def _build_btn_rects(self):
        bw = 44
        gap = 4
        x = self.rect.x + 4
        y = self.rect.y + 18
        self.btn_rects = []
        for i in range(len(self.SPEEDS)):
            self.btn_rects.append(pygame.Rect(x, y, bw, 18))
            x += bw + gap

    @property
    def tick_interval(self):
        return self.SPEEDS[self.mode][2]

    @property
    def is_paused(self):
        return self.mode == 0

    @property
    def label(self):
        return self.SPEEDS[self.mode][1]

    def set_mode(self, mode):
        self.mode = max(0, min(len(self.SPEEDS) - 1, mode))
        self.step_pending = False

    def request_step(self):
        """Advance exactly one tick, then return to paused."""
        self.mode = 1
        self.step_pending = True

    def after_step(self):
        """Called after a step-tick completes."""
        if self.step_pending:
            self.mode = 0
            self.step_pending = False

    def should_tick(self, elapsed_ms):
        """Return True if enough time has passed for a tick at current speed."""
        if self.mode == 0:
            return False
        if self.mode == 1:  # step mode: tick once
            return True
        return elapsed_ms >= self.tick_interval

    def handle_key(self, key):
        """Handle speed-related keys. Returns True if consumed."""
        if key == pygame.K_SPACE:
            if self.is_paused:
                self.set_mode(2)  # unpause to 1x
            else:
                self.set_mode(0)  # pause
            return True
        if key == pygame.K_PERIOD:  # '.' = step one tick
            self.request_step()
            return True
        if key == pygame.K_1:
            self.set_mode(2)
            return True
        if key == pygame.K_2:
            self.set_mode(3)
            return True
        if key == pygame.K_3:
            self.set_mode(4)
            return True
        return False

    def handle_click(self, pos):
        """Handle mouse click on speed buttons. Returns True if consumed."""
        for i, r in enumerate(self.btn_rects):
            if r.collidepoint(pos):
                if i == 1:  # step button
                    self.request_step()
                else:
                    self.set_mode(i)
                return True
        return False

    def draw(self, surface):
        pygame.draw.rect(surface, DARK_GREEN, self.rect, 1)

        # Title
        surface.blit(self.font.render("SPEED", True, GREEN),
                     (self.rect.x + 4, self.rect.y + 2))

        # Buttons
        for i, (sym, label, _) in enumerate(self.SPEEDS):
            r = self.btn_rects[i]
            active = (i == self.mode)
            bg = (0, 80, 0) if active else (0, 20, 0)
            border = HIGHLIGHT if active else DIM_GREEN
            pygame.draw.rect(surface, bg, r)
            pygame.draw.rect(surface, border, r, 1)
            color = HIGHLIGHT if active else GREEN
            surface.blit(self.font.render(sym, True, color),
                         (r.x + 4, r.y + 2))

        # Status label + keybinds
        status_x = self.rect.x + 4
        status_y = self.rect.y + 40
        surface.blit(self.font.render(
            f"[SPACE] pause/play  [.] step  [1] 1x  [2] 3x  [3] 10x",
            True, DIM_GREEN), (status_x, status_y))


class GameOverScreen:
    """Full-screen game over overlay."""
    def __init__(self, font, font_big):
        self.font = font
        self.font_big = font_big

    def draw(self, surface, msg):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))

        lines = [
            "G A M E   O V E R",
            "",
            msg,
            "",
            "Press ESC to exit or R to restart",
        ]
        y = surface.get_height() // 2 - 60
        for i, line in enumerate(lines):
            f = self.font_big if i == 0 else self.font
            color = WARN_RED if i == 0 else GREEN
            rendered = f.render(line, True, color)
            x = (surface.get_width() - rendered.get_width()) // 2
            surface.blit(rendered, (x, y))
            y += 24
