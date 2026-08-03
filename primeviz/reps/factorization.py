"""Multiplicative embeddings: map an integer to its exponent vector on the first
20 primes, then project to 2D.

Two versions, because the obvious one is degenerate and it is worth *seeing*
that it is degenerate:

  factor_embed   embed every integer, highlight the set. A prime larger than 71
                 has no factor in the basis, so its vector is all zeros: the
                 entire prime set collapses onto a single point. The picture is
                 of the composites.

  factor_shift   embed n-1 instead. Now every member has structure, and the
                 question becomes whether the multiplicative shape of p-1
                 differs from that of a random integer of the same size.
"""
from __future__ import annotations

import time

import numpy as np
from sklearn.decomposition import PCA

from ..registry import Representation
from ..stats import dispersion
from ..theme import INK_MUTED, SEQ_CMAP, SET_COLORS, bare, recessive

N_BASIS = 20


# --- embed the integers themselves -------------------------------------------


def _pca_all(ctx):
    if not hasattr(ctx, "_pca_all_cache"):
        E = ctx.exps(ctx.integers).astype(np.float32)
        p = PCA(n_components=2, random_state=0).fit(E)
        ctx._pca_all_cache = (p.transform(E), p.explained_variance_ratio_)
    return ctx._pca_all_cache


def embed_render(iset, sf, ctx):
    Z, evr = _pca_all(ctx)
    ax = sf.subplots(1, 1)
    sub = ctx.subsample(np.arange(Z.shape[0]), 40_000, seed=3)
    ax.scatter(Z[sub, 0], Z[sub, 1], s=5, c=INK_MUTED, alpha=0.35, linewidths=0,
               label="all integers")
    m = iset.mask[2 : ctx.N + 1]
    ax.scatter(Z[m, 0], Z[m, 1], s=10, c=SET_COLORS[iset.key], alpha=0.8,
               linewidths=0, label=iset.key)
    ax.set_title(
        f"PCA of exponent vectors (PC1 {evr[0]:.0%}, PC2 {evr[1]:.0%})", pad=6
    )
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.legend(loc="upper right", markerscale=6)
    recessive(ax)


def embed_stats(iset, ctx):
    E = ctx.exps(iset.values)
    tot = E.sum(axis=1)
    return {
        "frac_at_origin": float((tot == 0).mean()),
        "mean_basis_exponent": float(tot.mean()),
        "mean_v2": float(E[:, 0].mean()),
    }


Representation(
    key="factor_embed",
    title="Factorisation embedding of n (PCA)",
    question="where does the set sit in the space of small-prime exponent vectors?",
    render=embed_render,
    stats=embed_stats,
    headline="frac_at_origin",
    iteration=1,
    panel_size=(5.0, 4.6),
    notes=(
        "Read the axes before the pattern: the coordinates are 'how many times does "
        "2, 3, 5 ... divide n'. Almost every prime is at the origin because none of "
        "them do — the primes panel is one coloured dot. Note the disagreement "
        "between eye and statistic here, in the direction people usually assume is "
        "impossible: the *picture* cannot tell the primes from the sieved null "
        "(both collapse to the origin, since PC1 and PC2 are essentially the "
        "exponents of 2 and 3, which both sets have set to zero), while the "
        "*statistic* separates them at z = 122. Neither is wrong; they are answering "
        "different questions, and the statistic's question happens to be a "
        "tautology."
    ),
    mechanism=(
        "Tautological, and worth stating plainly so it is not mistaken for a "
        "finding: the embedding's coordinates are divisibility by the primes up to "
        "71, and a prime above 71 is divisible by none of them, so it maps to the "
        "zero vector by definition. `frac_at_origin` ≈ 1 for the primes is a "
        "restatement of what a prime is. It separates from the sieved null only "
        "because that null is sieved at 7, not at 71 -- a deeper null (integers with "
        "no factor below 71) would erase this entirely."
    ),
)


# --- embed n-1 ----------------------------------------------------------------


def shift_render(iset, sf, ctx):
    v = iset.values
    v = v[v > 2]
    E = ctx.exps(v - 1).astype(np.float32)
    axes = sf.subplots(1, 2)

    Z = PCA(n_components=2, random_state=0).fit_transform(E)
    axes[0].hexbin(Z[:, 0], Z[:, 1], gridsize=54, cmap=SEQ_CMAP, mincnt=1, linewidths=0,
                    bins="log")
    axes[0].set_title("PCA of exponent vectors of n−1", pad=6)
    axes[0].set_xlabel("PC1")
    axes[0].set_ylabel("PC2")
    recessive(axes[0])

    ax = axes[1]
    if ctx.use_umap:
        try:
            import umap

            S = ctx.subsample(E, ctx.umap_max, seed=11)
            t0 = time.time()
            U = umap.UMAP(
                n_neighbors=15, min_dist=0.1, n_components=2, random_state=42,
                verbose=False,
            ).fit_transform(S)
            ax.hexbin(U[:, 0], U[:, 1], gridsize=54, cmap=SEQ_CMAP, mincnt=1,
                      linewidths=0)
            ax.set_title(
                f"UMAP, {S.shape[0]:,} pts, {time.time()-t0:.0f}s", pad=6
            )
        except Exception as e:  # keep the sweep alive
            ax.text(0.5, 0.5, f"UMAP failed:\n{e}", ha="center", va="center",
                    color=INK_MUTED, fontsize=8)
            bare(ax)
            return
    else:
        ax.text(0.5, 0.5, "UMAP disabled", ha="center", va="center",
                color=INK_MUTED, fontsize=9)
        bare(ax)
        return
    ax.set_xlabel("UMAP1")
    ax.set_ylabel("UMAP2")
    recessive(ax)


def shift_stats(iset, ctx):
    v = iset.values
    v = v[v > 2]
    E = ctx.exps(v - 1)
    tot = E.sum(axis=1).astype(float)
    v2 = E[:, 0].astype(float)
    # distribution of the 2-adic valuation, as counts in bins 0..8+
    hb = np.minimum(v2, 8).astype(int)
    obs = np.bincount(hb, minlength=9).astype(float)
    geo = 2.0 ** (-np.arange(1, 10))  # the shape a random even/odd mix would give
    return {
        "mean_v2_of_shift": float(v2.mean()),
        "mean_basis_exponent_shift": float(tot.mean()),
        "frac_shift_div6": float(((v - 1) % 6 == 0).mean()),
        "v2_shape_dispersion": dispersion(obs, geo * obs.sum()),
    }


Representation(
    key="factor_shift",
    title="Factorisation embedding of n−1 (PCA + UMAP)",
    question="is the multiplicative shape of p−1 unusual for an integer of that size?",
    render=shift_render,
    stats=shift_stats,
    headline="mean_basis_exponent_shift",
    iteration=1,
    panel_size=(5.4, 4.6),
    notes=(
        "Both projections are log-scaled density hexbins, not scatter, because 10⁴ "
        "points overplot. PCA is dominated by the 2-adic valuation of n−1. Treat the "
        "UMAP clusters as furniture, not findings: the exponent vectors are short "
        "integer vectors with many exact duplicates, so UMAP separates them into "
        "islands of identical points, and it draws the same islands on all three "
        "panels. Cluster count and shape here are a function of n_neighbors and of "
        "the discreteness of the coordinates, not of which integers went in."
    ),
    mechanism=(
        "Every prime past 2 is odd, so p−1 is always even, and the density of the "
        "basis exponents shifts up accordingly. That is parity, not depth: a null "
        "whose members are already odd shows the same thing."
    ),
)
