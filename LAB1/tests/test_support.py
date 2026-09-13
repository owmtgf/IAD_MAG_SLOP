import unittest
from core import exact, evaluate, validate_costs, make_contractors, validate_order
from starter import independent
C = [[1,2,9],[2,15,2],[9,14,1]]

class SupportTests(unittest.TestCase):
    def test_exact(self):
        self.assertEqual(exact(C).assignment, [1,0,2])
    def test_independent(self):
        self.assertEqual(independent(C).assignment, [0,0,2])
    def test_invalid_cost_not_scored(self):
        m = evaluate(C, independent(C), 5)
        self.assertFalse(m['feasible']); self.assertIsNone(m['cost'])
        self.assertIsNone(m['gap_pct']); self.assertEqual(m['proposal_cost'],4)
        self.assertEqual(m['conflicts'],1)
    def test_bad_matrices(self):
        for c in [[], [[1,2]], [[0]], [[-1]], [[True]], [[1.0]]]:
            with self.subTest(c=c), self.assertRaises(ValueError): validate_costs(c)
    def test_bad_order(self):
        for o in [[0,0,2], [0,1], [True,0,2]]:
            with self.subTest(o=o), self.assertRaises(ValueError): validate_order(o,3)
    def test_agent_state(self):
        a=make_contractors(C)[0]
        self.assertEqual(a.propose(1),2); a.accept(1)
        self.assertIsNone(a.propose(0))
        with self.assertRaises(ValueError): a.accept(2)

if __name__ == '__main__': unittest.main()
