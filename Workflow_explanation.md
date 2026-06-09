# Project Workflow

1. Developer creates Pull Request
2. GitHub Action triggers
3. Changed C# files are collected
4. AI reviews code
5. Findings are validated
6. Review report is generated
7. Results are posted back to GitHub Pull Request

## Architecture

Developer
    ↓
GitHub PR
    ↓
GitHub Action
    ↓
AI Review Engine
    ↓
Gemini/OpenRouter
    ↓
Validation Layer
    ↓
Review Report
    ↓
GitHub Comments