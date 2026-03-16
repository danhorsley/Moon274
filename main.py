import pygame
import sys
import random
from lattice import KnowledgeLattice
from market import MarketSim
from rivals import RivalMoons
from tourists import TouristEmissaries
from equilibrium import VarianceEquilibrium
from orbital_map import OrbitalMap
from player import PlayerState
from flavor import get_flavor, get_game_over_flavor, SoundBank
from ui import (
    TerminalLog, MarketTicker, EquilibriumBar, MessagePanel,
    CommandInput, GameOverScreen, SpeedControl, COMMANDS,
    parse_command, run_simulate,
    BG, GREEN, DIM_GREEN, HIGHLIGHT, WARN_RED, COOL_BLUE, CYAN, WHITE,
    DARK_GREEN,
)

WIDTH, HEIGHT = 1280, 800
FPS = 15
TICK_INTERVAL = 600
PLAYER_MOON_COLOR = (0, 255, 100)
ROUTE_COLOR = (0, 220, 220)

# Layout: left terminal | center map | right panels | bottom input+events
TERMINAL_RECT = (4, 4, 420, 530)
MAP_RECT      = (428, 4, 430, 430)
TICKER_RECT   = (862, 4, 414, 178)
EQ_BAR_RECT   = (862, 186, 414, 58)
MSG_RECT      = (862, 248, 414, 186)
SCORE_RECT    = (428, 438, 430, 96)
SPEED_RECT    = (428, 538, 430, 56)
INPUT_RECT    = (4, 538, 420, 56)
LOG_BOTTOM    = (4, 598, 1272, 82)
# Map-side command hint
CMD_HINT_RECT = (862, 438, 414, 96)


