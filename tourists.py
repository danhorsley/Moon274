import random

TOURIST_DEFS = [
    {"name": "Emissary Zael",  "origin": 42,  "personality": "curious"},
    {"name": "Sage Nomura",    "origin": 188, "personality": "cautious"},
    {"name": "Drift Kova",     "origin": 7,   "personality": "chaotic"},
]


def _random_route(origin, length=6):
    """Generate a route of moon IDs (1-274) starting from origin."""
    route = [origin]
    for _ in range(length):
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


class TouristEmissaries:
    def __init__(self):
        self.tourists = [Tourist(d) for d in TOURIST_DEFS]
        self.events = []

    def move_and_interact(self, game_state):
        """Move all tourists, generate interactions if at Moon 274."""
        self.events = []
        eq_val = game_state.get("equilibrium", 0.0)
        interactions = []

        for t in self.tourists:
            old_pos = t.position
            t.move_tick()
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

    def get_status(self):
        return [(t.name, t.position, t.personality) for t in self.tourists]

    def get_positions(self):
        return [(t.name, t.position) for t in self.tourists]

    def get_routes(self):
        return [t.route for t in self.tourists]
