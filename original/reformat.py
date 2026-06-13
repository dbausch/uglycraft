#!/usr/bin/env python3
"""Reformat UGLI 2 Pascal sources to house style.

Usage: python reformat.py input.pas [output.pas]
Overwrites input.pas in-place (saves .bak) if output not given.
"""
import re, sys, shutil, tomllib
from pathlib import Path

# ── Casing tables ─────────────────────────────────────────────────────────────

KEYWORDS = frozenset("""
program uses label const var begin end if then else for to do while procedure
function repeat until case of not and or div mod type record array true false
unit interface implementation with downto in nil set file goto break exit
object constructor destructor forward external absolute packed shl shr xor
""".split())

TYPES = {
    'string': 'String', 'integer': 'Integer', 'longint': 'LongInt',
    'boolean': 'Boolean', 'char': 'Char', 'byte': 'Byte', 'word': 'Word',
    'real': 'Real', 'text': 'Text', 'shortint': 'ShortInt',
    'longword': 'LongWord', 'cardinal': 'Cardinal',
}

BUILTINS = {
    'writeln': 'WriteLn', 'write': 'Write', 'readln': 'ReadLn', 'read': 'Read',
    'readkey': 'ReadKey', 'gotoxy': 'GotoXY', 'clrscr': 'ClrScr',
    'clreol': 'ClrEol', 'textcolor': 'TextColor', 'textbackground': 'TextBackground',
    'textattr': 'TextAttr', 'keypressed': 'KeyPressed', 'getkey': 'GetKey',
    'window': 'Window', 'delay': 'Delay',
    'black': 'Black', 'blue': 'Blue', 'green': 'Green', 'cyan': 'Cyan',
    'red': 'Red', 'magenta': 'Magenta', 'brown': 'Brown', 'lightgray': 'LightGray',
    'darkgray': 'DarkGray', 'lightblue': 'LightBlue', 'lightgreen': 'LightGreen',
    'lightcyan': 'LightCyan', 'lightred': 'LightRed',
    'lightmagenta': 'LightMagenta', 'yellow': 'Yellow', 'white': 'White',
    'blink': 'Blink',
    'assign': 'Assign', 'rewrite': 'ReWrite', 'reset': 'Reset', 'flush': 'Flush',
    'close': 'Close', 'append': 'Append', 'eof': 'Eof', 'eoln': 'EoLn',
    'inc': 'Inc', 'dec': 'Dec', 'chr': 'Chr', 'ord': 'Ord', 'length': 'Length',
    'str': 'Str', 'val': 'Val', 'copy': 'Copy', 'pos': 'Pos',
    'concat': 'Concat', 'delete': 'Delete', 'insert': 'Insert', 'upcase': 'UpCase',
    'abs': 'Abs', 'sqr': 'Sqr', 'sqrt': 'Sqrt', 'random': 'Random',
    'randomize': 'Randomize', 'halt': 'Halt',
    'ioresult': 'IOResult', 'paramcount': 'ParamCount', 'paramstr': 'ParamStr',
    'hi': 'Hi', 'lo': 'Lo',
    'soundbrumm': 'SoundBrumm', 'soundpickup': 'SoundPickup',
    'soundcaught': 'SoundCaught', 'soundgameover': 'SoundGameOver',
    'soundgewonnen': 'SoundGewonnen',
    'ton': 'Ton', 'sound': 'Sound', 'nosound': 'NoSound',
    'erkennung': 'Erkennung', 'erkennung2': 'Erkennung2',
    'utf8cols': 'UTF8Cols', 'zentriert': 'Zentriert', 'wln': 'WLn',
    # Game-specific procedures with non-obvious casing
    'writexy': 'WriteXY', 'drawhline': 'DrawHLine', 'drawvline': 'DrawVLine',
    'mycursoron': 'MyCursorOn', 'mycursoroff': 'MyCursorOff',
    'writelevel': 'WriteLevel', 'restone': 'ReStone',
    'punktezaehlen': 'PunkteZaehlen', 'zahlenSetzung': 'ZahlenSetzung',
    'zahlensetzung': 'ZahlenSetzung', 'zuFalsPos': 'ZufalsPos',
    'zufalspos': 'ZufalsPos', 'steinesetzen': 'SteineSetzen',
    'steinenehmen': 'SteineNehmen', 'pausenzeigen': 'PausenZeigen',
    'levelneu': 'LevelNeu',
}