def build_game_state(lattice, market, equilibrium, rivals, tourists, player=None):
    gs = {
        "prices": market.get_prices(),
        "golden_ages": lattice.get_active_golden_ages(),
        "tags": lattice.get_tags(),
        "equilibrium": equilibrium.value,
        "rival_positions": rivals.get_positions(),
        "tourist_positions": tourists.get_positions(),
        "tourist_routes": tourists.get_routes(),
    }
    if player:
        gs["player_abilities"] = dict(player.abilities)
        gs["player_notoriety"] = player.notoriety
        gs["player_resources"] = player.resources
    return gs


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Moon 274 — Variance Terminal")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("courier", 13)
    font_big = pygame.font.SysFont("courier", 16, bold=True)
    font_sm = pygame.font.SysFont("courier", 11)

    # Sound
    sounds = SoundBank()

    # Engines
    lattice = KnowledgeLattice()
    market = MarketSim()
    rivals = RivalMoons()
    tourists = TouristEmissaries()
    equilibrium = VarianceEquilibrium()
    player = PlayerState()

    # UI panels
    terminal = TerminalLog(TERMINAL_RECT, font)
    orbital = OrbitalMap(MAP_RECT, font_sm)
    ticker = MarketTicker(TICKER_RECT, font)
    eq_bar = EquilibriumBar(EQ_BAR_RECT, font)
    msg_panel = MessagePanel(MSG_RECT, font)
    cmd_input = CommandInput(INPUT_RECT, font)
    speed = SpeedControl(SPEED_RECT, font)
    game_over_screen = GameOverScreen(font, font_big)

    # Event strip
    event_strip_lines = []

    # Scoring
    tick = 0
    last_tick_time = pygame.time.get_ticks()
    best_stability = 0.0  # longest streak with |eq| < 0.3
    current_streak = 0
    total_trades = 0
    total_heists = 0
    tourists_hosted = 0
    golden_ages_witnessed = 0

    def tlog(msg, color=GREEN):
        terminal.add(f"[t{tick:04d}] {msg}", color)

    def elog(msg, color=HIGHLIGHT):
        event_strip_lines.append((msg, color))
        if len(event_strip_lines) > 100:
            del event_strip_lines[:50]

    # Welcome
    terminal.add("=== MOON 274 VARIANCE TERMINAL ===", HIGHLIGHT)
    terminal.add("Type HELP for commands. Click moons on the map.", GREEN)
    terminal.add("Drag between moons to preview routes.", GREEN)
    terminal.add("[SPACE] pause/play  [.] step  [1] 1x  [2] 3x  [3] 10x", DIM_GREEN)
    terminal.add("Survive. Balance. Don't get reintegrated.", WARN_RED)
    terminal.add("", GREEN)

    # Flavor every N ticks
    flavor_cooldown = 0

    def execute_command(raw):
        nonlocal total_trades, total_heists
        parsed, err = parse_command(raw)
        if err:
            tlog(f"ERROR: {err}", WARN_RED)
            return
        if parsed is None:
            return

        cmd, args = parsed
        sounds.play("command")

        if cmd == "HELP":
            tlog("--- COMMANDS ---", HIGHLIGHT)
            for name, (desc, eq_act, tags) in COMMANDS.items():
                sign = "+" if eq_act in ("trade", "protect", "trade_idea",
                                         "diplomacy", "research", "broadcast") else "-"
                tlog(f"  {name:<12} {desc}  [eq:{sign}]", GREEN)
            tlog(f"  {'SIMULATE':<12} Preview: SIMULATE <CMD>", GREEN)
            tlog(f"  {'STATUS':<12} Show abilities & connections", GREEN)
            tlog(f"  {'HELP':<12} Show this list", GREEN)
            tlog("----------------", HIGHLIGHT)
            return

        if cmd == "STATUS":
            tlog("--- PLAYER STATUS ---", HIGHLIGHT)
            tlog(f"  {player.get_ability_line()}", CYAN)
            tlog("  CONNECTIONS:", GREEN)
            for line in player.get_connection_summary(rivals):
                tlog(line, GREEN)
            tlog("---------------------", HIGHLIGHT)
            return

        if cmd == "SIMULATE":
            action, target = args
            lines = run_simulate(action, lattice, market, equilibrium, rivals, player)
            for line in lines:
                tlog(line, CYAN)
            return

        if cmd not in COMMANDS:
            tlog(f"Unknown: {cmd}", WARN_RED)
            return

        desc, eq_action, chaos_tags = COMMANDS[cmd]

        # Pick target rival (from args or random)
        target_rival = player.get_target_rival(rivals, args)

        # Ensure connection exists for targeted actions
        if target_rival and target_rival.name not in player.connections:
            from player import Connection
            player.connections[target_rival.name] = Connection(target_rival.moon, target_rival.name)

        # Resolve through player ability system
        success, p_events, eq_modifier = player.resolve_action(
            eq_action, target_rival=target_rival, lattice=lattice, tourists=tourists
        )

        # Apply equilibrium impact (modified by betrayal/crit fail)
        from equilibrium import ACTION_IMPACTS
        base_delta = ACTION_IMPACTS.get(eq_action, 0.0)
        adjusted_delta = base_delta * eq_modifier
        equilibrium.value = max(-1.0, min(1.0, equilibrium.value + adjusted_delta))

        # Header
        result_tag = "SUCCESS" if success else "FAILED"
        result_color = COOL_BLUE if success else WARN_RED
        target_str = f" -> {target_rival.name}" if target_rival else ""
        tlog(f">>> {cmd}{target_str}: {result_tag}", result_color)
        tlog(f"    {desc}", result_color)

        # Player resolution events
        for e in p_events:
            color = GREEN if success else WARN_RED
            if "CRITICAL" in e or "BETRAYAL" in e:
                color = WARN_RED
            elif "SUCCESS" in e or "profit" in e or "undetected" in e:
                color = COOL_BLUE
            tlog(f"  {e}", color)

        # Flavor text
        flavor_cat = eq_action if eq_action in ("heist", "trade", "protect") else None
        if flavor_cat:
            tlog(f'    "{get_flavor(flavor_cat)}"', (140, 180, 140))

        tlog(f"    Equilibrium: {equilibrium.value:+.3f} (delta:{adjusted_delta:+.3f})", COOL_BLUE)
        tlog(f"    {player.get_ability_line()}", DIM_GREEN)

        # Sound
        if eq_action in ("heist", "sabotage"):
            sounds.play("heist")
            total_heists += 1
        elif eq_action in ("trade", "trade_idea", "diplomacy"):
            sounds.play("trade")
            total_trades += 1
        elif eq_action in ("protect",):
            sounds.play("protect")

        # Inject chaos into lattice
        if chaos_tags:
            lattice.inject_chaos(chaos_tags)
            for e in lattice.events:
                tlog(f"    {e}", HIGHLIGHT)

        # Reputation effects (scaled by success)
        if eq_action in ("heist", "sabotage"):
            rep_hit = -0.05 if success else -0.03
            for r in rivals.rivals:
                r.reputation += rep_hit
            tlog("    Rival relations deteriorated.", WARN_RED)
            # Check if a tourist was at the target moon
            if target_rival and success:
                for t in tourists.tourists:
                    if t.position == target_rival.moon:
                        tlog(f"    {t.name} witnessed your {eq_action}!", WARN_RED)
                        tlog(f"    Tourist avoids Moon 274 for 20 ticks.", WARN_RED)
                        equilibrium.action_impact("sabotage")  # extra penalty
                        # Push tourist away (skip route stops)
                        for _ in range(3):
                            t.move_tick()
        if eq_action == "diplomacy" and success:
            for r in rivals.rivals:
                r.reputation += 0.02
            if target_rival:
                target_rival.reputation += 0.03  # extra for target
            tlog("    Rival relations improved.", GREEN)

        elog(f"PLAYER: {cmd} {result_tag} (eq={equilibrium.value:+.2f})", result_color)

    running = True
    game_over = False
    cmd_input_focused = False

    while running:
        game_state = build_game_state(lattice, market, equilibrium, rivals, tourists, player)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif game_over and event.key == pygame.K_r:
                    return main()
                elif game_over:
                    continue
                elif event.key == pygame.K_PAGEUP:
                    terminal.scroll_up()
                elif event.key == pygame.K_PAGEDOWN:
                    terminal.scroll_down()
                # Speed controls take priority when input is empty
                elif not cmd_input.text and speed.handle_key(event.key):
                    pass  # consumed by speed control
                else:
                    result = cmd_input.handle_key(event)
                    if result is not None:
                        execute_command(result)
            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    terminal.scroll_up()
                else:
                    terminal.scroll_down()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check speed control buttons first
                if speed.handle_click(event.pos):
                    pass  # consumed
                else:
                    # Check if clicking command input area (auto-pause)
                    if pygame.Rect(INPUT_RECT).collidepoint(event.pos):
                        if not speed.is_paused:
                            speed.set_mode(0)
                            tlog("Auto-paused for command input.", DIM_GREEN)
                    # Forward to map
                    orbital.handle_event(event, game_state)
            elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
                map_result = orbital.handle_event(event, game_state)
                if map_result is not None:
                    if map_result[0] == "click":
                        moon_id = map_result[1]
                        tlog(f"MAP: Selected Moon {moon_id}", CYAN)
                        for r_name, r_pos in game_state["rival_positions"]:
                            if r_pos == moon_id:
                                tlog(f"  Rival: {r_name}", WARN_RED)
                        for t_name, t_pos in game_state["tourist_positions"]:
                            if t_pos == moon_id:
                                tlog(f"  Tourist: {t_name}", COOL_BLUE)
                        if moon_id == 274:
                            tlog("  >> YOUR MOON <<", PLAYER_MOON_COLOR)
                    elif map_result[0] == "route":
                        src, dst = map_result[1], map_result[2]
                        tlog(f"ROUTE: Moon {src} -> Moon {dst}", ROUTE_COLOR)
                        lines = run_simulate("TRADE", lattice, market, equilibrium, rivals)
                        for line in lines:
                            tlog(f"  {line}", CYAN)

        # Advance simulation based on speed control
        if not game_over:
            now = pygame.time.get_ticks()
            elapsed = now - last_tick_time
            if speed.should_tick(elapsed):
                last_tick_time = now
                tick += 1
                speed.after_step()  # if step mode, return to paused
                sounds.play("tick")

                # 1. Lattice
                for e in lattice.update():
                    tlog(e, HIGHLIGHT)
                    elog(e, HIGHLIGHT)
                    if "GOLDEN AGE" in e:
                        sounds.play("golden_age")
                        golden_ages_witnessed += 1
                        tlog(f'  "{get_flavor("golden_age")}"', (140, 180, 140))

                # 2. Market
                tag_weights = lattice.get_tags()
                golden_ages = lattice.get_active_golden_ages()
                for e in market.update(tag_weights, golden_ages):
                    tlog(e, HIGHLIGHT)

                # 3. Rivals (only half act each tick for pacing)
                game_state = build_game_state(lattice, market, equilibrium, rivals, tourists, player)
                for e in rivals.decide(game_state):
                    tlog(e, WARN_RED)
                    if "heist" in e.lower():
                        elog(e, WARN_RED)
                        if random.random() < 0.3:
                            tlog(f'  "{get_flavor("rival_heist")}"', (140, 140, 140))
                # Rival actions: reduced eq impact (only heists/spies matter)
                for r in rivals.rivals:
                    if r.last_action == "heist":
                        equilibrium.action_impact("heist")
                    elif r.last_action == "spy":
                        equilibrium.action_impact("spy")
                    elif r.last_action == "trade":
                        equilibrium.action_impact("trade")

                # 4. Tourists
                t_events, interactions = tourists.move_and_interact(game_state)
                for e in t_events:
                    tlog(e, COOL_BLUE)
                    elog(e, COOL_BLUE)
                    if "arrives" in e:
                        tourists_hosted += 1
                        sounds.play("tourist")
                        tlog(f'  "{get_flavor("tourist")}"', (140, 180, 140))
                for intr in interactions:
                    if intr["type"] != "warning":
                        equilibrium.action_impact(intr["type"])

                # 5. Equilibrium
                for e in equilibrium.update():
                    color = WARN_RED if equilibrium.value < 0 else GREEN
                    tlog(e, color)
                    elog(e, color)
                    if "WARNING" in e or "CRITICAL" in e:
                        sounds.play("warning")
                        tlog(f'  "{get_flavor("equilibrium_warn")}"', (180, 140, 140))

                if equilibrium.game_over:
                    game_over = True
                    sounds.play("game_over")
                    neg = equilibrium.value < 0
                    tlog(f'"{get_game_over_flavor(neg)}"', WARN_RED)

                # 6. Player passive updates
                for e in player.tick_update():
                    tlog(e, WARN_RED if "LOW" in e or "BANKRUPT" in e else DIM_GREEN)

                # 7. Scoring
                if abs(equilibrium.value) < 0.3:
                    current_streak += 1
                    best_stability = max(best_stability, current_streak)
                else:
                    current_streak = 0

                # Ambient flavor every 15-25 ticks
                flavor_cooldown -= 1
                if flavor_cooldown <= 0:
                    tlog(f'  "{get_flavor("idle")}"', (80, 120, 80))
                    flavor_cooldown = random.randint(15, 25)

        # ── RENDER ──
        screen.fill(BG)

        # Panels
        terminal.draw(screen)
        orbital.draw(screen, game_state)
        ticker.draw(screen, market)
        eq_bar.draw(screen, equilibrium)
        msg_panel.draw(screen, rivals, tourists, lattice)
        cmd_input.draw(screen)
        speed.draw(screen)

        # Score + Player panel
        score_r = pygame.Rect(SCORE_RECT)
        pygame.draw.rect(screen, DARK_GREEN, score_r, 1)
        sy = score_r.y + 4

        # Player abilities bar
        a = player.abilities
        stl_color = HIGHLIGHT if a["stealth"] >= 1.0 else GREEN
        inf_color = HIGHLIGHT if a["influence"] >= 1.0 else GREEN
        res_color = HIGHLIGHT if a["research"] >= 1.0 else GREEN
        ext_color = HIGHLIGHT if a["extraction"] >= 1.0 else GREEN
        # Render each ability with its own color
        ax = score_r.x + 4
        for label, val, col in [("STL", a["stealth"], stl_color),
                                 ("INF", a["influence"], inf_color),
                                 ("RES", a["research"], res_color),
                                 ("EXT", a["extraction"], ext_color)]:
            txt = f"{label}:{val:.1f}"
            screen.blit(font.render(txt, True, col), (ax, sy))
            ax += 70
        # Notoriety + Resources on same line
        noto_color = WARN_RED if player.notoriety > 0.5 else GREEN
        res_col = WARN_RED if player.resources < 20 else GREEN
        screen.blit(font.render(f"NOT:{player.notoriety:.2f}", True, noto_color), (ax, sy))
        ax += 80
        screen.blit(font.render(f"${player.resources:.0f}", True, res_col), (ax, sy))

        sy += 16
        screen.blit(font.render(f"Tick:{tick}  Streak:{current_streak}(best:{best_stability})"
                                f"  T:{total_trades} H:{total_heists} GA:{golden_ages_witnessed}",
                                True, GREEN),
                    (score_r.x + 4, sy))
        sy += 14
        # Score formula: ticks + stability_bonus + golden_age_bonus
        score = tick + best_stability * 2 + golden_ages_witnessed * 10
        screen.blit(font_big.render(f"SCORE: {score}", True, HIGHLIGHT),
                    (score_r.x + 4, sy))

        # Command hints
        hint_r = pygame.Rect(CMD_HINT_RECT)
        pygame.draw.rect(screen, DARK_GREEN, hint_r, 1)
        hy = hint_r.y + 4
        screen.blit(font_big.render("QUICK COMMANDS", True, GREEN), (hint_r.x + 4, hy))
        hy += 16
        hints = [
            ("TRADE / HEIST / PROTECT", "Core actions (+ target)"),
            ("RESEARCH / DIPLOMACY", "Positive eq, grow skills"),
            ("SABOTAGE / EAVESDROP", "Naughty, grow stealth"),
            ("SIMULATE <CMD>", "Preview w/ ability odds"),
            ("STATUS", "Show abilities & connections"),
        ]
        for label, desc in hints:
            screen.blit(font_sm.render(f"{label}: {desc}", True, DIM_GREEN),
                        (hint_r.x + 4, hy))
            hy += 13

        # Event strip
        strip_rect = pygame.Rect(LOG_BOTTOM)
        pygame.draw.rect(screen, (0, 20, 0), strip_rect, 1)
        esy = strip_rect.y + 2
        for msg, color in event_strip_lines[-6:]:
            screen.blit(font.render(msg, True, color), (strip_rect.x + 4, esy))
            esy += 14

        # Header bar
        speed_label = speed.label
        header = (f"MOON 274  |  [{speed_label}]  |  Tick:{tick}  |  GA:{len(lattice.golden_ages)}  |  "
                  f"Eq:{equilibrium.value:+.3f}  |  Score:{score}")
        header_color = HIGHLIGHT if speed.is_paused else GREEN
        screen.blit(font_big.render(header, True, header_color), (10, HEIGHT - 18))

        # Game over
        if game_over:
            game_over_screen.draw(screen, equilibrium.game_over_msg)
            # Show final score
            score_text = f"Final Score: {score}  |  Survived {tick} cycles"
            rendered = font_big.render(score_text, True, HIGHLIGHT)
            sx = (WIDTH - rendered.get_width()) // 2
            screen.blit(rendered, (sx, HEIGHT // 2 + 50))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
