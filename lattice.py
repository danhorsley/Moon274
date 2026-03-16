import random

TAGS = ["quantum", "neural", "carbon", "energy", "nano", "bio", "cyber", "plasma", "gravity", "optics"]

SEED_NODES = [
    ("Quantum Computing",       ["quantum", "cyber"]),
    ("Neural Interface",        ["neural", "cyber", "bio"]),
    ("Carbon Nanotubes",        ["carbon", "nano", "energy"]),
    ("Fusion Reactor",          ["energy", "plasma"]),
    ("Gene Editing",            ["bio", "nano"]),
    ("Photonic Chip",           ["optics", "cyber", "quantum"]),
    ("Plasma Shield",           ["plasma", "energy", "gravity"]),
    ("Nanobots",                ["nano", "bio", "cyber"]),
    ("Graviton Lens",           ["gravity", "optics"]),
    ("Synth Muscle",            ["bio", "carbon", "nano"]),
    ("Neural Lace",             ["neural", "nano", "cyber"]),
    ("Antimatter Cell",         ["energy", "quantum", "plasma"]),
    ("Bio-Processor",           ["bio", "cyber", "neural"]),
    ("Quantum Entangler",       ["quantum", "optics"]),
    ("Carbon Lattice Armor",    ["carbon", "nano"]),
    ("Plasma Drill",            ["plasma", "energy"]),
    ("Optical Brain",           ["optics", "neural", "cyber"]),
    ("Nanofiber Weave",         ["nano", "carbon"]),
    ("Gravity Engine",          ["gravity", "energy", "quantum"]),
    ("Cyber Cortex",            ["cyber", "neural", "quantum"]),
]

GOLDEN_AGE_THRESHOLD = 70
GOLDEN_AGE_FLAGGED = {"Neural Interface", "Fusion Reactor", "Quantum Computing",
                       "Neural Lace", "Gravity Engine", "Bio-Processor"}


class KnowledgeLattice:
    def __init__(self):
        self.nodes = {}
        for name, tags in SEED_NODES:
            self.nodes[name] = {
                "tags": tags,
                "maturity": random.uniform(5, 35),
                "flagged": name in GOLDEN_AGE_FLAGGED,
            }
        self.golden_ages = {}  # tag -> turns_remaining
        self.events = []       # log of recent events

    def get_tags(self):
        """Return dict of tag -> combined weight from all nodes."""
        tag_weights = {}
        for node in self.nodes.values():
            for t in node["tags"]:
                tag_weights[t] = tag_weights.get(t, 0) + node["maturity"]
        return tag_weights

    def get_active_golden_ages(self):
        return dict(self.golden_ages)

    def discovery_roll(self):
        """Attempt maturity gain on each node, weighted by tag presence."""
        tag_weights = self.get_tags()
        total_weight = max(sum(tag_weights.values()), 1)
        for name, node in self.nodes.items():
            tag_bonus = sum(tag_weights.get(t, 0) for t in node["tags"]) / total_weight
            ga_mult = 1.0
            for t in node["tags"]:
                if t in self.golden_ages:
                    ga_mult = max(ga_mult, 2.0)  # 2x during Golden Age (was 3x)
            roll = random.gauss(0.5, 0.3) * tag_bonus * ga_mult
            node["maturity"] = min(100, node["maturity"] + max(0, roll))

    def _check_golden_ages(self):
        for name, node in self.nodes.items():
            if not node["flagged"]:
                continue
            if node["maturity"] >= GOLDEN_AGE_THRESHOLD:
                for t in node["tags"]:
                    if t not in self.golden_ages:
                        self.golden_ages[t] = random.randint(25, 60)
                        self.events.append(f"GOLDEN AGE: '{t}' triggered by {name} ({node['maturity']:.0f}%)")

    def _decay_golden_ages(self):
        expired = [t for t, r in self.golden_ages.items() if r <= 0]
        for t in expired:
            del self.golden_ages[t]
            self.events.append(f"Golden Age ended: '{t}'")
        for t in self.golden_ages:
            self.golden_ages[t] -= 1

    def research_directed(self, tag, strength=3.0):
        """Directed research: push all nodes with this tag toward maturity.
        Returns list of event strings."""
        events = []
        if tag not in TAGS:
            events.append(f"Unknown research field: '{tag}'")
            return events

        pushed = 0
        for name, node in self.nodes.items():
            if tag in node["tags"]:
                boost = strength * random.uniform(0.8, 1.5)
                old = node["maturity"]
                node["maturity"] = min(100, node["maturity"] + boost)
                pushed += 1
                if node["maturity"] >= GOLDEN_AGE_THRESHOLD and old < GOLDEN_AGE_THRESHOLD:
                    events.append(f"BREAKTHROUGH: {name} hits {node['maturity']:.0f}%!")
                elif boost > 2.5:
                    events.append(f"RESEARCH: {name} +{boost:.1f}% ({node['maturity']:.0f}%)")

        events.insert(0, f"Research pushed '{tag}' across {pushed} nodes.")
        return events

    def get_tag_status(self, tag):
        """Get maturity info for a specific tag: avg maturity, closest to GA, etc."""
        nodes_with_tag = [(name, node) for name, node in self.nodes.items()
                          if tag in node["tags"]]
        if not nodes_with_tag:
            return None
        avg = sum(n["maturity"] for _, n in nodes_with_tag) / len(nodes_with_tag)
        closest = max(nodes_with_tag, key=lambda x: x[1]["maturity"])
        flagged = [(name, n) for name, n in nodes_with_tag if n["flagged"]]
        closest_flagged = max(flagged, key=lambda x: x[1]["maturity"]) if flagged else None
        return {
            "tag": tag,
            "node_count": len(nodes_with_tag),
            "avg_maturity": avg,
            "closest_name": closest[0],
            "closest_maturity": closest[1]["maturity"],
            "closest_flagged_name": closest_flagged[0] if closest_flagged else None,
            "closest_flagged_maturity": closest_flagged[1]["maturity"] if closest_flagged else None,
            "golden_age_active": tag in self.golden_ages,
            "golden_age_remaining": self.golden_ages.get(tag, 0),
        }

    def inject_chaos(self, tags, strength=2.0):
        """Player action injects tag-weighted maturity boost."""
        for name, node in self.nodes.items():
            overlap = sum(1 for t in node["tags"] if t in tags)
            if overlap > 0:
                boost = overlap * strength * random.uniform(0.5, 1.5)
                node["maturity"] = min(100, node["maturity"] + boost)
                if boost > 2.0:
                    self.events.append(f"LATTICE RIPPLE: {name} +{boost:.1f}% from chaos injection")

    def update(self):
        self.events = []
        self.discovery_roll()
        self._check_golden_ages()
        self._decay_golden_ages()
        return self.events
