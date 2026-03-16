ACTION_IMPACTS = {
    "heist":          -0.15,
    "trade":           0.10,
    "protect":         0.10,
    "spy":            -0.08,
    "fortify":         0.05,
    "idea_trade":      0.05,
    "knowledge_share": 0.03,
    "wild_card":      -0.05,
    "trade_idea":      0.08,
    "eavesdrop":      -0.10,
    "sabotage":       -0.20,
    "diplomacy":       0.12,
    "smuggle":        -0.12,
    "research":        0.06,
    "broadcast":       0.04,
    "scavenge":       -0.06,
}

THRESHOLDS = [
    (-0.8, "CRITICAL: The Variance tears at reality..."),
    (-0.5, "WARNING: Wings itching? The balance is unstable."),
    (-0.3, "CAUTION: Equilibrium drifting negative."),
    ( 0.3, "NOTICE: Equilibrium holding positive."),
    ( 0.5, "HARMONY: The Variance hums with stability."),
    ( 0.8, "TRANSCEND: Near-perfect balance achieved."),
]


class VarianceEquilibrium:
    def __init__(self):
        self.value = 0.0       # -1.0 to +1.0
        self.events = []
        self._prev_bracket = None
        self.game_over = False
        self.game_over_msg = ""

    def action_impact(self, action_type):
        """Apply impact from an action."""
        delta = ACTION_IMPACTS.get(action_type, 0.0)
        self.value = max(-1.0, min(1.0, self.value + delta))

    def decay_tick(self):
        """Slowly decay toward 0."""
        self.value *= 0.97

    def get_variance_modifier(self):
        """Extreme values add variance penalty to all rolls."""
        extremity = abs(self.value)
        if extremity > 0.7:
            return 1.0 + (extremity - 0.7) * 3.0  # up to 1.9x variance
        return 1.0

    def update(self):
        """Check thresholds and game over, then decay. Returns event list."""
        self.events = []

        # Game over check BEFORE decay (at the raw extreme)
        if abs(self.value) >= 0.95:
            self.game_over = True
            if self.value <= -0.95:
                self.game_over_msg = "REINTEGRATED: The Variance consumed Moon 274. You are unmade."
            else:
                self.game_over_msg = "REINTEGRATED: Perfect order crystallized. You are frozen in harmony."
            self.events.append(self.game_over_msg)
            return self.events

        # Threshold warnings
        bracket = None
        for threshold, msg in THRESHOLDS:
            if threshold < 0 and self.value <= threshold:
                bracket = msg
            elif threshold > 0 and self.value >= threshold:
                bracket = msg

        if bracket and bracket != self._prev_bracket:
            self.events.append(bracket)
        self._prev_bracket = bracket

        self.decay_tick()
        return self.events
