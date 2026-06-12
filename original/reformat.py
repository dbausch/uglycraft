#!/usr/bin/env python3
"""Reformat UGLI 2 Pascal sources to house style.

Usage: python reformat.py input.pas [output.pas]
Overwrites input.pas in-place (saves .bak) if output not given.
"""
import re, sys, shutil
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
    'vx': 'VX', 'vy': 'VY', 'sx': 'SX', 'sy': 'SY', 'dx': 'DX', 'dy': 'DY',
    'xx': 'XX', 'yy': 'YY', 'ti': 'TI', 'op': 'OP', 'iz': 'IZ',
    'danisoft': 'DANISOFT',
    'locx': 'LocX', 'locy': 'LocY',  # x/y suffix form
    'ugli_2': 'UGLI_2',               # program name
    'ugli2': 'UGLI2',                 # enemy AI procedure
}

UNIT_NAMES = {
    'cthreads': 'CThreads', 'crt': 'Crt', 'dos': 'Dos', 'uossound': 'UOSSound',
}


def case(val: str) -> str:
    low = val.lower()
    for tbl in (ALLCAPS, UNIT_NAMES, BUILTINS, TYPES):
        if low in tbl:
            return tbl[low]
    if low in KEYWORDS:
        return low
    return val[0].upper() + val[1:] if val else val


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


def format_line(line) -> str:
    """Apply casing and normalize spacing within one line."""
    out = []
    prev_kind, prev_val = None, None

    for k, v in line:
        if k == 'WS':
            continue
        if k == 'ID':
            v = case(v)

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

    begin_stack entries: (emit_depth, outer_depth)
      emit_depth  = depth at which 'begin'/'repeat'/'case' was emitted
                    (also used as the depth for the matching 'end'/'until')
      outer_depth = depth to restore after the closing 'end'/'until'
                    For ctrl-blocks (after then/do/else): outer_depth < emit_depth
                    For body-blocks (procedure/repeat/case):  outer_depth == emit_depth
    """
    depth = 0
    # Each entry: (emit_depth, outer_depth, is_case)
    # is_case=True marks a case...of block so numeric 'N:' lines are case arms.
    begin_stack: list[tuple[int, int, bool]] = []
    result = []
    in_decl = False     # inside var/const/type section
    after_ctrl = False  # last sig was then/do/else: next 'begin' indents one extra
    in_case = False     # saw 'case', waiting for 'of'

    def push_ctrl(d: int):
        """Push for a ctrl-block (then/do/else begin). emit_depth = d+1."""
        emit = d + 1
        begin_stack.append((emit, d, False))
        return emit

    def push_body(d: int, is_case: bool = False):
        """Push for a body-block (procedure begin / repeat / case-of). emit_depth = d."""
        begin_stack.append((d, d, is_case))
        return d

    def pop_block():
        """Pop and return (emit_depth, outer_depth). Falls back gracefully."""
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

        # ── Goto labels at column 0 ───────────────────────────────────────
        if is_goto_label(line, innermost_is_case()):
            result.append(format_line(line))
            after_ctrl = False
            continue

        # ── Compute this line's indentation ──────────────────────────────
        line_depth = depth

        if fs == 'begin':
            if after_ctrl:
                ed = push_ctrl(depth)
            else:
                ed = push_body(depth)
            line_depth = ed
            depth = ed + 1
            in_decl = False
            after_ctrl = False

        elif fs in ('end', 'until'):
            ed, od = pop_block()
            line_depth = ed    # 'end' emitted at same depth as 'begin'
            depth = od         # outer depth restored for what follows
            in_decl = False
            after_ctrl = False

        elif fs == 'else':
            # depth was already restored to outer_depth by the 'end' pop above,
            # so 'else' naturally lands at the 'if' level.
            line_depth = depth
            ls = last_sig(line)
            # If the else body is already on this line (ends with ';' or a value),
            # don't set after_ctrl — the branch is complete.
            if ls == ';':
                after_ctrl = False  # else stmt; — body complete inline
            else:
                after_ctrl = True   # else alone, else-if chain, or else without ';'

        elif fs == 'repeat':
            ed = push_body(depth)
            line_depth = ed    # repeat emitted at current depth
            depth = ed + 1     # body is one deeper
            after_ctrl = False

        elif fs == 'case':
            in_case = True
            line_depth = depth
            if 'of' in sv:
                ed = push_body(depth, is_case=True)
                depth = ed + 1
                in_case = False

        elif fs in ('var', 'const', 'type', 'label'):
            in_decl = True
            line_depth = depth
            after_ctrl = False

        elif fs in ('procedure', 'function', 'program', 'unit',
                    'interface', 'implementation'):
            in_decl = False
            line_depth = depth
            after_ctrl = False

        elif in_decl and fs not in KEYWORDS:
            line_depth = depth + 1

        elif after_ctrl:
            # Single-statement body (no 'begin'): one extra level, depth unchanged
            line_depth = depth + 1
            after_ctrl = False

        else:
            line_depth = depth

        # ── Update after_ctrl from this line's last keyword ──────────────
        if fs not in ('begin', 'end', 'until', 'repeat', 'else', 'case'):
            ls = last_sig(line)
            if ls in ('then', 'do'):
                after_ctrl = True
            elif ls == ':' and begin_stack:
                # Case arm colon: the body that follows gets +1 indent
                after_ctrl = True

        # ── Emit ─────────────────────────────────────────────────────────
        content = format_line(line)
        result.append('  ' * max(0, line_depth) + content)

    return result


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

    # Collapse runs of more than 2 blank lines to 1
    out = []
    blank = 0
    for ln in indented:
        if ln.strip() == '':
            blank += 1
            if blank <= 1:
                out.append('')
        else:
            blank = 0
            out.append(ln)

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