ALLCAPS = {
    'dx': 'DX', 'dy': 'DY',
    'ex': 'EX', 'ey': 'EY',          # enemy position (renamed from XX/YY)
    'tty': 'TTY',
    'danisoft': 'DANISOFT',
    'ugli_2': 'UGLI_2',               # program name
}

UNIT_NAMES = {
    'cthreads': 'CThreads', 'crt': 'Crt', 'dos': 'Dos', 'uossound': 'UOSSound',
}

# ── Renames: old-lowercase → new-cased name ───────────────────────────────────
# Loaded from renames.toml (same directory as this script).
# Checked first in case(), overrides every other table.

_RENAMES_FILE = Path(__file__).parent / 'renames.toml'
with _RENAMES_FILE.open('rb') as _f:
    RENAMES: dict[str, str] = tomllib.load(_f)['renames']

# ── Compound identifier abbreviation suffix rule ───────────────────────────────
# After PascalCase, identifiers whose tail matches one of these are uppercased.
# Sorted longest-first so 'TTY' is tried before 'TY', 'XX' before 'X', etc.
# Require prefix ≥ 2 chars so short words like 'My' are not altered.
_SUFFIX_ABBREVS: list[tuple[str, str]] = sorted([
    ('tty', 'TTY'),
    # xx/yy/x/y coordinate suffixes were removed: those identifiers are now
    # handled explicitly via RENAMES, and the single-letter rules caused false
    # positives on English words like Entry, Story, Delay, Key, etc.
], key=lambda t: len(t[0]), reverse=True)


def apply_compound_abbrevs(s: str) -> str:
    """Uppercase the first matching abbreviation found at the end of the identifier."""
    low = s.lower()
    for abbr_low, abbr_up in _SUFFIX_ABBREVS:
        n = len(abbr_low)
        if len(s) - n >= 2 and low.endswith(abbr_low):
            return s[:-n] + abbr_up
    return s


def case(val: str) -> str:
    low = val.lower()
    if low in RENAMES:
        return RENAMES[low]
    for tbl in (ALLCAPS, UNIT_NAMES, BUILTINS, TYPES):
        if low in tbl:
            return tbl[low]
    if low in KEYWORDS:
        return low
    pascal = val[0].upper() + val[1:] if val else val
    return apply_compound_abbrevs(pascal)


# ── Tokenizer ─────────────────────────────────────────────────────────────────

_RE = re.compile(r"""
    (?P<D>  \{\$[^}]*\}                   ) |
    (?P<CB> \{[^}]*\}                     ) |
    (?P<CP> \(\*.*?\*\)                   ) |
    (?P<CL> //[^\n]*                      ) |
    (?P<S>  '(?:''|[^'\n])*'             ) |
    (?P<CH> \#(?:\$[0-9a-fA-F]+|[0-9]+)  ) |
    (?P<ID> [a-zA-Z_][a-zA-Z0-9_]*       ) |
    (?P<N>  \$[0-9a-fA-F]+|\d+(?:\.\d+)? ) |
    (?P<NL> \r?\n                         ) |
    (?P<WS> [ \t]+                        ) |
    (?P<P>  \.\.|:=|<>|<=|>=|.            )
""", re.VERBOSE | re.DOTALL)

COMMENT_KINDS = frozenset(['D', 'CB', 'CP', 'CL'])


def tokenize(src: str):
    return [(m.lastgroup, m.group()) for m in _RE.finditer(src)]


# ── Token helpers ─────────────────────────────────────────────────────────────

def sig(line):
    """Lower-case values of significant (non-WS, non-comment) tokens."""
    return [v.lower() for k, v in line
            if k not in ('WS',) + tuple(COMMENT_KINDS)]


