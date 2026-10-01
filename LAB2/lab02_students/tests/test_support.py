import unittest
from core import parse_action, tool

class SupportTests(unittest.TestCase):
    def test_contract(self):
        self.assertEqual(parse_action(tool("read_ticket"))["args"], {})

    def test_reject_unknown_tool(self):
        with self.assertRaises(ValueError):
            parse_action(tool("shell", command="anything"))

    def test_bad_type(self):
        with self.assertRaises(ValueError):
            parse_action(tool("propose_assignment", resource_id=7))

    def test_extra_field(self):
        with self.assertRaises(ValueError):
            parse_action('{"type":"tool","name":"read_ticket","args":{},"secret":1}')
