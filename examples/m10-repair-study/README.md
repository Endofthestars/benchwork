# M10 Repair Study

This acceptance fixture creates the complete Phase 1 research chain in a fresh
project, rejects an invalid `CONTINUE` Decision, seals `REPAIR`, and verifies
the result from new Python processes.

```bash
python3 examples/m10-repair-study/scenario.py /tmp/m10-repair-study
cd /tmp/m10-repair-study
bwork --json doctor --deep
python3 /path/to/benchwork/examples/m10-repair-study/verify.py .
```

`expected-state.json` is the stable scientific projection contract. Chronicle
event IDs, Receipt IDs, timestamps, and Sigils are intentionally generated at
runtime and are verified rather than compared as incidental golden text.
