"""Test suite for ranktool.

Run with:  python -m unittest discover -s tests -v
       or: python -m pytest tests -q
"""

from __future__ import annotations

import unittest
from fractions import Fraction as F

from ranktool.arith import (
    is_square,
    is_square_in_qp,
    poly_eval,
    poly_shift_scale,
    squarefree_divisors,
    squarefree_part,
)
from ranktool.curve import Curve, DescentModel, O, Point, to_descent_model, two_torsion_models
from ranktool.descent import descend_one_side, is_subgroup, subgroup_generated, two_isogeny_descent
from ranktool.height import HeightEngine, height_constant
from ranktool.local import everywhere_locally_soluble, qp_soluble
from ranktool.rank import analyse


class TestArith(unittest.TestCase):
    def test_is_square(self):
        for n in range(0, 400):
            self.assertEqual(is_square(n), int(n ** 0.5 + 0.5) ** 2 == n, n)
        self.assertFalse(is_square(-4))
        self.assertTrue(is_square(10 ** 20))

    def test_squarefree_part(self):
        self.assertEqual(squarefree_part(12), 3)
        self.assertEqual(squarefree_part(-50), -2)
        self.assertEqual(squarefree_part(1), 1)
        self.assertEqual(squarefree_part(-1), -1)

    def test_squarefree_divisors(self):
        self.assertEqual(sorted(squarefree_divisors(12)),
                         sorted([1, -1, 2, -2, 3, -3, 6, -6]))
        for d in squarefree_divisors(360):
            self.assertEqual(360 % d, 0)
            self.assertEqual(abs(squarefree_part(d)), abs(d))

    def test_is_square_in_qp(self):
        # p odd: units are squares iff QR; valuation must be even
        self.assertTrue(is_square_in_qp(4, 5))
        self.assertFalse(is_square_in_qp(5, 5))
        self.assertTrue(is_square_in_qp(25, 5))
        self.assertFalse(is_square_in_qp(2, 5))     # 2 is not a QR mod 5
        self.assertTrue(is_square_in_qp(-1, 5))     # -1 = 4 is a QR mod 5
        # p = 2: odd squares are exactly 1 mod 8
        self.assertTrue(is_square_in_qp(17, 2))
        self.assertFalse(is_square_in_qp(3, 2))
        self.assertTrue(is_square_in_qp(-7, 2))     # -7 = 1 mod 8
        self.assertTrue(is_square_in_qp(0, 7))

    def test_poly_shift_scale(self):
        f = (1, 2, 3)  # 1 + 2x + 3x^2
        g = poly_shift_scale(f, 5, 7)
        for t in range(-3, 4):
            self.assertEqual(poly_eval(g, t), poly_eval(f, 5 + 7 * t))


class TestCurve(unittest.TestCase):
    def setUp(self):
        self.E = Curve(0, 0, 0, -25, 0)
        self.P = Point(F(-4), F(6))

    def test_on_curve(self):
        self.assertTrue(self.E.is_on(self.P))
        self.assertFalse(self.E.is_on(Point(F(-4), F(7))))

    def test_group_law_associative(self):
        pts = [self.E.mul(k, self.P) for k in range(1, 5)] + [O, Point(F(0), F(0))]
        for A in pts:
            for B in pts:
                for C in pts:
                    self.assertEqual(
                        self.E.add(self.E.add(A, B), C),
                        self.E.add(A, self.E.add(B, C)),
                    )

    def test_inverse_and_identity(self):
        for k in range(1, 6):
            Q = self.E.mul(k, self.P)
            self.assertTrue(self.E.is_on(Q))
            self.assertEqual(self.E.add(Q, self.E.neg(Q)), O)
            self.assertEqual(self.E.add(Q, O), Q)

    def test_two_torsion(self):
        self.assertEqual(sorted(self.E.two_torsion_x()), [F(-5), F(0), F(5)])
        self.assertEqual(Curve(0, 0, 0, 1, 0).two_torsion_x(), [F(0)])

    def test_transform_is_isomorphism(self):
        Et = self.E.transform(2, 3, 1, -4)
        # the j-invariant is an isomorphism invariant
        self.assertEqual(Et.j, self.E.j)

    def test_descent_model_roundtrip(self):
        for which in range(3):
            conv = to_descent_model(self.E, which)
            self.assertIsNotNone(conv)
            m, to_m, from_m = conv
            self.assertEqual(m.b, m.b)
            for k in range(1, 5):
                P = self.E.mul(k, self.P)
                Q = to_m(P)
                self.assertTrue(m.curve.is_on(Q))
                self.assertEqual(from_m(Q), P)

    def test_descent_model_is_group_homomorphism(self):
        m, to_m, from_m = to_descent_model(self.E)
        pts = [self.E.mul(k, self.P) for k in range(1, 4)] + [Point(F(0), F(0)), O]
        for A in pts:
            for B in pts:
                self.assertEqual(to_m(self.E.add(A, B)),
                                 m.curve.add(to_m(A), to_m(B)))

    def test_isogeny_composition_is_doubling(self):
        m = DescentModel(0, -25)
        for x in (-4, -5, 9, 45):
            val = x * (x * x + m.a * x + m.b)
            if val < 0 or not is_square(val):
                continue
            P = Point(F(x), F(int(val ** 0.5)))
            self.assertTrue(m.curve.is_on(P))
            self.assertEqual(m.phi_hat(m.phi(P)), m.curve.dbl(P))

    def test_two_torsion_models_count(self):
        self.assertEqual(len(two_torsion_models(self.E)), 3)
        self.assertEqual(len(two_torsion_models(Curve(0, 0, 0, 1, 0))), 1)


