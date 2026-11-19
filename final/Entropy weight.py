"""
Entropy weights (Shannon entropy method)
Project: A Multi-Criteria Decision Framework for Ranking AIS Solutions in IoT Security
Team: Aila Rainelle Medina, Rohan Bhandari, Saroj Dahal

Run on its own to print the weights step by step:
       python "Entropy weight.py"
       python "Entropy weight.py" other_data.xlsx
The ranking script "PROMETHEE I-Entropy method.py" and "PROMETHEE II-Entropy method.py" load entropy_weights() from this file.
Entropy is objective: rare properties (unevenly spread values) get more weight.
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


def entropy_weights(X, details=False):
    n = len(X)                                # number of alternatives

    # Step 1: share of each alternative in each criterion, p = x / column total
    P = (X / X.sum().replace(0, np.nan)).fillna(0)   # e.g. a property 3 alternatives have -> each gets p = 1/3
    show("Entropy Step 1: shares p = x / sum(x)", P)

    # Step 2: p * ln(p) for every cell; 0 * ln(0) is taken as 0 (its limit)
    plnp = P.apply(lambda col: np.where(col > 0, col * np.log(col.where(col > 0, 1)), 0))
    plnp = pd.DataFrame(plnp, index=X.index, columns=X.columns)   # keep the row and column labels
    show("Entropy Step 2: p * ln(p)  (0 * ln 0 taken as 0)", plnp)

    # Steps 3-5: entropy, divergence and weight
    k = 1 / np.log(n)                         # constant that scales entropy to the range 0..1
    E = -k * plnp.sum()                       # Step 3: entropy of each criterion; near 1 = values spread evenly
    div = 1 - E                               # Step 4: degree of divergence; high = criterion separates alternatives well
    w = div / div.sum()                       # Step 5: divide by the total so the weights add up to 1
    show(f"Entropy Steps 3-5: entropy E (k = 1/ln(n) = {k:.4f}), divergence 1 - E, weight",
         pd.DataFrame({"E": E, "1 - E": div, "weight": w}))
    if details:                               # the web frontend also asks for the working shown on its Weights tab
        return w, {"E": E, "div": div}
    return w                                  # weights labelled by criterion


if __name__ == "__main__":
    X = load_data(sys.argv[1] if len(sys.argv) > 1 else None)   # import the decision table
    show("Decision table (1 = present, 0 = absent)", X)
    w = entropy_weights(X)
    show("FINAL ENTROPY WEIGHTS", w.to_frame("weight"))
    print(f"\nSum of weights = {w.sum():.4f}")   # should always be 1.0000
