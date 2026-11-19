"""
VIKOR ranking with CRITIC weights (ranking 6 of 6)
Project: A Multi-Criteria Decision Framework for Ranking AIS Solutions in IoT Security
Team: Aila Rainelle Medina, Rohan Bhandari, Saroj Dahal

Run:   python "VIKOR-CRITIC method.py"
       python "VIKOR-CRITIC method.py" other_data.xlsx
Weights: loaded from "CRITIC weight.py" (keep both files in the same folder).
Lower Q = better.
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


critic = load_weight_module("CRITIC weight.py")   # gives access to critic.critic_weights()

V_STRATEGY = 0.5   # v: weight on group utility (S) versus individual regret (R); 0.5 = balanced "consensus"


def vikor(X, w, v=V_STRATEGY, details=False):
    # Step 1: best (f*) and worst (f-) value of each criterion
    f_best, f_worst = X.max(), X.min()        # benefit criteria: best = max, worst = min
    show("VIKOR Step 1: best f* and worst f-", pd.DataFrame({"f*": f_best, "f-": f_worst}).T)

    # Step 2: normalised distance from the best, d = (f* - x) / (f* - f-)
    d = ((f_best - X) / (f_best - f_worst).replace(0, np.nan)).fillna(0)   # 0 = has the best value, 1 = has the worst
    show("VIKOR Step 2: normalised distance from best", d)

    # Step 3: weight each distance by its CRITIC weight
    wd = d * w
    show("VIKOR Step 3: weighted distance w * d", wd)

    # Steps 4-6: S, R, Q and ranks
    S = wd.sum(axis=1)                        # S = group utility: total weighted shortfall (lower = better overall)
    R = wd.max(axis=1)                        # R = individual regret: the single worst shortfall (lower = better)
    s_part = (S - S.min()) / (S.max() - S.min()) if S.max() > S.min() else S * 0   # rescale S to 0..1
    r_part = (R - R.min()) / (R.max() - R.min()) if R.max() > R.min() else R * 0   # rescale R to 0..1
    Q = v * s_part + (1 - v) * r_part         # Q = compromise index mixing S and R; lower = better
    res = pd.DataFrame({"S": S, "R": R, "Q": Q})
    res["Rank S"] = res["S"].round(10).rank(method="min").astype(int)   # rank by S (1 = lowest); rounded so float noise does not split ties
    res["Rank R"] = res["R"].round(10).rank(method="min").astype(int)   # rank by R (1 = lowest)
    res["Rank Q"] = res["Q"].round(10).rank(method="min").astype(int)   # final VIKOR rank (1 = lowest Q)
    show(f"VIKOR Steps 4-6: S, R, Q (v = {v}) and ranks (lower Q = better)", res)

    # Compromise conditions: is the best-by-Q alternative a clear winner?
    n = len(X)
    dq = 1 / (n - 1)                          # DQ = minimum gap needed between first and second place
    q_sorted = res["Q"].sort_values()         # alternatives from lowest to highest Q
    best = q_sorted.index[0]                  # alternative with the lowest Q
    c1 = q_sorted.iloc[1] - q_sorted.iloc[0] >= dq                          # C1 acceptable advantage
    c2 = res.loc[best, "Rank S"] == 1 or res.loc[best, "Rank R"] == 1      # C2 acceptable stability
    close = list(res.index[res["Q"] - q_sorted.iloc[0] < dq])   # alternatives too close to the best to separate
    print(f"\nCompromise check: DQ = {dq:.4f}")
    print(f"  C1 acceptable advantage (Q2 - Q1 >= DQ): {'met' if c1 else 'not met'}")
    print(f"  C2 acceptable stability (best by S or R): {'met' if c2 else 'not met'}")
    if c1 and c2:
        print(f"  -> {best} is the compromise solution")
    else:
        print(f"  -> compromise set: {close}")
    if details:                               # the web frontend also shows the compromise check
        return res, {"DQ": dq, "c1": bool(c1), "c2": bool(c2), "best": best,
                     "compromise": [best] if (c1 and c2) else close}
    return res


if __name__ == "__main__":
    X = load_data(sys.argv[1] if len(sys.argv) > 1 else None)   # import the decision table from Excel
    show("Decision table (1 = present, 0 = absent)", X)
    w = critic.critic_weights(X)              # calculate the CRITIC weights (from CRITIC weight.py)
    show("CRITIC weights", w)
    result = vikor(X, w)                      # rank the alternatives
    show("FINAL RANKING: VIKOR with CRITIC weights", result.sort_values("Rank Q"))
