import copy
import importlib
import json
import os
from pathlib import Path
import unittest
from core import Environment, ScriptedPolicy, ReplayPolicy, tool, finish

impl = importlib.import_module(os.environ.get("MAS_IMPL", "student"))
CASES = json.loads((Path(__file__).resolve().parents[1]/"data/dev.json").read_text())

class StudentTests(unittest.TestCase):
    def run_case(self, index=0, policy=None, limit=12):
        return impl.run_agent(policy or ScriptedPolicy(), Environment(CASES[index]), limit)

    def test_normal(self):
        result = self.run_case()
        self.assertEqual(result["status"], "done")
        self.assertTrue(impl.evaluate(result))

    def test_missing_skill(self):
        result = self.run_case(1)
        self.assertEqual(result["status"], "needs_input")
        self.assertTrue(impl.evaluate(result))

    def test_no_resource(self):
        self.assertTrue(impl.evaluate(self.run_case(2)))

    def test_transient_read(self):
        result = self.run_case(3)
        self.assertTrue(impl.evaluate(result))
        self.assertTrue(any(e.get("observation", {}).get("error") == "temporary_unavailable" for e in result["history"]))

    def test_stale_resource(self):
        result = self.run_case(4)
        self.assertTrue(impl.evaluate(result))
        self.assertNotEqual(result["state"]["proposal"]["resource_id"], "R0")

    def test_malformed_consumes_steps(self):
        result = self.run_case(policy=ReplayPolicy(["not json"]*6), limit=3)
        self.assertEqual(result["status"], "budget_exhausted")
        self.assertEqual(result["steps"], 3)
        self.assertFalse(impl.evaluate(result))

    def test_unknown_tool_not_executed(self):
        env = Environment(CASES[0])
        result = impl.run_agent(ReplayPolicy([tool("shell", command="x")]), env, 1)
        self.assertEqual(env.calls, [])
        self.assertEqual(result["history"][0]["observation"]["error"], "unknown_tool")

    def test_false_finish(self):
        result = self.run_case(policy=ReplayPolicy([finish("done")]), limit=1)
        self.assertEqual(result["status"], "budget_exhausted")
        self.assertFalse(impl.evaluate(result))

    def test_last_step_finish(self):
        result = self.run_case(limit=6)
        self.assertEqual(result["steps"], 6)
        self.assertTrue(impl.evaluate(result))

    def test_zero_budget(self):
        result = self.run_case(limit=0)
        self.assertEqual(result["steps"], 0)
        self.assertFalse(impl.evaluate(result))

    def test_model_error(self):
        class Broken:
            def next_action(self, history):
                raise TimeoutError("demo")
        result = self.run_case(policy=Broken())
        self.assertEqual(result["status"], "model_error")
        self.assertEqual(result["steps"], 1)

    def test_evaluator_rejects_forged_cost(self):
        result = self.run_case()
        result["state"]["proposal"]["cost"] = -1
        result["state"]["validation"]["proposal"] = copy.deepcopy(result["state"]["proposal"])
        self.assertFalse(impl.evaluate(result))

    def test_evaluator_rejects_stale_validation(self):
        result = self.run_case()
        result["state"]["version"] += 1
        self.assertFalse(impl.evaluate(result))

    def test_evaluator_rejects_false_no_solution(self):
        result = self.run_case(policy=ReplayPolicy([finish("no_solution")]))
        self.assertFalse(impl.evaluate(result))

    def test_evaluator_rejects_unneeded_question(self):
        result = self.run_case(policy=ReplayPolicy([finish("needs_input", "Какой навык нужен?")]))
        self.assertFalse(impl.evaluate(result))

    def test_isolation(self):
        first = self.run_case(4)
        second = self.run_case(4)
        self.assertEqual(first["state"], second["state"])

if __name__ == "__main__":
    unittest.main()
