# Clinical protocol PDFs (ingestion source)

This folder holds the source PDFs for the assistant's RAG corpus. **PDFs
themselves are gitignored** (large files, redistribution rights vary),
but their names and the resulting SQLite index live in the repo.

## Get the protocols

Download from [diseases.medelement.com](https://diseases.medelement.com)
(filter `Клинические протоколы МЗ РК`). The 19 protocols currently
indexed match the simulator scenarios — see the table in the main README.

## Re-index after changes

After adding, removing, or replacing a PDF, re-run:

```bash
.venv/bin/python scripts/ingest_protocols.py
```

The script is idempotent: it skips PDFs whose content hash matches what
is already indexed and re-embeds the rest.
