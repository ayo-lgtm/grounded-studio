# craft: watch-footage
version: 1.0.0
source: diffusionstudio/skills watch
used_by: product-walkthrough, sop-training, grounded-qa

Answer what happens, where X occurs, pull a quote, list steps.
Prefer transcript timestamps. Sample frames at cuts and run vision-read-screen when the answer is visual.
Always return t_start_ms / t_end_ms.
