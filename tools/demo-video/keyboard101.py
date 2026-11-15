"""An early-90s 101-key keyboard layout (the ANSI "enhanced" layout), in key units: shared by kbd_texture.py (the
keycap legends, drawn with Pillow) and scene1993.py (the caps, built in Blender).

keys() -> [(x, y, w, h, legend, dark)]: x, y of the top-left corner in units (y grows towards the front), sizes in
units, the legend ("\\n" for two-line legends), and whether the cap is a darker modifier.
"""

WIDTH, DEPTH = 22.5, 6.5


def keys():
    K = []
    def row(y, x, items, dark=False):
        for it in items:
            if isinstance(it, tuple):
                leg, w = it[0], it[1]
                d = it[2] if len(it) > 2 else dark
            else:
                leg, w, d = it, 1.0, dark
            if leg is not None: K.append((x, y, w, 1.0, leg, d))   # None: a gap
            x += w
        return x
    # function row
    K.append((0, 0, 1, 1, 'Esc', True))
    row(0, 2, ['F1', 'F2', 'F3', 'F4'])
    row(0, 6.5, ['F5', 'F6', 'F7', 'F8'])
    row(0, 11, ['F9', 'F10', 'F11', 'F12'])
    row(0, 15.25, ['Print\nScreen', 'Scroll\nLock', 'Pause'], dark=True)
    # number row
    x = row(1.5, 0, ['~\n`', '!\n1', '@\n2', '#\n3', '$\n4', '%\n5', '^\n6', '&\n7', '*\n8', '(\n9', ')\n0', '_\n-', '+\n='])
    row(1.5, x, [('Backspace', 2.0, True)])
    row(1.5, 15.25, ['Insert', 'Home', 'Page\nUp'], dark=True)
    row(1.5, 18.5, ['Num\nLock', '/', '*', '-'], dark=True)
    # QWERTY rows
    x = row(2.5, 0, [('Tab', 1.5, True)] + list('QWERTYUIOP') + ['{\n[', '}\n]'])
    row(2.5, x, [('|\n\\', 1.5)])
    row(2.5, 15.25, ['Delete', 'End', 'Page\nDown'], dark=True)
    row(2.5, 18.5, ['7\nHome', '8\n↑', '9\nPgUp'])
    K.append((21.5, 2.5, 1, 2, '+', True))
    x = row(3.5, 0, [('Caps Lock', 1.75, True)] + list('ASDFGHJKL') + [':\n;', '"\n\''])
    row(3.5, x, [('Enter', 2.25, True)])
    row(3.5, 18.5, ['4\n←', '5', '6\n→'])
    x = row(4.5, 0, [('Shift', 2.25, True)] + list('ZXCVBNM') + ['<\n,', '>\n.', '?\n/'])
    row(4.5, x, [('Shift', 2.75, True)])
    K.append((16.25, 4.5, 1, 1, '↑', True))
    row(4.5, 18.5, ['1\nEnd', '2\n↓', '3\nPgDn'])
    K.append((21.5, 4.5, 1, 2, 'Enter', True))
    row(5.5, 0, [('Ctrl', 1.5, True), (None, 1.0), ('Alt', 1.5, True), ('', 7.0, False), ('Alt', 1.5, True),
                 (None, 1.0), ('Ctrl', 1.5, True)])
    row(5.5, 15.25, ['←', '↓', '→'], dark=True)
    row(5.5, 18.5, [('0\nIns', 2.0), '.\nDel'])
    return K
