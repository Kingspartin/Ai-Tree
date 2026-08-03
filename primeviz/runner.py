"""Render every representation on real primes and on both nulls, score, critique."""
from __future__ import annotations

import json
import os
import textwrap
import time
import traceback

import matplotlib.pyplot as plt
import numpy as np

from . import stats as st
from .context import Context
from .numbers import build_sets, null_replicates
from .registry import Representation, selected
from .theme import INK_2, INK_MUTED, SET_COLORS, VERDICT_COLORS, apply_style

PANEL_ORDER = ["primes", "cramer", "sieved"]


def _fmt(x: float) -> str:
    if x is None or not np.isfinite(x):
        return "n/a"
    if abs(x) >= 1000 or (abs(x) < 0.01 and x != 0):
        return f"{x:.3g}"
    return f"{x:.3f}"


def critique(rep: Representation, res: st.StatResult | None) -> tuple[str, str]:
    """(verdict, one-line critique). Skeptical by default."""
    if res is None:
        return "INCONCLUSIVE", "no statistic defined - eyeball only, assume artifact."
    v = st.verdict(res)
    zc, zs = res.z_cramer, res.z_sieved
    ref = zs if np.isfinite(zs) and abs(zs) >= st.Z_BAR else zc
    direction = ""
    if v in ("SURVIVES", "COPRIMALITY") and np.isfinite(ref):
        direction = " The real value is BELOW the nulls' " if ref < 0 else " The real value is ABOVE the nulls' "
        direction += "- more even/less clumped than random." if ref < 0 else "- more clumped than random."
    h = f"{res.name}={_fmt(res.real)} (Cramer z={_fmt(zc)}, sieved z={_fmt(zs)})"
    if v == "ARTIFACT":
        line = (
            f"ARTIFACT - {h}. Both nulls reproduce it; whatever you can see is the "
            f"encoding drawing itself, not the primes."
        )
    elif v == "COPRIMALITY":
        line = (
            f"COPRIMALITY - {h}. Beats random integers but not integers that merely "
            f"avoid factors 2,3,5,7. This is the definition of a prime showing "
            f"through, not distributional structure."
        )
    elif v == "SURVIVES":
        line = (
            f"SURVIVES - {h}. Neither matched-density randomness nor small-factor "
            f"avoidance reproduces this. Needs a mechanism."
        )
    else:
        line = f"INCONCLUSIVE - {h}. Degenerate null spread; statistic needs work."
    return v, line + direction


def run_iteration(
    ctx: Context,
    iteration: int,
    only: list[str] | None = None,
    iteration_max: int | None = None,
) -> dict:
    apply_style()
    t_all = time.time()
    out_dir = os.path.join(ctx.out_dir, f"iteration_{iteration:02d}")
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n{'='*78}\nITERATION {iteration}  |  N={ctx.N:,}  seed={ctx.seed}  "
          f"null replicates={ctx.n_rep}\n{'='*78}")

    sets = build_sets(ctx.N, ctx.seed)
    print(
        "  sets: "
        + "   ".join(f"{k}={v.count:,} (density {v.density:.5f})" for k, v in sets.items())
    )

    ensembles = {
        m: null_replicates(ctx.N, sets["primes"].count, m, ctx.n_rep, ctx.seed)
        for m in ("cramer", "sieved")
    }

    reps = selected(iteration_max=iteration_max if iteration_max else iteration, only=only)
    print(f"  representations: {len(reps)}  ->  {out_dir}\n")

    report: list[dict] = []
    for rep in reps:
        t0 = time.time()
        w, h = rep.panel_size
        fig = plt.figure(figsize=(w * 3, h + 1.0), layout="constrained")
        fig.get_layout_engine().set(hspace=0.02, wspace=0.02)
        subs = fig.subfigures(1, 3, wspace=0.015)
        errors = []
        for sf, key in zip(subs, PANEL_ORDER):
            iset = sets[key]
            sf.suptitle(
                iset.label, color=SET_COLORS[key], fontsize=11, fontweight="bold"
            )
            try:
                rep.render(iset, sf, ctx)
            except Exception as e:  # a broken rep must not kill the sweep
                errors.append(f"{key}: {e}")
                traceback.print_exc()

        # statistics + null ensemble
        res = None
        all_stats: dict[str, st.StatResult] = {}
        if rep.stats is not None:
            try:
                real_vals = rep.stats(sets["primes"], ctx)
                null_vals = {
                    m: [rep.stats(s, ctx) for s in ens] for m, ens in ensembles.items()
                }
                all_stats = st.score(real_vals, null_vals)
                res = all_stats.get(rep.headline)
            except Exception as e:
                errors.append(f"stats: {e}")
                traceback.print_exc()

        v, line = critique(rep, res)
        fig.suptitle(
            f"{rep.title}  ·  {rep.question}", fontsize=13, fontweight="bold"
        )
        body = line.split(" - ", 1)[1] if " - " in line else line
        wrapped = textwrap.fill(body, width=int(w * 3 * 11.5))
        fig.supxlabel(
            f"[{v}]  {wrapped}",
            color=VERDICT_COLORS[v],
            fontsize=8.5,
            fontweight="bold",
            ha="left",
            x=0.004,
        )
        path = os.path.join(out_dir, f"{rep.key}.png")
        fig.savefig(path)
        plt.close(fig)

        dt = time.time() - t0
        print(f"  [{v:12s}] {rep.key:24s} {dt:5.1f}s  {line}")
        for extra in errors:
            print(f"      !! {extra}")

        report.append(
            {
                "key": rep.key,
                "title": rep.title,
                "question": rep.question,
                "iteration": rep.iteration,
                "verdict": v,
                "critique": line,
                "headline": rep.headline,
                "mechanism": rep.mechanism if v in ("SURVIVES", "COPRIMALITY") else "",
                "notes": rep.notes,
                "image": os.path.relpath(path, ctx.out_dir),
                "errors": errors,
                "stats": {
                    k: {
                        "real": r.real,
                        **{
                            f"{m}_{f}": getattr(ns, f)
                            for m, ns in r.nulls.items()
                            for f in ("mean", "sd", "z")
                        },
                    }
                    for k, r in all_stats.items()
                },
            }
        )

    write_report(ctx, iteration, out_dir, sets, report, time.time() - t_all)
    return {"out_dir": out_dir, "report": report}


