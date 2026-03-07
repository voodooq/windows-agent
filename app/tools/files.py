from __future__ import annotations

import shutil
from pathlib import Path

from app.schemas.tool_result import ToolResult
from app.security.path_guard import PathGuard


_DEFAULT_ALLOWED_ROOTS = [
    "./data",
    "./workspace",
]

_path_guard = PathGuard(_DEFAULT_ALLOWED_ROOTS)


def configure_allowed_roots(allowed_roots: list[str]) -> None:
    global _path_guard
    _path_guard = PathGuard(allowed_roots)


def get_allowed_roots() -> list[str]:
    return _path_guard.describe()


def _validate_allowed_path(path: Path) -> ToolResult | None:
    ok, error = _path_guard.validate(path)
    if ok:
        return None
    return ToolResult(
        ok=False,
        error=error,
    )


def list_files(path: str) -> ToolResult:
    p = Path(path)
    validation = _validate_allowed_path(p)
    if validation:
        return validation

    if not p.exists():
        return ToolResult(ok=False, error=f"path not found: {path}")
    if not p.is_dir():
        return ToolResult(ok=False, error=f"not a directory: {path}")

    items = []
    for item in p.iterdir():
        items.append(
            {
                "name": item.name,
                "path": str(item.resolve()),
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else None,
            }
        )
    return ToolResult(ok=True, output={"items": items, "allowed_roots": get_allowed_roots()})


def create_dir(path: str) -> ToolResult:
    p = Path(path)
    validation = _validate_allowed_path(p)
    if validation:
        return validation

    p.mkdir(parents=True, exist_ok=True)
    return ToolResult(
        ok=True,
        output={
            "created": str(p.resolve()),
            "allowed_roots": get_allowed_roots(),
        },
    )


def move_file(src: str, dst: str) -> ToolResult:
    src_p = Path(src)
    dst_p = Path(dst)

    src_validation = _validate_allowed_path(src_p)
    if src_validation:
        return src_validation

    dst_validation = _validate_allowed_path(dst_p)
    if dst_validation:
        return dst_validation

    if not src_p.exists():
        return ToolResult(ok=False, error=f"source not found: {src}")

    dst_p.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_p), str(dst_p))
    return ToolResult(
        ok=True,
        output={
            "src": str(src_p.resolve()),
            "dst": str(dst_p.resolve()),
            "allowed_roots": get_allowed_roots(),
        },
    )


def read_text(path: str) -> ToolResult:
    p = Path(path)
    validation = _validate_allowed_path(p)
    if validation:
        return validation

    if not p.exists():
        return ToolResult(ok=False, error=f"file not found: {path}")
    if not p.is_file():
        return ToolResult(ok=False, error=f"not a file: {path}")

    try:
        content = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = p.read_text(encoding="utf-8", errors="ignore")
    return ToolResult(
        ok=True,
        output={
            "content": content,
            "path": str(p.resolve()),
            "allowed_roots": get_allowed_roots(),
        },
    )


def write_text(path: str, content: str) -> ToolResult:
    p = Path(path)
    validation = _validate_allowed_path(p)
    if validation:
        return validation

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return ToolResult(
        ok=True,
        output={
            "path": str(p.resolve()),
            "allowed_roots": get_allowed_roots(),
        },
    )