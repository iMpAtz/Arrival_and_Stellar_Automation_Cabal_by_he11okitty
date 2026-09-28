"""Entry point for a build that omits the Macro tab and implementation."""
import sys

sys.argv.append("--without-macro")

from main import main


if __name__ == "__main__":
    main()
