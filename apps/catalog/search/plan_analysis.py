from dataclasses import dataclass


@dataclass(frozen=True)
class PlanNodeReport:
    node_type: str
    relation_name: str | None
    index_name: str | None

    estimated_rows: float | None
    actual_rows: float | None

    estimated_total_cost: float | None
    actual_total_time_ms: float | None

    loops: int | None

    shared_hit_blocks: int
    shared_read_blocks: int

    rows_estimation_ratio: float | None
    estimation_factor: float | None


IMPORTANT_NODE_TYPES = frozenset(
    {
        "Seq Scan",
        "Index Scan",
        "Index Only Scan",
        "Bitmap Index Scan",
        "Bitmap Heap Scan",
        "Sort",
        "Incremental Sort",
        "Nested Loop",
        "Hash Join",
        "Merge Join",
    }
)


def _rows_ratio(estimated: float | None, actual: float | None) -> float | None:
    if estimated is None or actual is None:
        return None
    if estimated == 0:
        return None
    return actual / estimated


def _estimation_factor(estimated: float | None, actual: float | None) -> float | None:
    if estimated is None or actual is None or estimated <= 0 or actual <= 0:
        return None
    return max(actual / estimated, estimated / actual)


def flatten_plan(node: dict) -> tuple[PlanNodeReport, ...]:
    current = PlanNodeReport(
        node_type=node.get("Node Type", "Unknown"),
        relation_name=node.get("Relation Name"),
        index_name=node.get("Index Name"),
        estimated_rows=node.get("Plan Rows"),
        actual_rows=node.get("Actual Rows"),
        estimated_total_cost=node.get("Total Cost"),
        actual_total_time_ms=node.get("Actual Total Time"),
        loops=node.get("Actual Loops"),
        shared_hit_blocks=node.get("Shared Hit Blocks", 0),
        shared_read_blocks=node.get("Shared Read Blocks", 0),
        rows_estimation_ratio=_rows_ratio(
            node.get("Plan Rows"), node.get("Actual Rows")
        ),
        estimation_factor=_estimation_factor(
            node.get("Plan Rows"), node.get("Actual Rows")
        ),
    )

    children = []
    for child in node.get("Plans", []):
        children.extend(flatten_plan(child))

    return (current,) + children


class QueryPlanReport:
    planning_time_ms: float | None
    execution_time_ms: float | None
    nodes: tuple[PlanNodeReport, ...]

    def __init__(
        self,
        planning_time_ms: float | None,
        execution_time_ms: float | None,
        nodes: tuple[PlanNodeReport, ...],
    ):
        self.planning_time_ms = planning_time_ms
        self.execution_time_ms = execution_time_ms
        self.nodes = nodes


def build_plan_report(explain_result: list[dict]) -> QueryPlanReport:
    root = explain_result[0]
    nodes = flatten_plan(root["Plan"])
    return QueryPlanReport(
        planning_time_ms=root.get("Planning Time"),
        execution_time_ms=root.get("Execution Time"),
        nodes=tuple(nodes),
    )