#!/usr/bin/env python3
"""codehunt - look for secrets in Windows binaries that are not dialog geometry.

Given files or directories of PE (Win32/Win64) and NE (Win16) binaries, emit
one JSON object per candidate finding. No third-party modules; runs anywhere
with Python 3.8+.

    python3 -I codehunt.py [--mui DIR]... [--icons-dir DIR] PATH... > out.jsonl

On Vista and later most resources live in a language satellite
(en-US\\notepad.exe.mui) while the code stays in notepad.exe.  Pass the
satellite directories with --mui (or keep them beside the binary / in an
en-US subdirectory) and each binary is scanned together with its .mui:
resources come from both, code references from the binary.

Every record has "file", "class" and "detail"; most have "text".  Classes:

  pdb            CodeView debug record: build-machine PDB path, age, GUID
  version        VERSIONINFO oddities: Comments/PrivateBuild/SpecialBuild,
                 non-standard keys, FileFlags debug/prerelease/private bits
  string_kw      string-table entry matching a developer/debug/codename keyword
  string_unref   string-table entry whose ID never appears as an immediate
                 operand in the code (heuristic; only for small files or
                 entries that also match a weak keyword)
  accel_hidden   accelerator whose command ID is in no menu of the module
  res_unref      dialog / menu / accelerator table / RCDATA whose ID or name is
                 never referenced by the code (heuristic)
  res_unref_image  icon group / cursor group / bitmap with no immediate, name or
                 dialog (SS_ICON/SS_BITMAP ordinal) reference; the lowest icon
                 group (the program icon) is skipped.  With --icons-dir each one
                 is rendered to PNG.  Low precision: IDs computed as base+n and
                 icons used by index from other modules look orphaned too.
  surface        imports/resources that let something else drive the program:
                 listener (winsock bind/listen), named_pipe, mailslot, rpc_server,
                 dde_server, com_server, typelib, msaa_uia, hook, window_msg, cmdline
  api_arg        string literals passed to registry / INI / compare /
                 RegisterWindowMessage / DDE / pipe / RPC / OutputDebugString
                 calls (x86 PE32: pushes before call [IAT]; Win16: pushes before
                 relocated far calls, resolved in the automatic data segment)
  cmdline        switch-like strings ("/x", "-Embedding", "restart", ...) in a
                 program that reads its command line; "compared" = the string
                 is an argument of a string-compare call
  menu_odd       grayed item in the template, owner-draw item, item with an ID
                 but no text, popup whose children are all empty, or a menu in
                 a language other than the module's usual one
  menu_unloaded  MENU whose ID is never an immediate operand and never a
                 LoadMenu argument (class menus set via WNDCLASS fields can
                 still look unloaded)
  menu_runtime   a menu item whose ID is passed to DeleteMenu / RemoveMenu /
                 ModifyMenu / InsertMenu / EnableMenuItem (Win16 too): items
                 the program removes, renames or greys at runtime
  menu_nohandler item ID seen neither as an immediate nor in an MFC message
                 map entry (weak: table-driven command routing looks the same)
  code_str       string found outside the resource section, sub-classified in
                 "kind": regval, regkey, switch, srcpath, assert, debugfmt,
                 codename, devnote, email, envvar, ipc (pipe / RPC endpoints)
  debug_output   module imports OutputDebugString / DebugBreak etc.
  export_name    exported (PE) or entry-table (NE) name that looks like a
                 debug/test hook
  ne_desc        NE module description string (non-resident name #0)
  dos_stub       a DOS stub whose message is not the standard one
  manifest       side-by-side manifest with unusual content
  timestamp      link timestamp outside the plausible range for the release

The heuristics are deliberately loose: this produces candidates for a human,
not conclusions.  Immediate-operand matching knows push imm8/imm16/imm32,
mov reg,imm and cmp ax/eax,imm forms for x86, x64 and 16-bit code.
"""
import json
import os
import re
import struct
import sys

RT = {1: "CURSOR", 2: "BITMAP", 3: "ICON", 4: "MENU", 5: "DIALOG", 6: "STRING",
      7: "FONTDIR", 8: "FONT", 9: "ACCELERATOR", 10: "RCDATA", 11: "MESSAGETABLE",
      12: "GROUP_CURSOR", 14: "GROUP_ICON", 16: "VERSION", 23: "HTML", 24: "MANIFEST"}

CODENAMES = ["chicago", "cairo", "daytona", "whistler", "longhorn", "blackcomb",
             "vienna", "memphis", "nashville", "neptune", "odyssey", "janus",
             "sparta", "snowball", "razzle", "jaguar", "cougar", "o'hare", "ohare",
             "lonestar", "freestyle", "mantis", "harmony", "symphony", "springboard",
             "pegasus", "athena", "hydra", "aero", "glass", "milan", "palladium",
             "fiji", "wolverine", "redmond"]
# strong developer/debug words - flag wherever they occur
KW_STRONG = re.compile(
    r"(?i)(\btodo\b|\bfixme\b|\bxxx\b|\bhack\b|\bkludge\b|\bbogus\b|\bfoo\b|\bbar\b(?=\W)|"
    r"\bdebug|\bassert|\btest(ing)?\b|\btester\b|\bdummy\b|\bplaceholder\b|\binternal\b|"
    r"\bdo not (localize|translate|ship)|\bloc(alize)?\s*(note|comment)|\bunused\b|"
    r"\bnot (yet )?implemented\b|\bshould never\b|\bcan'?t happen\b|\bimpossible\b|"
    r"\bwhoops\b|\boops\b|\bdoh\b|\bbeta\b|\bprerelease\b|\bpre-release\b|\bbuild lab\b|"
    r"\bprivate build\b|\bspecial build\b|\bchecked build\b|\bfree build\b|\bmagic\b|"
    r"\beaster\b|\bsecret\b|\bhidden\b|\bundocumented\b|\bcheat\b|\bgod mode\b|\bcredits?\b|"
    r"\bdeveloped by\b|\bwritten by\b|\bprogrammed by\b|\bteam\b|\bthanks?\b|\bauthor\b|"
    r"\bversion \d+\.\d+\.\d+\.\d+|\\\\nt(builds|dev)?\\|[a-z]:\\nt\\|\\\\[a-z0-9_-]+\\(public|release|build))")
KW_CODENAME = re.compile(r"(?i)\b(" + "|".join(re.escape(c) for c in CODENAMES) + r")\b")
SRCPATH = re.compile(r"(?i)([a-z]:\\|\\\\|\\(nt|private|public|sdktools|shell|windows|base|ds|net|multimedia|admin|printscan|termsrv)\\)"
                     r"[^\x00\n\r]*\.(c|cpp|cxx|h|hpp|hxx|pdb|obj|lib|asm|inc|def|rc)\b"
                     r"|\b[\w\-]+\.(c|cpp|cxx|hxx|hpp)\b")
ASSERT = re.compile(r"(?i)assert|\bfailed\b.*\bline\b|\bline\s*%d|%s\(%d\)|%hs\(%d\)|__file__|"
                    r"\bfile\s*%s.*line|\bVERIFY\b|\bASSERTMSG\b|\bRIP\b|\bFATAL\b")
DEBUGFMT = re.compile(r"(?i)^(dbg|debug|trace|tr|warn|err(or)?|info|log)\s*[:\-\]>]|"
                      r"%[-+ #0]*\d*(l|h|hs|ls|I64)?[sdxXup].*%[-+ #0]*\d*(l|h|hs|ls|I64)?[sdxXup]"
                      r"|\b(entering|leaving|exiting|enter|leave)\b\s+\w+|"
                      r"\w+::\w+|\b\w+\(\)\s*:?\s*(failed|returned|error)|hr\s*=\s*%|"
                      r"\b0x%0?8?[xX]\b")
SWITCH = re.compile(r"^[/-][A-Za-z?][A-Za-z0-9_:?]{0,24}$")
REGVAL = re.compile(r"^(Enable|Disable|Debug|Test|Show|Hide|Allow|No|Use|Force|Skip|Always|Never|"
                    r"Max|Min|Verbose|Trace|Log|Dump|Break|Fake|Override|Experimental|Beta|"
                    r"Internal|Secret|Hidden|Dev|Feature|Turbo|Fast|Slow|Legacy|Old|New|Classic)"
                    r"[A-Z0-9_]\w{0,48}$")
