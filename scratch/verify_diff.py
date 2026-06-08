"""Verification script for C# file filtering and diff parsing services."""
import logging
from src.core.config import AppConfig
from src.core.logging import configure_logging
from src.models.findings import Finding
from src.services.diff.csharp_filter import CSharpFileFilter
from src.services.diff.diff_parser import DiffParser
from src.services.diff.diff_extractor import DiffExtractor
from src.services.diff.line_mapper import LineMapper

configure_logging("INFO")
logger = logging.getLogger("VerifyDiff")

MOCK_PATCH = (
    "@@ -40,6 +40,8 @@ public class DataSyncService\n"
    "     public void Process()\n"
    "     {\n"
    "-        var data = FetchOld();\n"
    "+        var data = FetchNew();\n"
    "+        logger.LogInformation(\"Sync started\");\n"
    "         Save(data);\n"
    "     }\n"
)

def run_verification() -> None:
    logger.info("Initializing configuration parameters.")
    config = AppConfig()
    
    # 1. Test C# File Filtering
    logger.info("--- Testing CSharpFileFilter ---")
    file_filter = CSharpFileFilter(config)
    test_files = [
        {"filename": "src/Core/Services/DataSyncService.cs", "status": "modified"},
        {"filename": "src/Core/Services/DataSyncService.Designer.cs", "status": "modified"},
        {"filename": "src/Core/bin/Debug/net8.0/Core.dll", "status": "added"},
        {"filename": "src/Core/Services/Sync.cs", "status": "deleted"}
    ]
    filtered = file_filter.filter_files(test_files)
    logger.info(f"Original files count: {len(test_files)}")
    logger.info(f"Filtered target C# files count: {len(filtered)}")
    for f in filtered:
        logger.info(f" - Target: {f['filename']} (Status: {f['status']})")
        
    # 2. Test Diff Parsing and Extraction
    logger.info("--- Testing DiffParser & DiffExtractor ---")
    parser = DiffParser()
    extractor = DiffExtractor(parser)
    
    # Simulate API file data
    file_data = {
        "filename": "src/Core/Services/DataSyncService.cs",
        "status": "modified",
        "additions": 2,
        "deletions": 1,
        "patch": MOCK_PATCH
    }
    
    changed_file = extractor.extract_file_diff(file_data)
    logger.info(f"Parsed chunks count: {len(changed_file.chunks)}")
    for idx, chunk in enumerate(changed_file.chunks):
        logger.info(f" Hunk {idx}: lines count = {len(chunk.lines)}")
        
    # Build reviewable chunks
    reviewable_chunks = extractor.build_reviewable_chunks(changed_file)
    logger.info(f"Reviewable chunks compiled: {len(reviewable_chunks)}")
    for r_chunk in reviewable_chunks:
        logger.info(f" Chunk target line numbers: {r_chunk.target_lines}")
        logger.info(f" Patch content block:\n{r_chunk.patch_content}")
        
    # 3. Test Line Mapping
    logger.info("--- Testing LineMapper ---")
    mapper = LineMapper()
    
    # Map a finding on a modified line (e.g. line 43)
    valid_finding = Finding(
        file_path="src/Core/Services/DataSyncService.cs",
        line_number=43,
        rule_id="CS-PERF-01",
        category="Performance",
        severity="Major",
        title="Avoid blocking sync call",
        description="Verify this is non-blocking.",
        suggestion=""
    )
    mapped_val = mapper.verify_and_map_finding(valid_finding, changed_file)
    logger.info(f"Finding at line 43 is modified: {mapped_val is not None}")
    
    # Map a finding on an unmodified line (e.g. line 40)
    invalid_finding = Finding(
        file_path="src/Core/Services/DataSyncService.cs",
        line_number=40,
        rule_id="CS-STYLE-01",
        category="Style",
        severity="Minor",
        title="Brace placement",
        description="Align braces.",
        suggestion=""
    )
    mapped_val_invalid = mapper.verify_and_map_finding(invalid_finding, changed_file)
    logger.info(f"Finding at line 40 is modified: {mapped_val_invalid is not None}")
    
    logger.info("Verification completed successfully.")

if __name__ == "__main__":
    run_verification()
