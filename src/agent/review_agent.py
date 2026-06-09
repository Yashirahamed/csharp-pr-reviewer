"""Autonomous Review Agent executing the 6-stage control loop."""
import json
import logging
from typing import Any
from src.interfaces.github_client import IGitHubClient
from src.interfaces.llm_client import ILLMClient
from src.interfaces.reviewer import IReviewer

# State and context
from src.agent.execution_context import ExecutionContext
from src.agent.agent_state_machine import AgentStateMachine, AgentState

# Services
from src.services.diff.csharp_filter import CSharpFileFilter
from src.services.diff.diff_extractor import DiffExtractor
from src.services.diff.line_mapper import LineMapper
from src.services.prompts.prompt_builder import PromptBuilder
from src.services.prompts.review_prompt_manager import ReviewPromptManager
from src.services.review.review_validator import ReviewValidator
from src.services.review.severity_engine import SeverityEngine
from src.services.review.finding_filter import FindingFilter
from src.services.publishing.publish_manager import PublishManager

# Models
from src.models.pull_request import PullRequest
from src.models.review import Review
from src.models.findings import Finding

logger = logging.getLogger("ReviewEngine.Agent")

class ReviewAgent(IReviewer):
    """Orchestrates the 6-stage code review lifecycle, managing states and dependencies."""

    def __init__(
        self,
        publish_manager: PublishManager,
        github_client: IGitHubClient,
        llm_client: ILLMClient,
        file_filter: CSharpFileFilter,
        diff_extractor: DiffExtractor,
        line_mapper: LineMapper,
        prompt_builder: PromptBuilder,
        prompt_manager: ReviewPromptManager,
        validator: ReviewValidator,
        severity_engine: SeverityEngine,
        finding_filter: FindingFilter
    ) -> None:
        self.publish_manager = publish_manager
        self.github_client = github_client
        self.llm_client = llm_client
        self.file_filter = file_filter
        self.diff_extractor = diff_extractor
        self.line_mapper = line_mapper
        self.prompt_builder = prompt_builder
        self.prompt_manager = prompt_manager
        self.validator = validator
        self.severity_engine = severity_engine
        self.finding_filter = finding_filter

        self.state_machine = AgentStateMachine()

    async def review_pull_request(self, pr_number: int) -> Review:
        # Initialize execution context
        context = ExecutionContext(pr_number)
        logger.info(
            f"ReviewAgent: Starting execution run for PR #{pr_number}",
            extra={"context": {"run_id": context.run_id, "pr_number": pr_number}}
        )

        raw_findings: list[Finding] = []

        try:
            # 1. OBSERVE
            self.state_machine.transition_to(AgentState.OBSERVING)
            pr_metadata = await self.github_client.get_pull_request(pr_number)
            changed_files_raw = await self.github_client.get_changed_files(pr_number)
            
            # Filter only target C# files
            csharp_files = self.file_filter.filter_files(changed_files_raw)
            context.files_analyzed = len(csharp_files)

            if not csharp_files:
                logger.warning("No reviewable C# files modified in this PR. Exiting early.")
                self.state_machine.transition_to(AgentState.REPORTING)
                return self._build_empty_review(pr_metadata, context)

            # 2. ANALYZE
            self.state_machine.transition_to(AgentState.ANALYZING)
            
            for file_data in csharp_files:
                # Parse diff hunks
                changed_file = self.diff_extractor.extract_file_diff(file_data)
                
                # Build reviewable chunks containing modifications and context
                chunks = self.diff_extractor.build_reviewable_chunks(changed_file)
                context.chunks_processed += len(chunks)

                for chunk in chunks:
                    # Run AI analysis for each category in parallel or sequentially
                    # For MVP, we run reviews for SOLID, Security, and AsyncAwait categories
                    for category in ["SOLID", "Security", "AsyncAwait"]:
                        system_inst = self.prompt_manager.get_system_instruction(category)
                        user_prompt = self.prompt_builder.build_chunk_prompt(chunk)
                        
                        raw_response = await self.llm_client.generate_structured_content(
                            prompt=user_prompt,
                            system_instruction=system_inst,
                            response_schema=self._get_findings_schema()
                        )
                        
                        # 3. VALIDATE
                        self.state_machine.transition_to(AgentState.VALIDATING)
                        try:
                            json_data = json.loads(raw_response)
                            findings_list = self.validator.validate_schema(json_data)
                            
                            for f_dict in findings_list:
                                # Ensure file_path matches chunk file context
                                f_dict["file_path"] = chunk.file_path
                                
                                # Validate required fields and build Pydantic model
                                finding = self.validator.validate_finding_fields(f_dict)
                                if not finding:
                                    continue
                                    
                                # Verify finding lines coordinates fall inside modifications bounds
                                is_in_bounds = self.validator.verify_finding_bounds(finding, changed_file)
                                if not is_in_bounds:
                                    logger.warning(
                                        f"Discarding hallucinated finding on line {finding.line_number}: line was not modified."
                                    )
                                    continue
                                    
                                raw_findings.append(finding)
                        except Exception as val_err:
                            logger.error(
                                f"Failed to parse and validate AI response for chunk: {val_err}",
                                exc_info=True
                            )
                            context.errors_logged += 1

            # 4. PRIORITIZE
            self.state_machine.transition_to(AgentState.PRIORITIZING)
            
            # Filter duplicates and low-confidence findings
            clean_findings = self.finding_filter.filter_findings(raw_findings)
            
            # Resolve and override severity levels
            for finding in clean_findings:
                finding.severity = self.severity_engine.resolve_severity(finding)
                
                # Update metrics counts
                if finding.severity == "Critical":
                    context.critical_count += 1
                elif finding.severity == "High":
                    context.high_count += 1
                elif finding.severity == "Medium":
                    context.medium_count += 1
                elif finding.severity == "Low":
                    context.low_count += 1
                else:
                    context.info_count += 1

            context.total_findings = len(clean_findings)

            # 5. ACT
            self.state_machine.transition_to(AgentState.ACTING)
            
            # Map comments to final coordinates and format markdown body
            github_comments = []
            summary_lines = []
            
            for finding in clean_findings:
                # Resolve mapping coordinate details
                # The line mapper checks changes and constructs comments
                mapped = self.line_mapper.verify_and_map_finding(
                    finding=finding,
                    changed_file=next(f for f in [self.diff_extractor.extract_file_diff(fd) for fd in csharp_files] if f.filename == finding.file_path)
                )
                
                if mapped:
                    github_comments.append(mapped)
                
                # Append description to the high-level summary list
                summary_lines.append(
                    f"| {finding.severity} | {finding.category} | `{finding.file_path}:{finding.line_number}` | {finding.title} - {finding.description} |"
                )

            # Build markdown review summary text
            summary_table = "\n".join(summary_lines)
            summary_markdown = (
                f"### Gemini Automated Code Review Summary\n\n"
                f"Completed analysis of {context.files_analyzed} files.\n"
                f"Identified {context.total_findings} findings.\n\n"
                f"| Severity | Category | File & Line | Description |\n"
                f"| :--- | :--- | :--- | :--- |\n"
                f"{summary_table if summary_table else '| Info | - | - | No concerns identified. |'}\n"
            )

            verdict = "COMMENT"
            if context.critical_count > 0 or context.high_count > 0:
                verdict = "REQUEST_CHANGES"

            review = Review(
                pull_request=pr_metadata,
                findings=clean_findings,
                verdict=verdict,
                summary_markdown=summary_markdown,
                stats=context.get_summary_stats()
            )

            # Publish comments and summary back to GitHub
            await self.publish_manager.publish_review(pr_number, review)

            # 6. REPORT
            self.state_machine.transition_to(AgentState.REPORTING)
            context.complete()
            self.state_machine.transition_to(AgentState.COMPLETED)
            
            logger.info("ReviewAgent execution successfully completed.")
            return review

        except Exception as exc:
            logger.critical(f"ReviewAgent: Execution failed with error: {exc}", exc_info=True)
            self.state_machine.transition_to(AgentState.FAILED)
            context.complete()
            context.errors_logged += 1
            
            # Ensure metrics report completes even on failures
            self.state_machine.transition_to(AgentState.REPORTING)
            self.state_machine.transition_to(AgentState.COMPLETED)
            raise exc

    def _build_empty_review(self, pr_metadata: PullRequest, context: ExecutionContext) -> Review:
        """Constructs a clean, empty review structure for early exits."""
        context.complete()
        return Review(
            pull_request=pr_metadata,
            findings=[],
            verdict="APPROVE",
            summary_markdown="### Gemini Automated Code Review Summary\n\nNo modified C# files found in this PR. Skipping analysis.",
            stats=context.get_summary_stats()
        )

    def _get_findings_schema(self) -> dict[str, Any]:
        """Returns the OpenAPI schema representation of a findings review output."""
        return {
            "type": "OBJECT",
            "properties": {
                "findings": {
                    "type": "ARRAY",
                    "description": "List of C# code quality and design findings.",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "file_path": {"type": "STRING"},
                            "line_number": {"type": "INTEGER"},
                            "rule_id": {"type": "STRING"},
                            "category": {"type": "STRING"},
                            "severity": {"type": "STRING"},
                            "title": {"type": "STRING"},
                            "description": {"type": "STRING"},
                            "suggestion": {"type": "STRING"},
                            "confidence_score": {"type": "NUMBER"}
                        },
                        "required": ["file_path", "line_number", "rule_id", "category", "severity", "title", "description"]
                    }
                }
            },
            "required": ["findings"]
        }
