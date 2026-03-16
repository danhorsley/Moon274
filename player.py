"""Player state: 4 abilities, connections to moons, action resolution with consequences."""
import random

# Ability caps
MAX_ABILITY = 3.0
GROWTH_RATE = 0.02   # per successful action
FAIL_PENALTY = 0.01  # lose a bit on failure

# Which abilities each action uses (primary, secondary)
ACTION_ABILITIES = {
    "heist":      ("stealth",    "extraction"),
    "eavesdrop":  ("stealth",    "research"),
    "sabotage":   ("stealth",    "extraction"),
    "smuggle":    ("stealth",    "extraction"),
    "trade":      ("influence",  "extraction"),
    "trade_idea": ("influence",  "research"),
    "diplomacy":  ("influence",  "research"),
    "broadcast":  ("influence",  "research"),
    "protect":    ("extraction", "influence"),
    "research":   ("research",   "influence"),
}

# Base success thresholds: roll must beat this (0-1 scale)
# Lower = easier to succeed
BASE_DIFFICULTY = {
    "heist":      0.55,
    "eavesdrop":  0.45,
    "sabotage":   0.60,
    "smuggle":    0.40,
    "trade":      0.25,
    "trade_idea": 0.20,
    "diplomacy":  0.20,
    "broadcast":  0.15,
    "protect":    0.15,
    "research":   0.10,
}


class Connection:
    """A trade/intel link to another moon."""
    __slots__ = ("moon_id", "moon_name", "trust", "open_trade", "times_heisted",
                 "times_traded", "eavesdropped", "grudge_ticks")

    def __init__(self, moon_id, moon_name):
        self.moon_id = moon_id
        self.moon_name = moon_name
        self.trust = 0.0          # -1 to +1
        self.open_trade = False
        self.times_heisted = 0
        self.times_traded = 0
        self.eavesdropped = False  # currently tapping
        self.grudge_ticks = 0     # ticks of hostility remaining


