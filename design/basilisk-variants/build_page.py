#!/usr/bin/env python3
"""Writes index.html: the local review page for the BASILISK Claude Code variants (not published)."""
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
E = html.escape

UX = [
    ('Prompt input (multi-line, history)', 'Notepad\'s Find box (today) / the Run dialog\'s combo / Explorer\'s Address bar',
     'Where you type. The Run combo adds a real drop-down for history and slash completions.'),
    ('Slash commands with autocomplete', 'The Run dialog\'s auto-complete drop-down', 'Typing "/" lists /compact /context /cost /model with one-line help.'),
    ('@-file mentions', 'Explorer\'s folder tree (and the Open dialog list)', 'Click or type @ to pull a file from C:\\b3\\work into the prompt.'),
    ('Tool-call blocks with folded output', 'Notepad / WordPad transcript', '"\u2022 Run(...)" then "\u2514 first lines \u2026 +N lines", as Claude Code prints them.'),
    ('Edit diffs (+/- lines)', 'WordPad\'s RichEdit (real red/green highlight)', 'The single most useful upgrade over plain Notepad: you can read what changed.'),
    ('Permission prompts', 'MessageBox (Yes / No / Cancel)', 'Allow once, deny, always allow this command. A real modal, so it cannot be missed.'),
    ('To-do list (TodoWrite)', 'Windows Components wizard check list', 'Checked = done, highlighted = in progress, empty = pending.'),
    ('Spinner: verb, elapsed, tokens, "esc to interrupt"', 'The shell\'s copy animation (flying papers) + its progress bar', 'Shows a tool is working and how long; Cancel = Esc.'),
    ('Status line: model, context %, cost, cwd', 'WordPad / Explorer status bar', 'Always-visible facts in a strip you already know how to read.'),
    ('Context usage (/context)', 'Disk Defragmenter\'s map; the drive Properties pie', 'Unmovable = system prompt + tools, contiguous = cached history, fragmented = new this turn, free = room left.'),
    ('Compaction (/compact)', 'Defragmenter\'s Defragment button + "after" map', 'The metaphor is exact: compaction squeezes the history to free space.'),
    ('Usage and cost', 'Task Manager Performance tab (meters, history graphs, totals)', 'Context %, output rate, tokens in/cached/out, session/day/month spend.'),
    ('Running tools / background tasks', 'Task Manager Processes list', 'One row per running tool with time and output size; End Process = stop it.'),
    ('Effort / model picker', 'Mouse Properties trackbar; Volume Control sliders; a property-sheet combo', 'Low \u2194 max effort; Haiku / Sonnet.'),
    ('Plan mode, auto-accept edits', 'Check boxes (Mouse Properties / Volume Control "Mute")', 'The two modes people toggle most, one click each.'),
    ('Queued messages while busy', 'The prompt stays live; queued lines show greyed in the transcript', 'Type the next thing while Claude works.'),
    ('Session history / resume', 'Explorer Back / Forward; a "Sessions" tab', 'Go back to an earlier conversation.'),
    ('Memory (CLAUDE.md)', 'A file in the Explorer tree; a "Memory" settings tab', 'Open and edit what Claude is told every session.'),
    ('Done notification', 'A tray balloon tip', 'Tells you a long turn finished while you looked elsewhere.'),
    ('Clock / time', 'Date and Time\'s analog clock and calendar', 'Kept from today\'s build: honest, readable, and the soul of the piece.'),
]

