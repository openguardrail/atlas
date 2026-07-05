# Security Policy

## Reporting a Vulnerability

Do not open public GitHub issues for security vulnerabilities.

Use [GitHub private vulnerability reporting](https://github.com/openguardrail/atlas/security/advisories/new) to submit security reports.

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact

## Scope

In scope:
- Vulnerabilities in Atlas source code
- Arbitrary code execution during scanning
- Path traversal or file system access beyond the target directory
- Dependency vulnerabilities that affect Atlas functionality

Out of scope:
- Security issues in scanned target codebases
- Vulnerabilities in dependencies that do not affect Atlas
- Social engineering

## Security Design Principles

- **No code execution** - Static analysis only. Source code is parsed via AST but never executed.
- **No network access** - Operates entirely offline. No data transmitted to external services.
- **Minimal permissions** - Requires only read access to the target directory.
- **No secrets handling** - Does not extract, store, or transmit credentials found in source code.
