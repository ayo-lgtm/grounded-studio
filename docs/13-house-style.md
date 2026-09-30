# 13 — House style

Quality lives in two renderers. Skills pick a story and a layout id. They do not pick the chrome.

## Tokens

`apps/engine/grounded/house.py` is the only place that sets paper, ink, accent, type, and the caption bar.

| Token | Value | Use |
|---|---|---|
| Paper | `#f3f0e8` | Slide ground |
| Ink | `#1a1814` | Titles and figures |
| Accent | `#1d3c34` | Eyebrows and positive delta |
| Negative | `#7a2e2e` | A down delta and the risk eyebrow |
| Title face | Georgia | Action titles and big numbers |
| UI face | Segoe UI | Eyebrows, table labels, footer |

A beat that carries `style`, `color`, `font`, `css`, `theme`, or `background` fails QA.

## Deck masters

`cover`, `big-number`, `versus-target`, `movers`, `risk`, `ask`, `statement`, `step`.

`weekly-ops-review` may use the first six. Leadership adds `statement` and does not use the numeric masters. Launch uses `cover`, `statement`, and `ask`.

Workbook sentences are built from cited cells. Document sentences are copied. An empty required KPI never becomes a slide.

## Recording editor

`product-walkthrough`, `sop-training`, and `feature-delta` share it.

The compiler drops filler (`um`, `uh`) and leaves gaps out of the cut list. It keeps the original timestamps so the editor can cut a source file. A chapter card names the screen. Captions are the spoken line, burned on after the cut. A click zooms the source pixels. Pass `source_video` to `render_edit` when the recording is a real file. With no file, the studio paints a source from the screen labels and then cuts that.

## Run

```bash
PYTHONPATH=apps/engine python -m grounded.demo out/demo
```

`out/demo/index.html` is the scorecard. Arrow keys move through each deck.