def first_sig(line):
    s = sig(line)
    return s[0] if s else ''


def last_sig(line):
    s = sig(line)
    return s[-1] if s else ''


def is_goto_label(line, innermost_is_case: bool) -> bool:
    """True if this line is just a numeric goto label like '100:' or '300:'.
    When the innermost block is a case block, numeric 'N:' lines are case arms."""
    if innermost_is_case:
        return False  # inside case...of, colons are case arms
    s = sig(line)
    return len(s) == 2 and s[0].isdigit() and s[1] == ':'


# ── Line splitter ─────────────────────────────────────────────────────────────

def split_begin(line):
    """
    'begin' is always on its own line.
    Split before any 'begin' that is not the first token.
    Then split after 'begin' if it is not the last token.
    """
    ns = [(i, k, v) for i, (k, v) in enumerate(line)
          if k not in ('WS',) + tuple(COMMENT_KINDS)]

    for pos, (orig_i, k, v) in enumerate(ns):
        if k == 'ID' and v.lower() == 'begin':
            if pos > 0:
                # Split BEFORE begin
                before = line[:orig_i]
                after = line[orig_i:]
                return [before] + split_begin(after)
            elif pos == 0 and len(ns) > 1:
                # begin IS first; split everything after it onto the next line
                next_orig_i = ns[1][0]
                before = line[:next_orig_i]  # [begin] only
                after = line[next_orig_i:]
                return [before] + split_begin(after)

    return [line]


def split_end_else(line):
    """Split before 'end'/'until' when not first, and split before 'else' after 'end'/';'."""
    ns = [(i, k, v) for i, (k, v) in enumerate(line)
          if k not in ('WS',) + tuple(COMMENT_KINDS)]

    for pos, (orig_i, k, v) in enumerate(ns):
        vl = v.lower()
        if k == 'ID' and vl in ('end', 'until') and pos > 0:
            # Split before 'end'
            before = line[:orig_i]
            after = line[orig_i:]
            return split_end_else(before) + split_end_else(after)
        if k == 'ID' and vl == 'else' and pos > 0:
            prev_v = ns[pos - 1][2].lower()
            if prev_v in ('end', ';'):
                before = line[:orig_i]
                after = line[orig_i:]
                return [before] + split_end_else(after)

    return [line]


def split_lines(lines):
    result = []
    for line in lines:
        for sub in split_begin(line):
            result.extend(split_end_else(sub))
    return result


# ── Line content formatter ────────────────────────────────────────────────────

NO_SPACE_BEFORE = frozenset([')', ']', ',', ';', ':', '.', '..', '['])
NO_SPACE_AFTER  = frozenset(['(', '[', '@', '^', '..'])


def reformat_end_comment(tok: str) -> str:
    """Reformat {content} on an end line: apply casing, strip leading/trailing spaces."""
    inner = tok[1:-1].strip()
    if not inner:
        return '{}'
    toks = [(k, v) for k, v in tokenize(inner) if k != 'NL']
    return '{' + format_line(toks) + '}'


def format_line(line, is_end_line: bool = False) -> str:
    """Apply casing and normalize spacing within one line."""
    out = []
    prev_kind, prev_val = None, None

    for k, v in line:
        if k == 'WS':
            continue
        if k == 'ID':
            v = case(v)
        if k == 'CB' and is_end_line:
            v = reformat_end_comment(v)

        if prev_val is not None:
            need_space = True
            if v in NO_SPACE_BEFORE:
                need_space = False
            elif prev_val in NO_SPACE_AFTER or prev_kind == 'CH':
                need_space = False
            elif v == '(' and prev_kind == 'ID' and prev_val.lower() not in KEYWORDS:
                need_space = False  # function call: no space
            elif v == '[':
                need_space = False
            elif prev_val == ',':
                need_space = True   # always space after comma
            if need_space:
                out.append(' ')

        out.append(v)
        prev_kind, prev_val = k, v

    return ''.join(out)