DONORS = [
    ('wordpad', 'WordPad', 'RichEdit transcript with real colour; status bar', 'Diffs, bold tool names'),
    ('perm', 'MessageBox (from a script)', 'A real Yes/No/Cancel prompt with our text', 'Permission prompts'),
    ('taskmgr_perf', 'Task Manager \u00b7 Performance', 'Usage meters, history graphs, totals; tab strip', 'Usage tab'),
    ('taskmgr_proc', 'Task Manager \u00b7 Processes', 'A sortable list with End Process', 'Running tools'),
    ('defrag2', 'Disk Defragmenter', 'Cluster map, legend, Analyze / Defragment', 'Context window, /compact'),
    ('driveprops', 'Local Disk Properties', 'Used / free pie', 'Context gauge'),
    ('display', 'Display Properties', 'Luna tab strip and tab-page body', 'Tabs: Chat | Plan | Files | Usage | Settings'),
    ('explorer', 'Explorer', 'Folder tree, Address bar + Go, toolbar, status bar', '@-mentions, prompt, history'),
    ('components', 'Windows Components wizard', 'Check-box list with sizes and a description', 'To-do list'),
    ('cleanup', 'Disk Cleanup', 'Green-tick check list with sizes', 'Always-allowed commands'),
    ('mouse', 'Mouse Properties', 'Trackbar, themed check boxes, property page', 'Effort slider, mode toggles, Settings'),
    ('volume', 'Volume Control', 'Vertical sliders with Mute check boxes', 'Effort / output / thinking mixer'),
    ('copy1', 'Copying\u2026 (shell)', 'Flying-papers animation, progress bar, Cancel', 'The busy spinner'),
    ('run', 'Run', 'Auto-complete combo with history', 'Prompt with slash completion'),
]
NOT_ON_SITE = ('Not on the Windows Secrets page but captured or used here: Disk Defragmenter, Task Manager, Disk Cleanup, '
               'the Windows Components wizard, the shell copy dialog, Volume Control, Mouse Properties, the Run dialog and '
               'WordPad. Worth capturing next: the tray balloon tip, HyperTerminal (a true VT100 transcript), '
               'Outlook Express\'s three panes (sessions), WinHelp/HTML Help (/help), the File Download security warning, '
               'and System Restore\'s calendar (checkpoints / undo).')

