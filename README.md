# Moon274

The prototype is a single-loop game: every "tick" (simulated in-game hour), the engines update sequentially and feed into each other. Player input happens via terminal commands during pauses.Core Loop (in main.py):
While running:  Update background engines (Lattice → Economy → Rivals/Tourists).  
Render UI (terminal log, orbital map, side panels).  
Handle player input (parse commands, execute actions, update Equilibrium).  
Check for events (Golden Ages, rebalancing, game over).
Tick advances on command or timer.

Key Engines/Toolkits (each a Python class):  KnowledgeLattice: Simulates core AGI tech progress. Outputs: active Golden Ages, Paradigm Shifts, dominant tags. Injects player "chaos" from actions.  
MarketSim: Monte Carlo economy for ~10 goods. Hooks: Lattice state modifies supply/demand rolls.  
RivalMoons: 4–6 instances with personality vectors. Decisions: heist, trade, react to player/Equilibrium.  
TouristEmissaries: 3–5 mobile agents with routes. Interactions: idea trades, SIMULATE boosts.  
VarianceEquilibrium: Tracks -1.0 to +1.0 meter. Weights actions, triggers warnings/rewards.  
UIConsole: Handles terminal input/output, map rendering (Pygame surfaces), panels.

Data flow: All engines communicate via shared state (e.g., a global "game_state" dict with tags, prices, reputation). Emergence comes from hooks like lattice.inject_chaos(action_tags) → market rolls variance up → rivals react.

## Tech "tree"/Knowledge Lattice

Core PhilosophyNo fixed tech tree — real scientific progress is incremental, path-dependent, noisy, and combinatorial.
Progress feels emergent from empire choices rather than a scripted unlock ladder.
Specialization is powerful but self-limiting (hammer-and-nail problem).
The singularity emerges as an acceleration curve, not a button press.

Data Structure: The Knowledge LatticeEvery technology is a node containing:Name + flavor text
3–5 knowledge tags (e.g., quantum, carbon-based, self-replicating, neural, energy-density)
Maturity level (0–100 %): theoretical → prototype → industrial → fully exploitable
Unlocks (units, buildings, bonuses, gameplay layers) that trigger at maturity thresholds

Starts with ~300 hand-authored seed nodes (21st–23rd century plausible techs)
Procedural generator creates new nodes on-the-fly from existing tag combinations

Research Mechanics (turn-by-turn)Player allocates research points into 6–8 broad domains (Physics, Information, Biology, Materials, Energy, Cognition, Macro-engineering)
Each domain accumulates expertise (floating-point value)
Every turn: discovery rolls per domainBase chance scales with expertise + global multipliers
Heavily biased by current tag distribution (path-dependency)
Small true randomness + cross-domain synergy bonuses

Breakthrough → node added at low maturity (~15 %)Injects its tags into global tag cloud → shifts future probabilities

Maturity grows automatically if domain keeps receiving funding (diminishing returns curve)

Incrementalism & Realism FeaturesAutomatic maturity gain per turn when funding continues
"Focus" mechanic to accelerate specific nodes (great scientist style)
Failed rolls give partial progress or "negative knowledge" (rules out dead ends → future bonus)
Expertise decay if domain is neglected (scientists get stale)

Hammer-and-Nail (Specialization Trap) SolutionsStrong diminishing returns when >40 % budget in one domain
Expertise decays when unfunded
Interdisciplinary bonus rolls when multiple domains funded simultaneously
Named scientist agents with specialties refuse distant domains without penalty

Golden Ages (Wave-Riding Byproduct Explosions)Trigger: foundational node reaches ~70–95 % maturity
Temporary multiplier (25–60 turns) on related nodes/tags+150–400 % discovery chance
2–5× maturity growth

Instant byproduct nodes seeded at low maturity (e.g., AI Golden Age → neural prosthetics, swarm robotics, etc.)
Decay + plateau event at end
Multiple overlapping Golden Ages accelerate everything dramatically

Paradigm Shifts (Game-Rule-Changing Moments)Detected automatically when node meets criteria:High maturity on foundational or novel-tag node
Obsoletes >25 % of current assets
Unlocks new gameplay layer + ≥35 % permanent empire multiplier

Triggers cinematic event, new domain/layer, permanent modifiers, obsolescence wave
Procedural shifts possible late-game when new tag category dominates

Singularity DynamicsGlobal research multiplier grows with total tags + average maturity
Parabolic acceleration once ~400 tags and ~60 % maturity
Chaining breakthroughs + faster procedural generation
"Pre-singularity" phase: AI proposes projects faster than player can review
Feels like gradual "holy crap it's speeding up" — only obvious in hindsight

Player-Facing FeelBroad domain investment choices (not micromanaging every tech)
Lattice Map visualization: force-directed graph of tag clusters/gaps
Serendipity events (rare lab accidents granting low-probability nodes)
Culture/ethics sliders bias tag probabilities
Memorable historical eras emerge naturally (e.g., "Age of Aviation", "Age of Mind")

