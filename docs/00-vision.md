# 00 — Vision

## Problem

Knowledge work produces the same artifacts over and over:

1. **Product demo** — someone clicks through a tool and talks. Next month the UI is the same, the talk is recorded again.
2. **Weekly report** — a manager walks leadership through an Excel pack. The template is stable. Only the numbers change.
3. **Launch / announcement / leadership briefing** — a Word doc already contains the argument. Someone still rebuilds PowerPoint and reads it aloud, then repeats it in another language.

Generic AI video tools fail two ways at work:

- they send the file to a third party
- they invent pictures, buttons, and numbers

## Product

Grounded Studio is an **internal communication compiler**.

```
source of truth  →  skill  →  briefing object  →  many outputs
```

Sources of truth:

- screen recording (+ optional rough voice)
- workbook (xlsx/csv + named ranges)
- document (docx/pdf/markdown)

Outputs from one object:

- chaptered narrated video (real UI or real charts, never redrawn fiction)
- HTML slide deck
- written guide
- grounded chat that can jump to `t=02:14` or cell `KPI!B12`
- translated sibling object (same citations, new language)

## Design principles

1. **Truth over cinema.** Show the real screen or the real sheet.
2. **Cite or cut.** Every claim has a pointer into a source.
3. **Recurring by default.** Save the skill instance (“Acme onboarding v3”, “Monday exec pack”). Next week you swap the file or recording, not the story.
4. **Skills, not one model.** The router picks a playbook. Quality comes from the playbook, not from a bigger video model.
5. **Data never egresses.** Inference, storage, and rendering stay on-network.
6. **Human ships it.** AI drafts. A person accepts. Nothing customer-facing or leadership-facing auto-publishes.

## Who it is for (job-internal)

| User | Job |
|---|---|
| Product owner / PM | Stop re-recording the same walkthrough |
| Enablement / CS | Training that stays true to the current UI |
| Operator / finance / bizops | Monday pack without rebuilding slides |
| Founder / lead | Launch or leadership note from a written doc, including other languages |
| Security / IT | Approve a tool that does not phone home |

## What this is not

- Not BookWatch. We do not generate whiteboard movies of books or of spreadsheets.
- Not `/brag`. A 20-second launch teaser can be a later skill. It is not v1.
- Not Gamma. We do not invent a deck from a one-line prompt.
- Not a browser agent that guesses a demo from the GitHub repo.
- Not an air-gapped replacement for Figma or Premiere.

## Success

A teammate who today spends two hours on a recurring briefing spends fifteen minutes: drop source, pick skill, review citations, publish internally.

If a number or button in the output cannot be traced to the upload, the build failed — even if the video looks expensive.
