"""
PROMETHEE I (partial) ranking with Entropy weights
Prototype for: A Multi-Criteria Decision Framework for Ranking AIS Solutions in IoT Security
Team: Aila Rainelle Medina, Rohan Bhandari, Saroj Dahal

Run:   python "PROMETHEE I-Entropy method.py"
       python "PROMETHEE I-Entropy method.py" other_data.xlsx
Weights: loaded from "Entropy weight.py" (keep both files in the same folder).
PROMETHEE I compares the leaving flow (Phi+) and entering flow (Phi-) separately.
It gives a PARTIAL ranking: some pairs are "incomparable" when the two flows disagree.
PROMETHEE II (the other file) combines them into the net flow for a COMPLETE ranking.
Needs: numpy, pandas, openpyxl (see README.md for setup)
"""
import sys                 # read the optional data-file name from the command line
import os                  # build file paths relative to this script's folder
import numpy as np         # numeric arrays and maths (sqrt, log, products)
import pandas as pd        # tables with labelled rows (alternatives) and columns (criteria)

pd.set_option("display.width", 140)     # print wide tables on one line
pd.set_option("display.precision", 4)   # show 4 decimal places

# The seven AIS properties from Table 9 of Aldhaheri et al. (2020), used as criteria.
# AD = Adaptive, SL = Self-learning, RES = Resiliency, DEF = Response/defense,
# ST = Self-tolerance, LH = Lightweight, DS = Distributed. All are benefit criteria.
CRITERIA = ["AD", "SL", "RES", "DEF", "ST", "LH", "DS"]

DATA_FILE = "Sample_Table9_Prototype_Data.xlsx"   # prototype test data (laid out like Table 9)
DATA_SHEET = "Sample Table 9 (ticks)"             # sheet with the ✓ / ✗ table


def load_data(path=None):
    """Import the decision table from Excel. Only the input data comes from Excel;
    every calculation below is done in Python."""
    if path is None:                                             # no file given on the command line
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_FILE)  # use the test data next to this script
    raw = pd.read_excel(path, sheet_name=DATA_SHEET, header=3, index_col=0)  # headers are on row 4; column A holds the alternative names
    raw = raw[raw.index.notna() & raw[CRITERIA].notna().all(axis=1)]          # keep only complete data rows (drops the key below the table)
    to_num = {"✓": 1, "✗": 0, "x": 0, "X": 0, "–": 0, "-": 0, 1: 1, 0: 0}   # tick = present (1); cross or "not reported" (–) = 0
    X = raw[CRITERIA].apply(lambda col: col.map(lambda v: to_num.get(v, v))).astype(float)  # convert every cell to 1.0 or 0.0
    X.index = X.index.astype(str)                                # alternative names as text (A, B, ... or S01, S02, ...)
    print(f"Imported {len(X)} alternatives x {len(CRITERIA)} criteria from {os.path.basename(path)} [{DATA_SHEET}]")
    return X                                                     # rows = alternatives, columns = criteria


def show(title, obj):
    """Print a labelled table so every step of the method can be followed."""
    print(f"\n=== {title} ===")
    print(obj)


import importlib.util      # lets us load a .py file whose name contains spaces


