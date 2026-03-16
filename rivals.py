import random

RIVAL_DEFS = [
    {"name": "Krath Syndicate",   "aggressive": 0.8, "sneaky": 0.3, "diplomatic": 0.2},
    {"name": "Velune Collective",  "aggressive": 0.2, "sneaky": 0.7, "diplomatic": 0.5},
    {"name": "Iron Meridian",      "aggressive": 0.6, "sneaky": 0.1, "diplomatic": 0.4},
    {"name": "Obsidian Court",     "aggressive": 0.4, "sneaky": 0.9, "diplomatic": 0.3},
    {"name": "Helios Compact",     "aggressive": 0.3, "sneaky": 0.2, "diplomatic": 0.8},
]

ACTIONS = ["heist", "trade", "spy", "fortify", "idle"]


class Rival:
    def __init__(self, defn):
        self.name = defn["name"]
        self.aggressive = defn["aggressive"]
        self.sneaky = defn["sneaky"]
        self.diplomatic = defn["diplomatic"]
        self.reputation = 0.0   # -1 hostile .. +1 friendly
        self.last_action = "idle"

    def decision_roll(self, market_state, lattice_state, equilibrium_val):
        """Monte Carlo pick an action based on personality + world state."""
        weights = {
            "heist":   self.aggressive * 2.0 + self.sneaky * 0.5,
            "trade":   self.diplomatic * 2.0 + 0.5,
            "spy":     self.sneaky * 2.0 + 0.3,
            "fortify": (1.0 - self.aggressive) * 1.5,
            "idle":    0.5,
        }

        # Golden Ages make rivals more active
        golden_count = len(lattice_state.get("golden_ages", {}))
        if golden_count > 0:
            weights["heist"] += golden_count * 0.4
            weights["trade"] += golden_count * 0.3

        # Extreme equilibrium pushes rivals toward aggression or diplomacy
        if equilibrium_val < -0.5:
            weights["heist"] += 1.0
            weights["spy"] += 0.5
        elif equilibrium_val > 0.5:
            weights["trade"] += 1.0
            weights["fortify"] += 0.5

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
            action = rival.decision_roll(market_state, lattice_state, eq_val)
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
