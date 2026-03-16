"""Timed proposals (comms from rivals/tourists) and bounties from anonymous moons."""
import random

# ── Proposal types ──────────────────────────────────────────────────
# Each proposal has: sender, text, timer, accept/deny effects

BOUNTY_TEMPLATES = [
    {
        "action": "heist",
        "text": "BOUNTY: Acquire black-market tech from {target}",
        "reward": (30, 60),
        "eq_action": "heist",
    },
    {
        "action": "eavesdrop",
        "text": "BOUNTY: Intercept comms from {target}",
        "reward": (20, 40),
        "eq_action": "eavesdrop",
    },
    {
        "action": "sabotage",
        "text": "BOUNTY: Disrupt {target}'s supply chain",
        "reward": (40, 80),
        "eq_action": "sabotage",
    },
    {
        "action": "trade",
        "text": "BOUNTY: Broker a trade deal with {target}",
        "reward": (15, 35),
        "eq_action": "trade",
    },
    {
        "action": "research",
        "text": "BOUNTY: Deliver research data on '{tag}'",
        "reward": (20, 45),
        "eq_action": "research",
    },
    {
        "action": "diplomacy",
        "text": "BOUNTY: Negotiate ceasefire with {target}",
        "reward": (25, 50),
        "eq_action": "diplomacy",
    },
]

PROPOSAL_TIMEOUT = 5  # ticks before proposal expires


class Proposal:
    """A timed message requiring RESPOND ACCEPT/DENY."""

    __slots__ = ("id", "sender", "text", "timer", "accept_fn", "deny_fn",
                 "ignore_fn", "category", "expired", "responded")

    _next_id = 1

    def __init__(self, sender, text, timer, accept_fn, deny_fn, ignore_fn=None,
                 category="proposal"):
        self.id = Proposal._next_id
        Proposal._next_id += 1
        self.sender = sender
        self.text = text
        self.timer = timer
        self.accept_fn = accept_fn    # fn(player, equilibrium) -> list[str]
        self.deny_fn = deny_fn        # fn(player, equilibrium) -> list[str]
        self.ignore_fn = ignore_fn    # fn(player, equilibrium) -> list[str] (on timeout)
        self.category = category      # "proposal" or "bounty"
        self.expired = False
        self.responded = False

    def tick(self):
        """Decrement timer. Returns True if just expired."""
        if self.responded or self.expired:
            return False
        self.timer -= 1
        if self.timer <= 0:
            self.expired = True
            return True
        return False


class Bounty:
    """A bounty from an anonymous moon — complete the action for a reward."""

    __slots__ = ("id", "source_moon", "text", "action_required", "target_name",
                 "reward", "timer", "completed", "expired", "tag")

    _next_id = 1

    def __init__(self, source_moon, text, action_required, target_name, reward,
                 timer=15, tag=None):
        self.id = Bounty._next_id
        Bounty._next_id += 1
        self.source_moon = source_moon
        self.text = text
        self.action_required = action_required  # e.g., "heist"
        self.target_name = target_name          # rival name or None
        self.reward = reward
        self.timer = timer
        self.completed = False
        self.expired = False
        self.tag = tag  # for research bounties

    def tick(self):
        """Decrement timer. Returns True if just expired."""
        if self.completed or self.expired:
            return False
        self.timer -= 1
        if self.timer <= 0:
            self.expired = True
            return True
        return False

    def check_completion(self, action_type, target_rival_name=None):
        """Check if a player action completes this bounty."""
        if self.completed or self.expired:
            return False
        if action_type != self.action_required:
            return False
        if self.target_name and target_rival_name:
            # Fuzzy match
            if self.target_name.upper() not in target_rival_name.upper():
                return False
        return True


