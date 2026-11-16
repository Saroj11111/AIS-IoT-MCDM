"""
Sensitivity analysis (Triantaphyllou & Sánchez, 1997), as in "Validation based on Sensitivity Analysis Approach"
Prototype for: A Multi-Criteria Decision Framework for Ranking AIS Solutions in IoT Security
Team: Aila Rainelle Medina, Rohan Bhandari, Saroj Dahal

For every pair of alternatives (Ai better than Aj) and every criterion k it finds
    delta(k,i,j)  = the smallest change in weight w_k that reverses the order of Ai and Aj
    delta'(k,i,j) = delta x 100 / w_k            (the change as a % of the current weight)
New weight = w_k - delta, so delta > 0 means the weight must FALL and delta < 0 means it must RISE.
"N/F" = not feasible (no change in that weight can reverse the pair).

Then, as in the PDF:
    Percent-Top (PT): smallest |delta'| for pairs that include the top-ranked alternative
    Percent-Any (PA): smallest |delta'| over all pairs
The criterion with the smallest PT / PA is the most critical (the ranking is most sensitive to it).

How delta is found:
    PROMETHEE II  net flow is a weighted sum, P(i) = sum_k w_k * a(i,k), so the PDF formula is used exactly:
                  delta = (P_j - P_i) / (a_jk - a_ik), feasible only if delta <= w_k
    TOPSIS, VIKOR are NOT weighted sums, so the formula cannot be used directly. Instead w_k is moved
                  step by step (other weights fixed) until the pair first swaps: same definition of delta,
                  found by numerical search.

Run:   python "Sensitivity analysis.py"                   (prototype test data)
       python "Sensitivity analysis.py" other_data.xlsx   (any file laid out like Table 9)
       python "Sensitivity analysis.py" --pdf-example     (re-check the formula on the PDF's Mobile 1-4 example)
Results are also saved to sensitivity_results.xlsx.
Needs: numpy, pandas, openpyxl (see README.md for setup)
"""
import sys                 # read command-line options
import os                  # build file paths relative to this script's folder
import io                  # used to silence the step-by-step printing of the method files
import contextlib          # (same purpose as above)
import importlib.util      # load the method/weight files, whose names contain spaces
import numpy as np         # numeric arrays and maths
import pandas as pd        # labelled tables

pd.set_option("display.width", 160)     # print wide tables on one line
pd.set_option("display.precision", 1)   # delta' is shown to 1 decimal place, as in the PDF

HERE = os.path.dirname(os.path.abspath(__file__))   # folder that holds all the prototype files


