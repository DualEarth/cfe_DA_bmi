"""
build_pptx.py

Creates helene_da_results.pptx from all DA routing and ensemble figures.

Run after downloading server figures:
    conda run -n base python build_pptx.py

All figures are looked up from FIGS_DIR; missing figures get a placeholder slide.
"""

import os
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
FIGS_DIR   = SCRIPT_DIR / "pptx_figures"
OUT_PATH   = SCRIPT_DIR / "helene_da_results.pptx"

# ── Slide dimensions  (16:9 widescreen) ──────────────────────────────────────
W = Inches(13.333)
H = Inches(7.5)

# ── Color palette ─────────────────────────────────────────────────────────────
C_DARK   = RGBColor(0x1a, 0x1a, 0x2e)   # near-black navy
C_ACCENT = RGBColor(0x16, 0x21, 0x3e)   # dark blue
C_HIGH   = RGBColor(0x0f, 0x3c, 0x78)   # headline blue
C_WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
C_GOLD   = RGBColor(0xE6, 0x9F, 0x00)
C_GRAY   = RGBColor(0xCC, 0xCC, 0xCC)


def _fill_bg(slide, color):
    from pptx.oxml.ns import qn
    from lxml import etree
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_text(slide, text, left, top, width, height,
              font_size=18, bold=False, color=C_WHITE,
              align=PP_ALIGN.LEFT, wrap=True):
    txb = slide.shapes.add_textbox(left, top, width, height)
    tf  = txb.text_frame
    tf.word_wrap = wrap
    p   = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color
    return txb


