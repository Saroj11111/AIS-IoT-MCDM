"""
AHP weights (Analytic Hierarchy Process)
Prototype for: A Multi-Criteria Decision Framework for Ranking AIS Solutions in IoT Security
Team: Aila Rainelle Medina, Rohan Bhandari, Saroj Dahal

Run on its own to print the weights step by step:
       python "AHP weight.py"
The ranking script "TOPSIS-AHP method.py" loads ahp_weights() from this file.
AHP weights come from judgments (AHP_LEVELS below), not from the data table.
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


# ------------------------------------------------------------------
# AHP INPUT: importance level of each criterion (team assumption)
# Higher number = more important. The pairwise comparison for criteria i and j is
#   a(i,j) = 1 + (level i - level j)          if level i >= level j
#   a(i,j) = 1 / (1 + (level j - level i))    otherwise (the reciprocal)
# Edit these numbers to use your own judgments.
# ------------------------------------------------------------------
AHP_LEVELS = {"AD": 3, "SL": 2, "RES": 3, "DEF": 4, "ST": 3, "LH": 5, "DS": 4}

# Saaty's Random Index (RI) for a matrix of size n, used in the consistency check.
RI = {1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def ahp_weights(levels):
    crit = list(levels)                       # criterion codes in a fixed order
    m = len(crit)                             # number of criteria (7)

    # Step 1: pairwise comparison matrix A (m x m)
    A = np.ones((m, m))                       # start with 1s (diagonal = a criterion compared with itself)
    for i, a in enumerate(crit):              # row criterion
        for j, b in enumerate(crit):          # column criterion
            d = levels[a] - levels[b]         # how many levels more important the row criterion is
            A[i, j] = 1 + d if d >= 0 else 1 / (1 - d)   # e.g. LH (5) vs SL (2): 1 + 3 = 4; SL vs LH: 1/4
    show("AHP Step 1: pairwise comparison matrix", pd.DataFrame(A, crit, crit))

    # Steps 2-4: geometric-mean method
    row_product = A.prod(axis=1)              # Step 2: multiply all values across each row
    geo_mean = row_product ** (1 / m)         # Step 3: m-th root of the row product = geometric mean
    w = geo_mean / geo_mean.sum()             # Step 4: divide by the total so the weights add up to 1
    show("AHP Steps 2-4: row product, geometric mean, weight",
         pd.DataFrame({"row product": row_product, "geometric mean": geo_mean, "weight": w}, index=crit))

    # Step 5: consistency check (are the judgments free of contradictions?)
    Aw = A @ w                                # matrix A multiplied by the weight vector
    lam = Aw / w                              # lambda for each criterion = (A·w)_i / w_i
    lam_max = lam.mean()                      # lambda_max = average of those values
    CI = (lam_max - m) / (m - 1)              # Consistency Index
    CR = CI / RI[m]                           # Consistency Ratio = CI / RI; must be below 0.10
    print(f"\nAHP Step 5: consistency  lambda_max = {lam_max:.4f}  CI = {CI:.4f}  "
          f"RI = {RI[m]}  CR = {CR:.4f}  -> {'consistent' if CR < 0.10 else 'NOT consistent, revise judgments'}")
    return pd.Series(w, index=crit)           # weights labelled by criterion


if __name__ == "__main__":
    # AHP weights come from judgments, not from the data, so no data file is read here.
    w = ahp_weights(AHP_LEVELS)
    show("FINAL AHP WEIGHTS", w.to_frame("weight"))
    print(f"\nSum of weights = {w.sum():.4f}")   # should always be 1.0000
