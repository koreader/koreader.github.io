#!/usr/bin/env python3
"""
Add leading section numbers to duplicate TOC/heading msgstr values.

An entry is considered a TOC/heading duplicate when the same numbered msgid
appears more than once in a PO file. For every such entry whose msgstr does
not already start with a number, the section number is prepended to msgstr.
Fuzzy flags and all other entry data are left untouched, so fuzzy entries stay
fuzzy and already-clean entries stay clean.

Usage examples:
    python add_section_numbers.py i18n/po/nl.po --dry-run -v
    python add_section_numbers.py i18n/po/nl.po -v

Exit codes:
    0 success
    1 file not found / parse error
"""
import argparse
import os
import re
import sys

_SECTION_NUMBER_RE = re.compile(r'^(\d+(?:\.\d+)*)\s+')

def safe_print(*a, **kw):
    try:
        print(*a, **kw)
    except BrokenPipeError:
        try:
            sys.stdout.close()
        finally:
            raise SystemExit(0)

def _collect_msgid(block_lines):
    pat_header = re.compile(r'^msgid\s+"(.*)"')
    pat_cont = re.compile(r'^"(.*)"')
    collecting = False
    parts = []
    for line in block_lines:
        if not collecting and line.startswith('msgid '):
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

def _collect_msgstr(block_lines):
    pat_header = re.compile(r'^msgstr\s+"(.*)"')
    pat_cont = re.compile(r'^"(.*)"')
    collecting = False
    parts = []
    for line in block_lines:
        if not collecting and line.startswith('msgstr '):
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

def _is_fuzzy(block_lines):
    for line in block_lines:
        if line.startswith('#,'):
            return 'fuzzy' in [t.strip() for t in line[2:].split(',')]
    return False

def _already_numbered(msgstr):
    return re.match(r'^\s*\d', msgstr) is not None

def _msgstr_line_index(block_lines):
    for i, line in enumerate(block_lines):
        if line.startswith('msgstr '):
            return i
    return None

def process_file(infile, outfile, dry_run, verbose):
    with open(infile, 'r', encoding='utf-8') as fh:
        lines = fh.readlines()

    total = len(lines)
    blocks = []
    i = 0
    while i < total:
        if lines[i].strip() == '':
            i += 1
            continue
        start = i
        while i < total and lines[i].strip() != '':
            i += 1
        block = lines[start:i]
        if any(line.startswith('#~') for line in block):
            continue
        msgid = _collect_msgid(block)
        if msgid is None:
            continue
        match = _SECTION_NUMBER_RE.match(msgid)
        if not match:
            continue
        msgstr = _collect_msgstr(block)
        if not msgstr:
            continue
        blocks.append({
            'start': start,
            'block': block,
            'msgid': msgid,
            'msgstr': msgstr,
            'number': match.group(1),
            'fuzzy': _is_fuzzy(block),
        })

    groups = {}
    for entry in blocks:
        groups.setdefault(entry['msgid'], []).append(entry)

    out_lines = lines[:]
    modified = 0
    for msgid, entries in groups.items():
        if len(entries) < 2:
            continue
        for entry in entries:
            if _already_numbered(entry['msgstr']):
                continue
            block = entry['block']
            offset = _msgstr_line_index(block)
            if offset is None:
                continue
            line_index = entry['start'] + offset
            original = out_lines[line_index]
            prefix, quoted = original.split('msgstr ', 1)
            out_lines[line_index] = prefix + 'msgstr "' + entry['number'] + ' ' + quoted[len('"'):]
            modified += 1
            if verbose:
                state = 'fuzzy' if entry['fuzzy'] else 'clean'
                safe_print(f'[NUMBER] {entry["number"]} ({state}) {msgid[:90]}')

    if dry_run:
        safe_print(f'Dry run: {modified} duplicate entries would get section numbers.')
        return 0

    target = outfile or infile
    try:
        with open(target, 'w', encoding='utf-8') as fh:
            fh.writelines(out_lines)
    except OSError as e:
        print(f'Error writing output {target}: {e}', file=sys.stderr)
        return 1
    safe_print(f'Updated {modified} duplicate entries. Written to {target}')
    return 0

def parse_args():
    ap = argparse.ArgumentParser(description="Add section numbers to duplicate TOC/heading translations.")
    ap.add_argument("po_file", help="Input .po file")
    ap.add_argument("-o", "--output", help="Output file (default: overwrite input)")
    ap.add_argument("--dry-run", action="store_true", help="Do not modify; just report")
    ap.add_argument("-v", "--verbose", action="store_true", help="Verbose per-entry reporting")
    return ap.parse_args()

def main():
    args = parse_args()
    if not os.path.isfile(args.po_file):
        print(f"Error: file not found: {args.po_file}", file=sys.stderr)
        return 1
    return process_file(args.po_file, args.output, args.dry_run, args.verbose)

if __name__ == "__main__":
    sys.exit(main())
