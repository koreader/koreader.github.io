#!/usr/bin/env python3
"""
Unfuzzy PO entries whose msgctxt only changed by a small numeric line offset shift.

Removes 'fuzzy' flag when  previous and current msgctxt differ only by numeric line offsets (":<start>-<len>") and EACH corresponding <start> delta <= --line-shift-threshold.

Usage examples:
    python unfuzzy_msgctxt.py i18n/po/nl.po --line-shift-threshold 8 --dry-run -v
    python unfuzzy_msgctxt.py i18n/po/nl.po --line-shift-threshold 10 -v

Exit codes:
    0 success
    1 file not found / parse error
"""
import argparse
import os
import re
import sys

_DEBUG_LINE_SHIFT = False

def safe_print(*a, **kw):
    try:
        print(*a, **kw)
    except BrokenPipeError:
        try:
            sys.stdout.close()
        finally:
            raise SystemExit(0)

_LINE_OFFSET_RE = re.compile(r':(\d+)-(\d+)')

def _normalize_context(ctx: str) -> str:
    """Normalize a msgctxt that may have been accidentally duplicated by concatenation.

    Example problematic form:
        'path:876-17path:876-17' -> 'path:876-17'

    Strategy:
      - Try k repetitions (2..6). If ctx == segment * k and segment contains at least
        one line offset pattern, collapse to segment.
      - Prefer the smallest k>1 that matches (thus highest compression) and return immediately.
    """
    s = ctx
    length = len(s)
    # Quick exit if too short
    if length < 4:
        return s
    for k in range(2, 7):  # allow up to 6 repeats just in case
        if length % k != 0:
            continue
        part_len = length // k
        segment = s[:part_len]
        if segment * k == s:
            # Only collapse if segment has at least one :<n>-<n> pattern
            if _LINE_OFFSET_RE.search(segment):
                if _DEBUG_LINE_SHIFT:
                    safe_print(f'[line-shift DEBUG] Normalizing duplicated context x{k} -> single segment')
                return segment
    return s

def evaluate_line_shift(old_ctx: str, new_ctx: str, threshold: int):
    """Return (passed: bool, reason: str) for line-shift heuristic.

    Reasons when passed is False:
      - threshold_disabled
      - structural_mismatch
      - match_count_mismatch
      - non_integer
      - delta_exceeded
    When passed is True:
      - ok (or ok_identical if identical before normalization)
    """
    if threshold <= 0:
        if _DEBUG_LINE_SHIFT:
            safe_print('[line-shift DEBUG] Threshold <= 0; heuristic disabled.')
        return False, 'threshold_disabled'
    identical = old_ctx == new_ctx
    # Limit printing length for readability
    def _short(s):
        return (s if len(s) <= 180 else s[:177] + '...')
    norm_old = _normalize_context(old_ctx)
    norm_new = _normalize_context(new_ctx)
    if _DEBUG_LINE_SHIFT and (norm_old != old_ctx or norm_new != new_ctx):
        safe_print('[line-shift DEBUG] Applied normalization to contexts')
    old_ctx_proc = norm_old
    new_ctx_proc = norm_new
    if identical:
        return True, 'ok_identical'

    old_struct = _LINE_OFFSET_RE.sub(':X-X', old_ctx_proc)
    new_struct = _LINE_OFFSET_RE.sub(':X-X', new_ctx_proc)
    if _DEBUG_LINE_SHIFT:
        safe_print('[line-shift DEBUG] old_ctx =', _short(old_ctx_proc))
        safe_print('[line-shift DEBUG] new_ctx =', _short(new_ctx_proc))
        safe_print('[line-shift DEBUG] old_struct =', _short(old_struct))
        safe_print('[line-shift DEBUG] new_struct =', _short(new_struct))
    if old_struct != new_struct:
        if _DEBUG_LINE_SHIFT:
            safe_print('[line-shift DEBUG] Structural mismatch')
        return False, 'structural_mismatch'
    old_matches = list(_LINE_OFFSET_RE.finditer(old_ctx_proc))
    new_matches = list(_LINE_OFFSET_RE.finditer(new_ctx_proc))
    if _DEBUG_LINE_SHIFT:
        safe_print(f'[line-shift DEBUG] old_matches={len(old_matches)} new_matches={len(new_matches)} threshold={threshold}')
    if len(old_matches) != len(new_matches):
        return False, 'match_count_mismatch'
    for idx, (om, nm) in enumerate(zip(old_matches, new_matches)):
        try:
            o_start = int(om.group(1))
            n_start = int(nm.group(1))
        except ValueError:
            return False, 'non_integer'
        delta = abs(o_start - n_start)
        if _DEBUG_LINE_SHIFT:
            safe_print(f'[line-shift DEBUG] pair {idx}: old={o_start} new={n_start} Δ={delta}')
        if delta > threshold:
            return False, 'delta_exceeded'
    return True, 'ok'

def _strip_fuzzy_flag_line(raw_line: str) -> str:
    """Remove the fuzzy token from a '#,' flag line, preserving other flags & spacing as much as possible.

    Returns modified line (with trailing newline) or empty string if only fuzzy was present.
    """
    if '#,' not in raw_line:
        return raw_line
    prefix, after = raw_line.split('#,', 1)
    tokens = [t for t in after.strip().split(',') if t.strip()]
    kept = [t for t in tokens if t.strip() != 'fuzzy']
    if not kept:
        return ''
    return f"{prefix}#, {', '.join(kept)}\n"

