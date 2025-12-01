#!/usr/bin/env python3
"""
Entry point for running scripts package as a module.
This allows: python -m scripts
"""
import sys
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import and run based on command line arguments
if len(sys.argv) > 1 and sys.argv[1] == "generate_mod650cat_pdf_clean_version":
    from scripts.generate_mod650cat_pdf_clean_version import main
    # Remove the subcommand from argv so argparse works correctly
    sys.argv.pop(1)
    main()
else:
    print("Usage: python -m scripts generate_mod650cat_pdf_clean_version")
    sys.exit(1)