class PlayerState:
    """Moon 274 operator: abilities, connections, resources."""

    def __init__(self):
        # Core abilities (start low, grow through actions)
        self.abilities = {
            "stealth":    0.20,
            "influence":  0.20,
            "research":   0.20,
            "extraction": 0.20,
        }

        # Connections: keyed by rival name
        self.connections = {}

        # Resources (abstract currency for trade/costs)
        self.resources = 100.0

        # Per-rival reputation is on the Rival objects, but we track
        # overall "notoriety" — how visible the player is
        self.notoriety = 0.0  # 0 = invisible, 1 = infamous

    def get_ability(self, name):
        return self.abilities.get(name, 0.0)

    def _grow_ability(self, name, amount=GROWTH_RATE):
        self.abilities[name] = min(MAX_ABILITY, self.abilities[name] + amount)

    def _shrink_ability(self, name, amount=FAIL_PENALTY):
        self.abilities[name] = max(0.0, self.abilities[name] - amount)

    def open_trade_line(self, rival):
        """Open a trade connection. Makes eavesdropping against you easier."""
        if rival.name not in self.connections:
            self.connections[rival.name] = Connection(rival.moon, rival.name)
        conn = self.connections[rival.name]
        conn.open_trade = True
        conn.trust = min(1.0, conn.trust + 0.1)
        return conn

    def get_connection(self, rival_name):
        return self.connections.get(rival_name, None)

    def resolve_action(self, action_type, target_rival=None, lattice=None, tourists=None):
        """
        Resolve a player action with Monte Carlo roll.
        Returns (success: bool, events: list[str], eq_modifier: float)
          eq_modifier adjusts the equilibrium impact (1.0 = normal, <1 = reduced)
        """
        events = []
        primary, secondary = ACTION_ABILITIES.get(action_type, ("influence", "extraction"))
        difficulty = BASE_DIFFICULTY.get(action_type, 0.30)

        # Ability bonus: each point reduces difficulty
        ability_bonus = self.abilities[primary] * 0.12 + self.abilities[secondary] * 0.06
        effective_diff = max(0.05, difficulty - ability_bonus)

        # Connection modifiers
        conn = self.connections.get(target_rival.name) if target_rival else None
        betrayal_mult = 1.0

        if conn and conn.open_trade and action_type in ("heist", "sabotage"):
            # Betraying a trade partner — easier to execute but worse consequences
            effective_diff *= 0.7  # easier (you have access)
            betrayal_mult = 2.0    # but double eq penalty if you do it
            events.append(f"  Exploiting trade access to {conn.moon_name}...")

        if conn and conn.grudge_ticks > 0 and action_type in ("trade", "diplomacy"):
            # Trying to be nice to someone who's angry
            effective_diff *= 1.5
            events.append(f"  {conn.moon_name} holds a grudge ({conn.grudge_ticks}t left)...")

        # Notoriety makes stealth actions harder
        if action_type in ("heist", "eavesdrop", "sabotage", "smuggle"):
            effective_diff += self.notoriety * 0.15
            if self.notoriety > 0.5:
                events.append(f"  High notoriety ({self.notoriety:.2f}) — they're watching you.")

        # Roll!
        roll = random.random()
        success = roll > effective_diff

        # Critical fail: bottom 10% of possible failures
        crit_fail = not success and roll < effective_diff * 0.10

        if success:
            self._grow_ability(primary)
            self._grow_ability(secondary, GROWTH_RATE * 0.5)
            eq_modifier = 1.0

            if action_type == "heist":
                loot = 15 + self.abilities["extraction"] * 8 + random.uniform(0, 10)
                self.resources += loot
                self.notoriety = min(1.0, self.notoriety + 0.05)
                events.append(f"  HEIST SUCCESS: Extracted {loot:.0f} resources.")
                if conn:
                    conn.trust -= 0.3
                    conn.times_heisted += 1
                    conn.grudge_ticks = max(conn.grudge_ticks, 15)
                    if conn.open_trade:
                        events.append(f"  BETRAYAL: {conn.moon_name} closes trade line!")
                        conn.open_trade = False
                        betrayal_mult = 2.0
                eq_modifier = betrayal_mult

            elif action_type == "eavesdrop":
                # Detection check
                detect_chance = 0.3 - self.abilities["stealth"] * 0.06
                if conn and conn.open_trade:
                    detect_chance -= 0.1  # trade line = better cover
                detected = random.random() < max(0.05, detect_chance)
                if detected:
                    events.append(f"  DETECTED! {target_rival.name if target_rival else 'Target'} knows you listened.")
                    if conn:
                        conn.trust -= 0.2
                        conn.grudge_ticks = max(conn.grudge_ticks, 10)
                    self.notoriety = min(1.0, self.notoriety + 0.08)
                else:
                    events.append(f"  Intel gathered undetected.")
                    if conn:
                        conn.eavesdropped = True
                # Return rival's next likely action
                if target_rival:
                    events.append(f"  {target_rival.name}: last={target_rival.last_action}, "
                                  f"aggro={target_rival.aggressive:.1f}, sneak={target_rival.sneaky:.1f}")

            elif action_type == "sabotage":
                self.notoriety = min(1.0, self.notoriety + 0.08)
                events.append(f"  Sabotage successful — target disrupted.")
                if conn:
                    conn.trust -= 0.4
                    conn.grudge_ticks = max(conn.grudge_ticks, 20)
                    if conn.open_trade:
                        conn.open_trade = False
                        events.append(f"  {conn.moon_name} cuts all trade!")
                eq_modifier = betrayal_mult

            elif action_type == "trade":
                profit = 8 + self.abilities["influence"] * 5 + random.uniform(0, 8)
                self.resources += profit
                events.append(f"  Trade profit: +{profit:.0f} resources.")
                if conn:
                    conn.trust = min(1.0, conn.trust + 0.05)
                    conn.times_traded += 1
                    if not conn.open_trade:
                        conn.open_trade = True
                        events.append(f"  Trade line opened with {conn.moon_name}.")

            elif action_type == "trade_idea":
                events.append(f"  Ideas exchanged — lattice injection underway.")
                self.notoriety = max(0, self.notoriety - 0.02)

            elif action_type == "diplomacy":
                events.append(f"  Diplomatic mission successful.")
                cost = 5 + random.uniform(0, 5)
                self.resources -= cost
                events.append(f"  Diplomatic gifts cost {cost:.0f} resources.")
                if conn:
                    conn.trust = min(1.0, conn.trust + 0.15)
                    conn.grudge_ticks = max(0, conn.grudge_ticks - 5)
                self.notoriety = max(0, self.notoriety - 0.03)

            elif action_type == "smuggle":
                profit = 20 + self.abilities["extraction"] * 10 + random.uniform(0, 15)
                self.resources += profit
                self.notoriety = min(1.0, self.notoriety + 0.06)
                events.append(f"  Contraband moved: +{profit:.0f} resources.")

            elif action_type == "protect":
                events.append(f"  Defenses reinforced.")
                self.notoriety = max(0, self.notoriety - 0.02)

            elif action_type == "research":
                events.append(f"  Lab output increased.")

            elif action_type == "broadcast":
                events.append(f"  Signal broadcast across moons.")
                self.notoriety = min(1.0, self.notoriety + 0.02)

        else:
            # FAILURE
            self._shrink_ability(primary)
            eq_modifier = 1.0

            if crit_fail:
                events.append(f"  !! CRITICAL FAILURE !!")

            if action_type == "heist":
                loss = 10 + random.uniform(0, 10)
                self.resources -= loss
                self.notoriety = min(1.0, self.notoriety + 0.10)
                events.append(f"  Heist FAILED — lost {loss:.0f} resources fleeing.")
                if conn:
                    conn.trust -= 0.4
                    conn.grudge_ticks = max(conn.grudge_ticks, 20)
                    if conn.open_trade:
                        conn.open_trade = False
                        events.append(f"  {conn.moon_name} slams trade shut!")
                if crit_fail and target_rival:
                    # They steal from you
                    stolen = 15 + random.uniform(0, 15)
                    self.resources -= stolen
                    events.append(f"  {target_rival.name} counter-raids you! Lost {stolen:.0f} more.")
                # Failed heist still moves eq (you tried)
                eq_modifier = 1.3 if crit_fail else 1.0

            elif action_type == "eavesdrop":
                events.append(f"  Eavesdrop failed — no useful intel.")
                # Always detected on fail
                if conn:
                    conn.trust -= 0.15
                    conn.grudge_ticks = max(conn.grudge_ticks, 8)
                events.append(f"  You were detected.")
                self.notoriety = min(1.0, self.notoriety + 0.06)

            elif action_type == "sabotage":
                events.append(f"  Sabotage failed — operation exposed.")
                self.notoriety = min(1.0, self.notoriety + 0.12)
                if conn:
                    conn.trust -= 0.5
                    conn.grudge_ticks = max(conn.grudge_ticks, 25)
                    if conn.open_trade:
                        conn.open_trade = False
                if crit_fail:
                    # Blow up your own stuff
                    self_damage = 20
                    self.resources -= self_damage
                    events.append(f"  Sabotage backfired! Lost {self_damage} resources.")

            elif action_type == "smuggle":
                loss = 10
                self.resources -= loss
                self.notoriety = min(1.0, self.notoriety + 0.08)
                events.append(f"  Contraband seized! Lost {loss} resources.")

            elif action_type in ("trade", "trade_idea", "diplomacy"):
                events.append(f"  Negotiation fell through.")
                # Mild consequence
                cost = 3
                self.resources -= cost
                events.append(f"  Wasted {cost} resources on failed deal.")

            else:
                events.append(f"  Action failed.")

        # Clamp resources
        self.resources = max(0, self.resources)

        return success, events, eq_modifier

    def tick_update(self):
        """Per-tick passive updates."""
        events = []
        # Notoriety decays slowly
        if self.notoriety > 0:
            self.notoriety = max(0, self.notoriety - 0.008)

        # Grudge decay on connections
        for conn in self.connections.values():
            if conn.grudge_ticks > 0:
                conn.grudge_ticks -= 1
                if conn.grudge_ticks == 0:
                    events.append(f"  {conn.moon_name}'s grudge has faded.")

        # Passive resource drain (maintenance)
        self.resources -= 0.5

        # Low resource warning
        if self.resources < 20:
            events.append(f"  LOW RESOURCES: {self.resources:.0f} — trade or smuggle soon.")
        if self.resources <= 0:
            events.append(f"  BANKRUPT: No resources left!")

        return events

    def get_target_rival(self, rivals, target_arg=None):
        """Pick a rival target from command args or random."""
        if target_arg:
            # Try to match by name fragment
            for r in rivals.rivals:
                if target_arg.upper() in r.name.upper():
                    return r
        # Random target
        return random.choice(rivals.rivals)

    def get_ability_line(self):
        """One-line summary for UI."""
        a = self.abilities
        return (f"STL:{a['stealth']:.2f} INF:{a['influence']:.2f} "
                f"RES:{a['research']:.2f} EXT:{a['extraction']:.2f} "
                f"| Noto:{self.notoriety:.2f} | ${self.resources:.0f}")

    def get_connection_summary(self, rivals):
        """Short list of connections for UI."""
        lines = []
        for r in rivals.rivals:
            conn = self.connections.get(r.name)
            if conn:
                trade = "OPEN" if conn.open_trade else "closed"
                grudge = f" GRUDGE:{conn.grudge_ticks}t" if conn.grudge_ticks > 0 else ""
                lines.append(f"  {r.name[:14]:<14} trd:{trade:<6} trust:{conn.trust:+.2f}{grudge}")
            else:
                lines.append(f"  {r.name[:14]:<14} (no contact)")
        return lines
