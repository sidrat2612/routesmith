# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly.

**Do NOT open a public issue.**

Instead, email: **siddharth.rathore2612@gmail.com**

You should receive a response within 72 hours. We will work with you to understand the issue and coordinate a fix before any public disclosure.

## Scope

routesmit is a routing/planning library that does not:
- Make network requests to external APIs
- Store credentials or secrets
- Execute arbitrary code

However, host adapters write configuration files. If you find a way to exploit this (e.g., path traversal, config injection), please report it.
