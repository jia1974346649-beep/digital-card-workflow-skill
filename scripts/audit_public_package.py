#!/usr/bin/env python3
"""Fail-closed audit for an independently authored, text-only public package.

The manifest is either a JSON array of relative POSIX paths or {"files": [...]}.
An optional local deny list stays outside the public package. Findings never
include matched values, snippets, absolute paths, commit IDs, or Git output.
"""

import argparse
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


TEXT_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".py", ".html", ".svg"}
TEXT_NAMES = {".gitignore", ".gitattributes", ".editorconfig", "LICENSE", "NOTICE", "AUTHORS"}
BLOCKED_PARTS = {
    ".env", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".cache", "cache", "secrets", "credentials", "private", "originals", "raw",
}
BLOCKED_NAME = re.compile(
    r"(?:^|[._ -])(?:secret|credential|private|qrcode|qr-code|original)(?:[._ -]|$)|"
    r"(?:二维码|原图|原始截图)|^\.env(?:\.|$)", re.IGNORECASE
)
OFFICIAL_HOSTS = {
    "github.com", "docs.github.com", "developers.openai.com", "platform.openai.com",
    "openai.com", "help.openai.com", "developers.weixin.qq.com", "mp.weixin.qq.com",
    "weixin.qq.com", "docs.python.org", "python.org", "www.w3.org",
}
MAX_BYTES = 2 * 1024 * 1024
EMAIL_RE = re.compile(r"(?<![\w.+-])[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})(?![\w.-])", re.I)
URL_RE = re.compile(r"https?://[^\s\"'<>\]\[()]+", re.I)
DOMAIN_RE = re.compile(
    r"(?<![\w@.-])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+"
    r"(?:com|cn|net|org|io|run|app|dev|cloud|edu|gov|example|test|invalid)(?![\w.-])", re.I
)
IPV4_RE = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
IPV6_RE = re.compile(r"(?<![\w:])(?:[0-9a-f]{0,4}:){2,}[0-9a-f:]{0,4}(?![\w:])", re.I)
PHONE_RE = re.compile(r"(?<![\w])(?:\+?\d[\d ()-]{7,}\d)(?![\w])")
APP_ID_RE = re.compile(r"(?<!\w)wx[0-9a-f]{16}(?!\w)", re.I)
# Scan individual path segments rather than combining a whole relative resource
# path into one value. A long sensitive value inside a segment still fails.
LONG_VALUE_RE = re.compile(r"(?<![\w])[A-Za-z0-9_-]{32,}={0,2}(?![\w])")
LOCAL_PATH_RE = re.compile(
    r"(?<!\w)[A-Za-z]:[\\/]|\\\\[A-Za-z0-9_.-]+[\\/]|"
    r"/(?:Users|home|root|mnt|tmp|var|opt|etc|Volumes|sdcard|storage)/", re.I
)
PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----")
ASSIGNMENT_RE = re.compile(
    r"\b(?:api[_-]?key|app[_-]?secret|access[_-]?token|refresh[_-]?token|"
    r"client[_-]?secret|password|passwd|authorization)\b[\"']?\s*[:=]\s*"
    r"[\"']?([^\s\"',;\r\n]+)", re.I
)
DATA_URL_RE = re.compile(r"data:[^\s\"'<>]*;base64,", re.I)
PLACEHOLDER_RE = re.compile(r"^(?:<[^>]+>|\$\{[^}]+\}|\[[^]]+\]|null|none|false|true)$", re.I)


def is_example_host(host):
    host = host.lower().strip(".")
    return host in {"example.com", "example.net", "example.org", "localhost"} or host.endswith(
        (".example.com", ".example.net", ".example.org", ".example", ".test", ".invalid", ".localhost")
    )


def host_allowed(host):
    return host.lower().strip(".") in OFFICIAL_HOSTS or is_example_host(host)