# name, title, pitch, parts [(part, from, does, space)], feasibility, verdict, scores (use, effort, risk) 1..5
V = [
    ('v01', 'Notepad, refined', 'Today\'s BASILISK III, plus the three things it most lacks: a status line, a context gauge and the to-do list.',
     [('Transcript', 'Notepad\'s edit', 'scrollback, tool blocks', '78%'),
      ('Prompt + Send/Stop', 'Notepad\'s own Find dialog', 'input, Esc', '5%'),
      ('Status line', 'a status bar (Notepad has one, off by default)', 'model \u00b7 effort \u00b7 context % \u00b7 cost \u00b7 cwd', '3%'),
      ('Clock', 'Date and Time page', 'time (kept)', '\u2014'),
      ('Context gauge', 'drive Properties pie', 'used / free tokens', '\u2014'),
      ('To do', 'Windows Components check list', 'Claude\'s plan, live', 'sidebar 22%')],
     'Small step from what runs today. Notepad\'s own status bar only shows with word wrap off and holds only "Ln, Col", so the status line is a borrowed status bar (WordPad\'s) or our own msctls_statusbar32 in Notepad. The pie is drawn by the shell from disk numbers we cannot feed: in practice we would draw a matching pie ourselves in a borrowed static. Components\' list is a plain check-box list view we can fill (LVM_INSERTITEM across processes needs memory allocated in that process, as we already do for the desktop).',
     'The safe next version: same calm screen, three useful additions.', (4, 2, 1)),
    ('v02', 'Property-sheet tabs', 'Display Properties\' tab strip turns the client into Chat | Tasks | Files | Usage | Settings.',
     [('Tabs', 'Display Properties (Luna tab control)', 'switch modality', '3%'),
      ('Chat page', 'tab-page body + Notepad edit + Find bar', 'the conversation', '85%'),
      ('Buttons', 'the sheet\'s OK/Cancel/Help row, relabelled', 'Clear \u00b7 Model\u2026 \u00b7 Help', '4%')],
     'A property sheet is the most natural container on XP: each page is a dialog, so other donors (Task Manager\'s graphs, a check list) can be hosted per tab. Lesson from today: a themed page moved while visible leaves stale copies of its controls, so lay pages out hidden and show once. Relabelling tabs is TCM_SETITEM with a pointer, so it needs process memory like the list views.',
     'The cleanest way to add modes without clutter. Good host for the others.', (5, 3, 2)),
    ('v03', 'Task Manager: the Usage tab', 'Task Manager\'s tabs as Chat | Tools | Usage | Model | Sessions; the Usage tab shown.',
     [('Context meter + history', 'Task Manager CPU meter and graph', 'context % now and over the session', '35%'),
      ('Output rate meter + graph', 'Task Manager PF meter and graph', 'tokens/s while streaming', '35%'),
      ('Totals boxes', 'Totals / Physical / Commit / Kernel groups', 'tokens, context window, spend, tools', '20%'),
      ('Status bar', 'Task Manager status bar', 'tools running, context, spend vs cap', '3%')],
     'Task Manager owner-draws its meters and graphs from its own counters, so we cannot feed its graphs: we would host Task Manager\'s frame and tab strip and draw identical meters ourselves (or, honestly, show XP\'s real CPU graph while tools run). The Processes tab, however, is a real list view we can fill with running tools, and End Process works as Stop.',
     'Best "Usage" page: dense, readable, and every number is something people ask Claude Code for.', (4, 3, 2)),
    ('v04', 'Defrag context map', 'Disk Defragmenter\'s analysis panel under the transcript, mapping the context window.',
     [('Transcript', 'Notepad', 'conversation', '60%'),
      ('Context map', 'Defragmenter map + legend', 'system prompt+tools / cached / new / free', '30%'),
      ('Buttons', 'Analyze, Defragment, Pause, Stop, View Report', '/context, /compact, pause, stop, /cost', '\u2014')],
     'The map is drawn by the defrag ActiveX inside MMC from real disk data; we can take the panel\'s frame, buttons and legend (buttons and statics are real children), but the map itself we would draw, in its sliver style. The metaphor is exact and needs no explanation: Defragment really is /compact.',
     'The most "secret Windows" idea that is also genuinely informative. Could be smaller.', (4, 3, 3)),
    ('v05', 'Explorer workspace', 'Explorer\'s folder tree is the project; its Address bar is the prompt; Back/Forward are sessions.',
     [('Prompt', 'Explorer Address bar + Go', 'type, @-mention, Send', '3%'),
      ('Files', 'Explorer folder tree', 'click to @-mention; open CLAUDE.md', '22%'),
      ('Transcript', 'Notepad edit in the list pane\'s place', 'conversation', '70%'),
      ('Status bar', 'Explorer status bar', 'objects \u00b7 model \u00b7 context \u00b7 cost', '3%')],
     'Explorer is one process with many threads; reparenting its panes is fragile (it rebuilds them on navigation). Safer: host our own SysTreeView32 styled identically and Explorer\'s address combo (ComboBoxEx32) which is a plain control. The Address bar\'s auto-complete is a free gift for history.',
     'Most "IDE-like" and the most useful for real coding; moderate risk.', (5, 4, 3)),
    ('v06', 'Permissions and plan', 'The approval-centric layout: plan, always-allowed list, modes, and a real MessageBox asking.',
     [('Transcript', 'Notepad', 'conversation', '70%'),
      ('Plan (to do)', 'Windows Components list', 'live plan', '\u2014'),
      ('Always allowed', 'Disk Cleanup green-tick list', 'which commands run without asking', '\u2014'),
      ('Modes', 'themed check boxes', 'plan mode, auto-accept edits', '\u2014'),
      ('Permission prompt', 'MessageBox', 'Yes = once, No = deny, Cancel = always', 'modal')],
     'MessageBox is the easiest real part of all: the client calls it. Yes/No/Cancel mapping is clumsy: a TaskDialog-like custom dialog built from a real #32770 with three relabelled buttons reads better. The check lists are list views we can fill.',
     'The most trustworthy-feeling version; shows Claude Code\'s safety model.', (4, 2, 1)),
    ('v07', 'WordPad transcript', 'WordPad\'s RichEdit as the transcript: real colour, bold tool names and red/green diffs; the Run box as the prompt.',
     [('Transcript', 'WordPad RichEdit', 'colour diffs, bold names', '75%'),
      ('Prompt', 'Run dialog combo + its drop-down', 'history, slash completions', '6%'),
      ('Status bar', 'WordPad status bar', 'model \u00b7 context \u00b7 cost', '3%')],
     'Very buildable: the client streams RTF into WordPad with EM_STREAMIN/EM_SETCHARFORMAT (cross-process needs a buffer in WordPad\'s memory, or simply write an .rtf and EM_REPLACESEL plain text then format ranges). The Run combo is a plain ComboBox; its drop-down list we fill.',
     'Biggest readability win per effort. Diffs alone justify it.', (5, 2, 2)),
    ('v08', 'Mixer controls', 'Volume Control\'s faders as the controls Claude Code really has: effort, output length, thinking; Mute boxes become modes.',
     [('Transcript', 'Notepad', 'conversation', '66%'),
      ('Faders', 'Volume Control columns', 'effort, output length, thinking depth', 'sidebar 34%'),
      ('Mode boxes', 'the columns\' Mute check boxes', 'plan, auto-accept, show thinking', '\u2014'),
      ('Clock', 'Date and Time', 'time', '\u2014')],
     'The faders are msctls_trackbar32 controls (sndvol32 is one process): we can reparent a column and read TBM_GETPOS. Fewer than three faders would be more honest: effort is the one that matters.',
     'Charming and tactile, but the controls are rarely touched: keep one fader.', (3, 2, 2)),
    ('v09', 'Busy strip', 'The shell\'s flying-papers copy animation docks above the prompt while a tool runs, with live output.',
     [('Transcript', 'Notepad', 'conversation', '68%'),
      ('Animation + progress', 'shell Copying\u2026 dialog (SysAnimate32 + progress bar)', 'something is running, for how long; Cancel = Esc', '17%'),
      ('Tool output', 'an edit', 'last lines of output, live', '\u2014')],
     'The animation is a SysAnimate32 control playing a resource from shell32.dll: we can create our own Animate control with ACM_OPEN on shell32\'s copy AVI, no reparenting needed. The strip appears only while a tool runs.',
     'Delightful and useful; best as a feature of v01/v02 rather than a layout.', (4, 1, 1)),
    ('v10', 'Windows for Workgroups 3.11', 'The 3.11 build, tidied: Terminal transcript, a normal-sized Clock, Calculator\'s display as the bill, a Cardfile to-do card, and 3.11\'s own Find dialog as the prompt.',
     [('Transcript', 'Terminal (real capture of today\'s build)', 'VT-100 scrollback', '64%'),
      ('Clock', 'Clock', 'time', '\u2014'),
      ('Bill', 'Calculator\'s display', 'session cost', '\u2014'),
      ('To do', 'Cardfile card', 'the plan, on a card', '\u2014'),
      ('Prompt', 'Find dialog (Find Next = Send, Cancel = Stop, Direction = history)', 'input', '\u2014')],
     'Same mechanics the 3.11 lane already uses (SetParent works in Win16; one shared message queue makes it easier than XP). Cardfile\'s card is a real edit; Find is COMMDLG\'s and posts back to its owner, so we own it. The card text here is drawn in Tahoma Bold as a stand-in for the System font.',
     'Fix the oversized clock and give the plan a card: clear improvement for 3.11.', (4, 2, 2)),
    ('v11', 'Settings page (/config)', 'Mouse Properties\' page rebuilt as BASILISK Settings: effort slider, mode check boxes, model combo.',
     [('Dialog + tabs', 'Mouse Properties sheet', 'Effort | Model | Permissions | Memory | Display', 'modal'),
      ('Effort', 'pointer-speed trackbar', 'low \u2194 max', '\u2014'),
      ('Modes', 'themed check boxes', 'plan, auto-accept, thinking, notify', '\u2014'),
      ('Model', 'a Luna combo box', 'Haiku / Sonnet', '\u2014')],
     'Opening main.cpl and reparenting its controls is exactly what we do with Date and Time today. Simplest honest version: create a real property sheet from the client (PropertySheet API) and borrow only the trackbar\'s look.',
     'Needed by any tabbed version; a /config that looks like home.', (3, 2, 1)),
    ('v12', 'The suite', 'Tabs (Display Properties) + WordPad-quality diffs + the plan + a slim context map + status line.',
     [('Tabs', 'Display Properties', 'Chat | Plan | Files | Usage | Settings', '3%'),
      ('Transcript', 'WordPad RichEdit', 'colour diffs', '62%'),
      ('Plan', 'Components check list', 'live to-do', '\u2014'),
      ('Clock', 'Date and Time', 'time', '\u2014'),
      ('Context strip', 'Defragmenter map', 'context at a glance', '9%'),
      ('Prompt + status', 'Find bar, status bar', 'input, facts', '8%')],
     'Combines v02 + v07 + v06\'s plan + v04\'s map. Every part is one we have already reparented in kind (pages, lists, edits). The Usage and Settings tabs would host v03 and v11.',
     'The recommended destination; build it in steps (v07, then v02 tabs, then the map).', (5, 4, 3)),
]

