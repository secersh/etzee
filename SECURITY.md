# Security Policy

etzee includes firmware, hardware designs, and manufacturing files. Security reports may involve firmware behavior, communication protocols, unsafe electrical assumptions, or supply-chain concerns.

## Reporting a Vulnerability

Do not open a public issue for a suspected security vulnerability.

Report privately through GitHub's private vulnerability reporting:

https://github.com/secersh/etzee/security/advisories/new

Include:

- affected component or path
- impact
- reproduction steps
- affected commit, release, or hardware revision
- any suggested mitigation

## Scope

In scope:

- firmware vulnerabilities
- htoyto protocol vulnerabilities
- unsafe update, build, or release automation
- hardware behavior that can cause unsafe electrical operation

Out of scope:

- unsupported local modifications
- speculative reports without a plausible impact
- third-party platform issues that should be reported upstream

## Disclosure

Maintainers will acknowledge reports within 7 days and coordinate fixes and public disclosure based on impact and practical mitigation timing.