class TestLocal(unittest.TestCase):
    def test_lind_reichardt_is_everywhere_locally_soluble(self):
        # w^2 = 2u^4 - 34v^4 (i.e. 2y^2 = x^4 - 17): the classical curve that
        # has points everywhere locally but none globally.
        ok, certain, _ = everywhere_locally_soluble(2, 0, -34)
        self.assertTrue(ok)
        self.assertTrue(certain)

    def test_real_obstruction(self):
        ok, certain, wit = everywhere_locally_soluble(-1, 0, -1)
        self.assertFalse(ok)
        self.assertEqual(wit["obstruction"], "R")

    def test_p_adic_obstruction(self):
        # w^2 = 3(u^4 + v^4) has no Q_2 point
        ok, _, wit = everywhere_locally_soluble(3, 0, 3)
        self.assertFalse(ok)
        self.assertTrue(wit["obstruction"].startswith("Q_"))

    def test_trivially_soluble(self):
        self.assertTrue(everywhere_locally_soluble(1, 0, 1)[0])
        self.assertTrue(qp_soluble([1, 0, 0, 0, 1], 2)[0])

    def test_soluble_when_a_square_value_exists(self):
        # d = 1 always works: (u,v,w) = (1,0,1)
        for p in (2, 3, 5, 7, 11):
            self.assertTrue(qp_soluble([1, 0, 5, 0, 7], p)[0])


class TestDescent(unittest.TestCase):
    def test_selmer_is_a_subgroup(self):
        for a, b in [(0, -1), (0, -25), (-102, 2312), (0, -68), (3, -7), (5, 6)]:
            r = descend_one_side(a, b)
            self.assertTrue(is_subgroup(r.selmer), (a, b, r.selmer))

    def test_realised_inside_selmer(self):
        for a, b in [(0, -1), (0, -25), (-102, 2312), (0, -68)]:
            r = descend_one_side(a, b)
            for d in r.realised:
                self.assertIn(d, r.selmer)

    def test_subgroup_generated(self):
        self.assertEqual(subgroup_generated([2, 3]), [1, 2, 3, 6])
        self.assertEqual(subgroup_generated([1]), [1])
        self.assertEqual(subgroup_generated([-1, 2]), [-2, -1, 1, 2])

    def test_congruent_curve_rank_one_descent(self):
        m = DescentModel(-15, 50)  # from y^2 = x^3 - 25x
        d = two_isogeny_descent(m)
        self.assertEqual(d.rank_upper, 1)
        self.assertEqual(d.rank_lower, 1)


