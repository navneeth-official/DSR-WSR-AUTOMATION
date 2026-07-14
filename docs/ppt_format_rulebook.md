# G10X WSR Delivery Status — PPT Format Rule Book

Machine-readable version: `app/constants/ppt_format_rulebook.json` (v1.1.0+)

---

## Layout principles (content-agnostic)

These rules apply to **every** service slide. They are **not** tied to named reference slides (Cost, Supplier, Wentworth, etc.). Box heights and continuation decisions scale with content volume.

### Dynamic sizing
- **Sparse content:** Shrink HL and KA gray boxes to rendered text + padding. White space at the bottom of the slide is valid.
- **Dense content:** Expand HL up to the column budget (footer safe zone).
- **Metrics:** `hl_waste_below_text_in`, `ka_waste_below_text_in`, `utilization_ratio`
- **Violations:** `HL-SIZE-01`, `KA-SIZE-01`, `CONT-SPARSE-01`

### HL ↔ KA spacing (when both on same slide)
- Stack: HL header → HL content → small buffer → KA header → KA content
- **Border gap:** `hl_ka_gap_in` between −0.12 and 0.28 in (borders may touch slightly)
- **Text clearance:** `text_ka_clearance_in` ≥ 0.15 in (text must not intrude into KA)
- **Violations:** `KA-PLC-01`, `KA-PLC-02`, `KA-OVERLAP-01`

### Footer boundary
- KA bottom ≤ **6.29 in** from slide top
- Dense HL-only main (utilization ≥ 85%, no KA on slide) may extend to **~6.55 in**
- **Violation:** `GEO-02`

### When to create `(Contd…)`
| Condition | Outcome |
|-----------|---------|
| HL + KA fit in footer zone with clearance | Both on main |
| HL sparse, room below text, KA fits | KA on main (`KA-PLC-04`) |
| HL dense, KA does not fit below HL | HL-only main + KA-only contd |
| HL exceeds main column | HL contd |
| Main &lt; 85% full but HL contd exists | Premature contd (`HL-UTIL-01`) |

### AI evaluation
The evaluator and repair loop use `layout_principles` in the rulebook JSON and extracted metrics only. They **never** pass/fail by matching inch heights to a named template slide.

---

## 1. Slide title

| Rule | Requirement |
|------|-------------|
| Format | `Delivery status – {Service Name}` |
| Continuation | `Delivery status – {Service Name} (Contd…)` |
| Font | **Manrope Bold 16pt** |
| Position | Top-left (~0.46 in from top/left) |

---

## 2. Highlights header bar

| Element | Font | Style |
|---------|------|-------|
| "Highlights" | Manrope 14pt | Bold, white on maroon |
| "Overall status" | Theme body 14pt | Orange cell |
| "Last week" / "This week" | Theme body 14pt | Green cells |

---

## 3. Paragraph hierarchy (inside Highlights content cell)

| Level | Role | Bullet | Font | Bold |
|-------|------|--------|------|------|
| 0 | Project name (optional) | none | Manrope 12pt | Yes |
| 0 | Sprint line | • (round) | Manrope / Light 12pt | Name+status bold; dates/counts light |
| 0 | Current week sprint status | • | Manrope Light 12pt | No |
| **7** | Category header | **Solid right-pointing arrowhead ONLY** — `buChar` **Ø** (U+00D8) + `buFont` **Wingdings** | Manrope 12pt | **Yes (entire line)** |
| **1** | Story item | **₋** or **-** (dash) | Manrope Light 12pt | No |

### Category header text patterns

Category headers **must** use **only** the G10X solid right-pointing arrowhead at list level 7:

- `buChar`: **Ø** (U+00D8)
- `buFont`: **Wingdings,Sans-Serif**

**Forbidden** for category headers: `•`, `-`, `₋`, `▶`, `►`, `➤`, `→`, `>`, or Ø without Wingdings.

### Story order within each sprint

1. Completed stories  
2. Released for partner review  
3. In-progress  

---

## 4. Spacing rules

| Between | Rule |
|---------|------|
| Category header → first story | **No** blank line (story on very next paragraph) |
| Story → story | Single spacing, `spcBef = 0` |
| End of sprint → next sprint | **Exactly one** blank paragraph |
| Highlights → Key Activities | Border gap ~0.05–0.28 in; text clearance ≥ 0.15 in |

---

## 5. Space utilization

| Metric | Reference |
|--------|-----------|
| Paragraph slots on main slide | **20** |
| Dense fill threshold | **85%** |
| Create (Contd...) only when | Main slide ≥ **85%** full (`HL-UTIL-01`) |
| Sparse HL max waste below text | **0.5 in** (`HL-SIZE-01`) |

---

## 6. Key Activities

| Element | Requirement |
|---------|-------------|
| Header | `Key activities for next week` — Manrope Bold 14pt |
| Content | Manrope Light 12pt, round bullets |
| Placement | Only **after** Highlights finish on that slide |
| Sparse sizing | Shrink KA table to item count (`KA-SIZE-01`) |

---

## 7. Continuation slides

| Situation | Rule |
|-----------|------|
| Same bucket continues | Do **not** repeat category header |
| Same sprint continues | Do **not** repeat sprint line / current week |
| New sprint on contd | **Do** repeat full sprint block |
| Sparse contd | **Fail** — large empty HL box with few bullets |

---

## 8. Layout geometry (illustrative only — not scoring targets)

`layout_geometry.behaviors` in the rulebook JSON describes layout **behaviors** (on_slide_ka, hl_only_main, contd_hl_ka, ka_contd_only). Do not score automation-filled slides against fixed inch snapshots.

Footer safe zone: KA bottom ≤ **6.29 in**; dense HL-only main ≤ **~6.55 in**.

---

## 9. Scoring (AI evaluation)

**Scope: entire deck** — every slide titled `Delivery status – …` is scored.

Each slide scored **0–100** across typography, bullet_hierarchy, spacing, layout_geometry, content_structure, space_utilization.

**Deck pass threshold:** ≥ **80** combined score.

---

## 10. Commands

### Evaluate (AI)

```powershell
cd Jira-Automation
python scripts/evaluate_ppt_format.py --ppt "..\HEB_Delivery_Status.pptx"
```

### Validate (deterministic layout principles)

```powershell
python scripts/validate_layout_principles.py --ppt "..\HEB_Delivery_Status.pptx" --content "..\ppt_content.json"
```

### Repair loop

```powershell
python scripts/repair_ppt_format.py --ppt "..\HEB_Delivery_Status.pptx" --content "..\ppt_content.json"
python scripts/generate_ppt_content.py --snapshot-date 2026-07-07 --auto-fix --max-fix-rounds 5
```

### Allowed fix actions

| Action | Purpose |
|--------|---------|
| `layout_repair` | Shrink sparse HL/KA, position KA, ensure clearance (HL-SIZE-01, KA-PLC-*, KA-OVERLAP-01, GEO-02) |
| `reflow_hl_ka` | Reflow HL with expanded layout mode |
| `fix_category_bullets` | Wingdings Ø at level 7 (HL-P-04) |
| `remove_category_story_blanks` | HL-SPC-01 |
| `remove_extra_sprint_blanks` | HL-SPC-03 |
| `fix_title_en_dash` | TITLE-01 |
| `rebuild_with_hints` | HL-UTIL-01, KA-PLC-04 pack-all-on-main |

Outputs `{deck}.repair_log.json` with actions per round.
