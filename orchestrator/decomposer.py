from typing import Optional, List
from state.schemas import Decision, Task
from orchestrator.dag import TaskDAG, DAGValidationError

ALL_SPECIALISTS = ["cfo", "growth", "cto", "customer", "product"]

def decompose_decision(
    decision: Decision,
    selected_specialists: Optional[List[str]] = None
) -> TaskDAG:
    dag = TaskDAG()

    if decision.type == "unsupported":
        raise DAGValidationError(
            f"VentureTwin v0.1 MVP specializes in Freemium / Free Plan packaging decisions. "
            f"Price change elasticity modeling is planned for v0.2 roadmap. (Query: {decision.question})"
        )
    if decision.type == "ambiguous" or (decision.classification and decision.classification.category in ["ambiguous", "insufficient_data"]):
        raise DAGValidationError(
            f"Clarification Required: {decision.objective}"
        )

    # Determine active specialists from argument, metadata, or default to all 5
    specs_to_use = selected_specialists
    if not specs_to_use and decision.metadata and isinstance(decision.metadata, dict):
        specs_to_use = decision.metadata.get("selected_specialists")

    if specs_to_use:
        active_specs = [s for s in ALL_SPECIALISTS if s in specs_to_use]
        if not active_specs:
            active_specs = ALL_SPECIALISTS
    else:
        active_specs = ALL_SPECIALISTS

    # 1. Parallel specialist analysis tasks (dynamically routed)
    analysis_tasks = [
        Task(id=f"task_{agent}_analysis", owner_agent=agent, depends_on=[], kind="agent_analysis")
        for agent in active_specs
    ]
    for t in analysis_tasks:
        dag.add_task(t)

    analysis_ids = [t.id for t in analysis_tasks]

    # 2. Skeptic Audit (depends on all selected analysis tasks)
    dag.add_task(Task(
        id="task_skeptic_audit",
        owner_agent="skeptic",
        depends_on=analysis_ids,
        kind="skeptic_audit"
    ))

    # 3. Agent Discussion & Rebuttal Node (bounded 1-round peer challenge)
    dag.add_task(Task(
        id="task_agent_discussion",
        owner_agent="supervisor",
        depends_on=["task_skeptic_audit"],
        kind="discussion"
    ))

    # 4. Conflict Detection and Simulation Resolution
    dag.add_task(Task(
        id="task_conflict_resolution",
        owner_agent="supervisor",
        depends_on=["task_agent_discussion"],
        kind="conflict_resolution"
    ))

    # 5. Scenario Simulation Engine
    dag.add_task(Task(
        id="task_simulation_engine",
        owner_agent="supervisor",
        depends_on=["task_conflict_resolution"],
        kind="simulation"
    ))

    # 6. Report Draft Generation
    dag.add_task(Task(
        id="task_report_draft",
        owner_agent="supervisor",
        depends_on=["task_simulation_engine"],
        kind="report_draft"
    ))

    # 7. Workflow Verification Layer (Audits Draft Report)
    dag.add_task(Task(
        id="task_workflow_verification",
        owner_agent="skeptic",
        depends_on=["task_report_draft"],
        kind="verification"
    ))

    # 8. Report Finalization & Cryptographic Stamping
    dag.add_task(Task(
        id="task_report_finalize",
        owner_agent="supervisor",
        depends_on=["task_workflow_verification"],
        kind="report_finalize"
    ))

    # Validate DAG integrity
    dag.validate()
    return dag
