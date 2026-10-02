# craft: placement-formats
version: 1.0.0
offline: true
used_by: placement-formats-export

job: Fit a master into 16:9, 9:16, and 1:1 with a safe zone.

rules:
  - Contain, then pad. Do not crop a cited control out of frame.
  - Pad with the house theater color.
  - The filter string is the deliverable until an operator renders it locally.

forbidden:
  - any external HTTP API or hosted resizer
  - public internet egress
  - a generated background
