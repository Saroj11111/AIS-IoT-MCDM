"""
CRITIC weights (CRiteria Importance Through Intercriteria Correlation)
Project: A Multi-Criteria Decision Framework for Ranking AIS Solutions in IoT Security
Team: Aila Rainelle Medina, Rohan Bhandari, Saroj Dahal

Run on its own to print the weights step by step:
       python "CRITIC weight.py"
       python "CRITIC weight.py" other_data.xlsx
The ranking script "VIKOR-CRITIC method.py" loads critic_weights() from this file.
CRITIC is objective: the weights come only from the data table.
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


def critic_weights(X, details=False):
    # Step 1: min-max normalisation, r = (x - min) / (max - min)
    rng = X.max() - X.min()                   # range of each criterion (column)
    if (rng == 0).any():                      # a criterion that never varies carries no information
        print("\nWarning: criteria with no variation get weight 0:", list(rng[rng == 0].index))
    R = ((X - X.min()) / rng.replace(0, np.nan)).fillna(0)   # rescale each column to 0..1 (0/1 data stays the same)
    show("CRITIC Step 1: normalised matrix r = (x - min) / (max - min)", R)

    # Step 2: contrast intensity = standard deviation of each criterion
    sigma = R.std(ddof=1)                     # sample standard deviation (divides by n - 1, as Excel STDEV)
    show("CRITIC Step 2: standard deviation of each criterion", sigma)

    # Step 3: how strongly each pair of criteria moves together
    rho = R.corr().fillna(0)                  # Pearson correlation matrix (m x m), same as Excel CORREL
    show("CRITIC Step 3: correlation matrix", rho)

    # Steps 4-6: conflict, information content and weight
    conflict = (1 - rho).sum()                # Step 4: sum of (1 - correlation); high = disagrees with the other criteria
    info = sigma * conflict                   # Step 5: information content C = spread x conflict
    w = info / info.sum()                     # Step 6: divide by the total so the weights add up to 1
    show("CRITIC Steps 4-6: conflict, information and weight",
         pd.DataFrame({"conflict sum(1-rho)": conflict, "C = sigma*conflict": info, "weight": w}))
    if details:                               # the web frontend also asks for the working shown on its Weights tab
        return w, {"sigma": sigma, "conflict": conflict, "info": info}
    return w                                  # weights labelled by criterion


if __name__ == "__main__":
    X = load_data(sys.argv[1] if len(sys.argv) > 1 else None)   # import the decision table
    show("Decision table (1 = present, 0 = absent)", X)
    w = critic_weights(X)
    show("FINAL CRITIC WEIGHTS", w.to_frame("weight"))
    print(f"\nSum of weights = {w.sum():.4f}")   # should always be 1.0000