REGKEY = re.compile(r"(?i)^(software|system|control panel|\\registry|hkey_|hklm|hkcu)[\\/]")
EMAIL = re.compile(r"[\w.\-]+@[\w\-]+\.(com|net|org|edu)", re.I)
ENVVAR = re.compile(r"^%[A-Za-z_]\w+%$|^_?[A-Z][A-Z0-9_]{3,}=$")
DEBUG_IMPORTS = {"OutputDebugStringA", "OutputDebugStringW", "DebugBreak",
                 "IsDebuggerPresent", "DbgPrint", "DbgPrintEx", "DbgBreakPoint",
                 "OUTPUTDEBUGSTRING", "DEBUGBREAK", "FATALEXIT", "FATALAPPEXIT"}

# ordinal-only imports we want to recognise (PE)
ORDINALS = {
    "ws2_32.dll": {1: "accept", 2: "bind", 3: "closesocket", 4: "connect", 13: "listen", 16: "recv",
                   19: "send", 23: "socket", 115: "WSAStartup", 116: "WSACleanup", 52: "gethostbyname"},
    "wsock32.dll": {1: "accept", 2: "bind", 3: "closesocket", 4: "connect", 13: "listen", 16: "recv",
                    19: "send", 23: "socket", 115: "WSAStartup", 116: "WSACleanup", 52: "gethostbyname"},
}
# Win16 ordinals (used when the exporting module is not among the scanned files)
NE_BUILTIN = {
    "KERNEL": {57: "GETPROFILEINT", 58: "GETPROFILESTRING", 127: "GETPRIVATEPROFILEINT",
               128: "GETPRIVATEPROFILESTRING", 115: "OUTPUTDEBUGSTRING"},
    "USER": {118: "REGISTERWINDOWMESSAGE", 121: "SETWINDOWSHOOK", 291: "SETWINDOWSHOOKEX",
             268: "GLOBALADDATOM", 145: "REGISTERCLIPBOARDFORMAT", 430: "LSTRCMP", 471: "LSTRCMPI"},
    "SHELL": {6: "REGQUERYVALUE"},
    "DDEML": {2: "DDEINITIALIZE", 21: "DDECREATESTRINGHANDLE", 27: "DDENAMESERVICE"},
}
NE_EXPORTS = {}   # filled from every NE module scanned: MODULE -> {ordinal: NAME}

# API -> group, for "which string literal is passed to this call" analysis
def _g(group, *names):
    return {n.upper(): group for n in names}
API_GROUPS = {}
for _n in ("RegQueryValueExA", "RegQueryValueExW", "RegGetValueA", "RegGetValueW", "SHGetValueA",
           "SHGetValueW", "SHRegGetUSValueA", "SHRegGetUSValueW", "SHRegGetBoolUSValueA",
           "SHRegGetBoolUSValueW", "SHRegGetValueA", "SHRegGetValueW", "SHQueryValueExA",
           "SHQueryValueExW", "RegQueryValueA", "RegQueryValueW", "REGQUERYVALUE", "SHRegGetDWORD",
           "SHRegGetIntW", "RegOpenKeyExA", "RegOpenKeyExW", "RegCreateKeyExW", "RegCreateKeyExA"):
    API_GROUPS[_n.upper()] = "registry"
API_GROUPS.update(_g("ini", "GetProfileIntA", "GetProfileIntW", "GetProfileStringA", "GetProfileStringW",
                     "GetPrivateProfileIntA", "GetPrivateProfileIntW", "GetPrivateProfileStringA",
                     "GetPrivateProfileStringW", "GETPROFILEINT", "GETPROFILESTRING",
                     "GETPRIVATEPROFILEINT", "GETPRIVATEPROFILESTRING"))
API_GROUPS.update(_g("compare", "lstrcmpiA", "lstrcmpiW", "lstrcmpA", "lstrcmpW", "_wcsicmp", "_stricmp",
                     "wcscmp", "strcmp", "_wcsnicmp", "_strnicmp", "StrCmpIW", "StrCmpIA", "StrCmpNIW",
                     "StrCmpW", "CompareStringW", "CompareStringA", "CompareStringOrdinal", "StrStrIW",
                     "LSTRCMP", "LSTRCMPI", "_mbsicmp", "_wcsicmp_l"))
API_GROUPS.update(_g("winmsg", "RegisterWindowMessageA", "RegisterWindowMessageW", "REGISTERWINDOWMESSAGE",
                     "RegisterClipboardFormatA", "RegisterClipboardFormatW", "REGISTERCLIPBOARDFORMAT"))
API_GROUPS.update(_g("dde", "DdeCreateStringHandleA", "DdeCreateStringHandleW", "DDECREATESTRINGHANDLE",
                     "GlobalAddAtomA", "GlobalAddAtomW", "GLOBALADDATOM"))
API_GROUPS.update(_g("ipc", "CreateNamedPipeA", "CreateNamedPipeW", "CallNamedPipeA", "CallNamedPipeW",
                     "CreateMailslotA", "CreateMailslotW", "CreateFileMappingW", "CreateFileMappingA",
                     "OpenFileMappingW", "CreateEventW", "OpenEventW", "CreateMutexW"))
API_GROUPS.update(_g("rpc", "RpcServerUseProtseqEpW", "RpcServerUseProtseqEpA", "RpcStringBindingComposeW",
                     "RpcServerUseProtseqW"))
API_GROUPS.update(_g("menu", "DeleteMenu", "RemoveMenu", "ModifyMenuA", "ModifyMenuW", "EnableMenuItem",
                     "LoadMenuA", "LoadMenuW", "LoadMenuIndirectA", "InsertMenuA", "InsertMenuW",
                     "DELETEMENU", "REMOVEMENU", "MODIFYMENU", "ENABLEMENUITEM", "CHANGEMENU", "LOADMENU",
                     "INSERTMENU"))
API_GROUPS.update(_g("debugout", "OutputDebugStringA", "OutputDebugStringW", "OUTPUTDEBUGSTRING"))
# imports that reveal a way to drive / talk to the program from outside
SURFACE = {
    "listener": {"bind", "listen", "accept", "WSAStartup", "socket"},
    "named_pipe": {"CreateNamedPipeA", "CreateNamedPipeW", "ConnectNamedPipe", "CallNamedPipeW", "CallNamedPipeA"},
    "mailslot": {"CreateMailslotA", "CreateMailslotW"},
    "rpc_server": {"RpcServerListen", "RpcServerUseProtseqEpW", "RpcServerUseProtseqEpA",
                   "RpcServerRegisterIf", "RpcServerRegisterIfEx", "RpcServerRegisterIf2"},
    "dde_server": {"DdeInitializeA", "DdeInitializeW", "DdeNameService", "DDEINITIALIZE", "DDENAMESERVICE"},
    "com_server": {"CoRegisterClassObject", "CoResumeClassObjects", "RegisterActiveObject",
                   "CoRegisterClassObject", "COREGISTERCLASSOBJECT"},
    "msaa_uia": {"LresultFromObject", "CreateStdAccessibleObject", "AccessibleObjectFromWindow",
                 "UiaReturnRawElementProvider", "UiaHostProviderFromHwnd", "UiaRaiseAutomationEvent",
                 "NotifyWinEvent", "SetWinEventHook"},
    "hook": {"SetWindowsHookExA", "SetWindowsHookExW", "SETWINDOWSHOOK", "SETWINDOWSHOOKEX",
             "SetWindowsHookA", "SetWindowsHookW"},
    "window_msg": {"RegisterWindowMessageA", "RegisterWindowMessageW", "REGISTERWINDOWMESSAGE"},
    "cmdline": {"GetCommandLineA", "GetCommandLineW", "CommandLineToArgvW", "__getmainargs",
                "__wgetmainargs", "__p___argv", "__p___wargv", "__p__acmdln", "__p__wcmdln"},
}
AUTOMATION_WORDS = re.compile(r"(?i)^[/-]?(embedding|automation|regserver|unregserver|nologo|test|debug|"
                              r"silent|quiet|unattend|setup|restart|server|service|safe|verbose|log|"
                              r"trace|pt|p|s|c|q)$")