class CommsQueue:
    """Manages active proposals and bounties. Max 2 proposals + 1 bounty at a time."""

    MAX_PROPOSALS = 2
    MAX_BOUNTIES = 1

    def __init__(self):
        self.proposals = []        # active Proposal objects
        self.bounties = []         # active Bounty objects
        self.completed_bounties = 0
        self.ignored_proposals = 0
        self._cooldown = 0         # ticks until next proposal can spawn

    def add_proposal(self, proposal):
        """Add a proposal if under the cap."""
        active = [p for p in self.proposals if not p.expired and not p.responded]
        if len(active) >= self.MAX_PROPOSALS:
            return False
        self.proposals.append(proposal)
        return True

    def add_bounty(self, bounty):
        """Add a bounty if under the cap."""
        active = [b for b in self.bounties if not b.expired and not b.completed]
        if len(active) >= self.MAX_BOUNTIES:
            return False
        self.bounties.append(bounty)
        return True

    def get_active_proposal(self):
        """Get the oldest active proposal (for RESPOND)."""
        for p in self.proposals:
            if not p.expired and not p.responded:
                return p
        return None

    def get_active_proposals(self):
        """All active proposals."""
        return [p for p in self.proposals if not p.expired and not p.responded]

    def get_active_bounties(self):
        """All active bounties."""
        return [b for b in self.bounties if not b.expired and not b.completed]

    def respond(self, accept, player, equilibrium):
        """Respond to the oldest active proposal. Returns (events, proposal_or_None)."""
        p = self.get_active_proposal()
        if not p:
            return ["No active proposals to respond to."], None

        p.responded = True
        if accept:
            events = p.accept_fn(player, equilibrium)
        else:
            events = p.deny_fn(player, equilibrium)
        return events, p

    def check_bounty_completion(self, action_type, target_rival_name, player):
        """Check if any active bounty is completed by this action."""
        events = []
        for b in self.bounties:
            if b.check_completion(action_type, target_rival_name):
                b.completed = True
                self.completed_bounties += 1
                player.resources += b.reward
                events.append(f"BOUNTY COMPLETE: {b.text}")
                events.append(f"  Reward: +{b.reward} resources from Node C{b.source_moon}")
        return events

    def tick(self, player, equilibrium):
        """Tick all proposals and bounties. Returns events for expirations."""
        events = []

        for p in self.proposals:
            if p.tick():  # just expired
                self.ignored_proposals += 1
                if p.ignore_fn:
                    events.extend(p.ignore_fn(player, equilibrium))
                else:
                    events.append(f"COMMS: Proposal from {p.sender} expired (ignored).")

        for b in self.bounties:
            if b.tick():  # just expired
                events.append(f"BOUNTY EXPIRED: {b.text} — Node C{b.source_moon} withdraws.")

        # Cleanup old entries
        self.proposals = [p for p in self.proposals
                          if not (p.expired or p.responded) or
                          (p.expired and p.timer > -5) or
                          (p.responded and p.timer > -5)]
        self.bounties = [b for b in self.bounties
                         if not (b.expired or b.completed) or
                         (b.expired and b.timer > -5) or
                         (b.completed and b.timer > -5)]

        self._cooldown = max(0, self._cooldown - 1)
        return events

    def can_spawn(self):
        return self._cooldown <= 0

    def set_cooldown(self, ticks):
        self._cooldown = ticks


# ── Proposal generators ────────────────────────────────────────────