def load_module(filename):
    """Load one of the prototype .py files (names contain spaces, so a normal import cannot be used)."""
    spec = importlib.util.spec_from_file_location(filename.replace(" ", "_")[:-3], os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def quiet(func, *args):
    """Run a function from another file without printing its step-by-step tables."""
    with contextlib.redirect_stdout(io.StringIO()):
        return func(*args)


def show(title, obj):
    print(f"\n=== {title} ===")
    print(obj)


# ------------------------------------------------------------------
# Fast scoring functions (same formulas as the method files, written with plain numpy
# because the numerical search calls them many thousands of times)
# ------------------------------------------------------------------
def topsis_scores(X, w):
    R = X / np.where(np.sqrt((X ** 2).sum(0)) == 0, 1, np.sqrt((X ** 2).sum(0)))   # vector normalisation
    V = R * w                                                                        # weighted normalised matrix
    d_pos = np.sqrt(((V - V.max(0)) ** 2).sum(1))                                    # distance to ideal best
    d_neg = np.sqrt(((V - V.min(0)) ** 2).sum(1))                                    # distance to ideal worst
    tot = d_pos + d_neg
    return np.where(tot == 0, 0, d_neg / np.where(tot == 0, 1, tot))                 # closeness coefficient CC (higher = better)


def vikor_scores(X, w, v=0.5):
    rng = X.max(0) - X.min(0)
    d = (X.max(0) - X) / np.where(rng == 0, 1, rng)              # normalised distance from the best value
    wd = d * w                                                   # weighted distance
    S, R = wd.sum(1), wd.max(1)                                  # group utility and individual regret
    s = (S - S.min()) / (S.max() - S.min()) if S.max() > S.min() else S * 0
    r = (R - R.min()) / (R.max() - R.min()) if R.max() > R.min() else R * 0
    return v * s + (1 - v) * r                                   # compromise index Q (lower = better)


def unicriterion_flows(X):
    """a(i,k) for PROMETHEE II with the usual preference function:
    (number of alternatives that i beats on k - number that beat i on k) / (n - 1)."""
    n = len(X)
    return np.array([[((X[:, k] < X[i, k]).sum() - (X[:, k] > X[i, k]).sum()) / (n - 1)
                      for k in range(X.shape[1])] for i in range(n)])


# ------------------------------------------------------------------
# Finding delta
# ------------------------------------------------------------------
def delta_closed_form(P, a, w, i, j, k):
    """PDF formula for weighted-sum scores. Returns delta, or None if not feasible."""
    if a[j, k] == a[i, k]:                         # same value on criterion k: changing w_k cannot separate them
        return None
    d = (P[j] - P[i]) / (a[j, k] - a[i, k])        # delta(k,i,j) = (Pj - Pi) / (ajk - aik)
    return d if d < w[k] - 1e-9 else None          # feasibility (PDF): delta must not exceed w_k; delta = w_k would remove the criterion, so it is treated as N/F


def delta_search(score, X, w, i, j, k, higher_better, upper=10.0, steps=600):
    """Numerical search for non-weighted-sum methods (TOPSIS, VIKOR).
    Moves w_k down towards 0 and up towards `upper`, and returns the smallest change that makes j beat i."""
    w0 = w[k]

    def gap(t):                                    # how far i is ahead of j when w_k = t (positive = i still ahead)
        ww = w.copy(); ww[k] = t
        s = score(X, ww)
        return (s[i] - s[j]) if higher_better else (s[j] - s[i])

    best = None
    for end in (0.0, upper):                       # search downwards (decrease) and upwards (increase)
        # test points packed closely near the current weight (where small, important changes happen)
        # and spaced further apart as the weight moves away from it
        ts = w0 + np.sign(end - w0) * np.concatenate(([0.0], np.geomspace(1e-7, abs(end - w0), steps)))
        prev_t, prev_g = ts[0], gap(ts[0])
        for t in ts[1:]:
            g = gap(t)
            if prev_g > 0 and g < -1e-12:          # the order has just reversed between prev_t and t
                lo, hi = prev_t, t
                for _ in range(60):                # bisection: narrow down the exact crossing point
                    mid = (lo + hi) / 2
                    if gap(mid) > 0: lo = mid
                    else: hi = mid
                d = w0 - (lo + hi) / 2             # delta = old weight - new weight
                if best is None or abs(d) < abs(best):
                    best = d
                break
            prev_t, prev_g = t, g
    return best


# ------------------------------------------------------------------
# One full sensitivity analysis for one method
# ------------------------------------------------------------------
def sensitivity(name, X, alt_names, w, crit, scores, higher_better, closed_form=None):
    # Identical rows always score the same and can never be separated, so group them first
    groups = {}
    for idx, row in enumerate(X):
        groups.setdefault(tuple(row), []).append(idx)
    reps = [g[0] for g in groups.values()]                       # one representative per group
    label = {g[0]: "/".join(alt_names[x] for x in g) for g in groups.values()}

    order = sorted(reps, key=lambda i: -scores[i] if higher_better else scores[i])   # best first
    print(f"\n{'#' * 90}\n# {name}\n{'#' * 90}")
    show("Current weights", pd.Series(w, index=crit).round(4))
    show("Current ranking (best first)", pd.DataFrame(
        {"score": [round(scores[i], 4) for i in order]}, index=[label[i] for i in order]))

    pairs = [(order[a], order[b]) for a in range(len(order)) for b in range(a + 1, len(order))]
    delta = pd.DataFrame(index=[f"{label[i]} - {label[j]}" for i, j in pairs], columns=crit, dtype=object)
    pct = delta.copy()
    for (i, j), pair in zip(pairs, delta.index):
        for k, c in enumerate(crit):
            if abs(scores[i] - scores[j]) < 1e-12:               # already tied: nothing to reverse
                d = None
            elif closed_form is not None:
                d = delta_closed_form(*closed_form, w, i, j, k)
            else:
                d = delta_search(*search_args, i, j, k, higher_better)
            if d is None or abs(d) < 1e-12:
                delta.loc[pair, c] = "N/F"; pct.loc[pair, c] = "N/F"
            else:
                delta.loc[pair, c] = round(d, 4)                 # delta(k,i,j)
                pct.loc[pair, c] = round(d * 100 / w[k], 1)      # delta'(k,i,j) = delta x 100 / w_k
    show("delta(k,i,j): smallest weight change that reverses the pair", delta)
    show("delta'(k,i,j) = delta x 100 / w_k  (%)   negative = weight must rise, positive = must fall", pct)

    # Percent-Top and Percent-Any
    num = pct.apply(pd.to_numeric, errors="coerce").abs()        # |delta'|, N/F becomes empty
    top_rows = [p for p, (i, j) in zip(num.index, pairs) if i == order[0]]
    summary = pd.DataFrame({
        "feasible reversals": num.notna().sum(),
        "PT: min |delta'| with top (%)": num.loc[top_rows].min(),
        "PA: min |delta'| any pair (%)": num.min(),
        "pair at PA": num.idxmin(skipna=True).where(num.notna().any(), "-"),
    })
    show("Criticality of each criterion (smaller % = more critical)", summary)
    pt, pa = summary.iloc[:, 1], summary.iloc[:, 2]
    res = {"method": name, "top": label[order[0]],
           "PT criterion": pt.idxmin() if pt.notna().any() else "none", "PT %": pt.min(),
           "PA criterion": pa.idxmin() if pa.notna().any() else "none", "PA %": pa.min(),
           "PA pair": summary.loc[pa.idxmin(), "pair at PA"] if pa.notna().any() else "-"}
    print(f"\nMost critical criterion for the top position (PT): {res['PT criterion']} ({res['PT %']:.1f}%)")
    print(f"Most critical criterion for any pair (PA):        {res['PA criterion']} ({res['PA %']:.1f}%, pair {res['PA pair']})")
    return res, delta, pct, summary


def pdf_example():
    """Re-check the closed-form formula on the worked example in the sensitivity-analysis PDF."""
    crit = ["C1", "C2", "C3", "C4"]
    a = np.array([[.3088, .2897, .3867, .1922], [.2163, .3458, .1755, .6288],
                  [.4509, .2473, .1194, .0575], [.0240, .1172, .3184, .1215]])   # normalised decision matrix (Mobile 1-4)
    w = np.array([.3277, .355, .2876, .0790])                                    # weights from the PDF
    P = np.array([.3162, .2768, .2623, .1449])                                   # P_i values as printed in the PDF
    print("PDF example: Mobile 1-4. Compare with the PDF's final delta' table.")
    sensitivity("PDF worked example (weighted sum)", a, ["A1", "A2", "A3", "A4"], w, crit, P, True, closed_form=(P, a))


if __name__ == "__main__":
    if "--pdf-example" in sys.argv:
        pdf_example(); sys.exit(0)

    # Load the prototype files (their own printing is switched off here)
    topsis_m = load_module("TOPSIS-AHP method.py")
    vikor_m = load_module("VIKOR-CRITIC method.py")
    prom_m = load_module("PROMETHEE II-Entropy method.py")

    data_path = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
    Xdf = topsis_m.load_data(data_path)                          # import the decision table from Excel
    crit, names, X = list(Xdf.columns), list(Xdf.index), Xdf.values

    # Weights from the three weight files
    w_ahp = quiet(topsis_m.ahp.ahp_weights, topsis_m.ahp.AHP_LEVELS).values
    w_critic = quiet(vikor_m.critic.critic_weights, Xdf).values
    w_entropy = quiet(prom_m.entropy.entropy_weights, Xdf).values

    # Check: the fast scoring functions give exactly the same results as the method files
    assert np.allclose(topsis_scores(X, w_ahp), quiet(topsis_m.topsis, Xdf, pd.Series(w_ahp, crit))["CC"].values)
    assert np.allclose(vikor_scores(X, w_critic), quiet(vikor_m.vikor, Xdf, pd.Series(w_critic, crit))["Q"].values)
    a = unicriterion_flows(X)
    assert np.allclose(a @ w_entropy, quiet(prom_m.promethee2, Xdf, pd.Series(w_entropy, crit))["Phi net"].values)

    results, sheets = [], {}
    # 1) TOPSIS with AHP weights: numerical search
    search_args = (topsis_scores, X, w_ahp)
    r = sensitivity("TOPSIS-AHP", X, names, w_ahp, crit, topsis_scores(X, w_ahp), True)
    results.append(r[0]); sheets["TOPSIS-AHP"] = r[1:]
    # 2) VIKOR with CRITIC weights: numerical search (lower Q = better)
    search_args = (vikor_scores, X, w_critic)
    r = sensitivity("VIKOR-CRITIC", X, names, w_critic, crit, vikor_scores(X, w_critic), False)
    results.append(r[0]); sheets["VIKOR-CRITIC"] = r[1:]
    # 3) PROMETHEE II with Entropy weights: closed-form PDF formula
    P = a @ w_entropy                                            # net flow = weighted sum of unicriterion flows
    r = sensitivity("PROMETHEE-Entropy", X, names, w_entropy, crit, P, True, closed_form=(P, a))
    results.append(r[0]); sheets["PROMETHEE-Entropy"] = r[1:]

    summary = pd.DataFrame(results).set_index("method")
    show("SUMMARY: most critical criteria by method", summary)

    # Save everything to Excel
    out = os.path.join(HERE, "sensitivity_results.xlsx")
    with pd.ExcelWriter(out) as xw:
        summary.to_excel(xw, sheet_name="Summary")
        for m, (delta, pct, crit_tbl) in sheets.items():
            delta.to_excel(xw, sheet_name=f"{m} delta")
            pct.to_excel(xw, sheet_name=f"{m} delta %")
            crit_tbl.to_excel(xw, sheet_name=f"{m} criticality")
    print(f"\nSaved all tables to {os.path.basename(out)}")
