"""Select eval cases and models, and size the noise floor of a comparison."""

import json
from pathlib import Path


EVALS = Path(__file__).resolve().parent


def pinned_model(plugin, name, fallback):
    """Return the model pinned in the frontmatter of the case's stage command.

    A case named "<stage>--<variant>" uses commands/<stage>.md. A case with no
    matching command, or a command with no model key, uses fallback.
    """
    command = plugin / "commands" / (name.split("--", 1)[0] + ".md")
    if not command.is_file():
        return fallback
    parts = command.read_text().split("---", 2)
    if len(parts) < 3:
        return fallback
    for line in parts[1].splitlines():
        key, _, value = line.partition(":")
        if key.strip() == "model" and value.strip():
            return value.strip()
    return fallback


def case_model(plugin, name, args):
    """Return the model for one case: the stage pin in pinned mode, else args.model."""
    if args.model == "pinned":
        return pinned_model(plugin, name, args.fallback_model)
    return args.model


def split_cases(split):
    """Return the case names assigned to split ("train" or "test") in split.json."""
    assignment = json.loads((EVALS / "split.json").read_text())["cases"]
    return {name for name, part in assignment.items() if part == split}


def noise_floor(trials):
    """Return the approximate 95% half-width of a pass-rate difference, 1/sqrt(n)."""
    return round(1 / trials ** 0.5, 3) if trials else None