def generate_rival_proposal(rival, player, equilibrium):
    """Maybe generate a proposal from a rival based on game state."""
    proposals = []

    conn = player.connections.get(rival.name)

    # Trade offer: diplomatic rivals with decent reputation
    if rival.diplomatic > 0.4 and rival.reputation > -0.1:
        def accept_trade(p, eq):
            profit = 10 + random.uniform(5, 15)
            p.resources += profit
            if conn:
                conn.trust = min(1.0, conn.trust + 0.1)
                if not conn.open_trade:
                    conn.open_trade = True
            rival.reputation += 0.05
            return [f"  Trade accepted with {rival.name}: +{profit:.0f} resources.",
                    f"  Trade line opened. Relations improved."]

        def deny_trade(p, eq):
            rival.reputation -= 0.03
            return [f"  Trade offer from {rival.name} declined.",
                    f"  {rival.name} is mildly insulted."]

        def ignore_trade(p, eq):
            rival.reputation -= 0.05
            return [f"  COMMS: {rival.name}'s trade offer ignored. They won't forget."]

        proposals.append(Proposal(
            sender=rival.name,
            text=f"{rival.name} proposes trade partnership",
            timer=PROPOSAL_TIMEOUT,
            accept_fn=accept_trade,
            deny_fn=deny_trade,
            ignore_fn=ignore_trade,
            category="proposal",
        ))

    # Threat: aggressive rival with grudge
    if conn and conn.grudge_ticks > 5 and rival.aggressive > 0.5:
        tribute = int(15 + rival.aggressive * 20)

        def accept_tribute(p, eq):
            p.resources -= tribute
            rival.reputation += 0.1
            if conn:
                conn.grudge_ticks = max(0, conn.grudge_ticks - 10)
            return [f"  Paid {tribute} tribute to {rival.name}.",
                    f"  Grudge reduced. Resources lost."]

        def deny_tribute(p, eq):
            # They'll heist you next tick
            rival.last_action = "heist"
            return [f"  Tribute refused! {rival.name} prepares to strike.",
                    f"  Expect a raid next tick."]

        def ignore_tribute(p, eq):
            rival.last_action = "heist"
            rival.reputation -= 0.05
            return [f"  COMMS: {rival.name}'s demand ignored. They're coming for you."]

        proposals.append(Proposal(
            sender=rival.name,
            text=f"{rival.name} demands {tribute} tribute — or else",
            timer=3,  # urgent!
            accept_fn=accept_tribute,
            deny_fn=deny_tribute,
            ignore_fn=ignore_tribute,
            category="proposal",
        ))

    # Peace offer: grudge expiring
    if conn and conn.grudge_ticks == 1 and rival.diplomatic > 0.2:
        def accept_peace(p, eq):
            rival.reputation = max(rival.reputation, 0.0)
            if conn:
                conn.grudge_ticks = 0
                conn.trust = 0.0
            eq.action_impact("diplomacy")
            return [f"  Peace established with {rival.name}.",
                    f"  Trust reset. Equilibrium shifts positive."]

        def deny_peace(p, eq):
            if conn:
                conn.grudge_ticks = 15  # renews!
            rival.reputation -= 0.1
            return [f"  Peace rejected! {rival.name} renews hostilities.",
                    f"  Grudge extended 15 ticks."]

        proposals.append(Proposal(
            sender=rival.name,
            text=f"{rival.name} offers ceasefire — bury the hatchet?",
            timer=PROPOSAL_TIMEOUT,
            accept_fn=accept_peace,
            deny_fn=deny_peace,
            category="proposal",
        ))

    return proposals


def generate_tourist_proposal(tourist, equilibrium_val):
    """Maybe generate a proposal from a tourist at Moon 274."""
    if not tourist.at_player_moon():
        return None

    tag = random.choice(["quantum", "neural", "bio", "energy", "nano",
                         "cyber", "plasma", "optics"])

    def accept_deal(p, eq):
        eq.action_impact("trade_idea")
        return [f"  {tourist.name} shares {tag} insights.",
                f"  Lattice injection + equilibrium shift."]

    def deny_deal(p, eq):
        return [f"  {tourist.name} shrugs and moves on."]

    def ignore_deal(p, eq):
        return [f"  COMMS: {tourist.name} left before you responded. Opportunity lost."]

    return Proposal(
        sender=tourist.name,
        text=f"{tourist.name} offers {tag} knowledge exchange",
        timer=2,  # tourists are fleeting
        accept_fn=accept_deal,
        deny_fn=deny_deal,
        ignore_fn=ignore_deal,
        category="proposal",
    )


def generate_bounty(rivals, lattice, tick):
    """Generate a bounty from an anonymous outer moon."""
    template = random.choice(BOUNTY_TEMPLATES)
    source_moon = random.randint(1, 273)
    target_rival = random.choice(rivals.rivals)
    reward = random.randint(*template["reward"])
    tag = None

    if template["action"] == "research":
        tags = list(lattice.get_tags().keys())
        tag = random.choice(tags) if tags else "quantum"
        text = template["text"].format(target=target_rival.name, tag=tag)
    else:
        text = template["text"].format(target=target_rival.name)

    # Timer scales with difficulty
    timer = 12 if template["action"] in ("heist", "sabotage") else 18

    return Bounty(
        source_moon=source_moon,
        text=text,
        action_required=template["action"],
        target_name=target_rival.name,
        reward=reward,
        timer=timer,
        tag=tag,
    )