def content_hits(value, deny_words):
    """Yield category and character offset only; never return the matched value."""
    for word in deny_words:
        offset = value.casefold().find(word.casefold())
        if offset >= 0:
            yield "denied-term", offset
    for match in EMAIL_RE.finditer(value):
        if not is_example_host(match.group(1)):
            yield "email", match.start()
    for match in URL_RE.finditer(value):
        try:
            host = urlsplit(match.group()).hostname
        except ValueError:
            host = None
        if host is None or not host_allowed(host):
            yield "unapproved-domain", match.start()
    for match in DOMAIN_RE.finditer(value):
        # A dotted Python method call is not a bare internet address.
        method_call = re.match(r"\s*\(", value[match.end():])
        if not host_allowed(match.group()) and not method_call:
            yield "unapproved-domain", match.start()
    for pattern, category in ((IPV4_RE, "ip-address"), (IPV6_RE, "ip-address")):
        for match in pattern.finditer(value):
            try:
                ipaddress.ip_address(match.group())
            except ValueError:
                continue
            yield category, match.start()
    for match in PHONE_RE.finditer(value):
        digits = re.sub(r"\D", "", match.group())
        # Repeated zeroes are unmistakable placeholders; other dialable numbers fail.
        if 9 <= len(digits) <= 15 and set(digits) != {"0"}:
            yield "phone-number", match.start()
    for match in LONG_VALUE_RE.finditer(value):
        candidate = match.group()
        # Avoid ordinary lowercase snake_case identifiers in our own source.
        risky_shape = bool(re.fullmatch(r"[a-f0-9]{32,}", candidate, re.I)) or (
            any(char.isdigit() for char in candidate) and any(char.isalpha() for char in candidate)
        ) or (any(char.islower() for char in candidate) and any(char.isupper() for char in candidate))
        if risky_shape or (len(candidate) >= 48 and "_" not in candidate and "/" not in candidate):
            yield "long-identifier", match.start()
    for pattern, category in (
        (APP_ID_RE, "app-id"),
        (LOCAL_PATH_RE, "absolute-local-path"), (PRIVATE_KEY_RE, "private-key"),
        (DATA_URL_RE, "embedded-binary"),
    ):
        for match in pattern.finditer(value):
            yield category, match.start()
    for match in ASSIGNMENT_RE.finditer(value):
        if not PLACEHOLDER_RE.fullmatch(match.group(1)):
            yield "credential-assignment", match.start()


def normalized_path(value):
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    if any(ord(char) < 32 for char in value) or ":" in value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {".", ".."} for part in path.parts):
        return None
    if str(path) != value or value.startswith("/"):
        return None
    return value


