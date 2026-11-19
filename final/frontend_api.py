"""
Calculation service for the web frontend.

The page (index.html) does no maths. It sends the decision table and the VIKOR v setting to
run_frontend.py, which calls the functions below. These functions run the SAME code as the
Python scripts (they import the script files) and send the results back as JSON for display.

The sensitivity analysis takes about a minute, so it runs in a separate Python process:
the page stays usable while it works.

You do not run this file yourself; run_frontend.py uses it.
"""
import contextlib
import importlib.util
import io
import json
import os
import threading
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))   # folder that holds all the project files


def load_module(filename):
    """Load one of the project .py files (names contain spaces, so a normal import cannot be used)."""
    spec = importlib.util.spec_from_file_location(filename.replace(" ", "_")[:-3], os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def quiet(func, *args, **kwargs):
    """Run a function from a script without printing its step-by-step tables in the terminal."""
    with contextlib.redirect_stdout(io.StringIO()):
        return func(*args, **kwargs)


# The script files, loaded once when the server starts
with contextlib.redirect_stdout(io.StringIO()):
    final_m = load_module("Final ranking.py")       # six_rankings(), final_ranking(), labels
    sens_m = load_module("Sensitivity analysis.py") # sensitivity(), sensitivity_promethee1(), decide_best()
topsis_m, vikor_m, prom1_m, prom2_m = final_m.topsis_m, final_m.vikor_m, final_m.prom1_m, final_m.prom2_m
ahp_m, critic_m, entropy_m = topsis_m.ahp, vikor_m.critic, prom1_m.entropy

CRITERIA = ahp_m.CRITERIA                          # ["AD", "SL", "RES", "DEF", "ST", "LH", "DS"]
DATA_FILE = os.path.join(HERE, ahp_m.DATA_FILE)    # Table9_Data.xlsx in this folder
LOCK = threading.Lock()                            # one calculation at a time in the server process
RANKINGS = final_m.RANKINGS                        # the six ranking names
SHORT = final_m.SHORT                              # short labels used in tables


# ------------------------------------------------------------------
# Small helpers to turn numpy / pandas values into plain JSON values
# ------------------------------------------------------------------
def num(x):
    """One number as a plain float, or None if it is missing or infinite."""
    return None if x is None or pd.isna(x) or (isinstance(x, float) and np.isinf(x)) else float(x)


def nums(values):
    return [num(x) for x in values]


def ints(values):
    return [int(x) for x in values]


# ------------------------------------------------------------------
# Reading the Excel data file (with the scripts' own load_data)
# ------------------------------------------------------------------
def read_table(path):
    """Read a decision table laid out like Table9_Data.xlsx (headers on row 4, ✓ / ✗ / – values)."""
    sheets = pd.ExcelFile(path).sheet_names
    sheet = (next((s for s in sheets if "tick" in s.lower()), None)       # prefer the ✓ / ✗ sheet
             or next((s for s in sheets if "0-1" in s), None) or sheets[0])
    with LOCK:
        ahp_m.DATA_SHEET = sheet                                          # load_data() reads the sheet named here
        X = quiet(ahp_m.load_data, path)                                  # ✓ -> 1, ✗ / – -> 0
    raw = pd.read_excel(path, sheet_name=sheet, header=3, index_col=0)   # read again for the text columns
    raw = raw[raw.index.notna()]
    raw.index = raw.index.astype(str)
    text = lambda col, name: "" if col not in raw.columns or pd.isna(raw[col].get(name)) else str(raw[col].get(name))
    rows = [{"id": name, "alg": text("AIS algorithm", name), "family": text("AIS family", name),
             "v": ints(X.loc[name])} for name in X.index]
    return {"data": rows, "sheet": sheet}


# ------------------------------------------------------------------
# Checking the table and building the matrix
# ------------------------------------------------------------------
def to_matrix(payload):
    """Turn the table the page sends into the DataFrame the scripts expect (rows = studies, columns = criteria)."""
    rows = payload["data"]
    X = pd.DataFrame([[float(x) for x in r["v"]] for r in rows], index=[str(r["id"]) for r in rows], columns=CRITERIA)
    X.index.name = "Study"
    return X


def problems(X):
    """Reasons the methods cannot run on this table (empty list = ready)."""
    out = []
    if len(X) < 3:
        out.append("At least 3 alternatives are needed.")
    if X.index.duplicated().any():
        out.append("Two alternatives have the same name; give each one a different name.")
    for c in CRITERIA:
        if X[c].nunique() < 2:                                  # all 1s or all 0s: CRITIC and Entropy cannot use it
            out.append(f"{c} has the same value for every alternative, so CRITIC and Entropy cannot use it.")
    return out


# ------------------------------------------------------------------
# Main results: weights, the six rankings and the final ranking
# ------------------------------------------------------------------
def compute(payload):
    X = to_matrix(payload)
    found = problems(X)
    if found:
        return {"problems": found}
    v = float(payload.get("v", 0.5))                         # VIKOR strategy weight from the slider
    names = list(X.index)

    with LOCK:
        # Weights, with the working shown on the Weights tab
        ahp = []
        topsis = {}
        for e in ahp_m.EXPERTS:                               # AHP 1 (Claude), AHP 2 (ChatGPT), AHP 3 (Gemini)
            w, d = quiet(ahp_m.ahp_weights, e, details=True)
            ahp.append({"label": ahp_m.AHP_LABEL[e], "expert": e, "w": nums(w), "A": [nums(r) for r in d["matrix"]],
                        "gm": nums(d["geo_mean"]), "CR": num(d["CR"])})
            t = quiet(topsis_m.topsis, X, w)                  # TOPSIS-AHP method.py
            topsis[f"TOPSIS-{ahp_m.AHP_LABEL[e]}"] = {"dp": nums(t["D+"]), "dm": nums(t["D-"])}
        w_critic, cd = quiet(critic_m.critic_weights, X, details=True)
        w_entropy, ed = quiet(entropy_m.entropy_weights, X, details=True)
        vk, vd = quiet(vikor_m.vikor, X, w_critic, v, details=True)
        p1, rel = quiet(prom1_m.promethee1, X, w_entropy)
        p2 = quiet(prom2_m.promethee2, X, w_entropy)

        # The six rankings and the final ranking, exactly as "Final ranking.py" calculates them
        ranks, _, scores, _ = final_m.six_rankings(X, v)
        avg, final = final_m.final_ranking(ranks)

    incomparable = [[a, b] for a in range(len(names)) for b in range(a + 1, len(names)) if rel.iloc[a, b] == "R"]
    score_name = {"PROMETHEE I-Entropy": "level", "PROMETHEE II-Entropy": "Φ net", "VIKOR-CRITIC": "Q"}
    rankings = [{"name": r, "short": SHORT[r], "rank": ints(ranks[r]), "score": nums(scores[r]),
                 "scoreName": score_name.get(r, "CC"), "higher": r not in ("VIKOR-CRITIC", "PROMETHEE I-Entropy")}
                for r in RANKINGS]
    return {
        "problems": [],
        "names": names,
        "rankings": rankings,
        "ahp": ahp,
        "critic": {"w": nums(w_critic), "sd": nums(cd["sigma"]), "conflict": nums(cd["conflict"]), "C": nums(cd["info"])},
        "entropy": {"w": nums(w_entropy), "E": nums(ed["E"]), "div": nums(ed["div"])},
        "topsis": topsis,
        "vikor": {"S": nums(vk["S"]), "R": nums(vk["R"]), "Q": nums(vk["Q"]), "c1": vd["c1"], "c2": vd["c2"],
                  "best": names.index(vd["best"]), "compromise": [names.index(x) for x in vd["compromise"]]},
        "p1": {"level": ints(p1["Level"]), "plus": nums(p1["Phi+"]), "minus": nums(p1["Phi-"]),
               "outranks": ints(p1["outranks"]), "outrankedBy": ints(p1["outranked by"]),
               "incomparable": ints(p1["incomparable"]), "rel": rel.values.tolist(), "incomp": incomparable},
        "p2": {"plus": nums(p2["Phi+"]), "minus": nums(p2["Phi-"]), "net": nums(p2["Phi net"])},
        "avg": nums(avg), "fin": ints(final),
        "agree": [nums(r) for r in ranks.corr(method="spearman").fillna(0).values],
    }


# ------------------------------------------------------------------
# Sensitivity analysis (runs in its own process; see run_sensitivity)
# ------------------------------------------------------------------
def pack_sensitivity(result):
    """Turn the tables returned by the sensitivity functions into what the page displays."""
    res, delta, pct, summary, ahead, label = result
    tops = res["top"].split(" = ")
    rows = [{"pair": pair, "top": any(pair.startswith(t + " - ") for t in tops),
             "cells": [None if pct.loc[pair, c] == "N/F" else num(pct.loc[pair, c]) for c in CRITERIA]}
            for pair in pct.index]
    crit = [{"feasible": int(summary.loc[c, "feasible reversals"]),
             "PT": num(summary.loc[c, "PT: min |delta'| with top (%)"]),
             "PA": num(summary.loc[c, "PA: min |delta'| any pair (%)"]),
             "paPair": None if summary.loc[c, "pair at PA"] == "-" else str(summary.loc[c, "pair at PA"])} for c in CRITERIA]
    pt_k = CRITERIA.index(res["PT criterion"]) if res["PT criterion"] in CRITERIA else None
    pa_k = CRITERIA.index(res["PA criterion"]) if res["PA criterion"] in CRITERIA else None
    return {"top": res["top"], "rows": rows, "crit": crit, "ptK": pt_k, "paK": pa_k}


def sensitivity_worker(payload_json):
    """All six sensitivity analyses plus the decision. Called in a separate process."""
    payload = json.loads(payload_json)
    Xdf = to_matrix(payload)
    found = problems(Xdf)
    if found:
        return {"problems": found}
    v = float(payload.get("v", 0.5))
    names, X, crit = list(Xdf.index), Xdf.values, CRITERIA

    def vikor_q(M, w):                                      # VIKOR Q with the v from the slider
        return sens_m.vikor_scores(M, w, v)

    with contextlib.redirect_stdout(io.StringIO()):          # this process prints nothing
        results = {}
        for e in ahp_m.EXPERTS:                              # 1-3: TOPSIS with each expert's AHP weights
            w = ahp_m.ahp_weights(e).values
            name = f"TOPSIS-{ahp_m.AHP_LABEL[e]}"
            results[name] = sens_m.sensitivity(name, X, names, w, crit, sens_m.topsis_scores(X, w), True,
                                               search=(sens_m.topsis_scores, X, w))
        w_entropy = entropy_m.entropy_weights(Xdf).values    # 4-5: PROMETHEE I and II with Entropy weights
        results["PROMETHEE I-Entropy"] = sens_m.sensitivity_promethee1("PROMETHEE I-Entropy", X, names, w_entropy,
                                                                       crit, prom1_m, Xdf)
        a = sens_m.unicriterion_flows(X); P = a @ w_entropy
        results["PROMETHEE II-Entropy"] = sens_m.sensitivity("PROMETHEE II-Entropy", X, names, w_entropy, crit, P, True,
                                                             closed_form=(P, a))
        w_critic = critic_m.critic_weights(Xdf).values       # 6: VIKOR with CRITIC weights
        results["VIKOR-CRITIC"] = sens_m.sensitivity("VIKOR-CRITIC", X, names, w_critic, crit, vikor_q(X, w_critic),
                                                     False, search=(vikor_q, X, w_critic))
        # Decision: which contender holds its lead (same as the end of "Sensitivity analysis.py")
        ranks, _, _, _ = final_m.six_rankings(Xdf, v)
        avg, final = final_m.final_ranking(ranks)
        _, label = sens_m.group_identical(X, names)
        label_of = {names[i]: label[next(r for r in label if tuple(X[r]) == tuple(X[i]))] for i in range(len(names))}
        table, contenders, h2h = sens_m.decide_best(results, avg, label_of)

    decision = [{"contender": c, "avg": num(table.loc[c, "average rank"]), "firsts": int(table.loc[c, "1st in (of 6)"]),
                 "wins": int(table.loc[c, "leads (wins)"]), "behind": int(table.loc[c, "behind"]),
                 "level": int(table.loc[c, "level/incomparable"]),
                 "weakest": None if table.loc[c, "weakest lead (%)"] == "N/F" else num(table.loc[c, "weakest lead (%)"])}
                for c in table.index]
    return {"problems": [], "methods": {r: pack_sensitivity(results[r]) for r in RANKINGS},
            "decision": decision, "best": table.index[0], "contenders": contenders,
            "h2h": [{"pair": f"{c} vs {r}", "cells": [h2h[(m, c, r)] for m in RANKINGS]}
                    for c in contenders for r in contenders if r != c],
            "comparisons": len(RANKINGS) * (len(contenders) - 1)}


_pool, _cache, _cache_lock = None, {}, threading.Lock()


def run_sensitivity(payload):
    """Run the sensitivity analysis in a separate process (cached for the same table and v)."""
    global _pool
    key = json.dumps({"data": [[r["id"], r["v"]] for r in payload["data"]], "v": payload.get("v", 0.5)})
    with _cache_lock:
        if key in _cache:
            return _cache[key]
        if _pool is None:
            _pool = ProcessPoolExecutor(max_workers=1)      # one background worker process
    result = _pool.submit(sensitivity_worker, json.dumps(payload)).result()
    with _cache_lock:
        _cache[key] = result
        while len(_cache) > 20:                              # keep only recent results
            _cache.pop(next(iter(_cache)))
    return result
