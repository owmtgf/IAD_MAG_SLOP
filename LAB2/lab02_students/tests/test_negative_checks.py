"""Самостоятельные негативные проверки evaluator для ЛР2."""
import copy
import importlib
import json
import os
from pathlib import Path
import unittest

from core import Environment, ScriptedPolicy


impl = importlib.import_module(os.environ.get("MAS_IMPL", "student"))
CASES = json.loads((Path(__file__).resolve().parents[1] / "data/dev.json").read_text())


class NegativeEvaluatorChecks(unittest.TestCase):
    def valid_done(self):
        result = impl.run_agent(ScriptedPolicy(), Environment(CASES[0]))
        self.assertTrue(impl.evaluate(result))
        return result

    def test_rejects_wrong_ticket_id(self):
        result = self.valid_done()
        result["state"]["proposal"]["ticket_id"] = "forged-ticket"
        result["state"]["validation"]["proposal"] = copy.deepcopy(result["state"]["proposal"])
        self.assertFalse(impl.evaluate(result))

    def test_rejects_wrong_policy_id(self):
        result = self.valid_done()
        result["state"]["proposal"]["policy_id"] = "P999"
        result["state"]["validation"]["proposal"] = copy.deepcopy(result["state"]["proposal"])
        self.assertFalse(impl.evaluate(result))

    def test_rejects_resource_without_required_skill(self):
        result = self.valid_done()
        resource = next(r for r in result["state"]["resources"]
                        if r["id"] == result["state"]["proposal"]["resource_id"])
        resource["skills"] = ["design"]
        self.assertFalse(impl.evaluate(result))

    def test_rejects_cost_above_budget(self):
        result = self.valid_done()
        result["state"]["ticket"]["budget"] = 1
        self.assertFalse(impl.evaluate(result))

    def test_rejects_validation_for_another_proposal(self):
        result = self.valid_done()
        result["state"]["validation"]["proposal"]["resource_id"] = "R1"
        self.assertFalse(impl.evaluate(result))


if __name__ == "__main__":
    unittest.main()