def write_report(ctx, iteration, out_dir, sets, report, elapsed):
    with open(os.path.join(out_dir, "results.json"), "w") as f:
        json.dump(
            {"N": ctx.N, "seed": ctx.seed, "n_rep": ctx.n_rep, "reps": report}, f, indent=2
        )

    order = {"SURVIVES": 0, "COPRIMALITY": 1, "INCONCLUSIVE": 2, "ARTIFACT": 3}
    L = [
        f"# Iteration {iteration}",
        "",
        f"`N = {ctx.N:,}`  ·  seed `{ctx.seed}`  ·  {ctx.n_rep} null replicates per model "
        f"·  {elapsed:.0f}s",
        "",
        "| set | count | density |",
        "|---|---|---|",
    ]
    for k, s in sets.items():
        L += [f"| {s.label} | {s.count:,} | {s.density:.5f} |"]
    L += [
        "",
        "Verdicts are on the headline statistic, z measured against an ensemble of "
        "independent null draws. `SURVIVES` = separates from both nulls. "
        "`COPRIMALITY` = separates from Cramér only, i.e. it is small-factor "
        "avoidance. `ARTIFACT` = both nulls reproduce it.",
        "",
        "| verdict | representation | headline | real | z vs Cramér | z vs sieved |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted(report, key=lambda r: (order[r["verdict"]], r["key"])):
        s = r["stats"].get(r["headline"] or "", {})
        L += [
            f"| **{r['verdict']}** | `{r['key']}` | {r['headline'] or '—'} | "
            f"{_fmt(s.get('real', float('nan')))} | {_fmt(s.get('cramer_z', float('nan')))} | "
            f"{_fmt(s.get('sieved_z', float('nan')))} |"
        ]
    L += [""]
    for r in sorted(report, key=lambda r: (order[r["verdict"]], r["key"])):
        L += [
            f"## {r['title']}  ·  {r['verdict']}",
            "",
            f"*{r['question']}*",
            "",
            f"![{r['key']}]({os.path.basename(r['image'])})",
            "",
            f"**Critique.** {r['critique']}",
            "",
        ]
        if r["notes"]:
            L += [f"**Reading the picture.** {r['notes']}", ""]
        if r["mechanism"]:
            L += [f"**Why it happens.** {r['mechanism']}", ""]
        if r["stats"]:
            L += ["| statistic | real | Cramér mean±sd | z | sieved mean±sd | z |",
                  "|---|---|---|---|---|---|"]
            for k, s in r["stats"].items():
                L += [
                    f"| `{k}` | {_fmt(s['real'])} | {_fmt(s.get('cramer_mean'))}±"
                    f"{_fmt(s.get('cramer_sd'))} | {_fmt(s.get('cramer_z'))} | "
                    f"{_fmt(s.get('sieved_mean'))}±{_fmt(s.get('sieved_sd'))} | "
                    f"{_fmt(s.get('sieved_z'))} |"
                ]
            L += [""]
        if r["errors"]:
            L += ["**Errors.** " + "; ".join(r["errors"]), ""]

    with open(os.path.join(out_dir, "report.md"), "w") as f:
        f.write("\n".join(L))
    print(f"\n  report: {os.path.join(out_dir, 'report.md')}")