def _collect_prev_ctx(block_lines):
    """Collect previous msgctxt from a block (multiline #| msgctxt)."""
    prev_ctx_parts = []
    collecting = False
    pat_header = re.compile(r'^#\|\s*msgctxt\s+"(.*)"')
    pat_cont = re.compile(r'^#\| "(.*)"')
    for line in block_lines:
        if not collecting and line.startswith('#| msgctxt'):
            collecting = True
            m = pat_header.match(line)
            if m:
                prev_ctx_parts.append(m.group(1))
            continue
        if collecting:
            if line.startswith('#| "'):
                m2 = pat_cont.match(line)
                if m2:
                    prev_ctx_parts.append(m2.group(1))
            else:
                break
    return ''.join(prev_ctx_parts) if prev_ctx_parts else None

def _collect_cur_ctx(block_lines):
    """Collect current msgctxt (may span multiple literal lines)."""
    pat_header = re.compile(r'^msgctxt\s+"(.*)"')
    pat_cont = re.compile(r'^"(.*)"')
    collecting = False
    parts = []
    for line in block_lines:
        if not collecting and line.startswith('msgctxt '):
            m = pat_header.match(line)
            if m:
                parts.append(m.group(1))
            collecting = True
            continue
        if collecting:
            if line.startswith('"'):
                m2 = pat_cont.match(line)
                if m2:
                    parts.append(m2.group(1))
            else:
                break
    return ''.join(parts) if parts else None

def process_file(infile, outfile, dry_run, verbose, keep_backup, line_shift_threshold):
    with open(infile, 'r', encoding='utf-8') as fh:
        lines = fh.readlines()

    out_lines = lines[:]  # copy for in-place style edits
    total = len(lines)
    i = 0
    modified = 0
    considered = 0

    while i < total:
        line = lines[i]
        if '#, ' in line and 'fuzzy' in line:
            block_start = i  # index in original lines
            block_end = i + 1
            while block_end < total and lines[block_end].strip() != '':
                block_end += 1
            block = lines[block_start:block_end]

            prev_ctx = _collect_prev_ctx(block)
            cur_ctx = _collect_cur_ctx(block)
            if prev_ctx and cur_ctx:
                considered += 1
                passed, reason_code = evaluate_line_shift(prev_ctx, cur_ctx, line_shift_threshold)
                if passed:
                    original_flag_line = out_lines[block_start]
                    new_flag_line = _strip_fuzzy_flag_line(original_flag_line)
                    out_lines[block_start] = new_flag_line
                    modified += 1
                    if verbose:
                        safe_print(f'[UNFUZZ] line-shift msgctxt={cur_ctx[:80]}{"..." if len(cur_ctx)>80 else ""}')
                else:
                    if verbose:
                        safe_print(f'[KEEP FUZZY] reason={reason_code} msgctxt={cur_ctx[:80]}{"..." if len(cur_ctx)>80 else ""}')
            i = block_end
        else:
            i += 1

    if dry_run:
        safe_print(f'Dry run: {modified} / {considered} fuzzy contextual entries would be unfuzzed.')
        return 0

    target = outfile or infile
    if keep_backup and target == infile:
        backup_name = infile + '.bak'
        if not os.path.exists(backup_name):
            try:
                with open(backup_name, 'w', encoding='utf-8') as bf:
                    bf.writelines(lines)
                if verbose:
                    safe_print(f'Backup saved to {backup_name}')
            except OSError as e:
                print(f'Error writing backup {backup_name}: {e}', file=sys.stderr)
                return 1
    # Collapse consecutive blank lines and remove leading blank lines created by fuzzy removal
    cleaned = []
    last_blank = True  # treat start as blank to avoid leading empties
    for line in out_lines:
        is_blank = line.strip() == ''
        if is_blank and last_blank:
            continue
        cleaned.append(line if line.endswith('\n') or line == '' else line + '\n')
        last_blank = is_blank
    try:
        with open(target, 'w', encoding='utf-8') as fh:
            fh.writelines(cleaned)
    except OSError as e:
        print(f'Error writing output {target}: {e}', file=sys.stderr)
        return 1
    safe_print(f'Unfuzzed {modified} / {considered} fuzzy contextual entries. Written to {target}')
    return 0

def parse_args():
    ap = argparse.ArgumentParser(description="Unfuzzy entries whose msgctxt only changed by small numeric line offset shifts.")
    ap.add_argument("po_file", help="Input .po file")
    ap.add_argument("-o", "--output", help="Output file (default: overwrite input)")
    ap.add_argument("--line-shift-threshold", type=int, default=8, help="Maximum allowed line offset delta per pair (default: 8; set 0 to disable).")
    ap.add_argument("--dry-run", action="store_true", help="Do not modify; just report")
    ap.add_argument("--debug-line-shift", action="store_true", help="Verbose debug output for line shift heuristic decisions.")
    ap.add_argument("--no-backup", action="store_true", help="Do not create .bak when overwriting")
    ap.add_argument("-v", "--verbose", action="store_true", help="Verbose per-entry reporting")
    return ap.parse_args()

def main():
    args = parse_args()
    if not os.path.isfile(args.po_file):
        print(f"Error: file not found: {args.po_file}", file=sys.stderr)
        return 1

    keep_backup = not args.no_backup

    global _DEBUG_LINE_SHIFT
    _DEBUG_LINE_SHIFT = args.debug_line_shift

    return process_file(
        args.po_file,
        args.output,
        args.dry_run,
        args.verbose,
        keep_backup,
        args.line_shift_threshold,
    )

if __name__ == "__main__":
    sys.exit(main())
