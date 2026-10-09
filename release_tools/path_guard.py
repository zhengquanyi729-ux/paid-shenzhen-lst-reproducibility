"""
path_guard.py — containment guard for the review layer
======================================================
Every file the portable verifiers open must live *inside* the release archive.
This guard fails loudly if a resolved path escapes RELEASE_ROOT, which is the
programmatic expression of the rule "no reviewer command may read a path outside
the archive".

It is deliberately tiny and dependency-free; callers use it like:

    from path_guard import guard
    with open(guard(release_paths.ZONE_C_ANALYSIS_READY), 'rb') as fh:
        ...
"""
from pathlib import Path

try:
    from release_paths import RELEASE_ROOT
except ImportError:                                   # pragma: no cover
    from .release_paths import RELEASE_ROOT


class PathEscapeError(RuntimeError):
    pass


def guard(path):
    """Resolve `path` and assert it is contained in RELEASE_ROOT; return the resolved Path."""
    resolved = Path(path).resolve()
    root = Path(RELEASE_ROOT).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise PathEscapeError(
            'Reviewer verification attempted to access a path outside the release '
            'archive: %s (release root: %s)' % (resolved, root))
    return resolved


def is_inside(path):
    """Non-raising variant: True if `path` resolves inside the release root."""
    try:
        guard(path)
        return True
    except PathEscapeError:
        return False


if __name__ == '__main__':
    # self-test: an in-archive path passes, an out-of-archive path raises.
    ok = is_inside(RELEASE_ROOT / 'README.md')
    outside = is_inside('/etc/hosts')
    print('guard self-test: inside=%s outside=%s' % (ok, outside))
    assert ok is True and outside is False
    print('path_guard OK')
