import random

GOODS = [
    {"name": "Neural-Lace",      "base": 1200, "tags": ["neural", "cyber"]},
    {"name": "Quantum Core",     "base": 2500, "tags": ["quantum", "energy"]},
    {"name": "Carbon Mesh",      "base": 300,  "tags": ["carbon", "nano"]},
    {"name": "Plasma Coil",      "base": 800,  "tags": ["plasma", "energy"]},
    {"name": "Bio-Gel",          "base": 450,  "tags": ["bio", "nano"]},
    {"name": "Optic Fiber",      "base": 150,  "tags": ["optics", "cyber"]},
    {"name": "Grav Stabilizer",  "base": 3000, "tags": ["gravity", "energy"]},
    {"name": "Nano Paste",       "base": 200,  "tags": ["nano", "carbon"]},
    {"name": "Synth Protein",    "base": 350,  "tags": ["bio", "carbon"]},
    {"name": "Cyber Module",     "base": 600,  "tags": ["cyber", "quantum"]},
]


class MarketSim:
    def __init__(self):
        self.goods = []
        for g in GOODS:
            self.goods.append({
                "name": g["name"],
                "base": g["base"],
                "tags": g["tags"],
                "price": float(g["base"]),
                "supply": 1.0,
                "demand": 1.0,
            })
        self.prices = {}
        self.events = []
        self._snapshot_prices()

    def _snapshot_prices(self):
        self.prices = {g["name"]: round(g["price"], 1) for g in self.goods}

    def monte_carlo_tick(self, tag_weights, golden_ages):
        """Roll supply/demand with Gaussian noise, modified by Lattice state."""
        self.events = []
        for g in self.goods:
            # Base Gaussian supply/demand shifts
            supply_shift = random.gauss(0, 0.05)
            demand_shift = random.gauss(0, 0.05)

            # Lattice tag influence: high tag weight -> more demand
            tag_pull = 0.0
            for t in g["tags"]:
                tag_pull += tag_weights.get(t, 0)
            # Normalize: tag_pull typically 0-500 range, map to small modifier
            demand_shift += tag_pull * 0.00005

            # Golden Age boost: +200% demand for matching tags
            for t in g["tags"]:
                if t in golden_ages:
                    demand_shift += 0.15
                    if random.random() < 0.1:
                        self.events.append(f"  BOOM: {g['name']} demand surges ('{t}' Golden Age)")

            # Mean-revert toward 1.0 so prices don't just inflate
            g["supply"] += (1.0 - g["supply"]) * 0.05 + supply_shift
            g["demand"] += (1.0 - g["demand"]) * 0.05 + demand_shift
            g["supply"] = max(0.3, min(2.0, g["supply"]))
            g["demand"] = max(0.3, min(3.0, g["demand"]))

            # Price = base * (demand / supply) with some noise
            ratio = g["demand"] / g["supply"]
            noise = random.gauss(1.0, 0.02)
            g["price"] = g["base"] * ratio * noise
            g["price"] = max(g["base"] * 0.2, min(g["base"] * 5.0, g["price"]))

        self._snapshot_prices()
        return self.events

    def update(self, tag_weights, golden_ages):
        return self.monte_carlo_tick(tag_weights, golden_ages)

    def get_prices(self):
        return dict(self.prices)
