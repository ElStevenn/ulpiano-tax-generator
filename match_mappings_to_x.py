from pathlib import Path
import json
import math
import sys

# Import FIELD_MAPPINGS from the main script
from generate_mod650cat_pdf import FIELD_MAPPINGS
from generate_mod650cat_pdf import FieldMapping


def load_x_positions(jsonl_path: Path):
    items = []
    with jsonl_path.open('r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def match_mappings(x_positions, threshold=5.0):
    # Index x_positions by page
    by_page = {}
    for p in x_positions:
        by_page.setdefault(p['page_index'], []).append(p)

    results = []
    for mapping in FIELD_MAPPINGS:
        if mapping.field_type != 'checkbox':
            continue
        # mapping.pages is a sequence; check each page where mapping applies
        for page in mapping.pages:
            # skip pages beyond available positions (handled by caller)
            candidates = by_page.get(page, [])
            # compute mapping's expected coord
            mx = float(mapping.x)
            my = float(mapping.y_from_top)
            best = None
            for c in candidates:
                # consider only capital X or x
                if c.get('char') not in ('X', 'x'):
                    continue
                # compute center of char bbox
                cx = (c['x0'] + c['x1']) / 2.0
                cy = c['y_from_top']
                dx = cx - mx
                dy = cy - my
                dist = math.hypot(dx, dy)
                if best is None or dist < best['dist']:
                    best = {'dist': dist, 'cx': cx, 'cy': cy, 'item': c}
            found = best is not None and best['dist'] <= threshold
            results.append({
                """
                Deprecated helper: matching logic was consolidated into
                `scripts/generate_mod650cat_pdf.py` (use `--match-threshold` after extraction).
                This file is kept as a stub for backward compatibility.
                """
                'min_dist': None if best is None else best['dist'],
