"""CLI entry point: parse an MTEF binary file and print the LaTeX result.

Usage:
    python -m mtef_py path/to/oleObject.bin
"""
import sys
from .mtef import MTEF


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m mtef_py <path_to_oleObject.bin>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "rb") as f:
        data = f.read()

    mtef, err = MTEF.OpenBytes(data)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    latex = mtef.Translate()
    print(latex)


if __name__ == "__main__":
    main()
