"""PR Review Summary document generator."""
import logging
from typing import Any
from src.models.findings import Finding
from src.services.publishing.review_formatter import ReviewFormatter

logger = logging.getLogger("ReviewEngine.Publishing")

class ReviewSummaryGenerator:
    """Aggregates findings and stats to generate the 11-section markdown summary report."""

    def __init__(self, formatter: ReviewFormatter) -> None:
        self.formatter = formatter

    def generate_summary(self, findings: list[Finding], stats: dict[str, Any]) -> str:
        """Constructs the complete 11-section markdown summary report.

        Args:
            findings: Array list of deduplicated findings.
            stats: Run execution statistics dictionary.

        Returns:
            The rendered markdown report.
        """
        logger.info(
            "Generating review summary report.",
            extra={"context": {"total_findings": len(findings)}}
        )

        # 1. Executive Summary
        exec_summary = (
            "## 1. Executive Summary\n"
            "This automated code review was conducted by the Gemini AI Pull Request Reviewer. "
            f"A total of **{len(findings)}** findings were identified across "
            f"**{stats.get('files_analyzed', 0)}** C# files modified in this Pull Request.\n\n"
            "### Findings Breakdown\n"
            "| Severity | Count |\n"
            "| :--- | :--- |\n"
            f"| 🔴 Critical | {stats.get('critical_count', 0)} |\n"
            f"| 🟠 High | {stats.get('high_count', 0)} |\n"
            f"| 🟡 Medium | {stats.get('medium_count', 0)} |\n"
            f"| 🔵 Low | {stats.get('low_count', 0)} |\n"
            f"| ⚪ Info | {stats.get('info_count', 0)} |\n"
        )

        # Helper to filter and format findings by severity
        def _get_severity_section(severity: str, title: str) -> str:
            severity_findings = [f for f in findings if f.severity == severity]
            lines = [f"### {title}"]
            if not severity_findings:
                lines.append(f"No {severity.lower()} severity findings identified.")
            else:
                for f in severity_findings:
                    badge = self.formatter.format_severity_badge(f.severity)
                    lines.append(
                        f"- {badge} on `{f.file_path}:{f.line_number}`: "
                        f"{f.title} - {f.description}"
                    )
            return "\n".join(lines)

        # 2-5: Severity Sections
        critical_findings = _get_severity_section("Critical", "2. Critical Findings")
        high_findings = _get_severity_section("High", "3. High Findings")
        medium_findings = _get_severity_section("Medium", "4. Medium Findings")
        low_findings = _get_severity_section("Low", "5. Low Findings")

        # Helper to filter and format findings by category
        def _get_category_section(category: str, title: str) -> str:
            cat_findings = [f for f in findings if f.category.lower() == category.lower()]
            lines = [f"### {title}"]
            if not cat_findings:
                lines.append(f"No {category.lower()} concerns identified.")
            else:
                for f in cat_findings:
                    badge = self.formatter.format_severity_badge(f.severity)
                    lines.append(
                        f"- {badge} on `{f.file_path}:{f.line_number}`: "
                        f"{f.title} - {f.description}"
                    )
            return "\n".join(lines)

        # 6-10: Category Sections
        security_issues = _get_category_section("Security", "6. Security Issues")
        solid_violations = _get_category_section("SOLID", "7. SOLID Violations")
        async_issues = _get_category_section("AsyncAwait", "8. Async Issues")
        null_risks = _get_category_section("Nullability", "9. Nullability Risks")
        clean_code_issues = _get_category_section("CleanCode", "10. Clean Code Issues")

        # 11. Metrics
        metrics = (
            "## 11. Run Metrics & Audit Log\n"
            f"- **Run ID**: `{stats.get('run_id', 'N/A')}`\n"
            f"- **PR ID**: `#{stats.get('pr_number', 'N/A')}`\n"
            f"- **Execution Latency**: `{stats.get('duration_s', 0.0)} seconds`\n"
            f"- **Total Chunks Processed**: `{stats.get('chunks_processed', 0)}`\n"
            f"- **Total Tokens Logged**: `{stats.get('total_tokens', 0)}`\n"
            f"- **System Warnings/Errors**: `{stats.get('errors_logged', 0)}`\n"
        )

        # Compile the 11 sections
        sections = [
            "# Gemini AI Pull Request Code Review Report\n",
            exec_summary,
            critical_findings,
            high_findings,
            medium_findings,
            low_findings,
            "## Category Review Details\n",
            security_issues,
            solid_violations,
            async_issues,
            null_risks,
            clean_code_issues,
            metrics
        ]

        logger.info("Summary report generated successfully.")
        return "\n".join(sections)
