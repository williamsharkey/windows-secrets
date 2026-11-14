#!/usr/bin/env python3
"""Search helpers that print candidate PD/CC0 audio (one line each). Run with python3 -I.

  search.py freesound "water drip" [--page N] [--maxdur S]     CC0-filtered Freesound search
  search.py commons   "glockenspiel"  [--n 50]                  audio files on Wikimedia Commons + license
  search.py commonscat "Category:Glockenspiel"                  audio files in a Commons category + license
  search.py archive   'collection:prelinger AND subject:business' [--n 50]   items + licenseurl
  search.py iafiles   <identifier>                              file list of an archive.org item
"""
import argparse, html, json, re, sys, urllib.parse, urllib.request

UA = "Mozilla/5.0 (compatible; pd-sample-library-collector/1.0)"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def freesound(a):
    q = urllib.parse.urlencode({"q": a.q, "f": 'license:"Creative Commons 0"', "page": a.page,
                                "s": "Rating highest first" if a.rated else "Automatic by relevance"})
    h = get("https://freesound.org/search/?" + q)
    # each result block carries the sound id, title and duration
    for m in re.finditer(r'href="/people/([^/"]+)/sounds/(\d+)/"[^>]*title="([^"]*)"', h):
        print(f"{m.group(2)}\t{html.unescape(m.group(1))}\t{html.unescape(m.group(3))}")
    if not re.search(r'title="', h):
        seen = set()
        for m in re.finditer(r'href="/people/([^/"]+)/sounds/(\d+)/"', h):
            if m.group(2) not in seen:
                seen.add(m.group(2)); print(f"{m.group(2)}\t{m.group(1)}")


def _lic(titles):
    out = {}
    for i in range(0, len(titles), 40):
        q = urllib.parse.urlencode(dict(action="query", titles="|".join(titles[i:i + 40]), prop="imageinfo",
                                        iiprop="extmetadata|size", iiextmetadatafilter="LicenseShortName|Artist",
                                        format="json"))
        j = json.loads(get("https://commons.wikimedia.org/w/api.php?" + q))
        for p in j["query"]["pages"].values():
            ii = (p.get("imageinfo") or [{}])[0]
            md = ii.get("extmetadata", {})
            out[p["title"]] = (re.sub("<[^>]+>", "", md.get("LicenseShortName", {}).get("value", "?")),
                               ii.get("duration"), ii.get("size"))
    return out


def _print_commons(titles):
    for t, (lic, d, sz) in _lic(titles).items():
        print(f"{lic}\t{d and round(d, 1)}s\t{sz}\t{t}")


def commons(a):
    q = urllib.parse.urlencode(dict(action="query", list="search", srsearch=a.q + " filetype:audio",
                                    srnamespace=6, srlimit=a.n, format="json"))
    j = json.loads(get("https://commons.wikimedia.org/w/api.php?" + q))
    _print_commons([x["title"] for x in j["query"]["search"]])


def commonscat(a):
    titles, cont = [], {}
    while True:
        q = dict(action="query", list="categorymembers", cmtitle=a.q, cmtype="file|subcat", cmlimit=500, format="json")
        q.update(cont)
        j = json.loads(get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(q)))
        for x in j["query"]["categorymembers"]:
            if x["title"].startswith("Category:"):
                print(f"SUBCAT\t\t\t{x['title']}")
            elif re.search(r"\.(ogg|oga|wav|flac|mp3|opus|webm)$", x["title"], re.I):
                titles.append(x["title"])
        if "continue" not in j or len(titles) >= a.n:
            break
        cont = j["continue"]
    _print_commons(titles[:a.n])


def archive(a):
    q = urllib.parse.urlencode([("q", a.q), ("fl[]", "identifier"), ("fl[]", "title"), ("fl[]", "licenseurl"),
                                ("fl[]", "mediatype"), ("rows", a.n), ("output", "json")])
    j = json.loads(get("https://archive.org/advancedsearch.php?" + q))
    for d in j["response"]["docs"]:
        print(f"{d.get('licenseurl', '-')}\t{d.get('mediatype')}\t{d['identifier']}\t{str(d.get('title'))[:90]}")


def iafiles(a):
    j = json.loads(get(f"https://archive.org/metadata/{a.q}"))
    m = j["metadata"]
    print("licenseurl:", m.get("licenseurl"), "| rights:", str(m.get("rights"))[:200])
    for f in j["files"]:
        print(f"{f.get('format')}\t{f.get('size')}\t{f.get('length')}\t{f['name']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kind")
    ap.add_argument("q")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--rated", action="store_true")
    a = ap.parse_args()
    globals()[a.kind](a)
