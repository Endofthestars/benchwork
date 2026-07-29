import random
import unittest

from benchwork.alembic import _student_t_cdf, _student_t_critical

try:
    from scipy import stats
except ImportError:  # pragma: no cover - exercised by the dedicated CI oracle job
    stats = None


@unittest.skipUnless(stats is not None, "SciPy oracle dependency is not installed")
class AlembicScipyOracleTest(unittest.TestCase):
    def test_critical_values_match_scipy_reference_grid(self) -> None:
        levels = (0.80, 0.90, 0.95, 0.99)
        degrees = (1, 2, 3, 5, 10, 30, 1000)
        for degree in degrees:
            previous = 0.0
            for level in levels:
                with self.subTest(degrees_of_freedom=degree, level=level):
                    expected = float(stats.t.ppf(0.5 + level / 2.0, degree))
                    actual = _student_t_critical(level, degree)
                    self.assertAlmostEqual(actual, expected, delta=1e-10)
                    self.assertGreater(actual, previous)
                    previous = actual

    def test_cdf_matches_scipy_for_deterministic_random_samples(self) -> None:
        generator = random.Random(20260730)
        for sample in range(100):
            degree = 10 ** generator.uniform(0.0, 3.0)
            value = generator.uniform(-20.0, 20.0)
            with self.subTest(sample=sample, degrees_of_freedom=degree, value=value):
                expected = float(stats.t.cdf(value, degree))
                actual = _student_t_cdf(value, degree)
                self.assertAlmostEqual(actual, expected, delta=1e-11)

    def test_cdf_is_monotonic_across_extreme_values(self) -> None:
        values = (-1_000.0, -100.0, -10.0, -1.0, 0.0, 1.0, 10.0, 100.0, 1_000.0)
        for degree in (1, 2, 30, 1000):
            probabilities = [_student_t_cdf(value, degree) for value in values]
            self.assertEqual(probabilities, sorted(probabilities))
            self.assertTrue(all(0.0 <= probability <= 1.0 for probability in probabilities))


if __name__ == "__main__":
    unittest.main()
