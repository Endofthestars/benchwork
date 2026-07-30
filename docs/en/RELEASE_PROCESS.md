---
language: en
canonical: true
---

# Release Process

1. Complete the milestone checklist and all related RFC acceptance tests.
2. Run lint, type checks, schema compatibility, full coverage, golden replay,
   migration, fault-injection, documentation-link, and wheel smoke checks.
3. Confirm the version in `pyproject.toml` and `benchwork.__version__` match.
4. For a non-development release, freeze the distribution, CLI, import, and
   schema-domain names in an accepted RFC and update `COMPATIBILITY.md`.
5. Create a signed or protected tag matching `v<package-version>`.
6. Publish a GitHub release only after CI succeeds for the exact tag.
7. The release workflow rebuilds and checks distributions before trusted
   publishing to PyPI.

M10 may publish development or prerelease artifacts. It must not publish a
stable package while any naming surface remains provisional.