class TestHeight(unittest.TestCase):
    def test_constant_is_finite_and_positive(self):
        c, rep = height_constant(-25, 0)
        self.assertGreater(c, 0)
        self.assertNotEqual(rep["resultant"], 0)

    def test_quadraticity(self):
        """hhat(nP) = n^2 hhat(P) -- a strong independent check on the engine."""
        E = Curve(0, 0, 0, -1156, 0)
        he = HeightEngine(E)
        P = E.to_short(Point(F(162), F(-2016)))
        h1 = he.canonical(P)
        for n in (2, 3):
            hn = he.canonical(he.short.mul(n, P))
            lo, hi = n * n * h1.lo, n * n * h1.hi
            self.assertLessEqual(hn.lo, hi + 1e-6, f"n={n}")
            self.assertLessEqual(lo, hn.hi + 1e-6, f"n={n}")

    def test_torsion_has_zero_height(self):
        E = Curve(0, 0, 0, -25, 0)
        he = HeightEngine(E)
        T = E.to_short(Point(F(5), F(0)))
        h = he.canonical(T)
        self.assertLessEqual(h.lo, 0.0)
        self.assertGreaterEqual(h.hi, 0.0)

    def test_independence_certificate(self):
        E = Curve(0, 0, 0, -1156, 0)
        he = HeightEngine(E)
        P = E.to_short(Point(F(162), F(-2016)))
        Qp = E.to_short(Point(F(153, 4), F(-867, 8)))
        ok, det = he.independent([P, Qp])
        self.assertTrue(ok)
        self.assertGreater(det.lo, 0)

    def test_dependent_points_are_not_certified(self):
        E = Curve(0, 0, 0, -1156, 0)
        he = HeightEngine(E)
        P = E.to_short(Point(F(162), F(-2016)))
        ok, det = he.independent([P, he.short.mul(2, P)])
        self.assertFalse(ok)


class TestRank(unittest.TestCase):
    KNOWN = {1: 0, 2: 0, 3: 0, 4: 0, 5: 1, 6: 1, 7: 1, 13: 1, 14: 1, 15: 1,
             34: 2, 41: 2, 65: 2}

    def test_known_congruent_number_ranks(self):
        for n, r in self.KNOWN.items():
            c = analyse(Curve(0, 0, 0, -n * n, 0))
            self.assertTrue(c.certified, f"n={n} not certified")
            self.assertEqual(c.rank, r, f"n={n}")

    def test_rank_two_has_two_independent_points(self):
        for n in (34, 41, 65):
            c = analyse(Curve(0, 0, 0, -n * n, 0))
            self.assertEqual(c.rank, 2)
            self.assertIsNotNone(c.independent_pair, f"n={n}")
            self.assertEqual(len(c.independent_pair), 2)
            self.assertGreater(c.regulator.lo, 0)
            for P in c.independent_pair:
                self.assertTrue(c.curve.is_on(P))

    def test_reported_points_really_lie_on_the_curve(self):
        for n in (5, 6, 7, 34, 41):
            E = Curve(0, 0, 0, -n * n, 0)
            c = analyse(E)
            for P in c.points:
                self.assertTrue(E.is_on(P), (n, P))
                self.assertIsNone(E.order_of(P, 16))  # infinite order

    def test_sha_obstruction_reported_honestly(self):
        """y^2 = x^3 - 68x has Sha[2] != 0.  The tool must NOT claim a rank."""
        c = analyse(Curve(0, 0, 0, -68, 0))
        self.assertFalse(c.certified)
        self.assertIsNone(c.rank)
        self.assertEqual(c.rank_lower, 0)
        self.assertEqual(c.rank_upper, 2)

    def test_model_invariance(self):
        for tup in [(0, 0, 0, -1, 0), (0, 0, 0, -25, 0), (0, 0, 0, -1156, 0),
                    (0, 0, 0, -68, 0)]:
            E = Curve(*tup)
            base = analyse(E)
            for (u, r, s, t) in [(1, 3, 0, 0), (2, -1, 1, 2), (3, 2, -1, 5)]:
                c = analyse(E.transform(u, r, s, t))
                self.assertEqual((c.rank_lower, c.rank_upper),
                                 (base.rank_lower, base.rank_upper),
                                 f"{tup} under {(u, r, s, t)}")

    def test_no_two_torsion_gives_lower_bound_only(self):
        E = Curve(0, 0, 1, -1, 0)  # 37a1, rank 1, trivial torsion, no 2-torsion
        c = analyse(E)
        self.assertIsNone(c.rank_upper)
        self.assertGreaterEqual(c.rank_lower, 1)
        self.assertFalse(c.certified)


class TestCLI(unittest.TestCase):
    def test_cli_runs(self):
        from ranktool.cli import main
        self.assertEqual(main(["--congruent", "34", "--quiet"]), 0)
        self.assertEqual(main(["--short", "-1", "0", "--quiet"]), 0)
        self.assertEqual(main(["--short", "-68", "0", "--quiet"]), 2)  # undecided


if __name__ == "__main__":
    unittest.main(verbosity=2)
