import random

# Archetypes: "hub" (trade), "military" (aggro/defense), "compute" (research/intel)
RIVAL_DEFS = [
    {"name": "Krath Syndicate",   "aggressive": 0.8, "sneaky": 0.3, "diplomatic": 0.2, "moon": 50,  "archetype": "military"},
    {"name": "Velune Collective",  "aggressive": 0.2, "sneaky": 0.7, "diplomatic": 0.5, "moon": 100, "archetype": "compute"},
    {"name": "Iron Meridian",      "aggressive": 0.6, "sneaky": 0.1, "diplomatic": 0.4, "moon": 150, "archetype": "hub"},
    {"name": "Obsidian Court",     "aggressive": 0.4, "sneaky": 0.9, "diplomatic": 0.3, "moon": 200, "archetype": "compute"},
    {"name": "Helios Compact",     "aggressive": 0.3, "sneaky": 0.2, "diplomatic": 0.8, "moon": 250, "archetype": "hub"},
]

ARCHETYPE_LABELS = {"hub": "[H]", "military": "[M]", "compute": "[C]"}
ARCHETYPE_DESC = {
    "hub":      "Trade hub — better trade income, attracts tourists",
    "military": "Military power — retaliates hard, can deter raids",
    "compute":  "Compute node — research synergy, rich intel",
}

ACTIONS = ["heist", "trade", "spy", "fortify", "idle"]


class Rival:
    def __init__(self, defn):
        self.name = defn["name"]
        self.aggressive = defn["aggressive"]
        self.sneaky = defn["sneaky"]
        self.diplomatic = defn["diplomatic"]
        self.moon = defn["moon"]
        self.archetype = defn["archetype"]  # "hub", "military", "compute"
        self.reputation = 0.0   # -1 hostile .. +1 friendly
        self.last_action = "idle"

    def decision_roll(self, market_state, lattice_state, equilibrium_val,
                       player_state=None):
        """Monte Carlo pick an action based on personality + world state + player."""
        weights = {
            "heist":   self.aggressive * 1.2 + self.sneaky * 0.3,
            "trade":   self.diplomatic * 2.5 + 1.0,
            "spy":     self.sneaky * 1.5 + 0.2,
            "fortify": (1.0 - self.aggressive) * 2.0 + 0.5,
            "idle":    1.5,
        }

        # Golden Ages make rivals more active (but balanced)
        golden_count = len(lattice_state.get("golden_ages", {}))
        if golden_count > 0:
            weights["heist"] += golden_count * 0.2
            weights["trade"] += golden_count * 0.4

        # Extreme equilibrium pushes rivals toward aggression or diplomacy
        if equilibrium_val < -0.5:
            weights["heist"] += 0.5
            weights["spy"] += 0.3
        elif equilibrium_val > 0.5:
            weights["trade"] += 0.8
            weights["fortify"] += 0.3

        # React to player state
        if player_state:
            p_stealth = player_state.get("player_abilities", {}).get("stealth", 0)
            p_notoriety = player_state.get("player_notoriety", 0)

            # High player notoriety: sneaky rivals spy more, aggressive ones heist
            if p_notoriety > 0.4:
                weights["spy"] += self.sneaky * p_notoriety * 1.5
                weights["heist"] += self.aggressive * p_notoriety * 0.8

            # Player has high stealth: paranoid (sneaky) rivals fortify
            if p_stealth > 1.0:
                weights["fortify"] += self.sneaky * (p_stealth - 1.0) * 0.5
                weights["spy"] += self.sneaky * 0.3

            # Grudge: if reputation is negative, more hostile
            if self.reputation < -0.2:
                weights["heist"] += abs(self.reputation) * 1.5
                weights["trade"] *= max(0.3, 1.0 + self.reputation)  # less trade

            # Diplomacy interpreted as weakness by aggressive rivals
            if self.reputation > 0.3 and self.aggressive > 0.5:
                weights["heist"] += (self.aggressive - 0.5) * self.reputation * 1.2

            # React to player upgrades
            p_upgrades = player_state.get("player_upgrades", {})
            drones = p_upgrades.get("drones", 0)
            clusters = p_upgrades.get("clusters", 0)
            leisure = p_upgrades.get("leisure", 0)

            # High drones: aggressive rivals deterred, sneaky ones spy instead
            if drones >= 2:
                weights["heist"] *= max(0.4, 1.0 - drones * 0.12)
                weights["spy"] += self.sneaky * drones * 0.15

            # High clusters: rivals want to trade (profit from research output)
            if clusters >= 2:
                weights["trade"] += clusters * 0.3

            # High leisure: sneaky rivals spy more (intel-rich environment)
            if leisure >= 2:
                weights["spy"] += self.sneaky * leisure * 0.2

        # Archetype bias
        if self.archetype == "hub":
            weights["trade"] += 1.0
            weights["heist"] *= 0.7
        elif self.archetype == "military":
            weights["fortify"] += 1.0
            weights["heist"] += 0.5
        elif self.archetype == "compute":
            weights["spy"] += 1.0
            weights["idle"] *= 0.5

        # Add Gaussian noise to each weight
        noisy = {k: max(0.01, v + random.gauss(0, 0.3)) for k, v in weights.items()}
        total = sum(noisy.values())
        roll = random.random() * total

        cumulative = 0
        chosen = "idle"
        for action, w in noisy.items():
            cumulative += w
            if roll <= cumulative:
                chosen = action
                break

        self.last_action = chosen
        return chosen


