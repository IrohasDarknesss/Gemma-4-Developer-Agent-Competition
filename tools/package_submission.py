"""Validate a conservative baseline config and build a reproducible submission ZIP.

This checks local packaging invariants, not the competition's full ADK schema.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import zipfile

import yaml

MODELS = {f"gemma-4-{size}-it-qat-w4a16-ct" for size in ("31b", "12b", "e4b", "e2b")}
TOOLS = {
    "run_command", "submit_patch", "get_status", "read_file", "edit_file",
    "write_file", "get_code_neighbors", "search_similar_code", "get_code_subgraph",
}


def files_under(root: Path) -> list[Path]:
    if not root.is_dir():
        raise ValueError(f"Submission directory does not exist: {root}")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlinks are forbidden: {path}")
        if path.is_file():
            files.append(path)
        elif not path.is_dir():
            raise ValueError(f"Unsupported file type: {path}")
    return files


def load_config(path: Path, root: Path, stack: tuple[Path, ...] = ()):
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Include escapes submission root: {path}")
    if len(stack) > 10:
        raise ValueError("Include depth exceeds 10")
    if resolved in stack:
        raise ValueError(f"Cyclic include: {path}")

    class Loader(yaml.SafeLoader):
        pass

    def include(loader, node):
        relative = Path(loader.construct_scalar(node))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe include: {relative}")
        target = path.parent / relative
        if not target.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Include escapes submission root: {target}")
        if target.suffix.lower() in {".yaml", ".yml"}:
            return load_config(target, root, (*stack, resolved))
        return target.read_text(encoding="utf-8")

    Loader.add_constructor("!include", include)
    return yaml.load(path.read_text(encoding="utf-8"), Loader=Loader)


def validate(root: Path) -> list[Path]:
    files = files_under(root)
    config = load_config(root / "agent.yaml", root)
    if not isinstance(config, dict) or config.get("agent_class") != "LlmAgent":
        raise ValueError("Baseline requires a root LlmAgent")
    if config.get("model") not in MODELS:
        raise ValueError("Unsupported Gemma model")
    if not isinstance(config.get("name"), str) or not config["name"].isidentifier():
        raise ValueError("Agent name must be a Python identifier")
    if not isinstance(config.get("instruction"), str) or not config["instruction"].strip():
        raise ValueError("Nonempty instructions are required")
    tools = config.get("tools")
    if not isinstance(tools, list) or not tools:
        raise ValueError("A nonempty tool list is required")
    names = []
    for tool in tools:
        if not isinstance(tool, str) or tool not in TOOLS:
            raise ValueError(f"Unsupported baseline tool: {tool!r}")
        names.append(tool)
    if len(names) != len(set(names)) or "submit_patch" not in names:
        raise ValueError("Tools must be unique and include submit_patch")
    # Reject extensions until their harness-specific schema is validated.
    if set(config) - {"agent_class", "name", "model", "description", "instruction", "tools"}:
        raise ValueError("Unsupported baseline config field")
    allowed = {"agent.yaml", "prompts/system.md"}
    if {p.relative_to(root).as_posix() for p in files} != allowed:
        raise ValueError("Baseline archive must contain only agent.yaml and prompts/system.md")
    return files


def build(root: Path, output: Path) -> None:
    files = validate(root)
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError("Output must be outside submission directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), (2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("submission"))
    parser.add_argument("--output", type=Path, default=Path("dist/submission.zip"))
    args = parser.parse_args()
    try:
        build(args.source, args.output)
    except (ValueError, OSError, yaml.YAMLError) as exc:
        parser.exit(1, f"Validation failed: {exc}\n")
    print(f"Built {args.output}")


if __name__ == "__main__":
    main()
