# craft: refine-loop
version: 1.0.0
offline: true
used_by: offline-refine-loop

job: Map a gate finding to one local fix.

rules:
  - carry-hold, recaption, trim, duck, or fail-closed. Nothing else.
  - fail-closed is the fix for an empty number.
  - Run the gate again after the fix. Do not loop into a generator.

forbidden:
  - any external HTTP API, cloud render, or cloud model
  - public internet egress
  - inventing a value to clear a fail
