# Photon

Image deduplication CLI tool.

## Commands

```bash
uv sync                          # install deps
uv run pytest                    # run all tests
uv run pytest tests/test_model.py -v -k "test_name"
uv run black src/                # format
uv run mypy --strict src/        # typecheck
uv run pylint src/               # lint
make precommit                   # format + lint (soft failures)
make smoke                       # manual end-to-end smoke tests
uv run photon dedupe --help      # CLI usage
```

## Architecture

Entrypoint: `photon.entrypoints.cli.main:main` -> `photon dedupe` subcommand.

Three layers under `src/photon/`:

| Layer | Files | Responsibility |
|---|---|---|
| **Model** | `model.py`, `core.py` | `ImgGroup` state machine, extension filtering |
| **Duplicates** | `detection.py`, `selection.py`, `pipeline.py` | MD5 hashing, selection rules, orchestration |
| **I/O** | `io.py`, `runtime.py` | File ops (load/trash/recover), config factory |

Detection: full-file **MD5 hash** (byte-level, not perceptual). Two files match iff identical bytes.

Selection pipeline (ordered): `remove_filename_with("copy")` -> `ask_user(auto_select)`.

Modes:
- `--ref <dir>` (inter-album): ref files protected, all src duplicates auto-staged
- `--intra` (intra-album): respects selection rules, at least 1 survivor kept

Trash: custom `.trash/` dir with `log_paths.json` for recovery.

## Key design decisions

- `ImgGroup` is a two-phase state machine: `add()` -> `stage_for_removal()`. Locked after first staging call.
- When protected files exist, `stage_for_removal()` ignores its `files` argument and stages all survivors.
- `make_selection_pipeline()` composes selection steps; short-circuits on `is_exhausted`.
- Pipeline does NOT lock the group explicitly — `stage_for_removal()` sets `_locked` internally.
- Single-file groups are never locked (no call to `stage_for_removal()`), but `is_exhausted` is `True`.
- No image processing deps (pillow commented out). Only pure Python + stdlib.
- Python 3.13+, uv for package management.

## Testing

Tests in `tests/` use class-based organization. Fixtures in `conftest.py`:
- `img_file` — creates `photo.jpg`
- `dup_file` — creates `dupli.jpg` (duplicate of `img_file`)
- `ref_dir` — creates `reference/` directory
- `ref_file` — creates `reference/img_ref.jpg` (duplicate of `img_file`)

No integration tests yet. No CI/CD configured.
