"""
PROMETHEE II ranking with Entropy weights (ranking 5 of 6)
Project: A Multi-Criteria Decision Framework for Ranking AIS Solutions in IoT Security
Team: Aila Rainelle Medina, Rohan Bhandari, Saroj Dahal

Run:   python "PROMETHEE II-Entropy method.py"
       python "PROMETHEE II-Entropy method.py" other_data.xlsx
Weights: loaded from "Entropy weight.py" (keep both files in the same folder).
Higher net flow = better.
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

DATA_FILE = "Table9_Data.xlsx"                    # Table 9 of Aldhaheri et al. (2020): 20 studies x 7 properties
DATA_SHEET = "Table 9 (ticks)"                    # sheet with the ✓ / ✗ / – table


def load_data(path=None):
    """Import the decision table from Excel. Only the input data comes from Excel;
    every calculation below is done in Python."""
    if path is None:                                             # no file given on the command line
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_FILE)  # use the Table 9 data file next to this script
    raw = pd.read_excel(path, sheet_name=DATA_SHEET, header=3, index_col=0)  # headers are on row 4; column A holds the alternative names
    raw = raw[raw.index.notna() & raw[CRITERIA].notna().all(axis=1)]          # keep only complete data rows (drops the key below the table)
    to_num = {"✓": 1, "✗": 0, "x": 0, "X": 0, "–": 0, "-": 0, 1: 1, 0: 0}   # tick = present (1); cross or "not reported" (–) = 0
    X = raw[CRITERIA].apply(lambda col: col.map(lambda v: to_num.get(v, v))).astype(float)  # convert every cell to 1.0 or 0.0
    X.index = X.index.astype(str)                                # study names as text (S01 ... S20)
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


def promethee2(X, w):
    alts = list(X.index)                      # alternative names
    n = len(alts)                             # number of alternatives

    # Steps 1-3: aggregated preference matrix pi(a, b)
    pi = pd.DataFrame(0.0, index=alts, columns=alts)   # start at 0; row = a, column = b
    for c in X.columns:                       # one criterion at a time
        # "Usual" preference function: a is preferred to b (P = 1) only if a scores higher than b
        P = pd.DataFrame([[1.0 if X.loc[a, c] > X.loc[b, c] else 0.0 for b in alts] for a in alts],
                         index=alts, columns=alts)
        pi += w[c] * P                        # add this criterion's preferences, weighted by its Entropy weight
    show("PROMETHEE Steps 1-3: aggregated preference matrix pi(a,b) = sum w(j) * P_j(a,b)", pi)

    # Steps 4-6: outranking flows and rank
    phi_plus = pi.sum(axis=1) / (n - 1)       # leaving flow Phi+: how strongly a outranks the others (row average)
    phi_minus = pi.sum(axis=0) / (n - 1)      # entering flow Phi-: how strongly the others outrank a (column average)
    net = phi_plus - phi_minus                # net flow Phi = Phi+ - Phi-; higher = better
    res = pd.DataFrame({"Phi+": phi_plus, "Phi-": phi_minus, "Phi net": net})
    res["Rank"] = res["Phi net"].round(10).rank(ascending=False, method="min").astype(int)   # highest net flow = rank 1; rounded so float noise does not split ties
    show("PROMETHEE Steps 4-6: leaving, entering and net flow, rank (higher net = better)", res)
    print(f"\nCheck: sum of net flows = {net.sum():.6f} (should be 0)")   # net flows always cancel out
    return res


if __name__ == "__main__":
    X = load_data(sys.argv[1] if len(sys.argv) > 1 else None)   # import the decision table from Excel
    show("Decision table (1 = present, 0 = absent)", X)
    w = entropy.entropy_weights(X)            # calculate the Entropy weights (from Entropy weight.py)
    show("Entropy weights", w)
    result = promethee2(X, w)                 # rank the alternatives
    show("FINAL RANKING: PROMETHEE II with Entropy weights", result.sort_values("Rank"))