# ── Indentation pass ──────────────────────────────────────────────────────────

def indent_lines(lines) -> list[str]:
    """
    Assign indentation to each line.

    begin_stack entries: (emit_depth, outer_depth, is_case)
      emit_depth  = depth at which 'begin'/'repeat'/'case' was emitted
                    (also used as the depth for the matching 'end'/'until')
      outer_depth = depth to restore after the closing 'end'/'until'
      is_case     = True when the block is a case...of block (so numeric N: are case arms)

    after_ctrl_extra: accumulated extra indent levels from chained then/do/else.
      0 = normal. N means the next non-structural line gets depth+N.
      Incremented by 1 for each chained ctrl keyword, so nested single-statement
      bodies like 'for J do\nfor I do\nstmt' each deepen by one extra level.

    paren_depth: unclosed '(' from previous lines; when > 0 the current line is a
      continuation of an argument list and gets depth+1 indentation.
    """
    depth = 0
    begin_stack: list[tuple[int, int, bool]] = []
    result = []
    in_decl = False
    after_ctrl_extra: int = 0
    in_case = False
    paren_depth = 0

    def push_body(d: int, is_case: bool = False):
        begin_stack.append((d, d, is_case))
        return d

    def pop_block():
        if begin_stack:
            e, o, _ = begin_stack.pop()
            return (e, o)
        return (max(0, depth - 1), max(0, depth - 1))

    def innermost_is_case() -> bool:
        return bool(begin_stack) and begin_stack[-1][2]

    for line in lines:
        sv = sig(line)
        if not sv:
            result.append('')
            continue

        fs = sv[0]
        is_continuation = paren_depth > 0

        # ── Goto labels at column 0 ───────────────────────────────────────
        if is_goto_label(line, innermost_is_case()):
            result.append(format_line(line))
            after_ctrl_extra = 0
            for k, v in line:
                if k == 'P':
                    if v == '(':
                        paren_depth += 1
                    elif v == ')':
                        paren_depth = max(0, paren_depth - 1)
            continue

        # ── Compute this line's indentation ──────────────────────────────
        line_depth = depth

        if fs == 'begin':
            ed = depth + after_ctrl_extra
            begin_stack.append((ed, depth, False))
            line_depth = ed
            depth = ed + 1
            in_decl = False
            after_ctrl_extra = 0

        elif fs in ('end', 'until'):
            ed, od = pop_block()
            line_depth = ed
            depth = od
            in_decl = False
            after_ctrl_extra = 0

        elif fs == 'else':
            line_depth = depth
            after_ctrl_extra = 0
            ls = last_sig(line)
            if ls != ';':
                after_ctrl_extra = 1

        elif fs == 'repeat':
            ed = push_body(depth)
            line_depth = ed
            depth = ed + 1
            after_ctrl_extra = 0

        elif fs == 'case':
            in_case = True
            line_depth = depth
            if 'of' in sv:
                ed = push_body(depth, is_case=True)
                depth = ed + 1
                in_case = False
            after_ctrl_extra = 0

        elif fs in ('var', 'const', 'type', 'label'):
            in_decl = True
            line_depth = depth
            after_ctrl_extra = 0

        elif fs in ('procedure', 'function', 'program', 'unit',
                    'interface', 'implementation'):
            in_decl = False
            line_depth = depth
            after_ctrl_extra = 0

        elif in_decl and fs not in KEYWORDS:
            line_depth = depth + 1

        else:
            # Regular statements and single-statement bodies.
            # after_ctrl_extra accumulates for nested chains (e.g. for J do\nfor I do\nstmt).
            line_depth = depth + after_ctrl_extra

        # ── Override indentation for continuation lines (unclosed parens) ──
        if is_continuation and fs not in ('begin', 'end', 'until', 'repeat', 'case'):
            line_depth = depth + 1

        # ── Update after_ctrl_extra from this line's last keyword ──────────
        if fs not in ('begin', 'end', 'until', 'repeat', 'else', 'case'):
            ls = last_sig(line)
            if ls in ('then', 'do'):
                after_ctrl_extra += 1
            elif ls == ':' and begin_stack:
                after_ctrl_extra += 1
            else:
                after_ctrl_extra = 0

        # ── Update paren_depth ────────────────────────────────────────────
        for k, v in line:
            if k == 'P':
                if v == '(':
                    paren_depth += 1
                elif v == ')':
                    paren_depth = max(0, paren_depth - 1)

        # ── Emit ─────────────────────────────────────────────────────────
        content = format_line(line, is_end_line=(fs == 'end'))
        result.append('  ' * max(0, line_depth) + content)

    return result