class RivalMoons:
    def __init__(self):
        self.rivals = [Rival(d) for d in RIVAL_DEFS]
        self.events = []

    def decide(self, game_state):
        """All rivals take a turn. Returns list of event strings."""
        self.events = []
        market_state = game_state.get("prices", {})
        lattice_state = {
            "golden_ages": game_state.get("golden_ages", {}),
            "tags": game_state.get("tags", {}),
        }
        eq_val = game_state.get("equilibrium", 0.0)

        for rival in self.rivals:
            action = rival.decision_roll(market_state, lattice_state, eq_val,
                                         player_state=game_state)
            if action == "heist":
                target = random.choice([r for r in self.rivals if r is not rival])
                self.events.append(f"RIVAL: {rival.name} heists {target.name}!")
                rival.reputation -= 0.05
                target.reputation -= 0.02
            elif action == "trade":
                self.events.append(f"RIVAL: {rival.name} opens trade channel")
                rival.reputation += 0.03
            elif action == "spy":
                self.events.append(f"RIVAL: {rival.name} runs covert op")
            elif action == "fortify":
                self.events.append(f"RIVAL: {rival.name} fortifies defenses")

        return self.events

    def get_status(self):
        return [(r.name, r.last_action, r.reputation) for r in self.rivals]

    def get_positions(self):
        return [(r.name, r.moon, r.archetype) for r in self.rivals]

    def get_rival_by_name(self, name):
        """Look up a rival by exact name."""
        for r in self.rivals:
            if r.name == name:
                return r
        return None

    def get_hub_trade_bonus(self, rival_name):
        """Multiplier for passive trade income with hub rivals. 1.5x for hubs, 1.0 otherwise."""
        r = self.get_rival_by_name(rival_name)
        if r and r.archetype == "hub":
            return 1.5
        return 1.0

    def get_compute_research_trickle(self, rival_name):
        """Research trickle rate when trade line open with compute rival."""
        r = self.get_rival_by_name(rival_name)
        if r and r.archetype == "compute":
            return 0.3  # small lattice push strength
        return 0.0

    def get_military_deterrent(self, rival_name):
        """Raid deterrence factor from military alliance (0.0 to 0.3)."""
        r = self.get_rival_by_name(rival_name)
        if r and r.archetype == "military" and r.reputation > 0.2:
            return min(0.3, r.reputation * 0.3)
        return 0.0

    def get_total_military_deterrent(self, player_connections):
        """Total raid deterrence from all military alliances."""
        total = 0.0
        for name, conn in player_connections.items():
            if conn.open_trade or conn.trust > 0.2:
                total += self.get_military_deterrent(name)
        return min(0.5, total)  # cap at 50% reduction
