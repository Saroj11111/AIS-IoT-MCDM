"""
AHP weights (Analytic Hierarchy Process)
Project: A Multi-Criteria Decision Framework for Ranking AIS Solutions in IoT Security
Team: Aila Rainelle Medina, Rohan Bhandari, Saroj Dahal

Run on its own to print the weights step by step for all three experts:
       python "AHP weight.py"
The ranking script "TOPSIS-AHP method.py" loads ahp_weights() and EXPERTS from this file.
AHP weights come from expert judgments, not from the data table. The three experts are
language models (Claude, ChatGPT, Gemini), each asked the same question (see README.md).
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


from fractions import Fraction   # read judgments written as "1/3" exactly

# ------------------------------------------------------------------
# AHP INPUT: pairwise judgments from three experts (Saaty scale 1-9)
# "AD vs SL": "3" means AD is moderately more important than SL; "1/3" means SL is.
# Each expert gave all 21 comparisons in answer to the same prompt (saved replies are in the report appendix).
# AHP 1 = Claude, AHP 2 = ChatGPT, AHP 3 = Gemini.
# ------------------------------------------------------------------
PAIRS = [("AD", "SL"), ("AD", "RES"), ("AD", "DEF"), ("AD", "ST"), ("AD", "LH"), ("AD", "DS"),
         ("SL", "RES"), ("SL", "DEF"), ("SL", "ST"), ("SL", "LH"), ("SL", "DS"),
         ("RES", "DEF"), ("RES", "ST"), ("RES", "LH"), ("RES", "DS"),
         ("DEF", "ST"), ("DEF", "LH"), ("DEF", "DS"),
         ("ST", "LH"), ("ST", "DS"),
         ("LH", "DS")]

EXPERTS = {
    #            AD:SL AD:RES AD:DEF AD:ST AD:LH AD:DS  SL:RES SL:DEF SL:ST SL:LH SL:DS  RES:DEF RES:ST RES:LH RES:DS  DEF:ST DEF:LH DEF:DS  ST:LH ST:DS  LH:DS
    "Claude":  ["3",  "5",   "4",   "1/2", "1/3", "2",   "3",   "2",   "1/4", "1/5", "1/2", "1/2",  "1/6", "1/7", "1/4",  "1/5", "1/6", "1/3",  "1/2", "3",   "4"],
    "ChatGPT": ["3",  "1/2", "1/3", "1/4", "1/5", "2",   "1/4", "1/5", "1/7", "1/9", "1/2", "1/2",  "1/3", "1/4", "3",    "1/2", "1/3", "4",    "1/2", "5",   "7"],
    "Gemini":  ["2",  "5",   "4",   "1/2", "1/5", "1/3", "4",   "3",   "1/3", "1/6", "1/4", "1/2",  "1/6", "1/9", "1/7",  "1/5", "1/8", "1/6",  "1/4", "1/2", "3"],
}
AHP_LABEL = {"Claude": "AHP 1 (Claude)", "ChatGPT": "AHP 2 (ChatGPT)", "Gemini": "AHP 3 (Gemini)"}

# Saaty's Random Index (RI) for a matrix of size n, used in the consistency check.
RI = {1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def comparison_matrix(judgments, crit=CRITERIA):
    """Step 1: build the full m x m matrix from the 21 upper-triangle judgments.
    a(i,j) = the judgment, a(j,i) = 1 / a(i,j), a(i,i) = 1."""
    idx = {c: k for k, c in enumerate(crit)}
    A = np.ones((len(crit), len(crit)))
    for (a, b), v in zip(PAIRS, judgments):
        x = float(Fraction(v))                # "1/3" -> 0.3333...
        A[idx[a], idx[b]] = x                 # row criterion compared with column criterion
        A[idx[b], idx[a]] = 1 / x             # the reverse comparison is the reciprocal
    return A


def ahp_weights(expert, details=False):
    """AHP weights for one expert ("Claude", "ChatGPT" or "Gemini"), or for a list of 21 judgments."""
    judgments = EXPERTS[expert] if isinstance(expert, str) else expert
    name = AHP_LABEL.get(expert, "custom judgments") if isinstance(expert, str) else "custom judgments"
    crit = CRITERIA
    m = len(crit)                             # number of criteria (7)

    # Step 1: pairwise comparison matrix A (m x m)
    A = comparison_matrix(judgments, crit)
    show(f"{name} - AHP Step 1: pairwise comparison matrix", pd.DataFrame(A, crit, crit))

    # Steps 2-4: geometric-mean method
    row_product = A.prod(axis=1)              # Step 2: multiply all values across each row
    geo_mean = row_product ** (1 / m)         # Step 3: m-th root of the row product = geometric mean
    w = geo_mean / geo_mean.sum()             # Step 4: divide by the total so the weights add up to 1
    show(f"{name} - AHP Steps 2-4: row product, geometric mean, weight",
         pd.DataFrame({"row product": row_product, "geometric mean": geo_mean, "weight": w}, index=crit))

    # Step 5: consistency check (are the judgments free of contradictions?)
    Aw = A @ w                                # matrix A multiplied by the weight vector
    lam = Aw / w                              # lambda for each criterion = (A·w)_i / w_i
    lam_max = lam.mean()                      # lambda_max = average of those values
    CI = (lam_max - m) / (m - 1)              # Consistency Index
    CR = CI / RI[m]                           # Consistency Ratio = CI / RI; must be below 0.10
    print(f"\n{name} - AHP Step 5: consistency  lambda_max = {lam_max:.4f}  CI = {CI:.4f}  "
          f"RI = {RI[m]}  CR = {CR:.4f}  -> {'consistent' if CR < 0.10 else 'NOT consistent, revise judgments'}")
    weights = pd.Series(w, index=crit)        # weights labelled by criterion
    if details:                               # the web frontend also asks for the working shown on its Weights tab
        return weights, {"matrix": A, "geo_mean": geo_mean, "CR": CR, "lambda_max": lam_max, "CI": CI}
    return weights


if __name__ == "__main__":
    # AHP weights come from the experts' judgments, not from the data, so no data file is read here.
    table, cr = {}, {}
    for expert in EXPERTS:                    # AHP 1, AHP 2, AHP 3
        print(f"\n{'#' * 90}\n# {AHP_LABEL[expert]}\n{'#' * 90}")
        w, d = ahp_weights(expert, details=True)
        table[AHP_LABEL[expert]] = w
        cr[AHP_LABEL[expert]] = d["CR"]
    W = pd.DataFrame(table)
    show("FINAL AHP WEIGHTS: all three experts", W)
    show("Consistency ratio (must be below 0.10)", pd.Series(cr).round(4))
    show("Priority order of each expert (1 = most important)", W.rank(ascending=False, method="min").astype(int))
    print(f"\nSum of weights = {', '.join(f'{c}: {W[c].sum():.4f}' for c in W)}")   # should always be 1.0000
