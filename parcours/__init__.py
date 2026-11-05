# -*- coding: utf-8 -*-
"""Parcours de progression de Forge Code : deux filières de 12 paliers et 13 grades, un défi = des tests entrée → sortie.

Chaque palier vit dans son module et expose une liste DEFIS : p00_bases.py … p11_projets.py pour la filière
« dev », m00_… à m11_… pour la filière « math » (algorithmique purement mathématique).
Certaines sorties attendues sont calculées avec la solution Python de référence : remplir(défi) les
complète à la demande (cache dans attendus.json.gz, régénéré par le vérificateur).
Vérification des solutions de référence : python3 -m parcours.verifier
"""
import gzip
import hashlib
import importlib
import json
import pkgutil
import subprocess
import sys
import threading
from pathlib import Path

from .base import LEVELS, SOL_LANGS, STAGE_THEMES, STAGES, TRACKS  # noqa: F401

CHALLENGES = []
for _m in sorted(m.name for m in pkgutil.iter_modules(__path__) if m.name[:1] in "pm" and m.name[1:3].isdigit()):
    for _c in importlib.import_module(f"{__name__}.{_m}").DEFIS:
        _c["track"] = "math" if _m.startswith("m") else "dev"
        CHALLENGES.append(_c)
CH_BY_ID = {c["id"]: c for c in CHALLENGES}

_CACHE_FILE = Path(__file__).with_name("attendus.json.gz")
_cache = None
_verrou = threading.Lock()


def _cle(src, inp):
    return hashlib.sha1((src + "\0" + inp).encode()).hexdigest()


def _charger():
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(gzip.decompress(_CACHE_FILE.read_bytes()))
        except (OSError, ValueError):
            _cache = {}
    return _cache


def sauver_cache(garder=None):
    """Écrit le cache ; « garder » (ensemble de clés) permet d'en retirer les entrées devenues inutiles."""
    cache = _charger()
    if garder is not None:
        for k in [k for k in cache if k not in garder]:
            del cache[k]
    try:
        tmp = _CACHE_FILE.with_suffix(".tmp")
        tmp.write_bytes(gzip.compress(json.dumps(cache, ensure_ascii=False, sort_keys=True).encode(), 9))
        tmp.replace(_CACHE_FILE)
    except OSError:
        pass                                    # installation en lecture seule : on recalculera


def _executer(src, inp):
    r = subprocess.run([sys.executable, "-c", src], input=inp + "\n", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, errors="replace", timeout=120)
    if r.returncode != 0:
        raise RuntimeError("La solution de référence a échoué : " + r.stderr[-400:])
    return r.stdout.rstrip("\n")


def entrees(c):
    """Fabrique les entrées des tests générés (une seule fois)."""
    for t in c["tests"]:
        if t["in"] is None:
            t["in"] = t["gen"]()
    return c


def cles(c):
    entrees(c)
    return {_cle(c["sol"]["python"], t["in"]) for t in c["tests"] if t.get("auto")}


def remplir(c, visibles=False, sauver=True):
    """Complète les sorties attendues manquantes d'un défi (seulement les tests visibles si « visibles »)."""
    todo = [t for t in c["tests"] if t["out"] is None and (not visibles or not t["hidden"])]
    if not todo:
        return c
    with _verrou:
        for t in todo:
            if t["in"] is None:
                t["in"] = t["gen"]()
        cache, neuf = _charger(), False
        for t in todo:
            k = _cle(c["sol"]["python"], t["in"])
            if k not in cache:
                cache[k] = _executer(c["sol"]["python"], t["in"])
                neuf = True
            t["out"] = cache[k]
        if neuf and sauver:
            sauver_cache()
    return c
