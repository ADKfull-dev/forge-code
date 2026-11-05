# -*- coding: utf-8 -*-
"""Vérifie toutes les solutions de référence du parcours contre leurs tests.

    python3 -m parcours.verifier                 # tous les défis, tous les langages
    python3 -m parcours.verifier fibo tri        # quelques défis
    python3 -m parcours.verifier -s 4 -l php     # un palier, un langage
    python3 -m parcours.verifier -f math -s 0    # un palier de la filière mathématique

Compile avec les mêmes options que Forge Code (C17 / C++20, -g, sans optimisation) et applique
la limite de temps de chaque défi. Code de sortie 1 si un test échoue.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

from . import CHALLENGES, cles, remplir, sauver_cache
from .base import SOL_LANGS

EXT = {"c": "main.c", "cpp": "main.cpp", "python": "main.py", "javascript": "main.js", "php": "main.php"}


def norm(t):
    return "\n".join(ln.rstrip() for ln in t.replace("\r\n", "\n").split("\n")).rstrip("\n")


def build(lang, d):
    src = os.path.join(d, EXT[lang])
    exe = os.path.join(d, "main")
    if lang == "c":
        cmd = ["gcc", "-std=c17", "-Wall", "-Wextra", "-g", src, "-o", exe, "-lm"]
    elif lang == "cpp":
        cmd = ["g++", "-std=c++20", "-Wall", "-Wextra", "-g", src, "-o", exe]
    elif lang == "php":
        cmd = ["php", "-l", src]
    elif lang == "javascript":
        cmd = ["node", "--check", src]
    else:
        cmd = [sys.executable, "-m", "py_compile", src]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    warn = r.stdout.strip() if lang in ("c", "cpp") and "warning" in r.stdout else ""
    run = {"c": [exe], "cpp": [exe], "python": [sys.executable, src], "javascript": ["node", src], "php": ["php", src]}[lang]
    return (r.returncode == 0, r.stdout, warn, run)


def constraints(c, lang):
    """Mêmes règles que le correcteur de Forge Code : lignes de code et motifs interdits."""
    src, lim = c["sol"][lang], c["limits"]
    com = "#" if lang == "python" else "//"
    n = sum(1 for ln in src.split("\n") if ln.strip() and not ln.strip().startswith(com))
    if lim.get("max_lines") and n > lim["max_lines"]:
        return f"{n} lignes > {lim['max_lines']}"
    for rx in (lim.get("banned") or {}).get("*", []) + (lim.get("banned") or {}).get(lang, []):
        m = re.search(rx, src)
        if m:
            return f"motif interdit « {m.group(0)} »"
    return ""


def check(c, lang, starter=False):
    if starter:
        c = dict(c, sol={lang: c["starter"][lang]}, limits=dict(c["limits"], banned={}, max_lines=0))
        r = check(c, lang)
        r.update(ok=not r["ok"] and not r["msg"].startswith("compilation"), msg="le code bogué de départ réussit tous les tests !" if r["ok"] else r["msg"], lang=lang + " (départ)")
        return r
    bad = constraints(c, lang)
    if bad:
        return {"id": c["id"], "lang": lang, "ok": False, "msg": "contrainte : " + bad}
    d = tempfile.mkdtemp(prefix="forge-verif-")
    try:
        with open(os.path.join(d, EXT[lang]), "w") as f:
            f.write(c["sol"][lang])
        ok, out, warn, run = build(lang, d)
        if not ok:
            return {"id": c["id"], "lang": lang, "ok": False, "msg": "compilation : " + out[-800:]}
        lim, worst, fails = c["limits"]["time"], 0.0, []
        for n, t in enumerate(c["tests"]):
            t0 = time.time()
            try:
                r = subprocess.run(run, cwd=d, input=t["in"] + "\n", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, errors="replace", timeout=lim * 3 + 1)
                secs = time.time() - t0
                got = r.stdout
            except subprocess.TimeoutExpired:
                secs, got, r = lim * 3 + 1, "", None
            worst = max(worst, secs / lim)
            if secs > lim:
                fails.append(f"test {n + 1} : trop lent ({secs:.2f} s > {lim} s)")
            elif norm(got) != norm(t["out"]):
                g, e = norm(got).split("\n"), norm(t["out"]).split("\n")
                k = next((i for i in range(max(len(g), len(e))) if (g[i] if i < len(g) else None) != (e[i] if i < len(e) else None)), 0)
                fails.append(f"test {n + 1} : ligne {k + 1} attendu {e[k] if k < len(e) else '(fin)'!r:.80} obtenu {g[k] if k < len(g) else '(fin)'!r:.80}"
                             + (f" · stderr {r.stderr.strip()[-300:]}" if r is not None and r.stderr.strip() else ""))
        return {"id": c["id"], "lang": lang, "ok": not fails, "msg": " ; ".join(fails[:3]), "worst": worst, "warn": warn}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="Vérifie les solutions de référence du parcours.")
    ap.add_argument("ids", nargs="*")
    ap.add_argument("-s", "--stage", type=int, action="append")
    ap.add_argument("-f", "--filiere", choices=("dev", "math"))
    ap.add_argument("-l", "--lang", action="append", choices=SOL_LANGS)
    ap.add_argument("-j", "--jobs", type=int, default=max(2, (os.cpu_count() or 4) - 1))
    a = ap.parse_args()
    chs = [c for c in CHALLENGES if (not a.ids or c["id"] in a.ids) and (not a.stage or c["stage"] in a.stage)
           and (not a.filiere or c["track"] == a.filiere)]
    langs = a.lang or SOL_LANGS
    t0 = time.time()
    with ThreadPoolExecutor(a.jobs) as ex:                 # sorties attendues calculées par la référence Python
        list(ex.map(lambda c: remplir(c, sauver=False), chs))
    sauver_cache(set().union(*(cles(c) for c in CHALLENGES)) if not a.ids and not a.stage and not a.filiere else None)
    print(f"sorties attendues prêtes ({time.time() - t0:.1f} s)")
    jobs = []
    for c in chs:
        miss = [l for l in SOL_LANGS if l not in c["sol"]]
        if miss:
            print(f"⚠ {c['id']} : pas de solution en {', '.join(miss)}")
        jobs += [(c, l, False) for l in langs if l in c["sol"]]
        jobs += [(c, l, True) for l in langs if l in c.get("starter", {})]
    t0 = time.time()
    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda j: check(*j), jobs))
    bad = [r for r in res if not r["ok"]]
    for r in res:
        if r.get("warn"):
            print(f"⚠ {r['id']} [{r['lang']}] avertissements :\n    " + "\n    ".join(r["warn"].splitlines()[:6]))
    for r in bad:
        print(f"✖ {r['id']} [{r['lang']}] {r['msg']}")
    slow = sorted((r for r in res if r["ok"] and r.get("worst", 0) > 0.5), key=lambda r: -r["worst"])[:8]
    for r in slow:
        print(f"⏱ {r['id']} [{r['lang']}] {r['worst'] * 100:.0f} % de la limite de temps")
    ids = {c["id"] for c in chs}
    print(f"\n{len(ids)} défis · {len(res)} solutions · {len(res) - len(bad)} OK · {len(bad)} en échec · {time.time() - t0:.1f} s")
    dup = [i for i in ids if sum(1 for c in CHALLENGES if c["id"] == i) > 1]
    if dup:
        print("✖ identifiants en double : " + ", ".join(dup))
    for c in chs:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", c["id"]):
            print(f"✖ identifiant invalide : {c['id']}")
    sys.exit(1 if bad or dup else 0)


if __name__ == "__main__":
    main()
