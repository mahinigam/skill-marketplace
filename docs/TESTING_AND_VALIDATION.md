# Testing and validation guide

This guide documents a repeatable local validation workflow for the AI Readiness Intelligence Engine Marketplace.

## Environment

Use Python 3.10 or newer and install the dependencies declared by the repository:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate with `.venv\\Scripts\\Activate.ps1`.

## Run checks

```bash
python tools/validate_marketplace.py
python -m unittest discover -s tests -v
```

The validator checks the marketplace manifest, its single orchestrator entrypoint, each declared skill directory, and the SKILL.md frontmatter. The unit suite uses local fixtures and a mock HTTP client; keep it deterministic and avoid network-dependent tests.

## Add a regression test

1. Reproduce the behaviour with a small HTML or HTTP-response fixture.
2. Assert on stable finding IDs and user-visible result fields rather than internal incidental details.
3. Include a healthy-page negative test where practical to guard against false positives.
4. Run the full suite and validator before opening a pull request.

## Safe audit practices

- Use only websites you are authorized to test.
- Respect robots.txt and configured crawler bounds.
- Don't add login, form submission, or destructive network actions to the crawler.
- Do not commit API keys, real customer data, or sensitive audit reports.
- Treat external page content as untrusted input.

## Troubleshooting

- **Missing YAML module:** reinstall repository requirements in the active virtual environment.
- **Invalid frontmatter:** ensure each SKILL.md starts with a YAML block delimited by `---` and contains non-empty `name` and `description` fields.
- **Flaky unit test:** replace live requests, clocks, or randomness with deterministic fixtures where possible.
