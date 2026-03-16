import pygame
import sys
from lattice import KnowledgeLattice
from market import MarketSim
from rivals import RivalMoons
from tourists import TouristEmissaries
from equilibrium import VarianceEquilibrium
from ui import (
    TerminalLog, MarketTicker, EquilibriumBar, MessagePanel,
    CommandInput, GameOverScreen, COMMANDS,
    parse_command, run_simulate,
    BG, GREEN, DIM_GREEN, HIGHLIGHT, WARN_RED, COOL_BLUE, CYAN, WHITE,
)

WIDTH, HEIGHT = 1000, 700
FPS = 15
TICK_INTERVAL = 600  # ms between simulation ticks

# Layout rects: left terminal, right panels, bottom input
TERMINAL_RECT = (4, 4, 580, 540)
TICKER_RECT   = (588, 4, 408, 190)
EQ_BAR_RECT   = (588, 198, 408, 60)
MSG_RECT      = (588, 262, 408, 282)
INPUT_RECT    = (4, 548, 992, 38)
LOG_BOTTOM    = (4, 590, 992, 106)


def build_game_state(lattice, market, equilibrium):
    return {
        "prices": market.get_prices(),
        "golden_ages": lattice.get_active_golden_ages(),
        "tags": lattice.get_tags(),
        "equilibrium": equilibrium.value,
    }


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Moon 274 — Variance Terminal")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("courier", 13)
    font_big = pygame.font.SysFont("courier", 16, bold=True)

    # Engines
    lattice = KnowledgeLattice()
    market = MarketSim()
    rivals = RivalMoons()
    tourists = TouristEmissaries()
    equilibrium = VarianceEquilibrium()

    # UI panels
    terminal = TerminalLog(TERMINAL_RECT, font)
    ticker = MarketTicker(TICKER_RECT, font)
    eq_bar = EquilibriumBar(EQ_BAR_RECT, font)
    msg_panel = MessagePanel(MSG_RECT, font)
    cmd_input = CommandInput(INPUT_RECT, font)
    game_over_screen = GameOverScreen(font, font_big)

    # Bottom event strip
    event_strip_lines = []

    tick = 0
    last_tick_time = pygame.time.get_ticks()

    def tlog(msg, color=GREEN):
        terminal.add(f"[t{tick:04d}] {msg}", color)

    def elog(msg, color=HIGHLIGHT):
        event_strip_lines.append((msg, color))
        if len(event_strip_lines) > 100:
            del event_strip_lines[:50]

    # Welcome
    terminal.add("=== MOON 274 VARIANCE TERMINAL ===", HIGHLIGHT)
    terminal.add("Type HELP for commands. Balance the Equilibrium.", GREEN)
    terminal.add("Reintegration occurs at extreme values. Stay on the tightrope.", WARN_RED)
    terminal.add("", GREEN)

    def execute_command(raw):
        """Parse and execute a player command."""
        parsed, err = parse_command(raw)
        if err:
            tlog(f"ERROR: {err}", WARN_RED)
            return
        if parsed is None:
            return

        cmd, args = parsed

        if cmd == "HELP":
            tlog("─── COMMANDS ───", HIGHLIGHT)
            for name, (desc, eq_act, tags) in COMMANDS.items():
                impact = f"eq:{'+' if eq_act in ('trade','protect','trade_idea','diplomacy','research','broadcast') else '-'}"
                tlog(f"  {name:<12} {desc}  [{impact}]", GREEN)
            tlog(f"  {'SIMULATE':<12} Preview action: SIMULATE <CMD> [MOON-N]", GREEN)
            tlog(f"  {'HELP':<12} Show this list", GREEN)
            tlog("─────────────────", HIGHLIGHT)
            return

        if cmd == "SIMULATE":
            action, target = args
            lines = run_simulate(action, lattice, market, equilibrium, rivals)
            for line in lines:
                tlog(line, CYAN)
            return

        # Execute action
        if cmd not in COMMANDS:
            tlog(f"Unknown: {cmd}", WARN_RED)
            return

        desc, eq_action, chaos_tags = COMMANDS[cmd]
        equilibrium.action_impact(eq_action)
        tlog(f">>> {cmd}: {desc}", COOL_BLUE)
        tlog(f"    Equilibrium: {equilibrium.value:+.3f}", COOL_BLUE)

        # Inject chaos into lattice
        if chaos_tags:
            lattice.inject_chaos(chaos_tags)
            for e in lattice.events:
                tlog(f"    {e}", HIGHLIGHT)

        # Heist/sabotage affect rival reputation
        if eq_action in ("heist", "sabotage"):
            for r in rivals.rivals:
                r.reputation -= 0.03
            tlog("    Rival relations deteriorated.", WARN_RED)

        # Diplomacy improves reputation
        if eq_action == "diplomacy":
            for r in rivals.rivals:
                r.reputation += 0.02
            tlog("    Rival relations improved.", GREEN)

        elog(f"PLAYER: {cmd} (eq={equilibrium.value:+.2f})", COOL_BLUE)

    running = True
    game_over = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif game_over and event.key == pygame.K_r:
                    # Restart
                    return main()
                elif game_over:
                    continue
                elif event.key == pygame.K_PAGEUP:
                    terminal.scroll_up()
                elif event.key == pygame.K_PAGEDOWN:
                    terminal.scroll_down()
                else:
                    result = cmd_input.handle_key(event)
                    if result is not None:
                        execute_command(result)
            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    terminal.scroll_up()
                else:
                    terminal.scroll_down()

        # Advance simulation on timer
        if not game_over:
            now = pygame.time.get_ticks()
            if now - last_tick_time >= TICK_INTERVAL:
                last_tick_time = now
                tick += 1

                # 1. Lattice
                for e in lattice.update():
                    tlog(e, HIGHLIGHT)
                    elog(e, HIGHLIGHT)

                # 2. Market
                tag_weights = lattice.get_tags()
                golden_ages = lattice.get_active_golden_ages()
                for e in market.update(tag_weights, golden_ages):
                    tlog(e, HIGHLIGHT)

                # 3. Game state
                game_state = build_game_state(lattice, market, equilibrium)

                # 4. Rivals
                for e in rivals.decide(game_state):
                    tlog(e, WARN_RED)
                    elog(e, WARN_RED)
                for r in rivals.rivals:
                    if r.last_action in ("heist", "spy", "trade", "fortify"):
                        equilibrium.action_impact(r.last_action)

                # 5. Tourists
                t_events, interactions = tourists.move_and_interact(game_state)
                for e in t_events:
                    tlog(e, COOL_BLUE)
                    elog(e, COOL_BLUE)
                for intr in interactions:
                    if intr["type"] != "warning":
                        equilibrium.action_impact(intr["type"])

                # 6. Equilibrium
                for e in equilibrium.update():
                    color = WARN_RED if equilibrium.value < 0 else GREEN
                    tlog(e, color)
                    elog(e, color)

                if equilibrium.game_over:
                    game_over = True

        # ── RENDER ──
        screen.fill(BG)

        # Header bar
        header = f"MOON 274  |  Tick:{tick}  |  GA:{len(lattice.golden_ages)}  |  Eq:{equilibrium.value:+.3f}"
        screen.blit(font_big.render(header, True, GREEN), (10, HEIGHT - 18))

        # Panels
        terminal.draw(screen)
        ticker.draw(screen, market)
        eq_bar.draw(screen, equilibrium)
        msg_panel.draw(screen, rivals, tourists, lattice)
        cmd_input.draw(screen)

        # Event strip at bottom
        strip_rect = pygame.Rect(LOG_BOTTOM)
        pygame.draw.rect(screen, (0, 20, 0), strip_rect, 1)
        sy = strip_rect.y + 2
        visible_events = event_strip_lines[-6:]
        for msg, color in visible_events:
            screen.blit(font.render(msg, True, color), (strip_rect.x + 4, sy))
            sy += 14

        # Game over overlay
        if game_over:
            game_over_screen.draw(screen, equilibrium.game_over_msg)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
