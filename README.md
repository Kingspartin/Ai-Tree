# Ai-Tree
Visualized mobile ai app

---

# Prime Line

A flat plot of the primes: `index.html`. Every prime, in order, joined by one
continuous line that walks up and out from the origin — then re-projected nine ways,
because the projection is what decides whether the primes look like noise or like
architecture.

Open `index.html` in a browser. No build, no dependencies, no network: one file, a
sieve, and a canvas.

## The nine paths

| # | Path | Map | What the line does |
|---|------|-----|--------------------|
| 1 | Prime galaxy | `r = p, θ = p rad` | Spiral arms appear where 2π has a good rational approximation. 44 ≈ 7·2π gives 44 lanes, of which only φ(44) = 20 can hold a prime; push the count and 710 ≈ 113·2π takes over with φ(710) = 280. |
| 2 | Sacks spiral | `r = √p, θ = 2π√p` | One turn per perfect square, so quadratics become smooth curves and prime-rich quadratics become visible ribs — Euler's n² + n + 41 among them. |
| 3 | Ulam spiral | square spiral, step 1 | The 1963 doodle. Primes fall on diagonals, each of which is a quadratic 4n² + bn + c that dodges small factors. |
| 4 | Golden angle | `r = √p, θ = p · 137.507°` | The control experiment. The golden angle is the worst-approximable number, so there are no lanes to fall into and the primes smear evenly. |
| 5 | Log spiral | `r = θ = 2π·log_B p` | One turn per order of magnitude. The line fills in rather than thinning; the note counts the primes per ring live, and the shortfall against ×B is the prime number theorem. |
| 6 | Residue rays | `θ = 2π·(p mod m)/m` | The disc collapses to φ(m) rays — Dirichlet's theorem, drawn. Drag m and watch the ray count lurch. |
| 7 | Prime staircase | `x = p, y = π(p)` | The literal up-and-out, against a dashed `x / ln x`. |
| 8 | Gap comb | `x = p, y = p − p_prev` | Even-valued rails, with the record (maximal) gaps as an ascending staircase. |
| 9 | Turtle walk | step 1, turn `2π·(p mod m)/m` | Nothing random, yet the walk wanders like a drunk. m selects the regime. |

## Controls

- **Path** — nine projections, or keys `1`–`9`. Each arrives with ink settings tuned
  to it; every one of them is overridable.
- **Scale** — 1,000 to 500,000 primes, sieved on demand. `m` drives the residue and
  turtle paths, `B` the log spiral.
- **Trace** — line and dot layers, weight, opacity, and colour by gap, by position in
  the sequence, or by `p mod m` (the eight busiest residue classes get the eight
  colour slots; the rare ones fold into one).
- **Drawing** — animate the trace with a moving head, or drop it in at once. Replay
  with `space`.
- **View** — drag to pan, wheel to zoom, double-click to fit, `S` to save a PNG.
- Hovering any point reports the prime, its index, its gap, and its residue.

## How it works

A plain sieve of Eratosthenes fills an `Int32Array`, each path maps prime index and
value to plane coordinates, and the result is normalised to a fitted box — aspect
preserved for the polar paths, axes stretched independently for the framed ones.

Drawing is chunked across animation frames and the chunk size adapts to keep frames
near 12 ms, so half a million points never block the main thread. Segments are batched
into one `Path2D` per colour bucket rather than stroked individually, dots into one
filled path per bucket. The animated head lives on its own overlay canvas so it can be
cleared each frame without touching (or reading back) the plot underneath.

Ink opacity scales down automatically as the prime count climbs — at 500,000
overlapping strokes a fixed alpha just renders a white disc.