TOP3 = [('v12', 'The suite', 'tabs + WordPad diffs + plan + context strip: the most useful whole, built from parts we already know how to move.'),
        ('v07', 'WordPad transcript', 'the cheapest big readability win; do it first.'),
        ('v04', 'Defrag context map', 'the idea people will remember; Defragment = /compact needs no explanation.')]

CSS = '''
:root { --bg:#f3f1ea; --ink:#1d1f22; --muted:#61656c; --line:#d9d4c6; --card:#fffdf8; --accent:#245edb; }
@media (prefers-color-scheme: dark) { :root { --bg:#16181b; --ink:#e9e6de; --muted:#9aa0a8; --line:#33373d; --card:#1e2125; --accent:#7aa5ff; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.55 Tahoma, "Segoe UI", system-ui, sans-serif; }
.wrap { max-width:1180px; margin:0 auto; padding:0 18px 60px; }
header { padding:34px 0 10px; }
h1 { font:700 26px/1.2 "Lucida Console", ui-monospace, monospace; margin:0 0 6px; }
h2 { font:700 18px/1.3 "Lucida Console", ui-monospace, monospace; margin:44px 0 10px; }
h3 { margin:0 0 4px; font-size:18px; }
p { margin:6px 0; max-width:900px; }
.note { color:var(--muted); font-size:13.5px; }
table { border-collapse:collapse; width:100%; margin:8px 0 4px; font-size:13.5px; background:var(--card); }
th, td { text-align:left; vertical-align:top; padding:6px 8px; border-bottom:1px solid var(--line); overflow-wrap:anywhere; }
p, li, .donor { overflow-wrap:anywhere; }
th { font-weight:700; color:var(--muted); font-size:12.5px; text-transform:uppercase; letter-spacing:.04em; }
.variant { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:16px; margin:26px 0; }
.variant img { width:100%; height:auto; display:block; border:1px solid var(--line); image-rendering:auto; cursor:zoom-in; }
.vhead { display:flex; gap:12px; align-items:baseline; flex-wrap:wrap; margin-bottom:8px; }
.vid { font:700 13px "Lucida Console", monospace; color:var(--accent); }
.verdict { margin-top:8px; padding:8px 10px; border-left:3px solid var(--accent); background:rgba(36,94,219,.06); }
.feas { color:var(--muted); font-size:13.5px; }
.donors { display:grid; grid-template-columns:repeat(auto-fill, minmax(260px,1fr)); gap:14px; }
.donor { background:var(--card); border:1px solid var(--line); border-radius:6px; padding:10px; font-size:13px; }
.donor img { max-width:100%; height:auto; display:block; margin-bottom:6px; }
.dots { letter-spacing:2px; color:var(--accent); }
.top3 li { margin:6px 0; }
#zoom { position:fixed; inset:0; background:rgba(0,0,0,.85); display:none; align-items:center; justify-content:center; z-index:9; cursor:zoom-out; }
#zoom img { max-width:98vw; max-height:96vh; image-rendering:pixelated; }
@media (max-width:640px) { th:nth-child(4), td:nth-child(4) { display:none; } }
'''


