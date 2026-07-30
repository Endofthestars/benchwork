---
language: en
canonical: true
---

# Uninstall and rollback

Preview removal:

```bash
bwork install uninstall --dry-run
```

Remove installer-owned CLI, plugin, Host entries, and PATH blocks:

```bash
bwork install uninstall
```

The public bootstrap can delegate to the same command:

```bash
curl -LsSf https://benchwork.dev/install.sh | sh -s -- --uninstall
```

Backups are retained by default. Add `--purge` only when those installer
backups are no longer required.

Uninstall preserves every research project and all `.benchwork/` data. It does
not remove uv or pipx themselves, even when Benchwork originally bootstrapped
uv, because the backend may now manage other tools.
