# Hybrid Pipeline Architecture

Geometry-driven correction with qualitative GPT-4o visual validation.

## Architecture diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     VisionLayoutPipeline (orchestrator)                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
          ┌─────────────────────────┴─────────────────────────┐
          │ pipeline_mode = hybrid (default)                  │
          │ pipeline_mode = legacy_vision_measurement (flag)  │
          └─────────────────────────┬─────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        HybridValidationLoop                              │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────┐   ┌────────────┐ │
│  │  Geometry    │ → │  Geometry    │ → │  Ppt       │ → │ Qualitative│ │
│  │  Inspector   │   │  Corrector   │   │  Renderer  │   │  Reviewer  │ │
│  └──────────────┘   └──────────────┘   └────────────┘   └────────────┘ │
│         │                  │                                    │       │
│         │                  │                                    │       │
│    ppt_format_*        ppt_format_repair                  GPT-4o        │
│    violations          tighten_hl_and_position_ka         (no pixels)   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Module interaction diagram

```
update_delivery_status.py  (unchanged — deck generation)
         │
         ▼
SubprocessDeckGenerator
         │
         ▼
    HEB_Delivery_Status.pptx
         │
         ├──────────────────────────────────────┐
         ▼                                      ▼
GeometryInspector                    (after correction)
  ├─ ppt_format_extractor.extract_deck          │
  └─ ppt_format_violations.detect_*             │
         │                                      │
         ▼                                      ▼
GeometryReport ──► GeometryCorrector     SlideImagePptRenderer
  └─ planner.plan_slide_repair (1/slide)   └─ PNG per slide
         │                                      │
         └─ ppt_format_repair.*                  ▼
                                    QualitativeVisionReviewer
                                      └─ QualitativeVisionClient
                                            └─ qualitative JSON only
```

## Pipeline flow (per iteration)

1. **Geometry Inspection** — read PPTX; compute EMU metrics and rule violations.
2. **Geometry Correction** — one coherent repair plan per slide; apply via `tighten_hl_and_position_ka` / `apply_layout_repair`.
3. **Render** — export delivery slides to PNG.
4. **Qualitative Vision Review** — GPT-4o returns categories + confidence (no measurements).
5. **Confidence gating** — decide next-iteration geometry plans or `manual_review_required`.
6. Repeat until pass, manual review only, or `max_iterations`.

## Component responsibilities

### Geometry Inspector (`app/geometry/inspector.py`)

- **Input:** `.pptx` path
- **Output:** `GeometryReport` with per-slide violations and EMU metrics
- **Source of truth for:** `text_ka_clearance_in`, `hl_ka_gap_in`, `hl_waste_below_text_in`, rule IDs (`KA-OVERLAP-01`, `HL-SIZE-01`, …)
- **Does not:** call vision, modify the deck

### Geometry Corrector (`app/geometry/corrector.py`)

- **Input:** `GeometryReport` + optional `SlideRepairPlan` per slide
- **Output:** `GeometryCorrectionResult`
- **Computes:** EMU movements via existing `ppt_format_repair` helpers
- **Policy:** at most one repair mode per slide per iteration (no shrink → maintain_gap → move conflicts)

### Vision Reviewer (`app/pipeline/qualitative_reviewer.py`)

- **Input:** rendered PNGs
- **Output:** `QualitativeReviewReport` (categories, severity, confidence, description)
- **Does not:** return pixels, coordinates, EMU, or movement recommendations

### Validation Loop (`app/pipeline/hybrid_validation_loop.py`)

- Orchestrates the four stages above
- Applies confidence gating (`app/geometry/confidence.py`)
- Marks slides `manual_review_required` when vision flags issues geometry cannot fix

## Feature flag

```python
PipelineDependencies.create_default(
    pipeline_mode=PipelineMode.HYBRID,  # default
)
PipelineDependencies.create_default(
    pipeline_mode=PipelineMode.LEGACY_VISION_MEASUREMENT,
)
```

CLI:

```bash
python scripts/run_hybrid_validation_loop.py --ppt deck.pptx
python scripts/run_hybrid_validation_loop.py --ppt deck.pptx --legacy-vision-measurement
```

## Legacy vs hybrid

| Aspect | Legacy vision measurement | Hybrid (default) |
|--------|---------------------------|------------------|
| Measurements | GPT-4o pixels | PPTX geometry / EMU |
| Correction sizing | Vision → mapper → EMU | Geometry planner → repair |
| Vision role | Primary measurement | Qualitative QA only |
| Stability | Poor (validated in PoC) | Expected stable numeric loop |
| Feature flag | `legacy_vision_measurement` | `hybrid` (default) |

See also: `HEB_hybrid_vs_legacy_comparison.md` for end-to-end results on the HEB test deck.

## HEB demonstration (2026-07-13)

```bash
python scripts/run_hybrid_validation_loop.py --ppt ..\HEB_Delivery_Status.pptx --max-iterations 2
```

**Results**

- Iteration 1: geometry corrected 6 slides (`ensure_clearance` on slide 3; `tighten_and_position` on 6–10).
- Vision returned qualitative JSON only (categories + confidence; no pixels).
- Confidence gating marked slides 4, 6–8 for manual review when `poor_visual_balance` lacked geometry confirmation.
- Iteration 2: stopped at `iteration_limit` with 9 geometry violations remaining (dense slide 3 footer overflow, near-threshold clearances).
- Full log: `HEB_Delivery_Status.hybrid_loop.json`
