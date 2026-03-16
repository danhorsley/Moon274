import random

RIVAL_DEFS = [
    {"name": "Krath Syndicate",   "aggressive": 0.8, "sneaky": 0.3, "diplomatic": 0.2, "moon": 50},
    {"name": "Velune Collective",  "aggressive": 0.2, "sneaky": 0.7, "diplomatic": 0.5, "moon": 100},
    {"name": "Iron Meridian",      "aggressive": 0.6, "sneaky": 0.1, "diplomatic": 0.4, "moon": 150},
    {"name": "Obsidian Court",     "aggressive": 0.4, "sneaky": 0.9, "diplomatic": 0.3, "moon": 200},
    {"name": "Helios Compact",     "aggressive": 0.3, "sneaky": 0.2, "diplomatic": 0.8, "moon": 250},
]

ACTIONS = ["heist", "trade", "spy", "fortify", "idle"]


class Rival:
    def __init__(self, defn):
        self.name = defn["name"]
        self.aggressive = defn["aggressive"]
        self.sneaky = defn["sneaky"]
        self.diplomatic = defn["diplomatic"]
        self.moon = defn["moon"]
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
        return [(r.name, r.moon) for r in self.rivals]