# ── Blank-line cleanup pass ───────────────────────────────────────────────────

def cleanup_blanks(lines: list[str]) -> list[str]:
    """
    Remove blank lines immediately after 'begin' or a goto label.
    Remove blank lines immediately before 'end'/'until'.
    Remove blank lines immediately before 'program'.
    Ensure a blank line between a top-level 'end;'/'end.' and the next procedure/function.
    """
    def _is_begin(ln: str) -> bool:
        return bool(re.search(r'\bbegin\s*(?:\{[^}]*\})?\s*$', ln))

    def _is_end_or_until(ln: str) -> bool:
        return bool(re.match(r'\s*(end|until)\b', ln))

    def _is_goto_label(ln: str) -> bool:
        return bool(re.match(r'\d+:\s*$', ln))

    def _is_program(ln: str) -> bool:
        return bool(re.match(r'\s*program\b', ln))

    def _is_toplevel_end(ln: str) -> bool:
        """end; or end. at depth 0 (no leading spaces) — closes a procedure body."""
        return bool(re.match(r'end[;.]', ln))

    def _is_proc_func(ln: str) -> bool:
        return bool(re.match(r'\s*(procedure|function)\b', ln))

    out: list[str] = []

    for i, line in enumerate(lines):
        # Look ahead: first non-blank line after current position
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        next_content = lines[j] if j < len(lines) else ''

        if line.strip() == '':
            prev = out[-1] if out else ''
            keep = True
            if prev and _is_begin(prev):
                keep = False          # blank immediately after begin
            elif prev and _is_goto_label(prev):
                keep = False          # blank immediately after goto label
            elif next_content and _is_end_or_until(next_content):
                keep = False          # blank immediately before end/until
            elif next_content and _is_program(next_content):
                keep = False          # blank before program declaration
            if keep:
                out.append(line)
        else:
            # Insert blank before procedure/function when it immediately follows end;
            if _is_proc_func(line) and out and out[-1].strip() \
                    and _is_toplevel_end(out[-1]):
                out.append('')
            out.append(line)

    return out


# ── Main reformat ─────────────────────────────────────────────────────────────

def reformat(src: str) -> str:
    all_toks = tokenize(src)

    # Split into lines on NL tokens
    raw_lines: list[list] = []
    cur: list = []
    for k, v in all_toks:
        if k == 'NL':
            raw_lines.append(cur)
            cur = []
        else:
            cur.append((k, v))
    if cur:
        raw_lines.append(cur)

    # Apply casing to each line
    cased = [[(k, case(v) if k == 'ID' else v) for k, v in line]
             for line in raw_lines]

    # Split lines at structural boundaries
    split = split_lines(cased)

    # Apply indentation
    indented = indent_lines(split)

    # Collapse runs of more than 1 blank line to 1
    out: list[str] = []
    blank = 0
    for ln in indented:
        if ln.strip() == '':
            blank += 1
            if blank <= 1:
                out.append('')
        else:
            blank = 0
            out.append(ln)

    # Apply blank-line rules
    out = cleanup_blanks(out)

    return '\n'.join(out) + '\n'


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    inp = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else inp

    src = inp.read_text(encoding='utf-8')

    if out == inp:
        shutil.copy(inp, inp.with_suffix('.bak'))

    result = reformat(src)
    out.write_text(result, encoding='utf-8')
    print(f'Done: {out}')


if __name__ == '__main__':
    main()