def load_weight_module(filename):
    """Load a weight script that sits in the same folder as this one.
    A normal 'import' cannot handle spaces in file names, so the file is loaded by path."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)        # full path to the weight file
    spec = importlib.util.spec_from_file_location(filename.replace(" ", "_")[:-3], path)  # describe the module to load
    module = importlib.util.module_from_spec(spec)                                   # create an empty module
    spec.loader.exec_module(module)                                                  # run the weight file to fill it
    return module


entropy = load_weight_module("Entropy weight.py")   # gives access to entropy.entropy_weights()


def flows(X, w):
    """Steps 1-3 (same as PROMETHEE II): preference matrix and the two outranking flows."""
    alts = list(X.index)
    n = len(alts)
    pi = pd.DataFrame(0.0, index=alts, columns=alts)          # aggregated preference pi(a,b); row = a, column = b
    for c in X.columns:
        # usual preference function: a is preferred to b on criterion c only if a scores higher
        P = pd.DataFrame([[1.0 if X.loc[a, c] > X.loc[b, c] else 0.0 for b in alts] for a in alts],
                         index=alts, columns=alts)
        pi += w[c] * P                                         # weight it by the Entropy weight and add
    phi_plus = pi.sum(axis=1) / (n - 1)                        # leaving flow: strength of a over the others
    phi_minus = pi.sum(axis=0) / (n - 1)                       # entering flow: weakness of a (others over a)
    return pi, phi_plus, phi_minus


def promethee1(X, w, eps=1e-12):
    pi, phi_plus, phi_minus = flows(X, w)
    show("PROMETHEE I Steps 1-3: aggregated preference matrix pi(a,b)", pi)
    show("PROMETHEE I Step 4: leaving flow Phi+ (higher = better) and entering flow Phi- (lower = better)",
         pd.DataFrame({"Phi+": phi_plus, "Phi-": phi_minus}))

    # Step 5: compare every pair on BOTH flows
    #   a P b (a outranks b): a is at least as good on both flows and strictly better on at least one
    #   a I b (indifferent): equal on both flows
    #   a R b (incomparable): a is better on one flow but worse on the other
    alts = list(X.index)
    rel = pd.DataFrame("", index=alts, columns=alts)
    for a in alts:
        for b in alts:
            if a == b:
                rel.loc[a, b] = "-"; continue
            p_ge = phi_plus[a] >= phi_plus[b] - eps            # a's leaving flow is not lower
            m_le = phi_minus[a] <= phi_minus[b] + eps          # a's entering flow is not higher
            p_eq = abs(phi_plus[a] - phi_plus[b]) <= eps
            m_eq = abs(phi_minus[a] - phi_minus[b]) <= eps
            if p_eq and m_eq:
                rel.loc[a, b] = "I"                            # indifferent
            elif p_ge and m_le:
                rel.loc[a, b] = "P"                            # a outranks b
            elif (phi_plus[a] <= phi_plus[b] + eps) and (phi_minus[a] >= phi_minus[b] - eps):
                rel.loc[a, b] = "p"                            # b outranks a (shown lower-case from a's row)
            else:
                rel.loc[a, b] = "R"                            # incomparable
    show("PROMETHEE I Step 5: relation of row to column  (P = outranks, p = is outranked by, I = indifferent, R = incomparable)", rel)

    # Step 6: partial ranking in levels. Level 1 = alternatives no one outranks; remove them and repeat.
    remaining, level, levels = set(alts), 1, {}
    while remaining:
        top = [a for a in remaining if not any(rel.loc[b, a] == "P" for b in remaining if b != a)]
        for a in top:
            levels[a] = level
        remaining -= set(top)
        level += 1
    res = pd.DataFrame({
        "Phi+": phi_plus, "Phi-": phi_minus,
        "outranks": [(rel.loc[a] == "P").sum() for a in alts],           # how many it beats on both flows
        "outranked by": [(rel.loc[a] == "p").sum() for a in alts],       # how many beat it on both flows
        "incomparable": [(rel.loc[a] == "R").sum() for a in alts],       # flows disagree
        "Level": [levels[a] for a in alts],                               # partial rank (1 = best level)
    }, index=alts)
    show("PROMETHEE I Step 6: partial ranking (alternatives on the same level are not ordered against each other)", res)
    return res, rel


if __name__ == "__main__":
    X = load_data(sys.argv[1] if len(sys.argv) > 1 else None)   # import the decision table from Excel
    show("Decision table (1 = present, 0 = absent)", X)
    w = entropy.entropy_weights(X)            # calculate the Entropy weights (from Entropy weight.py)
    show("Entropy weights", w)
    result, rel = promethee1(X, w)
    show("FINAL PARTIAL RANKING: PROMETHEE I with Entropy weights", result.sort_values(["Level", "Phi+"], ascending=[True, False]))
    incomp = [(a, b) for i, a in enumerate(rel.index) for b in rel.index[i + 1:] if rel.loc[a, b] == "R"]
    print("\nIncomparable pairs:", ", ".join(f"{a}-{b}" for a, b in incomp) if incomp else "none")
