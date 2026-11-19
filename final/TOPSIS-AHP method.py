"""
TOPSIS rankings with AHP weights from three experts (rankings 1-3 of 6)
Project: A Multi-Criteria Decision Framework for Ranking AIS Solutions in IoT Security
Team: Aila Rainelle Medina, Rohan Bhandari, Saroj Dahal

Run:   python "TOPSIS-AHP method.py"
       python "TOPSIS-AHP method.py" other_data.xlsx
Weights: loaded from "AHP weight.py" (keep both files in the same folder).
Runs TOPSIS three times: with AHP 1 (Claude), AHP 2 (ChatGPT) and AHP 3 (Gemini) weights.
Higher closeness coefficient (CC) = better.
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


ahp = load_weight_module("AHP weight.py")   # gives access to ahp.ahp_weights(), ahp.EXPERTS and ahp.AHP_LABEL


def topsis(X, w):
    # Steps 1-2: length of each criterion column, sqrt(sum of x squared)
    norm = np.sqrt((X ** 2).sum(axis=0))      # with 0/1 data this is sqrt(number of 1s in the column)
    show("TOPSIS Steps 1-2: column vector length sqrt(sum x^2)", norm)

    # Step 3: vector normalisation, r = x / sqrt(sum x^2)
    R = X / norm.replace(0, np.nan)           # divide each value by its column length (avoid dividing by 0)
    R = R.fillna(0)                           # a column of all 0s stays 0
    show("TOPSIS Step 3: normalised matrix r = x / sqrt(sum x^2)", R)

    # Step 4: weighted normalised matrix, v = w * r
    V = R * w                                 # multiply each column by its AHP weight
    show("TOPSIS Step 4: weighted normalised matrix v = w * r", V)

    # Step 5: ideal best (A+) and ideal worst (A-) for each criterion
    a_pos, a_neg = V.max(axis=0), V.min(axis=0)   # benefit criteria: best = column max, worst = column min
    show("TOPSIS Step 5: ideal best A+ and ideal worst A-", pd.DataFrame({"A+": a_pos, "A-": a_neg}).T)

    # Steps 6-8: distances, closeness coefficient and rank
    d_pos = np.sqrt(((V - a_pos) ** 2).sum(axis=1))   # D+ = Euclidean distance to the ideal best
    d_neg = np.sqrt(((V - a_neg) ** 2).sum(axis=1))   # D- = Euclidean distance to the ideal worst
    cc = d_neg / (d_pos + d_neg)                      # CC = D- / (D+ + D-); 1 = at the ideal, 0 = at the worst
    res = pd.DataFrame({"D+": d_pos, "D-": d_neg, "CC": cc})
    res["Rank"] = res["CC"].round(10).rank(ascending=False, method="min").astype(int)   # highest CC = rank 1; ties share a rank (rounded so float noise does not split ties)
    show("TOPSIS Steps 6-8: distances, closeness coefficient and rank (higher CC = better)", res)
    return res


if __name__ == "__main__":
    X = load_data(sys.argv[1] if len(sys.argv) > 1 else None)   # import the decision table from Excel
    show("Decision table (1 = present, 0 = absent)", X)
    ranks, cc = {}, {}
    for expert in ahp.EXPERTS:                # AHP 1 (Claude), AHP 2 (ChatGPT), AHP 3 (Gemini)
        label = f"TOPSIS-{ahp.AHP_LABEL[expert]}"
        print(f"\n{'#' * 90}\n# {label}\n{'#' * 90}")
        w = ahp.ahp_weights(expert)           # calculate this expert's AHP weights (from AHP weight.py)
        show(f"{ahp.AHP_LABEL[expert]} weights", w)
        result = topsis(X, w)                 # rank the alternatives
        show(f"FINAL RANKING: {label}", result.sort_values("Rank"))
        ranks[label], cc[label] = result["Rank"], result["CC"]
    show("SUMMARY: closeness coefficient CC under each expert's weights", pd.DataFrame(cc))
    show("SUMMARY: TOPSIS rank under each expert's weights (1 = best)",
         pd.DataFrame(ranks).sort_values(list(ranks)[0]))
