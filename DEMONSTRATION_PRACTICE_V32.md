# v32 Demonstration Practice Crawler

This build turns manual/monitor learning into an active exploration seed, not just historical graph data.

## Behavior

When the operator teaches a path through Teacher Mode or manually drives the STB from `/monitor`, the transition is tagged as a demonstrated/customer-like path. The crawler now:

1. prioritizes states touched by demonstrations in the frontier,
2. prioritizes demonstrated outgoing actions when it revisits those states,
3. gives demonstrated actions a larger retry budget,
4. periodically rehearses high-value demonstrated paths in continuous mode,
5. branches from the reached waypoint to discover nearby features,
6. reports demonstration stats in `/api/crawl/status`.

This lets the app do the human-like thing: "Jake showed me how to get to On Demand purchase options, so I should prove that path still works, then explore the neighboring buttons/features from each waypoint."

## Config

```json
{
  "demo_practice_enabled": true,
  "demo_practice_sources": ["manual_teaching", "manual_teaching_fast", "operator_monitor_auto"],
  "demo_practice_frontier_bonus": 18.0,
  "demo_practice_action_bonus": 9.0,
  "demo_practice_action_budget_bonus": 3,
  "demo_practice_min_confidence": 0.15,
  "demo_practice_every_cycles": 1,
  "demo_practice_max_edges_per_cycle": 2,
  "demo_practice_neighbor_actions": 3
}
```

## Safety

Demonstrated `select` actions still pass through the crawler's normal risky-screen guardrails. PPV final confirmation still requires the PPV test configuration/confirmation flags.