This system produces genuinely different tech histories every playthrough, rewards dynamic portfolio management, avoids both pure randomness and rigid trees, and lets the singularity sneak up on the player — exactly as it would in reality.In Moon 274 context, this entire Lattice runs silently in the background as the "gods" simulation, with player moon actions only injecting small chaos perturbations that can (rarely) snowball into distant Golden Ages or Paradigm Shifts felt as market crashes / demand spikes.

Core PhilosophyNo fixed tech tree — real scientific progress is incremental, path-dependent, noisy, and combinatorial.
Progress feels emergent from empire choices rather than a scripted unlock ladder.
Specialization is powerful but self-limiting (hammer-and-nail problem).
The singularity emerges as an acceleration curve, not a button press.

Data Structure: The Knowledge LatticeEvery technology is a node containing:Name + flavor text
3–5 knowledge tags (e.g., quantum, carbon-based, self-replicating, neural, energy-density)
Maturity level (0–100 %): theoretical → prototype → industrial → fully exploitable
Unlocks (units, buildings, bonuses, gameplay layers) that trigger at maturity thresholds

Starts with ~300 hand-authored seed nodes (21st–23rd century plausible techs)
Procedural generator creates new nodes on-the-fly from existing tag combinations

Research Mechanics (turn-by-turn)Player allocates research points into 6–8 broad domains (Physics, Information, Biology, Materials, Energy, Cognition, Macro-engineering)
Each domain accumulates expertise (floating-point value)
Every turn: discovery rolls per domainBase chance scales with expertise + global multipliers
Heavily biased by current tag distribution (path-dependency)
Small true randomness + cross-domain synergy bonuses

Breakthrough → node added at low maturity (~15 %)Injects its tags into global tag cloud → shifts future probabilities

Maturity grows automatically if domain keeps receiving funding (diminishing returns curve)

Incrementalism & Realism FeaturesAutomatic maturity gain per turn when funding continues
"Focus" mechanic to accelerate specific nodes (great scientist style)
Failed rolls give partial progress or "negative knowledge" (rules out dead ends → future bonus)
Expertise decay if domain is neglected (scientists get stale)

Hammer-and-Nail (Specialization Trap) SolutionsStrong diminishing returns when >40 % budget in one domain
Expertise decays when unfunded
Interdisciplinary bonus rolls when multiple domains funded simultaneously
Named scientist agents with specialties refuse distant domains without penalty

Golden Ages (Wave-Riding Byproduct Explosions)Trigger: foundational node reaches ~70–95 % maturity
Temporary multiplier (25–60 turns) on related nodes/tags+150–400 % discovery chance
2–5× maturity growth

Instant byproduct nodes seeded at low maturity (e.g., AI Golden Age → neural prosthetics, swarm robotics, etc.)
Decay + plateau event at end
Multiple overlapping Golden Ages accelerate everything dramatically

Paradigm Shifts (Game-Rule-Changing Moments)Detected automatically when node meets criteria:High maturity on foundational or novel-tag node
Obsoletes >25 % of current assets
Unlocks new gameplay layer + ≥35 % permanent empire multiplier

Triggers cinematic event, new domain/layer, permanent modifiers, obsolescence wave
Procedural shifts possible late-game when new tag category dominates

Singularity DynamicsGlobal research multiplier grows with total tags + average maturity
Parabolic acceleration once ~400 tags and ~60 % maturity
Chaining breakthroughs + faster procedural generation
"Pre-singularity" phase: AI proposes projects faster than player can review
Feels like gradual "holy crap it's speeding up" — only obvious in hindsight

Player-Facing FeelBroad domain investment choices (not micromanaging every tech)
Lattice Map visualization: force-directed graph of tag clusters/gaps
Serendipity events (rare lab accidents granting low-probability nodes)
Culture/ethics sliders bias tag probabilities
Memorable historical eras emerge naturally (e.g., "Age of Aviation", "Age of Mind")

This system produces genuinely different tech histories every playthrough, rewards dynamic portfolio management, avoids both pure randomness and rigid trees, and lets the singularity sneak up on the player — exactly as it would in reality.In Moon 274 context, this entire Lattice runs silently in the background as the "gods" simulation, with player moon actions only injecting small chaos perturbations that can (rarely) snowball into distant Golden Ages or Paradigm Shifts felt as market crashes / demand spikes.

## Tasks: 
Bootstrap project: Create main.py, lattice.py, market.py. Init Pygame window (800x600, black bg with green text).  
Build KnowledgeLattice class: ~50 lines. Seed 20 nodes with tags/maturity. Add discovery_roll() (weighted by tags + random). Track Golden Ages (trigger at 70% maturity on flagged nodes).  
Build MarketSim class: ~60 lines. List 10 goods with base prices/tags. monte_carlo_tick(): Gaussian rolls for supply/demand, modified by Lattice (e.g., if "neural" Golden Age, +200% demand for neural-lace). Output prices to a dict.  
Hook them: In main loop, every tick: lattice.update() → market.update(lattice.get_tags()). Print prices and any shifts.  
Checkpoint: Run and watch prices twitch based on simulated Lattice progress. Commit to Git.

