import sys


def step(name, detail=""):
    print(f"\n▸ {name:<9} {detail}".rstrip(), flush=True)


def info(text):
    print(f"  {text}", flush=True)


def done(text):
    print(f"  ✓ {text}", flush=True)


def warn(text):
    print(f"  ! {text}", file=sys.stderr, flush=True)


def error(text):
    print(f"  ✗ {text}", file=sys.stderr, flush=True)
