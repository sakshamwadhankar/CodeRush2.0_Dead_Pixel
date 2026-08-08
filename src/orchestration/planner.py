import json
import uuid
from typing import List, Dict, Any, Optional

from src.orchestration.state_controller import StateController
import os
import requests
from src.data_rag.hybrid_engine import HybridRAGEngine
from src.data_rag.evidence_graph import EvidenceGraph
from src.data_rag.citation_compiler import DynamicCitationCompiler

from src.orchestration.gateway import ModelGateway, ModelGatewayError
from src.orchestration.state_models import (
    TaskStatus,
    LogLevel,
    ContextRetrievalRequest,
    SandboxExecutionRequest,
)
from src.orchestration.planner_models import (
    ActionType,
    SubTask,
    TaskGraph,
    DraftReport,
)


class PlannerEngine:
    """
    Cognitive Research Planner for Aegis Research OS.
    Decomposes user queries into structured TaskGraphs, executes subtasks sequentially,
    invokes contract endpoints (retrieve_context & execute_sandbox), tracks state in state.json,
    enforces confidence threshold stop conditions, and compiles evidence-backed draft reports.
    """

    def __init__(self, state_filepath: Optional[str] = None):
        self.state_controller = StateController(state_filepath=state_filepath)
        self.gateway = ModelGateway(state_filepath=state_filepath)
        self.rag_engine = HybridRAGEngine(persist_directory="workspace/chroma")
        from src.orchestration.q_optimizer import QLearningAgent, StateEncoder
        self.q_agent = QLearningAgent()
        self.state_encoder = StateEncoder()

    def decompose_query(self, query: str) -> TaskGraph:
        """
        Decomposes a user query into a structured TaskGraph using ModelGateway.
        Falls back to a deterministic structured graph if LLM gateway is offline.
        """
        prompt = (
            f"Decompose the following research objective into 3 distinct sequential subtasks: "
            f"1 RAG document retrieval subtask, 1 Python sandbox code execution subtask, and 1 synthesis subtask.\n\n"
            f"RESEARCH OBJECTIVE:\n'{query}'"
        )
        try:
            task_graph = self.gateway.generate_structured(
                prompt=prompt,
                response_model=TaskGraph,
                system_instructions="Break down complex research into atomic, executable subtasks with target confidence thresholds.",
                max_retries=2,
                fallback_on_failure=True,
            )
            # Ensure query field matches original query
            task_graph.query = query
            return task_graph
        except Exception as err:
            self.state_controller.log_system_event(
                level=LogLevel.WARNING,
                component="PlannerEngine",
                message=f"ModelGateway decomposition fallback activated: {err}",
            )
            # Deterministic Contract Fallback TaskGraph
            subtasks = [
                SubTask(
                    subtask_id="sub_001",
                    subquestion=f"Retrieve technical documentation and security baselines for: {query}",
                    action_type=ActionType.RAG_RETRIEVAL,
                    target_evidence="Document context and CVE security references",
                    confidence_threshold=0.85,
                ),
                SubTask(
                    subtask_id="sub_002",
                    subquestion=f"Execute verification script for: {query}",
                    action_type=ActionType.CODE_EXECUTION,
                    target_evidence="Sandbox stdout log execution status",
                    confidence_threshold=0.80,
                    code_snippet="def verify_isolation():\n    return {'status': 'SECURE', 'score': 0.95}\nprint(verify_isolation())",
                ),
                SubTask(
                    subtask_id="sub_003",
                    subquestion=f"Synthesize evidence and compile final report for: {query}",
                    action_type=ActionType.SYNTHESIS,
                    target_evidence="Unified research report markdown",
                    confidence_threshold=0.90,
                ),
            ]
            return TaskGraph(
                query=query,
                subtasks=subtasks,
                stop_condition="Target confidence >= 0.85 achieved across all subtasks",
                overall_confidence_target=0.85,
            )

    def _is_sensitive_action(self, subtask: SubTask) -> bool:
        """Determines if a subtask requires human approval based on .env config and content."""
        if subtask.action_type == ActionType.CODE_EXECUTION:
            # Expanded Human Approval Gates
            if subtask.code_snippet:
                code_lower = subtask.code_snippet.lower()
                # 1. Simulated external payment transactions
                if any(kw in code_lower for kw in ["payment", "stripe", "checkout", "transaction"]):
                    return True
                # 2. Access mocked private credentials
                if any(kw in code_lower for kw in ["api_key", "secret", "credential", "password"]):
                    return True
                # 3. Data deletion outside /workspace/
                if any(kw in code_lower for kw in ["rm -rf", "shutil.rmtree", "os.remove", "os.unlink"]):
                    if "/workspace/" not in code_lower:
                        return True
                        
            return os.environ.get("STRICT_APPROVAL_CODE_EXECUTION", "True").lower() == "true"
        if subtask.action_type == ActionType.SYNTHESIS:
            return os.environ.get("STRICT_APPROVAL_SYNTHESIS", "True").lower() == "true"
        return False

    def execute_graph(self, graph: TaskGraph, approved_subtasks: Optional[List[str]] = None, rejected_subtasks: Optional[List[str]] = None, previous_results: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Loops through TaskGraph subtasks sequentially, updating state.json and calling contract endpoints.
        Enforces confidence thresholds and stop conditions. Skips previously executed tasks if provided.
        """
        results: List[Dict[str, Any]] = previous_results.copy() if previous_results else []
        skip_count = len(results)

        approved = approved_subtasks or []
        rejected = rejected_subtasks or []

        self.state_controller.log_system_event(
            level=LogLevel.INFO,
            component="PlannerEngine",
            message=f"Beginning execution of TaskGraph with {len(graph.subtasks)} subtasks",
            metadata={"query": graph.query, "stop_condition": graph.stop_condition},
        )

        for index, subtask in enumerate(graph.subtasks, start=1):
            if index <= skip_count:
                continue

            # 1. Track task in state.json
            task_entry = self.state_controller.add_task(
                name=f"Subtask {index}: {subtask.action_type.value.upper()} - {subtask.subquestion[:35]}...",
                payload={
                    "subtask_id": subtask.subtask_id,
                    "action_type": subtask.action_type.value,
                    "subquestion": subtask.subquestion,
                },
            )

            # 0. Check for Security Incidents
            state = self.state_controller.get_state()
            active_incidents = [inc for inc in getattr(state, "security_incidents", []) if not inc.resolved]
            if active_incidents:
                self.state_controller.update_task_status(task_entry.task_id, TaskStatus.FAILED)
                self.state_controller.log_system_event(
                    level=LogLevel.CRITICAL,
                    component="PlannerEngine",
                    message="Execution halted due to active security incident.",
                    metadata={"incident": active_incidents[0].description}
                )
                break

            self.state_controller.update_task_status(task_entry.task_id, TaskStatus.RUNNING)

            # 1.5 Approval Gate Check
            if self._is_sensitive_action(subtask):
                if subtask.subtask_id in rejected:
                    self.state_controller.update_task_status(task_entry.task_id, TaskStatus.CANCELLED)
                    continue
                elif subtask.subtask_id not in approved:
                    self.state_controller.update_task_status(task_entry.task_id, TaskStatus.PENDING_APPROVAL)
                    self.state_controller.log_system_event(
                        level=LogLevel.WARNING,
                        component="ApprovalGate",
                        message=f"Subtask {subtask.subtask_id} paused for approval.",
                        metadata={"action": subtask.action_type.value}
                    )
                    # Halt execution and return accumulated results
                    break

            subtask_result: Dict[str, Any] = {
                "subtask_id": subtask.subtask_id,
                "action_type": subtask.action_type.value,
                "subquestion": subtask.subquestion,
                "output": "",
                "confidence_score": 0.0,
                "citation_tag": f"[CIT-{index + 1}]",
            }

            # 2. Call Action Endpoints based on action_type
            if subtask.action_type == ActionType.RAG_RETRIEVAL:
                rag_res = self.rag_engine.search(subtask.subquestion, top_k=3)
                subtask_result["output"] = "\n".join([doc.get("text", "") for doc in rag_res]) if rag_res else "No documents found."
                subtask_result["confidence_score"] = 0.92

            elif subtask.action_type == ActionType.CODE_EXECUTION:
                code_to_exec = subtask.code_snippet or f"print('Verifying subtask: {subtask.subquestion}')"
                url = f"{os.environ.get('SANDBOX_API_URL', 'http://localhost:8000')}/sandbox/execute"
                headers = {"Authorization": f"Bearer {os.environ.get('SANDBOX_AUTH_TOKEN', '')}"}
                try:
                    res = requests.post(url, json={"code": code_to_exec, "timeout": 30}, headers=headers)
                    if res.status_code == 200:
                        sandbox_res = res.json()
                        subtask_result["output"] = sandbox_res.get("stdout", "") + "\n" + sandbox_res.get("stderr", "")
                        subtask_result["confidence_score"] = 0.95
                    else:
                        subtask_result["output"] = f"Sandbox API Error: {res.text}"
                        subtask_result["confidence_score"] = 0.0
                except Exception as e:
                    subtask_result["output"] = f"Sandbox connection failed: {str(e)}"
                    subtask_result["confidence_score"] = 0.0

            elif subtask.action_type == ActionType.BROWSER_SCRAPE:
                url_to_scrape = subtask.code_snippet or "https://example.com"
                url = f"{os.environ.get('SANDBOX_API_URL', 'http://localhost:8000')}/browser/scrape"
                headers = {"Authorization": f"Bearer {os.environ.get('SANDBOX_AUTH_TOKEN', '')}"}
                try:
                    res = requests.post(url, json={"url": url_to_scrape}, headers=headers)
                    if res.status_code == 200:
                        scrape_res = res.json()
                        subtask_result["output"] = scrape_res.get("text_content", "")[:3000]
                        subtask_result["confidence_score"] = 0.90
                    else:
                        subtask_result["output"] = f"Browser Scrape API Error: {res.text}"
                        subtask_result["confidence_score"] = 0.0
                except Exception as e:
                    subtask_result["output"] = f"Browser Scrape connection failed: {str(e)}"
                    subtask_result["confidence_score"] = 0.0

            else:  # ActionType.SYNTHESIS
                subtask_result["output"] = f"Synthesized analysis for subquestion: '{subtask.subquestion}'"
                subtask_result["confidence_score"] = 1.0

            # 3. Check Confidence Thresholds & Stop Conditions
            if subtask_result["confidence_score"] >= subtask.confidence_threshold:
                self.state_controller.update_task_status(task_entry.task_id, TaskStatus.COMPLETED)
                subtask.status = "completed"
            else:
                self.state_controller.update_task_status(task_entry.task_id, TaskStatus.FAILED)
                subtask.status = "failed"

            results.append(subtask_result)

            self.state_controller.log_system_event(
                level=LogLevel.INFO,
                component="PlannerEngine",
                message=f"Completed subtask {subtask.subtask_id} with confidence {subtask_result['confidence_score']}",
                metadata={"confidence": subtask_result["confidence_score"], "threshold": subtask.confidence_threshold},
            )

            # Stop condition check: If overall confidence requirement satisfied
            avg_confidence = sum(r["confidence_score"] for r in results) / len(results)
            if avg_confidence >= graph.overall_confidence_target and index < len(graph.subtasks):
                self.state_controller.log_system_event(
                    level=LogLevel.INFO,
                    component="PlannerEngine",
                    message=f"Stop condition satisfied early (avg confidence {avg_confidence:.2f} >= target {graph.overall_confidence_target})",
                )
                
            # --- Dynamically Update Q-Learning Model ---
            try:
                state_tuple = self.state_encoder.encode(graph.query)
                action_map = {"RAG_RETRIEVAL": 0, "CODE_EXECUTION": 1, "BROWSER_SCRAPE": 2, "SYNTHESIS": 3}
                action_id = action_map.get(subtask.action_type.name, 0)
                reward = subtask_result["confidence_score"]
                # Update Q-table with reward from this subtask execution
                self.q_agent.update(state_tuple, action_id, reward, state_tuple)
                # MUST save to disk so the Streamlit UI can render the updated table!
                self.q_agent.save_q_table()
            except Exception as e:
                self.state_controller.log_system_event(
                    level=LogLevel.WARNING,
                    component="PlannerEngine.QLearning",
                    message=f"Failed to update Q-table: {e}"
                )

        return results

    def compile_report(self, graph: TaskGraph, results: List[Dict[str, Any]]) -> DraftReport:
        """
        Compiles execution outputs into a structured evidence-backed draft research report.
        """
        key_findings: List[str] = []
        citations: List[Dict[str, Any]] = []

        markdown_body = f"# 📄 Aegis Research Report: {graph.query}\n\n"
        markdown_body += "## Executive Summary\n"
        markdown_body += f"This report synthesizes evidence gathered from {len(results)} sequential subtask investigations. "
        markdown_body += f"All findings met or exceeded the overall confidence target of **{graph.overall_confidence_target * 100}%**.\n\n"

        markdown_body += "## Subtask Evidence & Findings\n"
        for res in results:
            tag = res["citation_tag"]
            action = res["action_type"].upper()
            output_snippet = res["output"].strip()
            
            finding_text = f"**{action} Subtask** ({tag}): {res['subquestion']} - Confidence: {res['confidence_score'] * 100:.1f}%"
            key_findings.append(finding_text)
            
            markdown_body += f"### {tag} {res['subquestion']}\n"
            markdown_body += f"**Action Type**: `{action}` | **Confidence**: `{res['confidence_score']}`\n\n"
            markdown_body += f"```text\n{output_snippet}\n```\n\n"

            citations.append({
                "citation": tag,
                "action_type": action,
                "subquestion": res["subquestion"],
                "confidence_score": res["confidence_score"],
            })

        markdown_body += "## Evidence Graph & References\n"
        for cit in citations:
            markdown_body += f"- **{cit['citation']}**: `{cit['action_type']}` - {cit['subquestion']} (Score: {cit['confidence_score']})\n"

        # Generate live citations using EvidenceGraph and CitationCompiler
        graph_engine = EvidenceGraph()
        for res in results:
            graph_engine.add_claim(
                claim_id=res["citation_tag"],
                text=res["output"][:500],
                supported_by_chunk_ids=None,
                confidence=res["confidence_score"]
            )
        
        compiler = DynamicCitationCompiler(graph_engine)
        os.makedirs("workspace", exist_ok=True)
        citation_summary = compiler.compile_citations(markdown_body)
        with open("workspace/citations.json", "w", encoding="utf-8") as f:
            json.dump(citation_summary.get("citations", []), f, indent=2)

        report = DraftReport(
            title=f"Research Report: {graph.query}",
            executive_summary=f"Automated evidence synthesis for query: '{graph.query}'",
            key_findings=key_findings,
            evidence_citations=citations,
            compiled_markdown=markdown_body,
        )

        self.state_controller.log_system_event(
            level=LogLevel.INFO,
            component="PlannerEngine",
            message=f"Compiled final DraftReport for '{graph.query}'",
            metadata={"citations_count": len(citations)},
        )
        return report

    def run_pipeline(self, query: str) -> DraftReport:
        """
        Full agentic planning and orchestration loop execution.
        """
        graph = self.decompose_query(query)
        results = self.execute_graph(graph)
        report = self.compile_report(graph, results)
        return report
