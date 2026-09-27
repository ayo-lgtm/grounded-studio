# craft: vision-read-screen
version: 1.0.0
source: Anionex/agent-vision-toolkit
used_by: walkthrough compile, video-edit zoom, screenshot sheets

tools: glance, ground, detect, crop, long_ocr, pixel_diff, html_shot
Run on the worker against local files. If glance names a control detect cannot find, drop it from the script.