def dots(n):
    return '<span class="dots">' + '\u25cf' * n + '<span style="opacity:.25">' + '\u25cf' * (5 - n) + '</span></span>'


def main():
    o = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
         '<title>BASILISK variants</title><style>%s</style></head><body><div class="wrap">' % CSS]
    o.append('<header><h1>BASILISK, twelve ways</h1><p>Mockups of a fuller Claude Code client assembled from Windows parts. '
             'Every window, tab, list, button, meter and dialog in these images was cut from a screendump of a real Windows XP '
             'machine (or an existing 3.11 capture); the text a real build would put in them is drawn in the real XP fonts. '
             'Click any mockup to see it at full size. Local review page; not published.</p>'
             '<p class="note">Captured on the studio VM, 2026-11-12. The compositor is <code>compose.py</code>; captures are in <code>captures/</code>.</p></header>')
    o.append('<h2>Top three</h2><ol class="top3">')
    for vid, name, why in TOP3:
        o.append('<li><a href="#%s"><b>%s</b></a> \u2014 %s</li>' % (vid, E(name), E(why)))
    o.append('</ol>')
    o.append('<h2>1. Claude Code\'s UX, and which Windows part could carry each piece</h2><table><tr><th>Claude Code element</th><th>Windows part</th><th>Why it earns its space</th></tr>')
    for a, b, c in UX:
        o.append('<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (E(a), E(b), E(c)))
    o.append('</table>')
    o.append('<h2>2. Donors captured for this review</h2><div class="donors">')
    for f, name, parts, use in DONORS:
        o.append('<div class="donor"><img src="donors/%s.png" alt="%s" loading="lazy"><b>%s</b><br>%s<br><span class="note">Use: %s</span></div>'
                 % (f, E(name), E(name), E(parts), E(use)))
    o.append('</div><p class="note">%s</p>' % E(NOT_ON_SITE))
    o.append('<h2>3. The variants</h2>')
    for i, (vid, name, pitch, parts, feas, verdict, sc) in enumerate(V, 1):
        o.append('<section class="variant" id="%s"><div class="vhead"><span class="vid">%02d \u00b7 %s</span><h3>%s</h3></div>' % (vid, i, vid, E(name)))
        o.append('<p>%s</p><a href="img/%s.png" class="z"><img src="img/%s.png" alt="Mockup: %s" loading="lazy" width="1024" height="768"></a>' % (E(pitch), vid, vid, E(name)))
        o.append('<table><tr><th>Part</th><th>Taken from</th><th>Does</th><th>Space</th></tr>')
        for p, f, d, s in parts:
            o.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (E(p), E(f), E(d), E(s)))
        o.append('</table><p class="feas"><b>Feasibility.</b> %s</p><div class="verdict"><b>Verdict.</b> %s</div></section>' % (E(feas), E(verdict)))
    o.append('<h2>4. Side by side</h2><table><tr><th>Variant</th><th>Usefulness</th><th>Build effort</th><th>Risk</th></tr>')
    for i, (vid, name, *_rest) in enumerate(V, 1):
        u, e, r = _rest[-1]
        o.append('<tr><td><a href="#%s">%02d %s</a></td><td>%s</td><td>%s</td><td>%s</td></tr>' % (vid, i, E(name), dots(u), dots(e), dots(r)))
    o.append('</table><p class="note">Dots: more = more useful / more work / more risk. Risk is mostly cross-process fragility '
             '(themed pages leaving stale copies when moved visibly, XOR-drawn clock hands ghosting on forced repaints, statics '
             'moved off their dialogs painting the wrong background, controls that need memory in their own process to be filled).</p>')
    o.append('</div><div id="zoom"></div><script>'
             'var z=document.getElementById("zoom"),zi=null;'
             'document.querySelectorAll("a.z").forEach(function(a){a.addEventListener("click",function(e){e.preventDefault();if(!zi){zi=document.createElement("img");zi.alt="";z.appendChild(zi);}zi.src=a.getAttribute("href");z.style.display="flex";});});'
             'z.addEventListener("click",function(){z.style.display="none";});'
             'document.addEventListener("keydown",function(e){if(e.key==="Escape")z.style.display="none";});'
             '</script></body></html>')
    with open(os.path.join(HERE, 'index.html'), 'w') as f:
        f.write('\n'.join(o))


main()