def _add_image(slide, img_path, left, top, width=None, height=None):
    p = Path(img_path)
    if not p.exists():
        # grey placeholder box
        shape = slide.shapes.add_shape(
            1,  # MSO_SHAPE_TYPE.RECTANGLE
            left, top,
            width or Inches(10), height or Inches(5)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(0x44, 0x44, 0x44)
        shape.line.color.rgb = C_GRAY
        _add_text(slide, f"[Figure not found]\n{p.name}",
                  left + Inches(0.2), top + Inches(0.2),
                  (width or Inches(10)) - Inches(0.4),
                  (height or Inches(5)) - Inches(0.4),
                  font_size=12, color=C_GRAY, align=PP_ALIGN.CENTER)
        return
    if width and height:
        slide.shapes.add_picture(str(p), left, top, width, height)
    elif width:
        slide.shapes.add_picture(str(p), left, top, width=width)
    elif height:
        slide.shapes.add_picture(str(p), left, top, height=height)
    else:
        slide.shapes.add_picture(str(p), left, top)


def _header(slide, title, subtitle=None):
    """Dark header bar at top of slide."""
    bar = slide.shapes.add_shape(1, 0, 0, W, Inches(1.0))
    bar.fill.solid()
    bar.fill.fore_color.rgb = C_HIGH
    bar.line.fill.background()

    _add_text(slide, title,
              Inches(0.3), Inches(0.05), W - Inches(0.6), Inches(0.65),
              font_size=24, bold=True, color=C_WHITE, align=PP_ALIGN.LEFT)
    if subtitle:
        _add_text(slide, subtitle,
                  Inches(0.3), Inches(0.65), W - Inches(0.6), Inches(0.35),
                  font_size=13, bold=False, color=C_GOLD, align=PP_ALIGN.LEFT)


# ── Slide builders ────────────────────────────────────────────────────────────

def slide_title(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    _fill_bg(slide, C_DARK)

    # decorative bar
    bar = slide.shapes.add_shape(1, 0, Inches(2.6), W, Inches(0.08))
    bar.fill.solid()
    bar.fill.fore_color.rgb = C_GOLD
    bar.line.fill.background()

    _add_text(slide,
              "CFE + EnKF Data Assimilation",
              Inches(0.8), Inches(1.2), Inches(11.7), Inches(1.1),
              font_size=40, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)
    _add_text(slide,
              "Ensemble Flood Forecasting During Hurricane Helene",
              Inches(0.8), Inches(2.3), Inches(11.7), Inches(0.7),
              font_size=26, bold=False, color=C_GOLD, align=PP_ALIGN.CENTER)
    _add_text(slide,
              "USGS Gauge 03463300  |  South Toe River Near Celo, NC  |  September 2024",
              Inches(0.8), Inches(3.2), Inches(11.7), Inches(0.5),
              font_size=16, bold=False, color=C_GRAY, align=PP_ALIGN.CENTER)
    _add_text(slide,
              "CFE BMI  ·  EnKF (Vrugt dynamic R)  ·  T-route Muskingum-Cunge routing  ·  600-member crossed ensemble",
              Inches(0.8), Inches(3.8), Inches(11.7), Inches(0.5),
              font_size=13, bold=False, color=C_GRAY, align=PP_ALIGN.CENTER)
    _add_text(slide,
              "CIROH DocHub  |  2024",
              Inches(0.8), Inches(6.8), Inches(11.7), Inches(0.4),
              font_size=12, bold=False, color=C_GRAY, align=PP_ALIGN.CENTER)


def slide_overview(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "Experiment Overview",
            "CFE hydrological model + Ensemble Kalman Filter DA → T-route gauge routing")

    bullets = [
        ("Study site",
         "USGS 03463300 – South Toe River Near Celo, NC  |  Watershed area 113.18 km²  |  21 NWM catchments"),
        ("Event",
         "Hurricane Helene (Sep 24–29, 2024)  —  extreme flooding in the Southern Appalachians"),
        ("DA method",
         "EnKF with dynamic Vrugt heteroscedastic R:  R = (α·y)² + 0.001·σ²_krig,  α = 0.10"),
        ("Ensemble",
         "600-member crossed ensemble: 30 forcing draws × 20 hydro-state draws  → fully separable uncertainty"),
        ("Routing",
         "T-route Muskingum-Cunge (compute_network_structured)  →  terminal reach wb-1016283 at gauge"),
        ("Evaluation",
         "4a: Vrugt R comparison · 4b: Ensemble routing · 4c: 18-hr lead-time forecasts · 3-way DA vs Qkrig vs USGS"),
    ]

    top = Inches(1.2)
    for label, text in bullets:
        _add_text(slide, f"▸  {label}",
                  Inches(0.5), top, Inches(2.8), Inches(0.35),
                  font_size=14, bold=True, color=C_GOLD)
        _add_text(slide, text,
                  Inches(3.4), top, Inches(9.5), Inches(0.35),
                  font_size=13, bold=False, color=C_WHITE)
        top += Inches(0.7)


def slide_vrugt_grid(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "4a: Vrugt Dynamic R — Grid Search Comparison",
            "Best-fit α selected by KGE across full test period and Helene window")

    _add_image(slide, FIGS_DIR / "helene_da_v2_vrugt_vs_run3_grid.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))

    _add_text(slide,
              "Dynamic R = (α · y)² + 0.001 · σ²_krig    α = 0.10 selected",
              Inches(0.3), Inches(6.9), Inches(12.7), Inches(0.4),
              font_size=12, color=C_GOLD, align=PP_ALIGN.CENTER)


def slide_vrugt_zoomed(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "4a: Vrugt R — Helene Window Zoom",
            "DA with α = 0.10 captures rising limb; both methods underestimate peak due to NWM forcing")

    _add_image(slide, FIGS_DIR / "helene_da_v2_vrugt_vs_run3_grid_zoomed.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))


def slide_vrugt_kge_table(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "4a: KGE Summary Table — Vrugt α Comparison",
            "Columns: α value  |  Rows: full period / Helene window KGE")

    _add_image(slide, FIGS_DIR / "da_v2_vrugt_kge_table.png",
               Inches(1.5), Inches(1.2), width=Inches(10.3))


def slide_sensitivity_categories(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "Perturbation Category Sensitivity",
            "Shaded min-max bands: initial states (red) · meteorological forcings (blue) · hydrological states (green)")

    _add_image(slide, FIGS_DIR / "cat-1016300_perturbation_categories_linear.png",
               Inches(0.2), Inches(1.1), width=Inches(12.9))

    _add_text(slide,
              "DA off in all sub-experiments  |  20 members each  |  N=20 per category",
              Inches(0.3), Inches(6.85), Inches(12.7), Inches(0.4),
              font_size=11, color=C_GRAY, align=PP_ALIGN.CENTER)


def slide_2a_forcing(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "2a: Forcing Arm — Meteorological Uncertainty Ensemble",
            "30 members  |  Lognormal precip σ = 15%  |  Normal PET σ = 10%  |  DA on")

    _add_image(slide, FIGS_DIR / "cat-1016300_2a_forcing_arm_helene.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))


def slide_2b_hydro(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "2b: Hydro-State Arm — Initial State Uncertainty Ensemble",
            "20 members  |  5% multiplicative state perturbation  |  DA on")

    _add_image(slide, FIGS_DIR / "cat-1016300_2b_hydro_arm_helene.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))


def slide_2ab_comparison(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "2a vs 2b: Which Uncertainty Source Dominates?",
            "Side-by-side arm comparison during Helene window")

    _add_image(slide, FIGS_DIR / "cat-1016300_2ab_arms_comparison.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))

    _add_text(slide,
              "Forcing uncertainty (2a) dominates spread during peak  |  State uncertainty (2b) contributes to rising/falling limb",
              Inches(0.3), Inches(6.85), Inches(12.7), Inches(0.4),
              font_size=11, color=C_GOLD, align=PP_ALIGN.CENTER)


def slide_production_ensemble(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "4b: 600-Member Crossed Ensemble — Production Forecast",
            "30 forcing × 20 hydro-state = 600 members  |  Routed to USGS gauge via T-route")

    _add_image(slide, FIGS_DIR / "cat-1016300_production_ensemble_forecast_linear.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))


def slide_ensemble_gauge(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "4b: Ensemble Routing at Gauge 03463300",
            "Ensemble band (5–95 pct) + median vs USGS obs  |  Helene window highlighted")

    _add_image(slide, FIGS_DIR / "helene_ensemble_vs_usgs.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))

    _add_text(slide,
              "DA ensemble brackets the USGS peak  |  Median underestimates due to NWM forcing underestimate of Helene precip",
              Inches(0.3), Inches(6.85), Inches(12.7), Inches(0.4),
              font_size=11, color=C_GOLD, align=PP_ALIGN.CENTER)


def slide_ensemble_twopanel(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "4b: Full Period + Helene Zoom — Routed Ensemble",
            "Top: full test period  |  Bottom: Helene Sep 24–29 zoom")

    _add_image(slide, FIGS_DIR / "helene_ensemble_twopanel.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))


def slide_spaghetti(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "4c: Lead-Time Forecasts — Spaghetti Plot",
            "18 forecast cycles × 20 ensemble members  |  DA vs Open-loop  |  Helene window")

    _add_image(slide, FIGS_DIR / "forecast_spaghetti_helene.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))

    _add_text(slide,
              "Each ribbon = one 18-hr forecast cycle issued during Helene  |  DA (color) tighter than OL (grey) near peak",
              Inches(0.3), Inches(6.85), Inches(12.7), Inches(0.4),
              font_size=11, color=C_GOLD, align=PP_ALIGN.CENTER)


def slide_reconstructed_full(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "4c: Reconstructed Timeseries — Full Test Period",
            "All lead-time forecasts overlaid; ensemble mean vs USGS obs  |  NSE DA=0.437 vs OL=0.318")

    _add_image(slide, FIGS_DIR / "lead_time_reconstructed_timeseries.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))


def slide_reconstructed_helene(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "4c: Reconstructed Timeseries — Helene Zoom",
            "NSE DA=0.339  OL=0.198  |  DA adds +0.14 NSE  |  Sep 24–29")

    _add_image(slide, FIGS_DIR / "lead_time_reconstructed_timeseries_helene.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))

    _add_text(slide,
              "DA consistently outperforms open-loop across all leads during the Helene peak",
              Inches(0.3), Inches(6.85), Inches(12.7), Inches(0.4),
              font_size=11, color=C_GOLD, align=PP_ALIGN.CENTER)


def slide_lead_decay(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "4c: Forecast Error Decay vs Lead Time",
            "Fixed verification time view  |  Lead 1 = 1 hr before target  |  Lead 18 = 18 hr before target")

    # Try both possible names
    img = FIGS_DIR / "error_fixed_target_mean.png"
    if not img.exists():
        img = FIGS_DIR / "lead_time_decay_gauge.png"

    _add_image(slide, img, Inches(0.3), Inches(1.1), width=Inches(12.7))

    _add_text(slide,
              "DA error (purple) decays toward zero faster than OL (grey)  |  DA retains skill out to ~12 hr lead time",
              Inches(0.3), Inches(6.85), Inches(12.7), Inches(0.4),
              font_size=11, color=C_GOLD, align=PP_ALIGN.CENTER)


def slide_three_way(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "Three-Way Comparison: DA vs Qkrig vs USGS",
            "Does DA add value beyond simply routing the Qkrig observations?")

    _add_image(slide, FIGS_DIR / "da_vs_qkrig_vs_usgs.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))

    _add_text(slide,
              "Full period: Qkrig-routed KGE=0.320, DA-routed KGE=0.277  |  "
              "DA's value is in the 18-hr forecast window (leads 1–18), not in the analysis step",
              Inches(0.3), Inches(6.75), Inches(12.7), Inches(0.5),
              font_size=11, color=C_GOLD, align=PP_ALIGN.CENTER)


def slide_four_folder_full(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "R-Formula Comparison — All 4 Experiments (Full Period)",
            "F1 Vrugt (best) · F2 R=0.07 · F3 Dyn Vrugt seeded · F4 Direct σ²  |  at gauge 03463300")

    _add_image(slide, FIGS_DIR / "compare_all_folders_full.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))

    _add_text(slide,
              "Vrugt R (F1) consistently outperforms fixed or direct-variance R  |  "
              "Peak underestimate is a NWM forcing issue, not R-formula dependent",
              Inches(0.3), Inches(6.85), Inches(12.7), Inches(0.4),
              font_size=11, color=C_GOLD, align=PP_ALIGN.CENTER)


def slide_four_folder_helene(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "R-Formula Comparison — Helene Window",
            "F1 KGE=0.213 · F2 KGE=0.439 · F3 KGE=0.189 · F4 KGE=0.132  |  Fixed R=0.07 best at peak")

    _add_image(slide, FIGS_DIR / "compare_all_folders_helene.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))

    _add_text(slide,
              "Fixed R=0.07 (F2) keeps Kalman gain high at peak — Vrugt inflates R at high flows, dampening DA updates",
              Inches(0.3), Inches(6.85), Inches(12.7), Inches(0.4),
              font_size=11, color=C_GOLD, align=PP_ALIGN.CENTER)


def slide_f3_lead_decay(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "F3: Forecast Error Decay — Dynamic Vrugt Seeded (seed=42)",
            "R = (0.10·y)² + 0.001·σ²_krig  |  Pooled across all regimes  |  Helene window")

    _add_image(slide, FIGS_DIR / "f3_lead_time_decay_gauge_pooled.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))

    _add_text(slide,
              "F3 KGE=+0.261 (full period)  |  Helene KGE=+0.189  |  Peak 693.8 m³/s (37% of USGS 1885.7)",
              Inches(0.3), Inches(6.85), Inches(12.7), Inches(0.4),
              font_size=11, color=C_GOLD, align=PP_ALIGN.CENTER)


def slide_f3_ensemble(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "F3: Ensemble Routing at Gauge — Dynamic Vrugt Seeded",
            "600-member crossed ensemble  |  5–95 pct band + median vs USGS  |  Helene window")

    _add_image(slide, FIGS_DIR / "f3_helene_ensemble_twopanel.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))

    _add_text(slide,
              "p95=759 m³/s, p50=484 m³/s  |  Vrugt R grows at high flows, narrowing spread near peak",
              Inches(0.3), Inches(6.85), Inches(12.7), Inches(0.4),
              font_size=11, color=C_GOLD, align=PP_ALIGN.CENTER)


def slide_f4_lead_decay(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "F4: Forecast Error Decay — Direct σ²_krig (seed=42)",
            "R = σ²_krig directly (no Vrugt formula)  |  Pooled across all regimes")

    _add_image(slide, FIGS_DIR / "f4_lead_time_decay_gauge_pooled.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))

    _add_text(slide,
              "F4 KGE=+0.200 (full period)  |  Helene KGE=+0.132  |  Peak 667.9 m³/s (35% of USGS 1885.7)",
              Inches(0.3), Inches(6.85), Inches(12.7), Inches(0.4),
              font_size=11, color=C_GOLD, align=PP_ALIGN.CENTER)


def slide_f4_ensemble(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "F4: Ensemble Routing at Gauge — Direct σ²_krig",
            "600-member crossed ensemble  |  5–95 pct band + median vs USGS  |  Helene window")

    _add_image(slide, FIGS_DIR / "f4_helene_ensemble_twopanel.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))

    _add_text(slide,
              "p95=744 m³/s, p50=552 m³/s  |  Large σ²_krig collapses Kalman gain — worst performer across all metrics",
              Inches(0.3), Inches(6.85), Inches(12.7), Inches(0.4),
              font_size=11, color=C_GOLD, align=PP_ALIGN.CENTER)


def slide_f3_reconstructed(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "F3: Reconstructed Timeseries — Dynamic Vrugt Seeded",
            "Overlapping-leads pool from 18-hr forecast cycles  |  DA median vs open-loop vs USGS")

    _add_image(slide, FIGS_DIR / "f3_reconstructed_timeseries.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))


def slide_f3_reconstructed_helene(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "F3: Reconstructed Timeseries — Helene Zoom",
            "Dynamic Vrugt seeded (seed=42)  |  Sep 24–29, 2024")

    _add_image(slide, FIGS_DIR / "f3_reconstructed_timeseries_helene.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))

    _add_text(slide,
              "F3 Helene KGE=+0.189  |  Peak 693.8 m³/s (37% of USGS 1885.7)",
              Inches(0.3), Inches(6.85), Inches(12.7), Inches(0.4),
              font_size=11, color=C_GOLD, align=PP_ALIGN.CENTER)


def slide_f4_reconstructed(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "F4: Reconstructed Timeseries — Direct σ²_krig",
            "Overlapping-leads pool from 18-hr forecast cycles  |  DA median vs open-loop vs USGS")

    _add_image(slide, FIGS_DIR / "f4_reconstructed_timeseries.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))


def slide_f4_reconstructed_helene(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "F4: Reconstructed Timeseries — Helene Zoom",
            "Direct σ²_krig (seed=42)  |  Sep 24–29, 2024")

    _add_image(slide, FIGS_DIR / "f4_reconstructed_timeseries_helene.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))

    _add_text(slide,
              "F4 Helene KGE=+0.132  |  Peak 667.9 m³/s (35% of USGS 1885.7)",
              Inches(0.3), Inches(6.85), Inches(12.7), Inches(0.4),
              font_size=11, color=C_GOLD, align=PP_ALIGN.CENTER)


def slide_sensitivity_spaghetti(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "Sensitivity Ensemble — Spaghetti (All Catchments)",
            "Each thin line = one catchment ensemble trajectory  |  Helene window")

    _add_image(slide, FIGS_DIR / "helene_sensitivity_spaghetti_main.png",
               Inches(0.3), Inches(1.1), width=Inches(12.7))


def slide_summary(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, C_DARK)
    _header(slide, "Summary & Key Findings")

    findings = [
        ("DA improves forecasts",
         "EnKF DA with dynamic Vrugt R (α=0.10) adds +0.12 to +0.14 NSE over open-loop "
         "during Helene peak — skill retained out to ~12 hr lead time"),
        ("Peak underestimation",
         "Both DA-routed and Qkrig-routed underestimate Helene peak by ~2.5× — root cause "
         "is NWM forcing underestimating extreme precipitation, not the DA system"),
        ("DA vs Qkrig routing",
         "Routing Qkrig obs directly gives slightly higher KGE (0.320 vs 0.277) than DA in "
         "hindcast — DA's advantage is in operational forecasting 1–18 hr ahead"),
        ("Ensemble spread",
         "Forcing uncertainty (2a) dominates spread at peak; hydro-state uncertainty (2b) "
         "shapes the rising/falling limbs — 600-member crossed ensemble captures this cleanly"),
        ("Reproducibility",
         "All 600 ensemble members are fully traceable via member_manifest.csv and "
         "provenance parquets (da_snapshots, hydro_draw_states, forcing_draw_sequences)"),
    ]

    top = Inches(1.2)
    for i, (label, text) in enumerate(findings):
        num_color = [C_GOLD, RGBColor(0x5B, 0xD8, 0xFF), RGBColor(0x7B, 0xFF, 0x8A),
                     RGBColor(0xFF, 0x7B, 0x7B), C_GRAY][i]
        _add_text(slide, f"{i+1}. {label}",
                  Inches(0.5), top, Inches(3.5), Inches(0.4),
                  font_size=14, bold=True, color=num_color)
        _add_text(slide, text,
                  Inches(4.0), top, Inches(9.0), Inches(0.4),
                  font_size=13, bold=False, color=C_WHITE)
        top += Inches(0.72)

    _add_text(slide,
              "Code: github.com/DualEarth/cfe_DA_bmi  (branch: feature/da-v2-enkf)",
              Inches(0.5), Inches(7.1), Inches(12.3), Inches(0.3),
              font_size=11, color=C_GRAY, align=PP_ALIGN.CENTER)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    prs = Presentation()
    prs.slide_width  = W
    prs.slide_height = H

    print("Building slides...")
    slide_title(prs)
    print("  1. Title")
    slide_overview(prs)
    print("  2. Overview")
    slide_vrugt_grid(prs)
    print("  3. Vrugt grid")
    slide_vrugt_zoomed(prs)
    print("  4. Vrugt zoomed")
    slide_vrugt_kge_table(prs)
    print("  5. Vrugt KGE table")
    slide_sensitivity_categories(prs)
    print("  6. Perturbation categories")
    slide_2a_forcing(prs)
    print("  7. 2a forcing arm")
    slide_2b_hydro(prs)
    print("  8. 2b hydro arm")
    slide_2ab_comparison(prs)
    print("  9. 2a vs 2b comparison")
    slide_production_ensemble(prs)
    print(" 10. Production ensemble")
    slide_ensemble_gauge(prs)
    print(" 11. Ensemble at gauge")
    slide_ensemble_twopanel(prs)
    print(" 12. Ensemble two-panel")
    slide_spaghetti(prs)
    print(" 13. Lead-time spaghetti")
    slide_reconstructed_full(prs)
    print(" 14. Reconstructed timeseries (full)")
    slide_reconstructed_helene(prs)
    print(" 15. Reconstructed timeseries (Helene)")
    slide_lead_decay(prs)
    print(" 16. Lead-time error decay")
    slide_three_way(prs)
    print(" 17. Three-way comparison")
    slide_four_folder_full(prs)
    print(" 18. Four-folder comparison (full period)")
    slide_four_folder_helene(prs)
    print(" 19. Four-folder comparison (Helene)")
    slide_f3_lead_decay(prs)
    print(" 20. F3 lead-time error decay")
    slide_f3_ensemble(prs)
    print(" 21. F3 ensemble at gauge")
    slide_f4_lead_decay(prs)
    print(" 22. F4 lead-time error decay")
    slide_f4_ensemble(prs)
    print(" 23. F4 ensemble at gauge")
    slide_f3_reconstructed(prs)
    print(" 24. F3 reconstructed timeseries (full)")
    slide_f3_reconstructed_helene(prs)
    print(" 25. F3 reconstructed timeseries (Helene)")
    slide_f4_reconstructed(prs)
    print(" 26. F4 reconstructed timeseries (full)")
    slide_f4_reconstructed_helene(prs)
    print(" 27. F4 reconstructed timeseries (Helene)")
    slide_sensitivity_spaghetti(prs)
    print(" 28. Sensitivity spaghetti")
    slide_summary(prs)
    print(" 29. Summary")

    prs.save(str(OUT_PATH))
    print(f"\nSaved: {OUT_PATH}")
    print(f"Slides: {len(prs.slides)}")

    # Report which figures were missing
    all_figs = [
        "helene_da_v2_vrugt_vs_run3_grid.png",
        "helene_da_v2_vrugt_vs_run3_grid_zoomed.png",
        "da_v2_vrugt_kge_table.png",
        "cat-1016300_perturbation_categories_linear.png",
        "cat-1016300_2a_forcing_arm_helene.png",
        "cat-1016300_2b_hydro_arm_helene.png",
        "cat-1016300_2ab_arms_comparison.png",
        "cat-1016300_production_ensemble_forecast_linear.png",
        "helene_ensemble_vs_usgs.png",
        "helene_ensemble_twopanel.png",
        "forecast_spaghetti_helene.png",
        "lead_time_reconstructed_timeseries.png",
        "lead_time_reconstructed_timeseries_helene.png",
        "error_fixed_target_mean.png",
        "da_vs_qkrig_vs_usgs.png",
        "compare_all_folders_full.png",
        "compare_all_folders_helene.png",
        "f3_lead_time_decay_gauge_pooled.png",
        "f3_helene_ensemble_twopanel.png",
        "f3_reconstructed_timeseries.png",
        "f3_reconstructed_timeseries_helene.png",
        "f4_lead_time_decay_gauge_pooled.png",
        "f4_helene_ensemble_twopanel.png",
        "f4_reconstructed_timeseries.png",
        "f4_reconstructed_timeseries_helene.png",
        "helene_sensitivity_spaghetti_main.png",
    ]
    missing = [f for f in all_figs if not (FIGS_DIR / f).exists()]
    if missing:
        print(f"\nMissing {len(missing)} figure(s) — slides show placeholders:")
        for f in missing:
            print(f"  {f}")
    else:
        print("\nAll figures found — no placeholders.")


if __name__ == "__main__":
    main()
