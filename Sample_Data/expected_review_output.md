# Expected AI Review Output

## File Reviewed
vulnerable_login.cs

## Findings

### Critical - Hardcoded Secret

Issue:
Hardcoded password detected in source code.

Recommendation:
Store credentials in environment variables or secret managers.

---

### Critical - SQL Injection

Issue:
User input is directly concatenated into SQL query.

Recommendation:
Use parameterized SQL queries.

Example:

SELECT * FROM Users WHERE Name=@username

---

## Review Summary

Files Reviewed: 1

Critical Findings: 2

High Findings: 0

Medium Findings: 0

Low Findings: 0

Review Score: 40/100