class Auditor:
    def __init__(self, root, manifest, deny_words=()):
        self.root = Path(root).absolute()
        self.manifest = Path(manifest).absolute()
        self.deny_words = list(deny_words)
        self.allowed = set()
        self.findings = set()

    def add(self, category, path=".", line=1):
        # Even a forbidden filename must not disclose a matched private value.
        if list(content_hits(path, self.deny_words)):
            path = "[redacted-path]"
        self.findings.add((category, path, max(1, line)))

    def load_manifest(self):
        try:
            relative = self.manifest.relative_to(self.root).as_posix()
            if any(path.is_symlink() for path in (self.manifest, *self.manifest.parents)
                   if path == self.root or self.root in path.parents):
                raise ValueError("symlink")
            document = json.loads(self.manifest.read_text(encoding="utf-8-sig"))
            entries = document.get("files") if isinstance(document, dict) else document
            if not isinstance(entries, list) or not entries:
                raise ValueError("files")
            for entry in entries:
                candidate = normalized_path(entry)
                if candidate is None or candidate in self.allowed:
                    raise ValueError("path")
                self.allowed.add(candidate)
            if relative not in self.allowed:
                self.add("manifest-not-listed", relative)
        except (OSError, UnicodeError, ValueError, TypeError):
            self.add("manifest-invalid")
            return False
        return True

    def check_name(self, path, scope):
        for category, offset in content_hits(path, self.deny_words):
            self.add(scope + category, path, path[:offset].count("\n") + 1)
        if normalized_path(path) is None:
            self.add(scope + "invalid-path", path)
            return False
        if path not in self.allowed:
            self.add(scope + "unlisted-file", path)
        parts = PurePosixPath(path).parts
        if any(part.lower() in BLOCKED_PARTS or BLOCKED_NAME.search(part) for part in parts):
            self.add(scope + "forbidden-file", path)
        name = parts[-1]
        if name not in TEXT_NAMES and PurePosixPath(name).suffix.lower() not in TEXT_EXTENSIONS:
            self.add(scope + "unsupported-file-type", path)
        return True

    def check_payload(self, path, payload, scope=""):
        self.check_name(path, scope)
        if len(payload) > MAX_BYTES:
            self.add(scope + "oversize-file", path)
            return
        try:
            text = payload.decode("utf-8-sig", errors="strict")
        except UnicodeError:
            self.add(scope + "binary-or-non-utf8", path)
            return
        if any(ord(char) < 32 and char not in "\t\n\r" for char in text):
            self.add(scope + "binary-or-control-character", path)
            return
        for category, offset in content_hits(text, self.deny_words):
            self.add(scope + category, path, text[:offset].count("\n") + 1)
        if PurePosixPath(path).suffix.lower() == ".svg":
            self.check_svg(path, text, scope)

    def check_svg(self, path, text, scope):
        if re.search(r"<!\s*(?:DOCTYPE|ENTITY)", text, re.I):
            self.add(scope + "svg-declaration", path)
            return
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            self.add(scope + "svg-invalid", path)
            return
        if root.tag.rsplit("}", 1)[-1].lower() != "svg":
            self.add(scope + "svg-invalid", path)
        for element in root.iter():
            name = element.tag.rsplit("}", 1)[-1].lower()
            if name in {"script", "foreignobject", "iframe", "object", "embed", "image"}:
                self.add(scope + "svg-active-or-image-content", path)
            for attribute, value in element.attrib.items():
                attribute = attribute.rsplit("}", 1)[-1].lower()
                if attribute.startswith("on"):
                    self.add(scope + "svg-event-handler", path)
                if attribute in {"href", "src"} and value and not value.startswith("#"):
                    self.add(scope + "svg-external-reference", path)
                if any(not target.strip(" \t\"'").startswith("#")
                       for target in re.findall(r"url\s*\(([^)]*)\)", value, re.I)):
                    self.add(scope + "svg-external-reference", path)
            if name == "style":
                styles = element.text or ""
                if "@import" in styles.lower() or any(
                    not target.strip(" \t\"'").startswith("#")
                    for target in re.findall(r"url\s*\(([^)]*)\)", styles, re.I)
                ):
                    self.add(scope + "svg-external-reference", path)

    def check_working_tree(self):
        if self.root.is_symlink():
            self.add("symbolic-link")
            return
        seen = set()
        for directory, folders, files in os.walk(self.root, followlinks=False):
            for name in list(folders):
                entry = Path(directory) / name
                path = entry.relative_to(self.root).as_posix()
                if entry.is_symlink():
                    self.add("symbolic-link", path)
                    folders.remove(name)
                elif name == ".git" and entry.parent == self.root:
                    folders.remove(name)
                elif name.lower() in BLOCKED_PARTS or BLOCKED_NAME.search(name):
                    self.add("forbidden-directory", path)
            for name in files:
                entry = Path(directory) / name
                path = entry.relative_to(self.root).as_posix()
                if path == ".git" and not entry.is_symlink():
                    continue
                seen.add(path)
                if entry.is_symlink():
                    self.add("symbolic-link", path)
                    continue
                try:
                    if entry.stat().st_size > MAX_BYTES:
                        self.check_name(path, "")
                        self.add("oversize-file", path)
                    else:
                        self.check_payload(path, entry.read_bytes())
                except OSError:
                    self.add("unreadable-file", path)
        for missing in self.allowed - seen:
            self.add("missing-listed-file", missing)

    def git(self, arguments, payload=None):
        return subprocess.run(
            ["git", "-C", str(self.root)] + arguments,
            input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )

    def is_git_root(self):
        try:
            result = self.git(["rev-parse", "--show-toplevel"])
            return result.returncode == 0 and Path(
                os.fsdecode(result.stdout).strip()
            ).resolve() == self.root.resolve()
        except (OSError, ValueError):
            return False

    def inspect_git_entries(self, entries, scope):
        objects = {}
        for mode, object_id, stage, path in entries:
            self.check_name(path, scope)
            if mode == "120000":
                self.add(scope + "symbolic-link", path)
                continue
            if mode not in {"100644", "100755"}:
                self.add(scope + "unsupported-git-mode", path)
                continue
            if stage != "0":
                self.add(scope + "unmerged-entry", path)
            objects.setdefault(object_id, []).append(path)
        self.inspect_git_blobs(objects, scope)
        return set(objects)

    def inspect_git_blobs(self, objects, scope):
        if not objects:
            return
        request = ("\n".join(objects) + "\n").encode("ascii")
        metadata = self.git(["cat-file", "--batch-check"], request)
        if metadata.returncode:
            self.add(scope + "git-read-error")
            return
        accepted = {}
        for row in metadata.stdout.splitlines():
            fields = row.split()
            if len(fields) != 3 or fields[1] != b"blob":
                self.add(scope + "git-object-invalid")
                continue
            object_id = fields[0].decode("ascii")
            try:
                size = int(fields[2])
            except ValueError:
                self.add(scope + "git-object-invalid")
                continue
            if size > MAX_BYTES:
                for path in objects.get(object_id, ["."]):
                    self.add(scope + "oversize-file", path)
            else:
                accepted[object_id] = objects[object_id]
        if not accepted:
            return
        request = ("\n".join(accepted) + "\n").encode("ascii")
        result = self.git(["cat-file", "--batch"], request)
        if result.returncode:
            self.add(scope + "git-read-error")
            return
        cursor = 0
        for expected_id, paths in accepted.items():
            ending = result.stdout.find(b"\n", cursor)
            header = result.stdout[cursor:ending].split()
            if ending < 0 or len(header) != 3 or header[0].decode("ascii") != expected_id:
                self.add(scope + "git-object-invalid")
                return
            size = int(header[2])
            start = ending + 1
            payload = result.stdout[start:start + size]
            if len(payload) != size or result.stdout[start + size:start + size + 1] != b"\n":
                self.add(scope + "git-object-invalid")
                return
            cursor = start + size + 1
            for path in paths:
                if path == "[unmapped-history-blob]":
                    self.add(scope + "unmapped-blob", path)
                    try:
                        text = payload.decode("utf-8-sig", errors="strict")
                    except UnicodeError:
                        self.add(scope + "binary-or-non-utf8", path)
                        continue
                    for category, offset in content_hits(text, self.deny_words):
                        self.add(scope + category, path, text[:offset].count("\n") + 1)
                else:
                    self.check_payload(path, payload, scope)

    def check_git_index(self):
        result = self.git(["ls-files", "--stage", "-z"])
        if result.returncode:
            self.add("staged.git-read-error")
            return
        entries = []
        for row in result.stdout.split(b"\0"):
            if not row:
                continue
            try:
                metadata, raw_path = row.split(b"\t", 1)
                mode, object_id, stage = metadata.decode("ascii").split()
                entries.append((mode, object_id, stage, raw_path.decode("utf-8")))
            except (ValueError, UnicodeError):
                self.add("staged.git-entry-invalid")
        self.inspect_git_entries(entries, "staged.")

    def check_git_history(self):
        # Discover every reachable object first; no reliance on only HEAD or the worktree.
        objects_result = self.git(["rev-list", "--objects", "--all", "--no-object-names"])
        commits_result = self.git(["rev-list", "--all"])
        if objects_result.returncode or commits_result.returncode:
            self.add("history.git-read-error")
            return
        reachable = {row.decode("ascii") for row in objects_result.stdout.splitlines()}
        entries = set()
        for commit in commits_result.stdout.splitlines():
            tree = self.git(["ls-tree", "-rz", "--full-tree", commit.decode("ascii")])
            if tree.returncode:
                self.add("history.git-read-error")
                continue
            for row in tree.stdout.split(b"\0"):
                if not row:
                    continue
                try:
                    metadata, raw_path = row.split(b"\t", 1)
                    mode, kind, object_id = metadata.decode("ascii").split()
                    if object_id not in reachable:
                        self.add("history.git-object-invalid")
                        continue
                    entries.add((mode, object_id, "0", raw_path.decode("utf-8")))
                except (ValueError, UnicodeError):
                    self.add("history.git-entry-invalid")
        mapped = self.inspect_git_entries(sorted(entries), "history.")
        # A ref can point directly to a blob, outside every committed file tree.
        unmapped = reachable - mapped
        if unmapped:
            request = ("\n".join(sorted(unmapped)) + "\n").encode("ascii")
            metadata = self.git(["cat-file", "--batch-check"], request)
            if metadata.returncode:
                self.add("history.git-read-error")
            else:
                blobs = {}
                for row in metadata.stdout.splitlines():
                    fields = row.split()
                    if len(fields) == 3 and fields[1] == b"blob":
                        blobs[fields[0].decode("ascii")] = ["[unmapped-history-blob]"]
                self.inspect_git_blobs(blobs, "history.")

    def run(self, include_history=False):
        if self.load_manifest():
            self.check_working_tree()
            if self.is_git_root():
                self.check_git_index()
                if include_history:
                    self.check_git_history()
            elif include_history:
                self.add("history.git-unavailable")
        return {"ok": not self.findings, "findings": [
            {"category": category, "path": path, "line": line}
            for category, path, line in sorted(self.findings)
        ]}


def read_deny_words(path):
    if not path:
        return []
    text = Path(path).read_text(encoding="utf-8-sig")
    if text.lstrip().startswith("["):
        words = json.loads(text)
        if not isinstance(words, list) or any(not isinstance(word, str) for word in words):
            raise ValueError("deny list")
        return [word.strip() for word in words if word.strip()]
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--deny-file")
    parser.add_argument("--git-history", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        result = Auditor(arguments.root, arguments.manifest, read_deny_words(arguments.deny_file)).run(
            arguments.git_history
        )
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
        result = {"ok": False, "findings": [{"category": "audit-error", "path": ".", "line": 1}]}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
