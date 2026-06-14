# Security Policy

## Supported versions

This repository is an educational MVP. Security fixes are applied to the latest
commit on the `main` branch.

## Reporting a vulnerability

Do not open a public issue for a vulnerability that exposes credentials,
private documents, authentication bypasses, or cross-user data.

Use the repository's **Security** tab and select **Report a vulnerability**.
Include:

- affected endpoint or component
- reproduction steps
- expected and observed behavior
- impact
- suggested mitigation, if known

Do not include real API keys, customer logs, resumes, or other sensitive data.

## Security boundaries

The MVP includes JWT-protected APIs, per-user document paths and FAISS indexes,
file-type and upload-size checks, prompt-injection phrase blocking, grounded
citations, and audit logging.

It is not production-ready. It uses one environment-configured demo account and
does not yet include RBAC, account lockout, rate limiting, malware scanning,
OCR sandboxing, encrypted storage, centralized audit retention, or TLS
termination. Run it only with non-sensitive demonstration data.
