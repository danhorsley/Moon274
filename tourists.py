import random

TOURIST_DEFS = [
    {"name": "Emissary Zael",  "origin": 42,  "personality": "curious"},
    {"name": "Sage Nomura",    "origin": 188, "personality": "cautious"},
    {"name": "Drift Kova",     "origin": 7,   "personality": "chaotic"},
]

# ── Tourist synergy: personality -> action difficulty reduction ──
# When a tourist with this personality is at Moon 274, these actions get easier
TOURIST_SYNERGY = {
    "curious":  {"research": 0.06, "trade_idea": 0.05, "broadcast": 0.03},
    "cautious": {"diplomacy": 0.06, "protect": 0.05, "trade": 0.03},
    "chaotic":  {"heist": 0.05, "sabotage": 0.06, "smuggle": 0.04, "eavesdrop": 0.03},
}

# ── Resident system ──
# Residents are former tourists who settled permanently at Moon 274.
# Each gives a passive bonus but increases rival attention.
RESIDENT_DEFS = [
    {"name": "Dr. Voss",      "personality": "curious",  "specialty": "research",
     "bonus": {"research": 0.04, "trade_idea": 0.03}, "maintenance": 0.3,
     "desc": "Xenobiologist — boosts research & trade ideas"},
    {"name": "Fixer Ren",     "personality": "chaotic",  "specialty": "stealth",
     "bonus": {"heist": 0.05, "sabotage": 0.04, "smuggle": 0.03}, "maintenance": 0.4,
     "desc": "Black-market operative — boosts covert ops"},
    {"name": "Consul Vey",    "personality": "cautious", "specialty": "influence",
     "bonus": {"diplomacy": 0.05, "trade": 0.04, "protect": 0.02}, "maintenance": 0.3,
     "desc": "Retired diplomat — boosts diplomacy & trade"},
    {"name": "Wraith Kael",   "personality": "chaotic",  "specialty": "stealth",
     "bonus": {"eavesdrop": 0.06, "sabotage": 0.03}, "maintenance": 0.5,
     "desc": "Signal ghost — boosts eavesdrop, attracts spies"},
    {"name": "Prof. Luma",    "personality": "curious",  "specialty": "research",
     "bonus": {"research": 0.05, "broadcast": 0.04}, "maintenance": 0.3,
     "desc": "Lattice theorist — boosts research & broadcast"},
]


def _random_route(origin, length=6, moon274_weight=1.0):
    """Generate a route of moon IDs (1-274) starting from origin.
    moon274_weight > 1 biases routes to include Moon 274 (from Leisure upgrades)."""
    route = [origin]
    for _ in range(length):
        # Leisure attraction: chance to route through Moon 274
        if moon274_weight > 1.0 and route[-1] != 274:
            attract_chance = min(0.5, (moon274_weight - 1.0) * 0.15)
            if random.random() < attract_chance:
                route.append(274)
                continue
        next_moon = random.randint(1, 274)
        while next_moon == route[-1]:
            next_moon = random.randint(1, 274)
        route.append(next_moon)
    return route


class Tourist:
    def __init__(self, defn):
        self.name = defn["name"]
        self.personality = defn["personality"]
        self.route = _random_route(defn["origin"])
        self.route_idx = 0
        self.position = self.route[0]
        self.inventory = []  # idea packets carried

    def move_tick(self):
        """Advance one stop along route, loop when done."""
        self.route_idx += 1
        if self.route_idx >= len(self.route):
            self.route = _random_route(self.position)
            self.route_idx = 0
        self.position = self.route[self.route_idx]

    def at_player_moon(self):
        return self.position == 274

    def interaction_options(self, equilibrium_val):
        """Generate trade/idea packets tied to Equilibrium value."""
        options = []
        if self.personality == "curious":
            options.append({"type": "idea_trade", "tag": random.choice(["quantum", "neural", "bio"]),
                            "boost": 0.05 + abs(equilibrium_val) * 0.1})
        elif self.personality == "cautious":
            if equilibrium_val > -0.3:
                options.append({"type": "knowledge_share", "tag": random.choice(["energy", "nano", "optics"]),
                                "boost": 0.03})
            else:
                options.append({"type": "warning", "message": "The balance tips too far..."})
        elif self.personality == "chaotic":
            options.append({"type": "wild_card", "tag": random.choice(["plasma", "gravity", "cyber"]),
                            "boost": random.uniform(-0.1, 0.2)})

        return options


class Resident:
    """A former tourist or specialist who settled permanently at Moon 274."""
    def __init__(self, defn):
        self.name = defn["name"]
        self.personality = defn["personality"]
        self.specialty = defn["specialty"]
        self.bonus = defn["bonus"]         # dict: action_type -> difficulty reduction
        self.maintenance = defn["maintenance"]
        self.desc = defn["desc"]

    def get_bonus(self, action_type):
        """Return difficulty reduction for this action type (0 if no bonus)."""
        return self.bonus.get(action_type, 0.0)


