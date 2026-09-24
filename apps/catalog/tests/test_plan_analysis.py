from django.test import SimpleTestCase

from apps.catalog.search.plan_analysis import (
    build_plan_report,
    estimation_factor,
)


class PlanAnalysisTests(SimpleTestCase):

    def test_estimation_factor(self):
        self.assertEqual(estimation_factor(10, 100), 10)
        self.assertEqual(estimation_factor(100, 10), 10)

    def test_estimation_factor_handles_zero(self):
        self.assertIsNone(estimation_factor(0, 10))

    def test_nested_plan_is_flattened(self):
        explain_result = [
            {
                "Plan": {
                    "Node Type": "Sort",
                    "Plan Rows": 5,
                    "Actual Rows": 5,
                    "Actual Total Time": 1.2,
                    "Plans": [
                        {
                            "Node Type": "Index Scan",
                            "Relation Name": "catalog_product",
                            "Index Name": "product_slug_idx",
                            "Plan Rows": 5,
                            "Actual Rows": 5,
                            "Actual Total Time": 0.8,
                            "Plans": [],
                        }
                    ],
                },
                "Planning Time": 0.2,
                "Execution Time": 1.4,
            }
        ]

        report = build_plan_report(explain_result)

        self.assertEqual(report.execution_time_ms, 1.4)
        self.assertEqual(len(report.nodes), 2)
        self.assertEqual(report.nodes[0].node_type, "Sort")
        self.assertEqual(report.nodes[1].node_type, "Index Scan")