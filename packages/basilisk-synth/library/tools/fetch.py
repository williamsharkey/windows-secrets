#!/usr/bin/env python3
"""Fetch one public-domain / CC0 source file into library/sources-raw/<category>/ and print a
catalog stub (JSON) with its provenance. Refuses anything whose license is not PD or CC0.

  fetch.py freesound <category> <sound-id-or-url>
  fetch.py commons   <category> "File:Some name.ogg"
  fetch.py archive   <category> <identifier> <filename> [--start S --dur D]
  fetch.py url       <category> <direct-url> --author A --license L --proof URL --page URL

Downloads are untrusted data: this script only writes bytes to disk and runs ffprobe/ffmpeg on them.
Run with `python3 -I`.
"""
import argparse, hashlib, html, json, os, re, subprocess, sys, urllib.parse, urllib.request

LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(LIB, "sources-raw")
UA = "Mozilla/5.0 (compatible; pd-sample-library-collector/1.0)"
FFMPEG = os.path.expanduser("~/.local/bin/ffmpeg")
PD_WORDS = ("public domain", "cc0", "pd-", "pd ", "cc-zero", "publicdomain")


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "replace")


def save(category, name, data):
    d = os.path.join(RAW, category)
    os.makedirs(d, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:120]
    p = os.path.join(d, name)
    with open(p, "wb") as f:
        f.write(data)
    return p


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def probe(p):
    try:
        out = subprocess.run([FFMPEG.replace("ffmpeg", "ffprobe"), "-v", "error", "-show_entries",
                              "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout
        return round(float(out.strip()), 3)
    except Exception:
        return None


def stub(category, path, **kw):
    rel = os.path.relpath(path, RAW)
    d = dict(id=os.path.splitext(os.path.basename(path))[0].lower(), raw=rel, category=category,
             description=kw.pop("title", ""), tonal=False, start=0, dur=None,
             raw_duration=probe(path), raw_sha256=sha(path))
    d.update(kw)
    print(json.dumps(d, ensure_ascii=False))


def freesound(a):
    sid = re.findall(r"(\d+)/?$", a.ref.strip())[0]
    page = f"https://freesound.org/s/{sid}/"
    req = urllib.request.Request(page, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        final = r.geturl()
        h = r.read().decode("utf-8", "replace")
    lic = set(re.findall(r'creativecommons\.org/(licenses/[a-z-]+|publicdomain/zero)', h))
    if lic != {"publicdomain/zero"}:
        sys.exit(f"REFUSED freesound {sid}: license links {lic}")
    title = html.unescape(re.search(r'og:audio:title" content="([^"]*)"', h).group(1))
    artist = html.unescape(re.search(r'og:audio:artist" content="([^"]*)"', h).group(1))
    m = re.search(r'https://cdn\.freesound\.org/previews/[^"]*-hq\.ogg', h) or \
        re.search(r'https://cdn\.freesound\.org/previews/[^"]*-hq\.mp3', h)
    if not m:
        m = re.search(r'previews/(\d+)/(\d+_\d+)-lq\.mp3', h)
        url = f"https://cdn.freesound.org/previews/{m.group(1)}/{m.group(2)}-hq.mp3"
    else:
        url = m.group(0)
    data = get(url, True)
    p = save(a.category, f"fs_{sid}{os.path.splitext(url)[1]}", data)
    stub(a.category, p, title=title, source_url=final, download_url=url, author=artist,
         license="CC0-1.0", license_proof_url=final,
         note="Freesound HQ preview (original download requires login)")


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def commons(a):
    t = a.ref if a.ref.startswith("File:") else "File:" + a.ref
    q = urllib.parse.urlencode(dict(action="query", titles=t, prop="imageinfo",
                                    iiprop="url|extmetadata|size", format="json"))
    j = json.loads(get("https://commons.wikimedia.org/w/api.php?" + q))
    pg = next(iter(j["query"]["pages"].values()))
    ii = pg["imageinfo"][0]
    md = ii["extmetadata"]
    lic = strip_tags(md.get("LicenseShortName", {}).get("value"))
    licl = lic.lower()
    if not any(w in licl for w in PD_WORDS) or "by" in licl.replace("pd-", "").split():
        sys.exit(f"REFUSED commons {t}: {lic}")
    data = get(ii["url"], True)
    p = save(a.category, "wc_" + t[5:], data)
    stub(a.category, p, title=strip_tags(md.get("ImageDescription", {}).get("value"))[:200] or t[5:],
         source_url=ii["descriptionurl"], download_url=ii["url"],
         author=strip_tags(md.get("Artist", {}).get("value"))[:200] or "unknown",
         license=lic, license_proof_url=ii["descriptionurl"],
         license_url=md.get("LicenseUrl", {}).get("value"))


def archive(a):
    md = json.loads(get(f"https://archive.org/metadata/{a.ref}"))
    m = md["metadata"]
    lic = m.get("licenseurl", "") or ""
    rights = " ".join(m.get("rights", [])) if isinstance(m.get("rights"), list) else (m.get("rights") or "")
    ok = "publicdomain" in lic or (a.allow_pd_text and "public domain" in (rights + str(m.get("description", ""))).lower())
    if not ok:
        sys.exit(f"REFUSED archive {a.ref}: licenseurl={lic!r} rights={rights[:100]!r}")
    url = f"https://archive.org/download/{a.ref}/{urllib.parse.quote(a.file)}"
    base = re.sub(r"\.[^.]+$", "", a.file)
    if a.start is not None or a.dur is not None:
        # excerpt only: seek in the remote file, keep the audio as FLAC at its native rate
        out = os.path.join(RAW, a.category, re.sub(r"[^A-Za-z0-9._-]+", "_",
                           f"ia_{a.ref}_{base}_{int(a.start or 0)}s.flac")[:140])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        cmd = [FFMPEG, "-y", "-v", "error", "-ss", str(a.start or 0)]
        if a.dur:
            cmd += ["-t", str(a.dur)]
        # the static ffmpeg build cannot open https URLs, so download to a temp file first
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(a.file)[1]) as tmp:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=600) as r:
                for b in iter(lambda: r.read(1 << 20), b""):
                    tmp.write(b)
            tmp.flush()
            cmd += ["-i", tmp.name, "-vn", "-c:a", "flac", out]
            subprocess.run(cmd, check=True)
        p = out
    else:
        p = save(a.category, f"ia_{a.ref}_{a.file}", get(url, True))
    author = m.get("creator") or m.get("publisher") or "unknown"
    if isinstance(author, list):
        author = "; ".join(author)
    title = m.get("title") or a.ref
    if isinstance(title, list):
        title = title[0]
    stub(a.category, p, title=f"{title} ({a.file})", source_url=f"https://archive.org/details/{a.ref}",
         download_url=url, author=author, license=("Public Domain Mark 1.0" if "mark" in lic else
         "CC0-1.0" if "zero" in lic else "Public domain"), license_proof_url=lic or f"https://archive.org/details/{a.ref}",
         excerpt_start=a.start, excerpt_dur=a.dur)


def url(a):
    data = get(a.ref, True)
    name = a.name or urllib.parse.unquote(os.path.basename(urllib.parse.urlparse(a.ref).path))
    p = save(a.category, (a.prefix or "") + name, data)
    stub(a.category, p, title=a.title or name, source_url=a.page or a.ref, download_url=a.ref,
         author=a.author, license=a.license, license_proof_url=a.proof)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["freesound", "commons", "archive", "url"])
    ap.add_argument("category")
    ap.add_argument("ref")
    ap.add_argument("file", nargs="?")
    ap.add_argument("--start", type=float)
    ap.add_argument("--dur", type=float)
    ap.add_argument("--allow-pd-text", action="store_true",
                    help="archive: accept an explicit 'public domain' statement in rights/description")
    for k in ("author", "license", "proof", "page", "title", "name", "prefix"):
        ap.add_argument("--" + k)
    a = ap.parse_args()
    globals()[a.kind](a)
