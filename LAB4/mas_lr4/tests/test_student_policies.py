"""Offline routing checks with scripted replies; not LLM evaluation."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from maslab import student_policies as core
from advanced import student_policies as advanced
from advanced.engine import Engine as AdvancedEngine
from test_harness import ScriptedProvider, engine, GOOD, BAD, ROOT, read_json


class StudentPoliciesTests(unittest.TestCase):
    def exercise(self, module, actions, initial_good=False):
        provider = ScriptedProvider(actions)
        if module is core:
            instance = engine(provider)
            if initial_good:
                instance.code = GOOD
            return instance, provider, None
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        folder = Path(temporary.name) / 'M00'
        (folder / 'starter/app').mkdir(parents=True)
        (folder / 'starter/app/__init__.py').write_text('')
        (folder / 'starter/app/api.py').write_text(GOOD if initial_good else BAD)
        (folder / 'SPEC.md').write_text('Return input + 1.')
        (folder / 'task.json').write_text(json.dumps({
            'id': 'fixture', 'editable_files': ['app/api.py', 'app/__init__.py']}))
        (folder / 'visible.json').write_text(json.dumps([
            {'id': 'one', 'input': 2, 'expected': 3}]))
        instance = AdvancedEngine(folder, read_json(ROOT / 'advanced/config.json'),
                                  provider, 1000, 1, Path(temporary.name) / 'out')
        return instance, provider, {}

    def edit(self, module, code):
        return ({'action': 'replace_code', 'code': code} if module is core else
                {'action': 'replace_files', 'files': {'app/api.py': code}})

    def run_policy(self, instance, policy, metadata):
        return instance.execute(policy) if metadata is None else instance.execute(policy, metadata)

    def test_fixed_keeps_all_stages_when_already_correct(self):
        for module in (core, advanced):
            with self.subTest(module=module.__name__):
                instance, provider, metadata = self.exercise(module, [{'action': 'finish'}] * 3, True)
                with patch.object(instance, 'run_role', wraps=instance.run_role) as roles:
                    self.run_policy(instance, module.fixed, metadata)
                self.assertTrue(instance.finished)
                self.assertEqual([call.args[0] for call in roles.call_args_list],
                                 ['programmer', 'reviewer', 'programmer'])

    def test_review_is_explicitly_passed_to_last_programmer(self):
        for module in (core, advanced):
            with self.subTest(module=module.__name__):
                instance, provider, metadata = self.exercise(module, [
                    {'action': 'finish'},
                    {'action': 'yield', 'message': 'REVIEW_SENTINEL: add one'},
                    self.edit(module, GOOD), {'action': 'finish'}])
                self.run_policy(instance, module.fixed, metadata)
                self.assertTrue(instance.finished)
                self.assertIn('REVIEW_SENTINEL', json.dumps(provider.calls[-1]))

    def test_coordinator_recovers_from_invalid_decisions(self):
        invalid = [[], {'action': 'delegate', 'role': 'intruder', 'instruction': 'x'},
                   {'action': 'finish', 'extra': True},
                   {'action': 'delegate', 'role': [], 'instruction': 'x'},
                   {'action': 'delegate', 'role': 'tester', 'instruction': 42}]
        for module in (core, advanced):
            with self.subTest(module=module.__name__):
                instance, provider, metadata = self.exercise(module, invalid + [
                    {'action': 'delegate', 'role': 'developer', 'instruction': 'Fix'},
                    self.edit(module, GOOD), {'action': 'finish'}, {'action': 'finish'}])
                with patch.object(instance, 'run_role', wraps=instance.run_role) as roles:
                    self.run_policy(instance, module.coordinator, metadata)
                self.assertTrue(instance.finished)
                self.assertEqual(roles.call_count, 1)
                self.assertIn('error', provider.calls[1][-1]['content'])

    def test_stale_verification_and_false_finish_do_not_succeed(self):
        for module in (core, advanced):
            with self.subTest(module=module.__name__):
                actions = [
                    {'action': 'delegate', 'role': 'developer', 'instruction': 'Work'},
                    self.edit(module, GOOD), {'action': 'run_tests'}, self.edit(module, BAD),
                ] + [{'action': 'finish'}] * 9
                instance, provider, metadata = self.exercise(module, actions)
                result = self.run_policy(instance, module.coordinator, metadata)
                self.assertFalse(instance.finished)
                self.assertEqual(result['status'], 'unfinished')
                self.assertFalse(instance.current_report()['passed'])
                self.assertEqual(len(provider.calls), 13)

    def test_decision_schema_and_length(self):
        for module in (core, advanced):
            for bad in [None, 'finish', {'action': 'delegate'},
                        {'action': 'delegate', 'role': 'tester', 'instruction': 'x' * 6001},
                        {'action': 'delegate', 'role': 'tester', 'instruction': 'x', 'extra': 1}]:
                with self.subTest(module=module.__name__, bad=repr(bad)[:80]):
                    self.assertIsNotNone(module._decision_error(bad))
            self.assertIsNone(module._decision_error({'action': 'finish'}))

    def test_handoff_keeps_claims_separate_from_current_report(self):
        for module in (core, advanced):
            report = {'passed': True, 'code_sha256': 'old'}
            original = {'message': 'review notes', 'code_sha256': 'old',
                        'finish_requested': True, 'verified_report': report}
            forwarded = module._handoff(original)
            self.assertEqual(forwarded, {
                'message': 'review notes', 'code_sha256': 'old',
                'finish_requested': True})
            self.assertIs(original['verified_report'], report)

    def test_budget_stop_propagates_without_extra_calls(self):
        for module in (core, advanced):
            with self.subTest(module=module.__name__):
                instance, provider, metadata = self.exercise(module, [
                    {'action': 'delegate', 'role': 'developer', 'instruction': 'Fix'}])
                instance.budget = 5
                result = self.run_policy(instance, module.coordinator, metadata)
                self.assertEqual(result['status'], 'budget_exhausted')
                self.assertEqual(len(provider.calls), 1)
