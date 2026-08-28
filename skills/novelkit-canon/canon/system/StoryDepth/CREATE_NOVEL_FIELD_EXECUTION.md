# CREATE NOVEL Field Execution Contract

Purpose: every field selected in CREATE NOVEL must become observable story behavior. Agents must not treat these fields as labels, tags, or decorative summary.

## Required Field Execution

- **MC Archetype:** must appear as a decision pattern under pressure. Show what the protagonist chooses, what cost they accept, and what they refuse.
- **Hook Strategy:** must shape chapter opening, mid-chapter turn, and end beat. Rotate hook surface so the same trick does not repeat for 3 chapters.
- **style_model:** must shape sentence rhythm, imagery, dialogue pressure, taboo list, and prose density. It is not enough to name the author/style code.
- **worldbuilding_guide:** must surface as a rule of resources, hierarchy, geography, history, faction behavior, economy, or survival pressure inside scene action.
- **World frame:** must constrain character choices. The setting should create pressure, not sit behind the plot as scenery.

## Outline Contract

Every chapter outline should include a `dna_execution` block:

```yaml
dna_execution:
  mc_archetype_action: ...
  hook_used: ...
  style_cues: ...
  worldbuilding_rule: ...
  world_frame_pressure: ...
  micro_payoff: ...
  watch_flags: []
```

## Review Gate

Reviewer must audit these 5 fields: MC Archetype, Hook Strategy, style_model, worldbuilding_guide, world frame.

- 0 weak fields: PASS or PASS_WITH_FLAGS for unrelated minor issues.
- 1 weak field: PASS_WITH_FLAGS and write a concrete watch flag.
- 2 weak fields: SOFT_FAIL_STYLE.
- 3 weak fields: HARD_FAIL_DEPTH.
- Same surface-level weakness repeated for 3 chapters: HARD_FAIL_DEPTH.

## Sync Feedback

Sync must preserve these fields in memory/RAG feedback:

- `hook_used`
- `surface_conflict`
- `mc_archetype_action`
- `worldbuilding_rule`
- `payoff_level`
- `watch_flags`

Do not write technical metadata into the chapter prose artifact.
