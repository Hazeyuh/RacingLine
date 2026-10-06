#!/usr/bin/env python3
"""Regenerate the corrected manual trace; raster extraction is retained as legacy."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('trace_nanjing.py')),run_name='__main__')
