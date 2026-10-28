#!/usr/bin/env python3
"""Compatibility entry point for the four linked founding PDFs."""
import runpy
from pathlib import Path
if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parents[1] / 'founding/build_documents.py'), run_name='__main__')