PIPE_STR = re.compile(r"(?i)\\\\[.*]\\(pipe|mailslot)\\|\\pipe\\|ncacn_|ncalrpc|ncadg_|"
                      r"\\\\\.\\")


STD_VER_KEYS = {"CompanyName", "FileDescription", "FileVersion", "InternalName",
                "LegalCopyright", "OriginalFilename", "ProductName", "ProductVersion",
                "LegalTrademarks"}


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def cstr_w(b, o, maxlen=4096):
    e = o
    while e + 1 < len(b) and e - o < maxlen * 2:
        if b[e] == 0 and b[e + 1] == 0:
            break
        e += 2
    return b[o:e].decode("utf-16-le", "replace"), e + 2


def cstr_a(b, o, maxlen=4096):
    e = b.find(b"\0", o, o + maxlen)
    if e < 0:
        e = min(len(b), o + maxlen)
    return b[o:e].decode("cp1252", "replace"), e + 1


class Res:
    """One resource: type (int or str), name (int or str), lang, data bytes."""
    __slots__ = ("type", "name", "lang", "data", "src")

    def __init__(self, t, n, l, d, src):
        self.type, self.name, self.lang, self.data, self.src = t, n, l, d, src


class Module:
    def __init__(self, path):
        self.path = path
        self.b = open(path, "rb").read()
        self.kind = None          # "PE32", "PE32+", "NE"
        self.res = []
        self.code = []            # list of bytes objects (code sections / segments)
        self.rsrc_ranges = []     # (start, end) in file of resource data
        self.imports = set()
        self.import_dlls = set()
        self.iat = {}             # PE: VA of IAT slot -> function name
        self.ne_relocs = {}       # NE: (seg, off) -> (module, ordinal or name)
        self.ne_segs = []         # NE: (num, fileoff, length, flags)
        self.autodata = 0
        self.imagebase = 0
        self.exports = []         # (name, ordinal)
        self.ne_desc = None
        self.debug = []
        self.timestamp = None
        self.wide = True          # resources store UTF-16 strings
        self.stub = b""
        b = self.b
        if len(b) < 64 or b[:2] != b"MZ":
            return
        lfa = u32(b, 0x3C)
        self.stub = b[0x40:min(lfa, len(b), 0x200)] if 0x40 < lfa < len(b) else b""
        if lfa + 4 <= len(b) and b[lfa:lfa + 4] == b"PE\0\0":
            self._pe(lfa)
        elif lfa + 2 <= len(b) and b[lfa:lfa + 2] == b"NE":
            self._ne(lfa)

    # ---------------- PE ----------------
    def _pe(self, pe):
        b = self.b
        nsec = u16(b, pe + 6)
        self.timestamp = u32(b, pe + 8)
        optsz = u16(b, pe + 20)
        opt = pe + 24
        magic = u16(b, opt)
        self.imagebase = u32(b, opt + 28) if magic != 0x20B else struct.unpack_from("<Q", b, opt + 24)[0]
        self.kind = "PE32+" if magic == 0x20B else "PE32"
        ddir = opt + (112 if magic == 0x20B else 96)
        ndd = u32(b, ddir - 4)
        dd = [(u32(b, ddir + i * 8), u32(b, ddir + i * 8 + 4)) for i in range(min(ndd, 16))]
        sec = opt + optsz
        self.secs = []
        for i in range(nsec):
            s = sec + i * 40
            name = b[s:s + 8].rstrip(b"\0").decode("latin1")
            vsz, va, rsz, rptr, ch = u32(b, s + 8), u32(b, s + 12), u32(b, s + 16), u32(b, s + 20), u32(b, s + 36)
            self.secs.append((name, va, max(vsz, rsz), rptr, rsz, ch))
            if ch & 0x20000000 or ch & 0x20:   # executable
                self.code.append(b[rptr:rptr + rsz])

        def rva2off(rva):
            for name, va, sz, rptr, rsz, ch in self.secs:
                if va <= rva < va + sz:
                    o = rva - va
                    return rptr + o if o < rsz else None
            return None
        self.rva2off = rva2off
        self.va2off = lambda va: rva2off(va - self.imagebase) if va >= self.imagebase else None
        # resources
        if len(dd) > 2 and dd[2][0]:
            base = rva2off(dd[2][0])
            if base is not None:
                self.rsrc_ranges.append((base, base + dd[2][1]))
                try:
                    self._pe_res(base, base, 0, [])
                except (struct.error, IndexError):
                    pass
        # imports (normal and delay-load)
        step = 8 if magic == 0x20B else 4

        def thunks(dll, names_rva, iat_rva):
            t, i = rva2off(names_rva), 0
            while t is not None and t + step <= len(b):
                v = struct.unpack_from("<Q" if step == 8 else "<I", b, t)[0]
                if not v:
                    break
                if v >> (63 if step == 8 else 31):
                    nm = ORDINALS.get(dll.lower(), {}).get(v & 0xFFFF, "%s#%d" % (dll, v & 0xFFFF))
                else:
                    no = rva2off(v & 0x7FFFFFFF)
                    nm = cstr_a(b, no + 2, 256)[0] if no is not None else "?"
                self.imports.add(nm)
                self.iat[self.imagebase + iat_rva + i * step] = nm
                t += step
                i += 1
        if len(dd) > 1 and dd[1][0]:
            o = rva2off(dd[1][0])
            while o is not None and o + 20 <= len(b):
                ilt, nm, iat = u32(b, o), u32(b, o + 12), u32(b, o + 16)
                if not nm:
                    break
                dll = cstr_a(b, rva2off(nm) or 0, 64)[0]
                self.import_dlls.add(dll.lower())
                thunks(dll, ilt or iat, iat)
                o += 20
        if len(dd) > 13 and dd[13][0]:
            o = rva2off(dd[13][0])
            while o is not None and o + 32 <= len(b):
                attr, nm, iat, intr = u32(b, o), u32(b, o + 4), u32(b, o + 12), u32(b, o + 16)
                if not nm:
                    break
                fix = 0 if attr & 1 else self.imagebase
                dll = cstr_a(b, rva2off(nm - fix) or 0, 64)[0]
                self.import_dlls.add(dll.lower())
                thunks(dll, intr - fix, iat - fix)
                o += 32
        # exports
        if dd and dd[0][0]:
            o = rva2off(dd[0][0])
            if o is not None:
                try:
                    obase, nn = u32(b, o + 16), u32(b, o + 24)
                    an, ao = rva2off(u32(b, o + 32)), rva2off(u32(b, o + 36))
                    for i in range(min(nn, 20000)):
                        no = rva2off(u32(b, an + 4 * i))
                        self.exports.append((cstr_a(b, no, 256)[0], obase + u16(b, ao + 2 * i)))
                except (struct.error, TypeError):
                    pass
        # debug directory
        if len(dd) > 6 and dd[6][0]:
            o = rva2off(dd[6][0])
            for i in range(dd[6][1] // 28 if o is not None else 0):
                e = o + i * 28
                if e + 28 > len(b):
                    break
                typ, sz, ptr = u32(b, e + 12), u32(b, e + 16), u32(b, e + 24)
                if typ == 2 and ptr + 24 <= len(b):
                    sig = b[ptr:ptr + 4]
                    if sig == b"RSDS":
                        g = b[ptr + 4:ptr + 20]
                        age = u32(b, ptr + 20)
                        p = cstr_a(b, ptr + 24, 512)[0]
                        self.debug.append({"format": "RSDS", "pdb": p, "age": age,
                                           "guid": g.hex()})
                    elif sig == b"NB10":
                        self.debug.append({"format": "NB10", "pdb": cstr_a(b, ptr + 16, 512)[0],
                                           "age": u32(b, ptr + 12)})
                elif typ == 4 and ptr + sz <= len(b):     # MISC: image name
                    self.debug.append({"format": "MISC", "name": b[ptr + 12:ptr + sz].rstrip(b"\0").decode("latin1", "replace")})

    def _pe_res(self, base, d, depth, path):
        b = self.b
        n = u16(b, d + 12) + u16(b, d + 14)
        for i in range(min(n, 4096)):
            e = d + 16 + i * 8
            nm, off = u32(b, e), u32(b, e + 4)
            if nm & 0x80000000:
                so = base + (nm & 0x7FFFFFFF)
                key = b[so + 2:so + 2 + 2 * u16(b, so)].decode("utf-16-le", "replace")
            else:
                key = nm
            if off & 0x80000000:
                if depth < 2:
                    self._pe_res(base, base + (off & 0x7FFFFFFF), depth + 1, path + [key])
            else:
                de = base + off
                rva, sz = u32(b, de), u32(b, de + 4)
                fo = self.rva2off(rva)
                if fo is None or len(path) < 2:
                    continue
                self.res.append(Res(path[0], path[1], key, b[fo:fo + sz], os.path.basename(self.path)))

    # ---------------- NE ----------------
    def _ne(self, ne):
        b = self.b
        self.kind = "NE"
        self.wide = False
        nseg = u16(b, ne + 0x1C)
        segtab = ne + u16(b, ne + 0x22)
        rtab = ne + u16(b, ne + 0x24)
        self.rsrc_ranges.append((rtab, ne + u16(b, ne + 0x26)))
        resnames = ne + u16(b, ne + 0x26)
        nonres = u32(b, ne + 0x2C)
        nonres_len = u16(b, ne + 0x20)
        align = u16(b, ne + 0x32) or 9
        self.autodata = u16(b, ne + 0x0E)
        for i in range(nseg):
            s = segtab + i * 8
            off, ln, fl = u16(b, s) << align, u16(b, s + 2) or 0x10000, u16(b, s + 4)
            self.ne_segs.append((i + 1, off, ln, fl))
            if off and not (fl & 1):        # code segment (bit0 = data)
                self.code.append(b[off:off + ln])
            elif off:
                self.code_data = getattr(self, "code_data", []) + [b[off:off + ln]]

        def names(o, end=None):
            out = []
            while o < len(b) and (end is None or o < end):
                ln = b[o]
                if not ln:
                    break
                out.append((b[o + 1:o + 1 + ln].decode("cp1252", "replace"), u16(b, o + 1 + ln)))
                o += 3 + ln
            return out
        rn = names(resnames)
        nr = names(nonres, nonres + nonres_len) if nonres else []
        if nr:
            self.ne_desc = nr[0][0]
        self.exports = [(n, o) for n, o in rn[1:] + nr[1:]]
        # imported module names only (NE imports by ordinal mostly)
        # resources
        if rtab != ne + u16(b, ne + 0x26):
            shift = u16(b, rtab)
            p = rtab + 2
            while p + 8 <= len(b):
                tid, cnt = u16(b, p), u16(b, p + 2)
                if not tid:
                    break
                if tid & 0x8000:
                    t = tid & 0x7FFF
                else:
                    t = cstr_pas(b, rtab + tid)
                p += 8
                for _ in range(cnt):
                    off, ln, rid = u16(b, p) << shift, u16(b, p + 2) << shift, u16(b, p + 6)
                    name = rid & 0x7FFF if rid & 0x8000 else cstr_pas(b, rtab + rid)
                    self.res.append(Res(t, name, 0, b[off:off + ln], os.path.basename(self.path)))
                    self.rsrc_ranges.append((off, off + ln))
                    p += 12
        # imports: NE module reference table names; plus scan for ordinal-imported debug fns
        modref = ne + u16(b, ne + 0x28)
        impn = ne + u16(b, ne + 0x2A)
        for i in range(u16(b, ne + 0x1E)):
            self.imports.add("module:" + cstr_pas(b, impn + u16(b, modref + 2 * i)))
        mods = [cstr_pas(b, impn + u16(b, modref + 2 * i)) for i in range(u16(b, ne + 0x1E))]
        for n, off, ln, fl in self.ne_segs:
            if not (fl & 0x100) or not off or off + ln + 2 > len(b):
                continue
            rl = off + ln
            for k in range(u16(b, rl)):
                e = rl + 2 + k * 8
                if e + 8 > len(b):
                    break
                st_, f2, so, a1, a2 = struct.unpack_from("<BBHHH", b, e)
                t = f2 & 3
                if t == 1 and 0 < a1 <= len(mods):
                    tgt = (mods[a1 - 1], a2)
                elif t == 2 and 0 < a1 <= len(mods):
                    tgt = (mods[a1 - 1], cstr_pas(b, impn + a2))
                else:
                    continue
                if f2 & 4:                       # additive: single fixup
                    self.ne_relocs[(n, so)] = tgt
                    continue
                o, guard = so, 0
                while o != 0xFFFF and o + 2 <= ln and guard < 4096:
                    self.ne_relocs[(n, o)] = tgt
                    o = u16(b, off + o)
                    guard += 1
        # names imported by name appear in the imported-names table too
        o, end = impn, ne + u16(b, ne + 0x2C) if False else ne + u16(b, ne + 0x04)
        while o < end and o < len(b):
            ln = b[o]
            if ln:
                self.imports.add(b[o + 1:o + 1 + ln].decode("latin1"))
            o += 1 + ln


def cstr_pas(b, o):
    if o >= len(b):
        return ""
    return b[o + 1:o + 1 + b[o]].decode("cp1252", "replace")


# ---------------- resource decoders ----------------
def parse_strings(r, wide):
    out = []
    if not isinstance(r.name, int):
        return out
    base = (r.name - 1) * 16
    d, o = r.data, 0
    for i in range(16):
        if wide:
            if o + 2 > len(d):
                break
            n = u16(d, o)
            o += 2
            s = d[o:o + 2 * n].decode("utf-16-le", "replace")
            o += 2 * n
        else:
            if o >= len(d):
                break
            n = d[o]
            o += 1
            s = d[o:o + n].decode("cp1252", "replace")
            o += n
        if s:
            out.append((base + i, s))
    return out


def parse_accel(r, wide):
    out = []
    d = r.data
    step = 8 if wide else 5
    for o in range(0, len(d) - step + 1, step):
        if wide:
            fl, key, cmd = u16(d, o), u16(d, o + 2), u16(d, o + 4)
        else:
            fl, key, cmd = d[o], u16(d, o + 1), u16(d, o + 3)
        out.append((fl, key, cmd))
        if fl & 0x80:
            break
    return out


VK = {8: "Backspace", 9: "Tab", 13: "Enter", 27: "Esc", 32: "Space", 33: "PgUp", 34: "PgDn",
      35: "End", 36: "Home", 37: "Left", 38: "Up", 39: "Right", 40: "Down", 45: "Ins", 46: "Del",
      0x6A: "Num*", 0x6B: "Num+", 0x6D: "Num-", 0x6E: "Num.", 0x6F: "Num/", 0xBB: "=", 0xBD: "-",
      0xBC: ",", 0xBE: ".", 0xBF: "/", 0xC0: "`", 0xDB: "[", 0xDC: "\\", 0xDD: "]", 0xDE: "'",
      0xBA: ";", 0x90: "NumLock", 0x91: "ScrollLock", 0x13: "Pause", 0x2C: "PrtSc", 3: "Break",
      0x5D: "Apps"}


def accel_desc(fl, key):
    mods = []
    if fl & 0x08:
        mods.append("Ctrl")
    if fl & 0x10:
        mods.append("Alt")
    if fl & 0x04:
        mods.append("Shift")
    if fl & 0x01:                       # FVIRTKEY
        if 0x70 <= key <= 0x87:
            k = "F%d" % (key - 0x6F)
        elif 0x30 <= key <= 0x39 or 0x41 <= key <= 0x5A:
            k = chr(key)
        elif 0x60 <= key <= 0x69:
            k = "Num%d" % (key - 0x60)
        else:
            k = VK.get(key, "VK_0x%02X" % key)
    else:
        k = ("Ctrl+" + chr(key + 64)) if 0 < key < 32 else repr(chr(key)) if key < 0x110000 else str(key)
    return "+".join(mods + [k])


def parse_menu(r, wide):
    """Return list of (id, text, flags) for command items, plus popup list."""
    d = r.data
    items = []
    try:
        if wide:
            ver = u16(d, 0)
            if ver == 1:                          # MENUEX
                o = 4 + u16(d, 2)

                def ex(o, depth):
                    while o + 14 <= len(d):
                        typ, state, mid = u32(d, o), u32(d, o + 4), u32(d, o + 8)
                        res = u16(d, o + 12)
                        txt, o = cstr_w(d, o + 14)
                        o = (o + 3) & ~3
                        fl = (state & 0xFFFF) | (typ & 0x0B00)      # keep MFT_OWNERDRAW/SEPARATOR bits
                        if res & 1:
                            o += 4
                            items.append((None, txt, fl | 0x10 | 0x10000, depth))
                            o = ex(o, depth + 1)
                        else:
                            items.append((mid if mid != 0xFFFFFFFF else 0, txt, fl, depth))
                        if res & 0x80:
                            break
                    return o
                ex(o, 0)
                return items
            o = 4 + u16(d, 2)
        else:
            o = 4

        def std(o, depth):
            while o + 2 <= len(d):
                fl = u16(d, o)
                o += 2
                if fl & 0x10:                     # MF_POPUP
                    if wide:
                        txt, o = cstr_w(d, o)
                    else:
                        txt, o = cstr_a(d, o)
                    items.append((None, txt, fl, depth))
                    o = std(o, depth + 1)
                else:
                    mid = u16(d, o)
                    o += 2
                    if wide:
                        txt, o = cstr_w(d, o)
                    else:
                        txt, o = cstr_a(d, o)
                    items.append((mid, txt, fl, depth))
                if fl & 0x80:
                    break
            return o
        std(o, 0)
    except (struct.error, IndexError):
        pass
    return items


def parse_dialog_ids(r, wide, refs=None):
    """Control IDs of a dialog template (PE DLGTEMPLATE[EX] or Win16).  Ordinal control
    texts (icons / bitmaps shown by SS_ICON / SS_BITMAP statics) are added to refs."""
    d, ids = r.data, set()
    refs = set() if refs is None else refs
    try:
        if wide:
            def sz(o):
                w = u16(d, o)
                if w == 0:
                    return o + 2
                if w == 0xFFFF:
                    return o + 4
                return cstr_w(d, o)[1]
            ex = u16(d, 0) == 1 and u16(d, 2) == 0xFFFF
            if ex:
                style, n, o = u32(d, 12), u16(d, 16), 26
            else:
                style, n, o = u32(d, 0), u16(d, 8), 18
            o = sz(sz(sz(o)))
            if style & 0x40:
                o += 6 if ex else 2
                o = cstr_w(d, o)[1]
            for _ in range(n):
                o = (o + 3) & ~3
                if ex:
                    ids.add(u32(d, o + 20) & 0xFFFF)
                    o += 24
                else:
                    ids.add(u16(d, o + 16))
                    o += 18
                o = sz(o)
                if u16(d, o) == 0xFFFF:
                    refs.add(u16(d, o + 2))
                o = sz(o)
                o += 2 + u16(d, o)
        else:
            style, n = u32(d, 0), d[4]
            o = 13

            def sa(o):
                if d[o] == 0xFF:
                    return o + 3
                return cstr_a(d, o)[1]
            o = sa(o)
            o = cstr_a(d, o)[1]
            o = cstr_a(d, o)[1]
            if style & 0x40:
                o = cstr_a(d, o + 2)[1]
            for _ in range(n):
                ids.add(u16(d, o + 8))
                o += 14
                c = d[o]
                o = o + 1 if c & 0x80 else cstr_a(d, o)[1]
                if d[o] == 0xFF:
                    refs.add(u16(d, o + 1))
                o = sa(o)
                o += 1 + d[o]
    except (struct.error, IndexError):
        pass
    return ids


def parse_version(data, wide):
    """Return (fixed dict, {key: value}) from a VS_VERSIONINFO blob."""
    fixed, kv = {}, {}
    i = data.find(b"\xbd\x04\xef\xfe")
    if i >= 0 and i + 52 <= len(data):
        f = struct.unpack_from("<13I", data, i)
        fixed = {"FileVersion": "%d.%d.%d.%d" % (f[2] >> 16, f[2] & 0xFFFF, f[3] >> 16, f[3] & 0xFFFF),
                 "FileFlagsMask": f[6], "FileFlags": f[7], "FileOS": f[8], "FileType": f[9]}
    def node(o, end, depth, path):
        if o + 4 > end:
            return end
        ln = u16(data, o)
        vln = u16(data, o + 2)
        if ln < 4 or o + ln > len(data):
            return end
        if wide:
            typ = u16(data, o + 4)
            key, p = cstr_w(data, o + 6, 256)
        else:
            typ = 1
            key, p = cstr_a(data, o + 4, 256)
        p = (p + 3) & ~3
        if wide and typ == 1:
            vbytes = vln * 2
        else:
            vbytes = vln
        if depth == 3 and path[1] == "StringFileInfo":
            raw = data[p:p + vbytes]
            val = raw.decode("utf-16-le" if wide else "cp1252", "replace").split("\0")[0]
            kv[key] = val
        c = (p + vbytes + 3) & ~3
        while depth < 3 and c + 4 <= o + ln:
            nc = node(c, o + ln, depth + 1, path + [key])
            if nc <= c:
                break
            c = nc
        return (o + ln + 3) & ~3
    try:
        node(0, len(data), 0, [])
    except (struct.error, IndexError):
        pass
    return fixed, kv


# ---------------- code reference index ----------------
def immediates(code_blobs, bits16):
    """Set of small integers that occur as immediates in plausible encodings."""
    s = set()
    for c in code_blobs:
        n = len(c)
        for m in re.finditer(rb"[\x68\xB8-\xBF\x3D]", c):
            o = m.start()
            if bits16:
                if o + 3 <= n:
                    s.add(c[o + 1] | c[o + 2] << 8)
            elif o + 5 <= n and c[o + 3] == 0 and c[o + 4] == 0:
                s.add(c[o + 1] | c[o + 2] << 8)
        for m in re.finditer(rb"\x6A", c):
            o = m.start()
            if o + 2 <= n:
                s.add(c[o + 1])
        # cmp r/m, imm32 / imm16 (81 /7) and imm8 (83 /7), mov r/m,imm (C7 /0) register forms
        for m in re.finditer(rb"[\x81\xC7][\xC0-\xFF]", c):
            o = m.start()
            if bits16 and o + 4 <= n:
                s.add(c[o + 2] | c[o + 3] << 8)
            elif o + 6 <= n and c[o + 4] == 0 and c[o + 5] == 0:
                s.add(c[o + 2] | c[o + 3] << 8)
        for m in re.finditer(rb"\x83[\xF8-\xFF]", c):
            if m.start() + 3 <= n:
                s.add(c[m.start() + 2])
        # x64: mov r8d/r9d,imm32 ; mov dword [rsp+..], imm32
        if not bits16:
            for m in re.finditer(rb"\x41[\xB8-\xBF]", c):
                o = m.start()
                if o + 6 <= n and c[o + 4] == 0 and c[o + 5] == 0:
                    s.add(c[o + 2] | c[o + 3] << 8)
    return s


def extract_strings(b, ranges, minlen=5):
    """ASCII and UTF-16LE strings outside the given byte ranges -> [(off, enc, text)]."""
    out = []

    def inside(o):
        return any(a <= o < z for a, z in ranges)
    for m in re.finditer(rb"[\x20-\x7e\t]{%d,}" % minlen, b):
        if not inside(m.start()):
            out.append((m.start(), "a", m.group().decode("ascii")))
    for m in re.finditer(rb"(?:[\x20-\x7e\t]\x00){%d,}" % minlen, b):
        if not inside(m.start()):
            out.append((m.start(), "w", m.group().decode("utf-16-le")))
    return out


STD_STUBS = ("This program cannot be run in DOS mode", "This program must be run under Win32",
             "This program requires Microsoft Windows", "This program requires Microsoft Windows.")


def classify_code_string(s):
    kinds = []
    t = s.strip()
    if SWITCH.match(t) and not re.match(r"^-[0-9]", t):
        kinds.append("switch")
    if REGVAL.match(t):
        kinds.append("regval")
    if REGKEY.match(t):
        kinds.append("regkey")
    if SRCPATH.search(t):
        kinds.append("srcpath")
    if ASSERT.search(t):
        kinds.append("assert")
    if KW_CODENAME.search(t):
        kinds.append("codename")
    if KW_STRONG.search(t):
        kinds.append("devnote")
    if EMAIL.search(t):
        kinds.append("email")
    if ENVVAR.match(t):
        kinds.append("envvar")
    if len(t) >= 12 and DEBUGFMT.search(t) and not kinds:
        kinds.append("debugfmt")
    return kinds


def boring(s):
    """Filter compiler/CRT noise and random byte runs."""
    if len(set(s)) < 4:
        return True
    if re.fullmatch(r"[A-Za-z0-9+/=]{20,}", s) and not re.search(r"[aeiou]{1}", s.lower()):
        return True
    alnum = sum(ch.isalnum() for ch in s)
    if alnum < len(s) * 0.5:
        return True
    return False


CRT_NOISE = re.compile(r"(?i)^(R6\d\d\d|runtime error|microsoft visual c\+\+ runtime|"
                       r"\.\.\.|<program name unknown>|SunMonTue|JanFebMar|GetLastActivePopup|"
                       r"GetActiveWindow|MessageBoxA|user32\.dll|api-ms-win|ext-ms-win|"
                       r"_?(nmh|tmp)|ole32\.dll|kernel32\.dll|ntdll\.dll|advapi32\.dll)")


def _string_at_va(m, va, maxlen=300):
    o = m.va2off(va) if m.kind != "NE" else None
    if o is None or o + 2 > len(m.b):
        return None
    b = m.b
    if b[o + 1] == 0 and 32 <= b[o] < 127:
        s, _ = cstr_w(b, o, maxlen)
        if len(s) >= 2 and all(32 <= ord(c) < 0x3000 for c in s):
            return s
    if 32 <= b[o] < 127:
        s, _ = cstr_a(b, o, maxlen)
        if len(s) >= 2 and all(32 <= ord(c) < 127 or c in "\t\r\n" for c in s):
            return s
    return None


def call_args_pe(m):
    """x86 PE32 only: for every call to an interesting import, the string literals pushed
    (or mov'd into a register) in the 64 bytes before it.  Yields (api, va, [strings])."""
    if m.kind != "PE32":
        return
    want = {va: n for va, n in m.iat.items() if n.upper() in API_GROUPS}
    if not want:
        return
    b = m.b
    for name, va, sz, rptr, rsz, ch in m.secs:
        if not (ch & 0x20000000):
            continue
        code = b[rptr:rptr + rsz]
        base = m.imagebase + va
        sites = []
        for mm in re.finditer(rb"\xFF\x15(....)", code, re.S):
            t = u32(mm.group(1), 0)
            if t in want:
                sites.append((mm.start(), want[t]))
        # mov esi/edi/ebx/ebp,[iat] ... call esi/edi/ebx/ebp
        for mm in re.finditer(rb"\x8B([\x35\x3D\x1D\x2D])(....)", code, re.S):
            t = u32(mm.group(2), 0)
            if t not in want:
                continue
            reg = {0x35: 0xD6, 0x3D: 0xD7, 0x1D: 0xD3, 0x2D: 0xD5}[mm.group(1)[0]]
            end = min(len(code), mm.end() + 1500)
            p = mm.end()
            while True:
                p = code.find(bytes([0xFF, reg]), p, end)
                if p < 0:
                    break
                sites.append((p, want[t]))
                p += 2
        for p, api in sites:
            lo = max(0, p - 64)
            strs = []
            for q in re.finditer(rb"[\x68\xB8-\xBF](....)", code[lo:p], re.S):
                s = _string_at_va(m, u32(q.group(1), 0))
                if s and s not in strs:
                    strs.append(s)
            imms = []
            for q in re.finditer(rb"\x68(..)\x00\x00|\x6A(.)", code[max(0, p - 24):p], re.S):
                imms.append(u16(q.group(1), 0) if q.group(1) else q.group(2)[0])
            if strs or (imms and API_GROUPS.get(api.upper()) == "menu"):
                yield api, base + p, strs, imms


def call_args_ne(m):
    """Win16: far calls (9A) whose target is a relocated import; string offsets pushed
    (68 imm16) shortly before are resolved in the automatic data segment."""
    if m.kind != "NE" or not m.ne_relocs:
        return
    data = None
    for n, off, ln, fl in m.ne_segs:
        if n == m.autodata:
            data = m.b[off:off + ln]
    if data is None:
        return
    for n, off, ln, fl in m.ne_segs:
        if fl & 1:
            continue
        code = m.b[off:off + ln]
        for (sn, so), (mod, ordn) in m.ne_relocs.items():
            if sn != n or so < 1 or code[so - 1:so] != b"\x9A":
                continue
            api = ordn if isinstance(ordn, str) else NE_EXPORTS.get(mod, {}).get(ordn) or \
                NE_BUILTIN.get(mod, {}).get(ordn) or "%s.%d" % (mod, ordn)
            if api.upper() not in API_GROUPS:
                continue
            lo = max(0, so - 1 - 48)
            strs = []
            for q in re.finditer(rb"\x68(..)", code[lo:so - 1], re.S):
                v = u16(q.group(1), 0)
                if 0 < v < len(data) and 32 <= data[v] < 127:
                    s, _ = cstr_a(data, v, 200)
                    if len(s) >= 2 and all(32 <= ord(c) < 127 for c in s) and s not in strs:
                        strs.append(s)
            imms = []
            for q in re.finditer(rb"\x68(..)|\x6A(.)", code[max(0, so - 1 - 20):so - 1], re.S):
                imms.append(u16(q.group(1), 0) if q.group(1) else q.group(2)[0])
            if strs or (imms and API_GROUPS.get(api.upper()) == "menu"):
                yield "%s.%s" % (mod, api), "seg%d:%04x" % (n, so - 1), strs, imms


def ne_imported_names(m):
    names = set()
    for (mod, ordn) in set(m.ne_relocs.values()):
        if isinstance(ordn, str):
            names.add(ordn.upper())
        else:
            nm = NE_EXPORTS.get(mod, {}).get(ordn) or NE_BUILTIN.get(mod, {}).get(ordn)
            if nm:
                names.add(nm.upper())
    return names


def dib_header_size(d):
    hs = u32(d, 0)
    if hs == 12:                                   # BITMAPCOREHEADER
        bc = u16(d, 10)
        return hs + (3 << bc if bc <= 8 else 0)
    bc, comp, used = u16(d, 14), u32(d, 16), u32(d, 32)
    pal = (used or (1 << bc if bc <= 8 else 0)) * 4
    if comp == 3 and hs == 40:
        pal += 12
    return hs + pal


def render_png(kind, data, res_by_key, out_path):
    """Write a PNG for an icon group / cursor group / bitmap.  Needs Pillow; returns bool."""
    try:
        from PIL import Image
        import io
    except ImportError:
        return False
    try:
        if kind == 2:                                   # BITMAP
            if data[:8] == b"\x89PNG\r\n\x1a\n":
                img = Image.open(io.BytesIO(data))
            else:
                off = 14 + dib_header_size(data)
                img = Image.open(io.BytesIO(b"BM" + struct.pack("<IHHI", 14 + len(data), 0, 0, off) + data))
        else:                                           # 14 GROUP_ICON / 12 GROUP_CURSOR
            cnt = u16(data, 4)
            best = None
            for i in range(cnt):
                e = 6 + i * 14
                rid = u16(data, e + 12)
                part = res_by_key.get((1 if kind == 12 else 3, rid))
                if part is None:
                    continue
                if kind == 12:
                    part = part[4:]                     # strip hotspot
                if part[:8] == b"\x89PNG\r\n\x1a\n":
                    im = Image.open(io.BytesIO(part))
                else:
                    core = u32(part, 0) == 12
                    w = u16(part, 4) if core else u32(part, 4)
                    bpp = u16(part, 10) if core else u16(part, 14)
                    ico = struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", w & 0xFF, (w & 0xFF), 0, 0, 1,
                                                                     bpp, len(part), 22) + part
                    im = Image.open(io.BytesIO(ico))
                im.load()
                if best is None or im.size[0] * im.size[1] > best.size[0] * best.size[1]:
                    best = im
            if best is None:
                return False
            img = best
        img.load()
        img.convert("RGBA").save(out_path)
        return True
    except Exception:
        return False


