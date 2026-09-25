#!/usr/bin/env python3
"""
Shell-command write analysis for the /m:develop phase gate.

`bash_write_targets(command)` returns the paths a Bash command would write,
derived from shell syntax alone: output redirections, `tee`, in-place `sed`
and `perl`, file-management commands such as `cp`, `mv`, `rm`, `touch`, and
`mkdir`, `git` subcommands that mutate the working tree, and inline
interpreter scripts that call a write API. A write whose target cannot be
named (a `git apply`, a `patch`, a Python heredoc that opens a file for
writing) is reported as OPAQUE_TARGET so the caller can fail closed.

The analysis is a heuristic over shell syntax, not an interpreter. Known
limits: a target that contains a shell expansion (`"$OUT"`) is returned
verbatim, a `cd` earlier in the command does not move the base directory,
and `find -delete` and `-exec` are not recognized.
"""

import os
import re
import shlex


OPAQUE_TARGET = "<opaque>"
BASH_WRITE_COMMANDS = {
    "cp", "install", "ln", "mkdir", "mv", "rm", "rmdir", "rsync", "tee",
    "touch", "truncate",
}
UNATTRIBUTABLE_WRITE_COMMANDS = {"dd", "patch"}
IN_PLACE_EDITORS = {"perl", "sed"}
INLINE_INTERPRETERS = {"node", "perl", "python", "python3", "ruby"}
GIT_MUTATING_SUBCOMMANDS = {
    "am", "apply", "checkout", "cherry-pick", "clean", "merge", "mv", "pull",
    "rebase", "reset", "restore", "revert", "rm", "stash", "switch",
    "worktree",
}
COMMAND_WRAPPERS = {"command", "env", "exec", "nohup", "sudo", "time", "xargs"}
CONTROL_OPERATORS = {";", "&&", "||", "|", "&", "(", ")"}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
OUTPUT_REDIRECT = re.compile(r"^(\d*>{1,2}|&>{1,2}|>\|)$")
INPUT_REDIRECT = re.compile(r"^\d*<{1,3}$")
IN_PLACE_FLAG = re.compile(r"^(-[a-zA-Z]*i\S*|--in-place(=.*)?)$")
SCRIPT_FLAG = re.compile(r"^(-[a-zA-Z]*[ef]|--expression(=.*)?|--file(=.*)?)$")
HEREDOC_START = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
INLINE_WRITE_CALL = re.compile(
    r"open\s*\([^)]*['\"](?:[wax]\+?b?|r\+b?)['\"]|\.write_(?:text|bytes)\s*\("
    r"|writeFile(?:Sync)?\s*\(|fs\.(?:append|write|rm|unlink|rename|mkdir)"
    r"|File\.(?:write|open|delete|rename)"
    r"|os\.(?:remove|unlink|rename|replace|makedirs|mkdir|rmdir)\s*\("
    r"|shutil\.\w+\s*\("
)


def strip_heredocs(command: str) -> str:
    """Drop heredoc bodies so their text is not parsed as shell syntax."""
    lines = command.split("\n")
    kept = []
    index = 0
    while index < len(lines):
        line = lines[index]
        kept.append(line)
        match = HEREDOC_START.search(line)
        index += 1
        if not match:
            continue
        delimiter = match.group(2)
        while index < len(lines) and lines[index].strip() != delimiter:
            index += 1
        index += 1
    return "\n".join(kept)


def shell_tokens(command: str):
    """Tokenize a shell command with operators split out.

    Falls back to whitespace splitting when the command has unbalanced
    quotes, so a malformed command is still inspected rather than skipped.
    """
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError:
        return command.split()


def split_simple_commands(tokens):
    """Split a token list on control operators into simple commands."""
    commands, current = [], []
    for token in tokens:
        if token in CONTROL_OPERATORS:
            if current:
                commands.append(current)
            current = []
        else:
            current.append(token)
    if current:
        commands.append(current)
    return commands


def command_word(tokens):
    """Return (word, args) of a simple command, skipping wrappers.

    Leading variable assignments, wrapper commands such as `sudo` or
    `xargs`, and the wrapper's own options are skipped. The word is the
    basename of the executable, so `/usr/bin/sed` reads as `sed`.
    """
    index = 0
    while index < len(tokens):
        token = tokens[index]
        is_wrapper_option = index > 0 and token.startswith("-")
        if token in COMMAND_WRAPPERS or ASSIGNMENT.match(token) or is_wrapper_option:
            index += 1
            continue
        return os.path.basename(token), tokens[index + 1:]
    return None, []


def positional_args(args, consume_script_flags=False):
    """Non-option arguments of a simple command.

    Redirect operators and their targets are dropped. When
    `consume_script_flags` is set, `-e`/`-f` style flags also consume the
    token that follows them, which is how `sed` and `perl` take a script.
    """
    positional, skip_next = [], False
    for token in args:
        if skip_next:
            skip_next = False
            continue
        if OUTPUT_REDIRECT.match(token) or INPUT_REDIRECT.match(token):
            skip_next = True
            continue
        if consume_script_flags and SCRIPT_FLAG.match(token):
            skip_next = True
            continue
        if token.startswith("-") and token != "-":
            continue
        positional.append(token)
    return positional


def redirect_targets(tokens):
    """Files named as output redirection targets, excluding `/dev/*`."""
    targets = []
    for index, token in enumerate(tokens[:-1]):
        if OUTPUT_REDIRECT.match(token):
            target = tokens[index + 1]
            if not target.startswith("/dev/"):
                targets.append(target)
    return targets


def in_place_edit_targets(args):
    """Files an in-place `sed` or `perl` invocation rewrites.

    Returns an empty list when no in-place flag is present. When the script
    is not given through `-e`/`-f`, the first positional argument is the
    script and is not a target. A write with no resolvable file is opaque.
    """
    if not any(IN_PLACE_FLAG.match(arg) for arg in args):
        return []
    script_by_flag = any(SCRIPT_FLAG.match(arg) for arg in args)
    positional = positional_args(args, consume_script_flags=True)
    targets = positional if script_by_flag else positional[1:]
    return targets or [OPAQUE_TARGET]


def write_targets(word, args):
    """Paths a simple command writes, or [OPAQUE_TARGET] when unattributable."""
    if word == "git":
        subcommand = next((arg for arg in args if not arg.startswith("-")), None)
        return [OPAQUE_TARGET] if subcommand in GIT_MUTATING_SUBCOMMANDS else []
    if word in IN_PLACE_EDITORS:
        return in_place_edit_targets(args)
    if word in UNATTRIBUTABLE_WRITE_COMMANDS:
        return [OPAQUE_TARGET]
    if word in BASH_WRITE_COMMANDS:
        return positional_args(args) or [OPAQUE_TARGET]
    return []


def bash_write_targets(command: str):
    """Every write target in a Bash command.

    Heredoc bodies are removed before shell parsing and newlines act as
    command separators. Inline interpreter scripts are scanned in the
    original text, heredoc body included, for write API calls; a hit is
    recorded as OPAQUE_TARGET because the written path lives inside the
    script.
    """
    flattened = strip_heredocs(command).replace("\\\n", " ").replace("\n", " ; ")
    targets = []
    interpreter_seen = False
    for simple in split_simple_commands(shell_tokens(flattened)):
        word, args = command_word(simple)
        if word is None:
            continue
        targets.extend(redirect_targets(simple))
        targets.extend(write_targets(word, args))
        interpreter_seen = interpreter_seen or word in INLINE_INTERPRETERS
    if interpreter_seen and INLINE_WRITE_CALL.search(command):
        targets.append(OPAQUE_TARGET)
    return targets
