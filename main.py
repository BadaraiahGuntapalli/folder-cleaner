"""
Folder Cleaner — entry point.
Usage: python main.py <command> [options]
"""

from cleaner.cleaner import build_parser

if __name__ == "__main__":
    parser = build_parser()
    args   = parser.parse_args()
    args.func(args)
