from apps.catalog.search.plan_analysis import QueryPlanReport


def format_plan_report(report: QueryPlanReport) -> str:
    lines = []

    lines.append("SEARCH QUERY PLAN")
    lines.append("=" * 60)

    lines.append(
        f"Planning Time: {report.planning_time_ms:.3f} ms"
        if report.planning_time_ms is not None
        else "Planning Time: N/A"
    )

    lines.append(
        f"Execution Time: {report.execution_time_ms:.3f} ms"
        if report.execution_time_ms is not None
        else "Execution Time: N/A"
    )

    lines.append("")

    for index, node in enumerate(report.nodes, start=1):
        lines.append(f"[{index}] {node.node_type}")

        if node.relation_name:
            lines.append(f"    Relation: {node.relation_name}")

        if node.index_name:
            lines.append(f"    Index: {node.index_name}")

        lines.append(f"    Estimated rows: {node.estimated_rows}")

        lines.append(f"    Actual rows: {node.actual_rows}")

        lines.append(f"    Actual time: {node.actual_total_time_ms} ms")

        lines.append(f"    Loops: {node.loops}")

        lines.append(f"    Shared hit: {node.shared_hit_blocks}")

        lines.append(f"    Shared read: {node.shared_read_blocks}")

        lines.append(f"    Estimation factor: {node.estimation_factor}")

        lines.append("")

    return "\n".join(lines)