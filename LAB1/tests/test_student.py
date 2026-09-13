"""После реализации TODO эти проверки перестанут пропускаться.

SKIP означает незавершённую реализацию, а НЕ успешную сдачу.
"""
import unittest
import starter
from core import make_contractors, evaluate
C = [[1,2,9],[2,15,2],[9,14,1]]

class ImplementationTests(unittest.TestCase):
    def call(self, fn, *args):
        try: return fn(*args)
        except NotImplementedError as e: self.skipTest(str(e))
    def test_greedy_demo(self):
        out=self.call(starter.greedy, C)
        self.assertEqual(out.assignment,[0,1,2])
        m=evaluate(C,out,5)
        self.assertEqual(m['cost'],17); self.assertIsNone(m['messages'])
    def test_cnp_demo(self):
        out=self.call(starter.contract_net,make_contractors(C),[0,1,2])
        self.assertEqual(out.assignment,[0,2,1])
        self.assertEqual(evaluate(C,out,5)['cost'],17)
    def test_cnp_other_order(self):
        out=self.call(starter.contract_net,make_contractors(C),[1,0,2])
        self.assertEqual(out.assignment,[1,0,2])
    def test_message_count(self):
        out=self.call(starter.contract_net,make_contractors(C),[0,1,2])
        self.assertEqual(len(out.messages),21)
        self.assertEqual({m['type'] for m in out.messages},
                         {'CFP','PROPOSE','ACCEPT','REJECT','INFORM'})
        self.assertEqual(sum(m['type']=='ACCEPT' for m in out.messages),3)
    def test_ties(self):
        c=[[1,1,1] for _ in range(3)]
        self.assertEqual(self.call(starter.greedy,c).assignment,[0,1,2])
        self.assertEqual(self.call(starter.contract_net,make_contractors(c),[0,1,2]).assignment,[0,1,2])

if __name__ == '__main__': unittest.main()