class TouristEmissaries:
    def __init__(self):
        self.tourists = [Tourist(d) for d in TOURIST_DEFS]
        self.residents = []  # Resident objects
        self._resident_pool = list(RESIDENT_DEFS)  # available to recruit
        random.shuffle(self._resident_pool)
        self.events = []

    def move_and_interact(self, game_state):
        """Move all tourists, generate interactions if at Moon 274."""
        self.events = []
        eq_val = game_state.get("equilibrium", 0.0)
        leisure_mult = game_state.get("leisure_tourist_mult", 1.0)
        extended_stay = game_state.get("leisure_extended_stay", False)
        interactions = []

        for t in self.tourists:
            old_pos = t.position

            # Extended stay: if tourist is at Moon 274, chance to linger
            if extended_stay and old_pos == 274 and random.random() < 0.35:
                self.events.append(f"TOURIST: {t.name} extends stay at Moon 274")
                options = t.interaction_options(eq_val)
                for opt in options:
                    if opt["type"] == "warning":
                        self.events.append(f"  {t.name}: \"{opt['message']}\"")
                    else:
                        self.events.append(f"  {t.name} offers {opt['type']} ({opt.get('tag', '?')})")
                interactions.extend(options)
                continue  # skip movement

            t.move_tick()
            # When generating new routes, use leisure weight
            if t.route_idx == 0:  # just started a new route
                t.route = _random_route(t.position, moon274_weight=leisure_mult)
                t.position = t.route[0]

            if t.position == 274:
                self.events.append(f"TOURIST: {t.name} arrives at Moon 274!")
                options = t.interaction_options(eq_val)
                for opt in options:
                    if opt["type"] == "warning":
                        self.events.append(f"  {t.name}: \"{opt['message']}\"")
                    else:
                        self.events.append(f"  {t.name} offers {opt['type']} ({opt.get('tag', '?')})")
                interactions.extend(options)
            elif old_pos == 274:
                self.events.append(f"TOURIST: {t.name} departs Moon 274 -> Moon {t.position}")

        return self.events, interactions

    def get_synergy_bonus(self, action_type):
        """Total difficulty reduction from tourists at Moon 274 + residents."""
        bonus = 0.0
        # Visiting tourists
        for t in self.tourists:
            if t.at_player_moon():
                synergy = TOURIST_SYNERGY.get(t.personality, {})
                bonus += synergy.get(action_type, 0.0)
        # Permanent residents
        for r in self.residents:
            bonus += r.get_bonus(action_type)
        return bonus

    def get_synergy_sources(self, action_type):
        """Return list of (name, bonus) for an action — for SIMULATE display."""
        sources = []
        for t in self.tourists:
            if t.at_player_moon():
                synergy = TOURIST_SYNERGY.get(t.personality, {})
                b = synergy.get(action_type, 0.0)
                if b > 0:
                    sources.append((f"{t.name} (visiting)", b))
        for r in self.residents:
            b = r.get_bonus(action_type)
            if b > 0:
                sources.append((f"{r.name} (resident)", b))
        return sources

    def get_resident_maintenance(self):
        """Total per-tick maintenance cost for all residents."""
        return sum(r.maintenance for r in self.residents)

    def maybe_offer_resident(self):
        """Check if a new resident can be offered. Returns Resident defn or None."""
        if not self._resident_pool:
            return None
        if len(self.residents) >= 3:  # cap at 3 residents
            return None
        return self._resident_pool[0]  # peek at next available

    def recruit_resident(self):
        """Recruit the next available resident. Returns (Resident, events) or (None, events)."""
        events = []
        if not self._resident_pool:
            events.append("No residents available to recruit.")
            return None, events
        if len(self.residents) >= 3:
            events.append("Moon 274 is at resident capacity (max 3).")
            return None, events
        defn = self._resident_pool.pop(0)
        resident = Resident(defn)
        self.residents.append(resident)
        events.append(f"RESIDENT: {resident.name} settles at Moon 274!")
        events.append(f"  Specialty: {resident.desc}")
        events.append(f"  Maintenance: {resident.maintenance:.1f}/tick")
        for action, bonus in resident.bonus.items():
            events.append(f"  {action}: -{bonus:.0%} difficulty")
        return resident, events

    def get_status(self):
        return [(t.name, t.position, t.personality) for t in self.tourists]

    def get_positions(self):
        return [(t.name, t.position) for t in self.tourists]

    def get_routes(self):
        return [t.route for t in self.tourists]

    def get_resident_summary(self):
        """Summary lines for STATUS display."""
        lines = []
        for r in self.residents:
            bonuses = ", ".join(f"{a}:-{b:.0%}" for a, b in r.bonus.items())
            lines.append(f"  {r.name:<14} {r.desc[:30]}  ({bonuses})")
        if not self.residents:
            lines.append("  (none — BUILD LEISURE to attract candidates)")
        return lines
