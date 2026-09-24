"""Artificial traces test accounting, not Norwegian model performance."""
import unittest
from tools.candidate_audit import audit, classify


def trace(**kw):
    row = dict(id='test', is_error=True, flagged=True, acceptable=['answer'],
               generated=['wrong', 'answer'], ranked=['answer', 'wrong'], displayed=['answer'])
    row.update(kw)
    return row


class AuditTests(unittest.TestCase):
    def test_missing_candidate(self):
        self.assertEqual(classify(trace(generated=['wrong'], ranked=['wrong'], displayed=['wrong']))['outcome'], 'candidate_missing')

    def test_available_but_ranked_fourth(self):
        xs = ['a', 'b', 'c', 'answer']
        self.assertEqual(classify(trace(generated=xs, ranked=xs, displayed=xs[:3]))['outcome'], 'ranking_or_pruning_failure')

    def test_detection_gate(self):
        self.assertEqual(classify(trace(flagged=False, displayed=[]))['outcome'], 'detection_or_display_failure')

    def test_false_alarm_and_no_error_denominator(self):
        result = audit([trace(is_error=False)])['overall']
        self.assertEqual(result['false_alarm_rate']['rate'], 1)
        self.assertIsNone(result['candidate_recall']['rate'])

    def test_rank_denominator_excludes_missing_candidate(self):
        rows = [trace(id='hit'), trace(id='miss', generated=[], ranked=[], displayed=[], flagged=False)]
        result = audit(rows)['overall']
        self.assertEqual(result['candidate_recall']['rate'], .5)
        self.assertEqual(result['conditional_top3']['rate'], 1)
        self.assertEqual(result['end_to_end_displayed_top3']['rate'], .5)

    def test_multiple_acceptable_forms(self):
        self.assertEqual(classify(trace(acceptable=['alternative', 'answer']))['outcome'], 'success')

    def test_invalid_trace_rejected(self):
        for row in [trace(generated=[]), trace(flagged=False), trace(ranked=['answer', 'answer'])]:
            with self.assertRaises(ValueError):
                classify(row)
        with self.assertRaises(ValueError):
            audit([])
        with self.assertRaises(ValueError):
            audit([trace(), trace()])


if __name__ == '__main__':
    unittest.main()