def scan(path, mui_index, out, args):
    try:
        m = Module(path)
    except (OSError, struct.error, IndexError, ValueError) as e:
        print("codehunt: %s: %s" % (path, e), file=sys.stderr)
        return
    if not m.kind:
        return
    base = os.path.basename(path)
    sats = []
    for cand in (path + ".mui", os.path.join(os.path.dirname(path), "en-US", base + ".mui")):
        if os.path.exists(cand):
            sats.append(cand)
    sats += [p for p in mui_index.get(base.lower() + ".mui", []) if p not in sats]
    for s in sats[:1]:
        try:
            sm = Module(s)
            m.res += sm.res
        except (OSError, struct.error, IndexError):
            pass
    fname = os.path.relpath(path, args.root) if args.root else path
    wide = m.wide
    bits16 = m.kind == "NE" or (m.kind == "PE32" and False)
    imms = immediates(m.code, m.kind == "NE")
    rec_n = [0]

    def emit(cls, detail, text=None, **kw):
        r = {"file": fname, "fmt": m.kind, "class": cls, "detail": detail}
        if text is not None:
            r["text"] = text
        r.update(kw)
        out.write(json.dumps(r, ensure_ascii=False) + "\n")
        rec_n[0] += 1

    # all strings outside resources (used both for refs and code_str)
    cstrs = extract_strings(m.b, m.rsrc_ranges)
    cset = set(s for _, _, s in cstrs)
    cset_l = set(s.lower() for s in cset)
    for _, _, s in cstrs:                      # names glued to neighbours
        for part in re.split(r"[^\w.#-]+", s):
            cset_l.add(part.lower())

    # --- debug directory
    for d in m.debug:
        emit("pdb", d.get("format"), d.get("pdb") or d.get("name"), **{k: v for k, v in d.items() if k not in ("pdb", "name", "format")})
    # --- timestamp
    if m.timestamp is not None:
        emit("timestamp", "link time", None, epoch=m.timestamp)
    # --- NE description
    if m.ne_desc:
        emit("ne_desc", "non-resident name 0", m.ne_desc)
    # --- DOS stub
    st = re.findall(rb"[\x20-\x7e]{12,}", m.stub)
    for s in st:
        s = s.decode()
        s = s.strip("!$ \t")
        if len(s) >= 12 and not any(s.startswith(x) for x in STD_STUBS) and "Rich" not in s:
            emit("dos_stub", "MZ stub text", s)
    # --- imports / exports
    dbg = sorted(i for i in m.imports if i in DEBUG_IMPORTS)
    if dbg:
        emit("debug_output", "imports", ", ".join(dbg))
    for n, o in m.exports:
        if (re.search(r"(?i)debug|dbg|trace|dump|hack|secret|hidden|easter|credit|cheat|magic|dummy|unused", n)
                or re.search(r"(?i)test(?!atus)", n)) and "EXPORTEDSTUB" not in n.upper():
            emit("export_name", "ordinal %d" % o, n)

    # --- resources
    menu_ids, menu_res = set(), []
    for r in m.res:
        if r.type == 4:
            its = parse_menu(r, wide)
            menu_res.append((r, its))
            for mid, txt, fl, dep in its:
                if mid is not None:
                    menu_ids.add(mid)
    # dialog control ids (accelerators sometimes target buttons)
    dlg_ids, dlg_refs = set(), set()
    for r in m.res:
        if r.type == 5:
            dlg_ids |= parse_dialog_ids(r, wide, dlg_refs)
    for r in m.res:
        if r.type == 9:
            for fl, key, cmd in parse_accel(r, wide):
                if cmd not in menu_ids and cmd not in dlg_ids:
                    emit("accel_hidden", "ACCELERATOR %s" % r.name, accel_desc(fl, key),
                         cmd=cmd, in_code=cmd in imms, src=r.src)
    for r, its in menu_res:
        for mid, txt, fl, dep in its:
            if fl & 0x3 and mid is not None and fl & 0x10000 == 0:     # MF_GRAYED/MF_DISABLED / MFS_DISABLED
                emit("menu_odd", "MENU %s grayed item" % r.name, txt, id=mid, flags=fl, src=r.src)
            if txt and KW_STRONG.search(txt):
                emit("string_kw", "MENU %s item" % r.name, txt, id=mid, src=r.src)

    def name_ref(nm):
        return nm.lower() in cset_l

    seen_unref = 0
    res_by_key = {(r.type, r.name): r.data for r in m.res}
    group_ids = sorted(r.name for r in m.res if r.type == 14 and isinstance(r.name, int))
    app_icon = group_ids[0] if group_ids else None
    named_groups = [r.name for r in m.res if r.type == 14 and not isinstance(r.name, int)]
    is_dll = base.lower().rsplit(".", 1)[-1] in ("dll", "cpl", "ocx", "drv", "mui")
    for r in m.res:
        if r.type in (2, 12, 14) and m.code:
            if isinstance(r.name, int):
                ref = r.name in imms or r.name in dlg_refs
            else:
                ref = name_ref(r.name)
            appicon = r.type == 14 and not named_groups and r.name == app_icon
            if ref or appicon:
                continue
            rec = {"src": r.src, "size": len(r.data), "dll": is_dll}
            if args.icons_dir:
                safe = re.sub(r"[^\w.-]", "_", "%s__%s_%s" % (base, RT[r.type], r.name))
                pth = os.path.join(args.icons_dir, safe + ".png")
                if render_png(r.type, r.data, res_by_key, pth):
                    rec["png"] = os.path.relpath(pth, args.icons_rel) if args.icons_rel else pth
            emit("res_unref_image", "%s %s" % (RT[r.type], r.name),
                 "possible orphan (no immediate, dialog or name reference found)", **rec)
    for r in m.res:
        t = r.type
        if t == 6:
            for sid, s in parse_strings(r, wide):
                hit = KW_STRONG.search(s) or KW_CODENAME.search(s) or SRCPATH.search(s) or EMAIL.search(s)
                if hit:
                    emit("string_kw", "STRINGTABLE id %d" % sid, s, id=sid, match=hit.group(0),
                         in_code=sid in imms, src=r.src)
                elif m.code and sid not in imms and args.unref_strings:
                    emit("string_unref", "STRINGTABLE id %d" % sid, s, id=sid, src=r.src)
                    seen_unref += 1
        elif t in (4, 5, 9, 10, 23) and m.code:
            if isinstance(r.name, int):
                ref = r.name in imms
            else:
                ref = name_ref(r.name)
            if not ref:
                emit("res_unref", "%s %s" % (RT.get(t, t), r.name), None, src=r.src, size=len(r.data))
        elif t == 16:
            fixed, kv = parse_version(r.data, wide)
            odd = {k: v for k, v in kv.items() if k not in STD_VER_KEYS or k in ("Comments", "PrivateBuild", "SpecialBuild")}
            for k, v in odd.items():
                emit("version", "VERSIONINFO key %s" % k, v)
            ff = fixed.get("FileFlags", 0) & fixed.get("FileFlagsMask", 0xFFFF)
            if ff:
                names = [n for bit, n in ((1, "DEBUG"), (2, "PRERELEASE"), (4, "PATCHED"), (8, "PRIVATEBUILD"),
                                          (0x10, "INFOINFERRED"), (0x20, "SPECIALBUILD")) if ff & bit]
                emit("version", "FileFlags", "|".join(names), fileversion=fixed.get("FileVersion"))
            for k, v in kv.items():
                if KW_STRONG.search(v) or KW_CODENAME.search(v):
                    emit("version", "VERSIONINFO value %s" % k, v)
        elif t == 24:
            txt = r.data.decode("utf-8", "replace")
            for mm in re.finditer(r"<(description|dpiAware|autoElevate|uiAccess|disableTheming|supportedOS|"
                                  r"requestedExecutionLevel|windowsSettings|ms_compatibility|gdiScaling|"
                                  r"printerDriverIsolation|disableWindowFiltering|longPathAware|"
                                  r"heapType|activeCodePage)[^>]*>([^<]*)", txt):
                emit("manifest", mm.group(1), mm.group(0).strip()[:300])
            for mm in re.finditer(r"<!--(.*?)-->", txt, re.S):
                emit("manifest", "comment", mm.group(1).strip()[:300])
        elif t in ("REGINST", "TYPELIB", "AVI", "WAVE", "MIDI", "JPEG", "PNG", "GIF", "TEXT", "TXT", "HTML",
                   "WEVT_TEMPLATE", "MUI") or (isinstance(t, str)):
            emit("res_custom", "custom type %s/%s" % (t, r.name), None, size=len(r.data), src=r.src)

    calls = list(call_args_pe(m)) + list(call_args_ne(m))
    # --- hidden menus
    item_ids = {}
    for r, its in menu_res:
        for mid, txt, fl, dep in its:
            if mid:
                item_ids.setdefault(mid, []).append((r.name, txt))
    loaded = set()
    for api, where, strs, ims in calls:
        a = api.split(".")[-1].upper()
        if API_GROUPS.get(a) != "menu":
            continue
        if a.startswith("LOADMENU"):
            loaded.update(ims)
            continue
        for v in ims:
            for mname, txt in item_ids.get(v, []):
                emit("menu_runtime", "%s(id %d) at %s" % (api, v,
                     ("%08x" % where) if isinstance(where, int) else where), txt, id=v, menu=mname)
    menu_langs = [r.lang for r, _ in menu_res]
    main_lang = max(set(menu_langs), key=menu_langs.count) if menu_langs else None
    mfc_map = lambda i: struct.pack("<IIII", 0x111, 0, i, i) in m.b
    for r, its in menu_res:
        if m.code and isinstance(r.name, int) and r.name not in imms and r.name not in loaded:
            emit("menu_unloaded", "MENU %s" % r.name, " / ".join(t for i, t, f, d in its if d == 0)[:200],
                 items=len(its), src=r.src)
        if main_lang is not None and r.lang != main_lang:
            emit("menu_odd", "MENU %s language 0x%04x (module mostly 0x%04x)" % (r.name, r.lang, main_lang),
                 None, src=r.src)
        # popups whose children are all separators / empty
        for k, (mid, txt, fl, dep) in enumerate(its):
            if mid is None:
                kids = []
                for mid2, t2, f2, d2 in its[k + 1:]:
                    if d2 <= dep:
                        break
                    if d2 == dep + 1:
                        kids.append((mid2, t2))
                if kids and all(not t2 for _, t2 in kids):
                    emit("menu_odd", "MENU %s empty popup" % r.name, txt, children=len(kids), src=r.src)
            elif mid and (fl & 0x100) and not (fl & 0x10000):
                emit("menu_odd", "MENU %s owner-draw item" % r.name, txt, id=mid, src=r.src)
            elif mid and not txt and not (fl & 0x900):
                emit("menu_odd", "MENU %s item with id %d but no text" % (r.name, mid), txt, id=mid, src=r.src)
            elif mid and m.code and mid > 15 and mid not in imms and not mfc_map(mid) and mid < 0xE000:
                emit("menu_nohandler", "MENU %s id %d" % (r.name, mid), txt, id=mid, src=r.src)

    # --- external control surface: imports that let something else drive the program
    imported = set(m.imports) | (ne_imported_names(m) if m.kind == "NE" else set())
    for grp, fns in SURFACE.items():
        hit = sorted(f for f in imported if f in fns or f.upper() in {x.upper() for x in fns})
        if hit:
            emit("surface", grp, ", ".join(hit))
    if any(r.type == "TYPELIB" for r in m.res):
        emit("surface", "typelib", "embedded TYPELIB resource (OLE automation description)")
    sock = sorted(d for d in m.import_dlls if d in ("ws2_32.dll", "wsock32.dll", "winsock.dll"))
    if sock:
        emit("surface", "winsock", ", ".join(sock))
    has_cmdline = m.kind == "NE" or any(f in imported for f in SURFACE["cmdline"]) or \
        base.lower().endswith(".exe")
    # --- literal arguments of interesting calls
    for api, where, strs, _imms in calls:
        grp = API_GROUPS.get(api.split(".")[-1].upper(), "?")
        if not strs:
            continue
        emit("api_arg", "%s %s" % (grp, api), " | ".join(strs),
             at=("%08x" % where) if isinstance(where, int) else where, group=grp, args=strs)
    # --- command-line switch candidates
    if has_cmdline:
        cmp_strs = set()
        for api, where, strs, _imms in calls:
            if API_GROUPS.get(api.split(".")[-1].upper()) == "compare":
                cmp_strs.update(strs)
        for off, enc, s in cstrs:
            t = s.strip()
            if SWITCH.match(t) or AUTOMATION_WORDS.match(t) or (t in cmp_strs and len(t) <= 24):
                emit("cmdline", "offset 0x%x %s" % (off, "utf16" if enc == "w" else "ascii"), t,
                     compared=t in cmp_strs)
    # --- code strings
    seen = set()
    for off, enc, s in cstrs:
        if s in seen or s in m.imports or boring(s) or CRT_NOISE.match(s):
            continue
        kinds = classify_code_string(s)
        if PIPE_STR.search(s):
            kinds.append("ipc")
        if not kinds:
            continue
        seen.add(s)
        emit("code_str", "offset 0x%x %s" % (off, "utf16" if enc == "w" else "ascii"), s, kind=kinds)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--mui", action="append", default=[], help="directory of .mui satellites")
    ap.add_argument("--root", help="report paths relative to this directory")
    ap.add_argument("--icons-dir", help="render possibly-orphaned icons/cursors/bitmaps to PNG here (needs Pillow)")
    ap.add_argument("--icons-rel", help="record PNG paths relative to this directory")
    ap.add_argument("--ne-sysdir", action="append", default=[],
                    help="extra directories of Win16 modules used only to name imported ordinals")
    ap.add_argument("--unref-strings", action="store_true",
                    help="also emit every string-table entry with no immediate reference (noisy)")
    args = ap.parse_args()
    mui_index = {}
    for d in args.mui:
        for dp, dn, fn in os.walk(d):
            for f in fn:
                if f.lower().endswith(".mui"):
                    mui_index.setdefault(f.lower(), []).append(os.path.join(dp, f))
    files = []
    for p in args.paths:
        if os.path.isdir(p):
            for dp, dn, fn in os.walk(p):
                for f in sorted(fn):
                    if not f.lower().endswith(".mui") and f.lower().rsplit(".", 1)[-1] in (
                            "exe", "dll", "cpl", "drv", "ocx", "scr", "com", "386", "mod", "acm", "ax", "sys", "tsk"):
                        files.append(os.path.join(dp, f))
        else:
            files.append(p)
    if args.icons_dir:
        os.makedirs(args.icons_dir, exist_ok=True)
    # first pass: Win16 export tables, so imported ordinals can be named
    pool = list(files)
    for d in args.ne_sysdir:
        for dp, dn, fn in os.walk(d):
            pool += [os.path.join(dp, f) for f in fn]
    for f in pool:
        try:
            with open(f, "rb") as fh:
                head = fh.read(0x400)
            if head[:2] != b"MZ" or len(head) < 0x40:
                continue
            lfa = u32(head, 0x3C)
            with open(f, "rb") as fh:
                fh.seek(lfa)
                if fh.read(2) != b"NE":
                    continue
            mm = Module(f)
            b = mm.b
            ne = u32(b, 0x3C)
            modname = cstr_pas(b, ne + u16(b, ne + 0x26))
            if modname and modname not in NE_EXPORTS:
                NE_EXPORTS[modname] = {o: n for n, o in mm.exports}
                NE_EXPORTS[modname].setdefault(0, modname)
        except (OSError, struct.error, IndexError, ValueError):
            pass
    out = sys.stdout
    for f in sorted(files):
        scan(f, mui_index, out, args)


if __name__ == "__main__":
    main()
