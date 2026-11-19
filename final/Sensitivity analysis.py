"""
Sensitivity analysis (Triantaphyllou & Sánchez, 1997), as in "Validation based on Sensitivity Analysis Approach"
Project: A Multi-Criteria Decision Framework for Ranking AIS Solutions in IoT Security
Team: Aila Rainelle Medina, Rohan Bhandari, Saroj Dahal

Runs on all six rankings:
    1-3  TOPSIS with AHP 1 (Claude), AHP 2 (ChatGPT), AHP 3 (Gemini) weights
    4    PROMETHEE I with Entropy weights
    5    PROMETHEE II with Entropy weights
    6    VIKOR with CRITIC weights

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
                  delta = (P_j - P_i) / (a_jk - a_ik), feasible only if delta < w_k
    PROMETHEE I   partial ranking: "Ai outranks Aj" needs Ai to be at least as good on BOTH flows (Phi+ and Phi-).
                  Each flow is a weighted sum, so the PDF formula is applied to each flow; the pair changes
                  when EITHER flow reverses (the smaller change counts). Top = every alternative on level 1.
    TOPSIS, VIKOR are NOT weighted sums, so the formula cannot be used directly. Instead w_k is moved
                  step by step (other weights fixed) until the pair first swaps: same definition of delta,
                  found by numerical search.

Choosing the best alternative:
    The final ranking (average of the six ranks) gives the leading alternatives. The sensitivity analysis
    then decides between the contenders (the top 3 of the final ranking plus every alternative that is
    first in at least one ranking): for each pair of contenders and each ranking, who is ahead and how
    large a weight change (delta') would reverse that. The best alternative is the contender that is ahead
    of its rivals most often; a tie is broken by whose weakest lead needs the larger weight change.

Run:   python "Sensitivity analysis.py"                   (Table 9 data, about 1-3 minutes)
       python "Sensitivity analysis.py" other_data.xlsx   (any file laid out like Table 9)
       python "Sensitivity analysis.py" --pdf-example     (re-check the formula on the PDF's Mobile 1-4 example)
Output is printed in the terminal only (nothing is saved).
Needs: numpy, pandas, openpyxl (see README.md for setup)
"""
import sys                 # read command-line options
import os                  # build file paths relative to this script's folder
import io                  # used to silence the step-by-step printing of the method files
import contextlib          # (same purpose as above)
import importlib.util      # load the method/weight files, whose names contain spaces
import time                # show progress while the search runs
import numpy as np         # numeric arrays and maths
import pandas as pd        # labelled tables

pd.set_option("display.width", 200)          # print wide tables on one line
pd.set_option("display.max_columns", None)   # never hide columns with "..."
pd.set_option("display.max_rows", 500)       # print every pair, not just the first and last few
pd.set_option("display.precision", 1)        # delta' is shown to 1 decimal place, as in the PDF

HERE = os.path.dirname(os.path.abspath(__file__))   # folder that holds all the project files


def load_module(filename):
    """Load one of the project .py files (names contain spaces, so a normal import cannot be used)."""
    spec = importlib.util.spec_from_file_location(filename.replace(" ", "_")[:-3], os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def quiet(func, *args, **kwargs):
    """Run a function from another file without printing its step-by-step tables."""
    with contextlib.redirect_stdout(io.StringIO()):
        return func(*args, **kwargs)


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


def unicriterion_plus_minus(X):
    """Per-criterion leaving and entering flows for PROMETHEE I (usual preference function).
    plus[i,k]  = share of the others that i beats on k     ->  Phi+ = plus @ w
    minus[i,k] = share of the others that beat i on k      ->  Phi- = minus @ w"""
    n = len(X)
    plus = np.array([[(X[:, k] < X[i, k]).sum() / (n - 1) for k in range(X.shape[1])] for i in range(n)])
    minus = np.array([[(X[:, k] > X[i, k]).sum() / (n - 1) for k in range(X.shape[1])] for i in range(n)])
    return plus, minus


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


def delta_promethee1(plus, minus, w, i, j, k, eps=1e-12):
    """PROMETHEE I: smallest change in w_k after which Ai no longer outranks Aj.
    Ai outranks Aj while it is ahead (or equal) on Phi+ AND on Phi-; each is a weighted sum,
    so the PDF formula gives the change that closes each gap. The pair changes at the smaller one."""
    options = []
    gap_plus = plus[i] @ w - plus[j] @ w           # how far Ai is ahead on Phi+ (higher = better)
    gap_minus = minus[j] @ w - minus[i] @ w        # how far Ai is ahead on Phi- (lower = better)
    for gap, b in ((gap_plus, plus[i, k] - plus[j, k]), (gap_minus, minus[j, k] - minus[i, k])):
        if abs(b) > eps:                           # changing w_k moves this gap
            d = gap / b                            # change in w_k that brings the gap to 0 (PDF formula)
            if d < w[k] - 1e-9 and abs(d) > eps:   # feasible (weight stays above 0) and a real change
                options.append(d)
    return min(options, key=abs) if options else None


# ------------------------------------------------------------------
# Shared steps: grouping identical studies, filling the tables, PT and PA
# ------------------------------------------------------------------
def group_identical(X, alt_names):
    """Identical rows always score the same and can never be separated, so they are analysed as one group."""
    groups = {}
    for idx, row in enumerate(X):
        groups.setdefault(tuple(row), []).append(idx)
    reps = [g[0] for g in groups.values()]                       # one representative per group
    label = {g[0]: "/".join(alt_names[x] for x in g) for g in groups.values()}
    return reps, label


def fill(delta, pct, pair, c, d, wk):
    """Write one delta and delta' cell ("N/F" if not feasible)."""
    if d is None or abs(d) < 1e-12:
        delta.loc[pair, c] = "N/F"; pct.loc[pair, c] = "N/F"
    else:
        delta.loc[pair, c] = round(d, 4)                         # delta(k,i,j)
        pct.loc[pair, c] = round(d * 100 / wk, 1)                # delta'(k,i,j) = delta x 100 / w_k


def criticality(pct, top_rows):
    num = pct.apply(pd.to_numeric, errors="coerce").abs()        # |delta'|, N/F becomes empty
    return pd.DataFrame({
        "feasible reversals": num.notna().sum(),
        "PT: min |delta'| with top (%)": num.loc[top_rows].min() if top_rows else np.nan,
        "PA: min |delta'| any pair (%)": num.min(),
        "pair at PA": num.apply(lambda col: col.idxmin() if col.notna().any() else "-"),   # "-" = no pair can swap
    })


def report(name, top, delta, pct, top_rows):
    """Print delta, delta', criticality and the most critical criterion; return the one-line result."""
    show("delta(k,i,j): smallest weight change that reverses the pair", delta)
    show("delta'(k,i,j) = delta x 100 / w_k  (%)   negative = weight must rise, positive = must fall", pct)
    summary = criticality(pct, top_rows)
    show("Criticality of each criterion (smaller % = more critical)", summary)
    pt, pa = summary.iloc[:, 1], summary.iloc[:, 2]
    res = {"method": name, "top": top,
           "PT criterion": pt.idxmin() if pt.notna().any() else "none", "PT %": pt.min(),
           "PA criterion": pa.idxmin() if pa.notna().any() else "none", "PA %": pa.min(),
           "PA pair": summary.loc[pa.idxmin(), "pair at PA"] if pa.notna().any() else "-"}
    if pt.notna().any():
        print(f"\nMost critical criterion for the top position (PT): {res['PT criterion']} ({res['PT %']:.1f}%)")
    else:
        print("\nMost critical criterion for the top position (PT): none (no single weight change moves the top)")
    if pa.notna().any():
        print(f"Most critical criterion for any pair (PA):        {res['PA criterion']} ({res['PA %']:.1f}%, pair {res['PA pair']})")
    else:
        print("Most critical criterion for any pair (PA):        none (no single weight change swaps any pair)")
    return res, delta, pct, summary


def header(name, w, crit):
    print(f"\n{'#' * 90}\n# {name}\n{'#' * 90}")
    show("Current weights", pd.Series(w, index=crit).round(4))


# ------------------------------------------------------------------
# One full sensitivity analysis for one method
# ------------------------------------------------------------------
def sensitivity(name, X, alt_names, w, crit, scores, higher_better, closed_form=None, search=None):
    """Complete rankings (TOPSIS, VIKOR, PROMETHEE II).
    closed_form = (P, a) for weighted sums; search = (score function, X, w) for the numerical search."""
    reps, label = group_identical(X, alt_names)
    order = sorted(reps, key=lambda i: -scores[i] if higher_better else scores[i])   # best first
    header(name, w, crit)
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
                d = delta_closed_form(*closed_form, w, i, j, k)   # PDF formula
            else:
                d = delta_search(*search, i, j, k, higher_better)   # numerical search
            fill(delta, pct, pair, c, d, w[k])
    best = [label[i] for i in reps if abs(scores[i] - scores[order[0]]) < 1e-12]   # every group tied for first
    top_rows = [p for p, (i, j) in zip(delta.index, pairs) if label[i] in best]
    out = report(name, " = ".join(best), delta, pct, top_rows)
    ahead = {(label[i], label[j]) for i, j in pairs if abs(scores[i] - scores[j]) >= 1e-12}   # (better, worse)
    return out + (ahead, label)


def sensitivity_promethee1(name, X, alt_names, w, crit, prom1_m, Xdf):
    """PROMETHEE I (partial ranking): pairs are every 'Ai outranks Aj'; top = every group on level 1."""
    reps, label = group_identical(X, alt_names)
    res_df, rel = quiet(prom1_m.promethee1, Xdf, pd.Series(w, crit))   # current partial ranking (PROMETHEE I script)
    level = res_df["Level"]
    header(name, w, crit)
    show("Current partial ranking (level 1 = best; same level = not ordered)",
         pd.DataFrame({"Phi+": [res_df["Phi+"].iloc[i] for i in reps], "Phi-": [res_df["Phi-"].iloc[i] for i in reps],
                       "Level": [level.iloc[i] for i in reps]}, index=[label[i] for i in reps]).sort_values("Level").round(4))

    plus, minus = unicriterion_plus_minus(X)
    pairs = [(i, j) for i in reps for j in reps if rel.iloc[i, j] == "P"]   # every "Ai outranks Aj"
    pairs.sort(key=lambda p: (level.iloc[p[0]], level.iloc[p[1]]))
    delta = pd.DataFrame(index=[f"{label[i]} - {label[j]}" for i, j in pairs], columns=crit, dtype=object)
    pct = delta.copy()
    for (i, j), pair in zip(pairs, delta.index):
        for k, c in enumerate(crit):
            fill(delta, pct, pair, c, delta_promethee1(plus, minus, w, i, j, k), w[k])
    top = [label[i] for i in reps if level.iloc[i] == 1]
    top_rows = [p for p, (i, j) in zip(delta.index, pairs) if label[i] in top]
    out = report(name, " = ".join(top), delta, pct, top_rows)
    ahead = {(label[i], label[j]) for i, j in pairs}             # (outranks, outranked)
    return out + (ahead, label)


# ------------------------------------------------------------------
# Choosing the best alternative with the sensitivity results
# ------------------------------------------------------------------
def decide_best(results, final_avg, label_of):
    """Head-to-head between the contenders in every ranking, using the delta' tables.
    results: {ranking name: (res, delta, pct, summary, ahead, label)}; final_avg: average rank per study."""
    group_avg = {}
    for study, g in label_of.items():
        group_avg.setdefault(g, final_avg[study])
    ordered = sorted(group_avg, key=group_avg.get)
    top_values = sorted(set(group_avg.values()))[:3]           # the three best average ranks
    top3 = [g for g in ordered if group_avg[g] in top_values]
    firsts = {g for name, r in results.items() for g in r[0]["top"].split(" = ")}
    contenders = [g for g in ordered if g in set(top3) | firsts]

    def lead_size(pct, a, b):
        """Smallest |delta'| that reverses 'a ahead of b' (inf = no single weight change can)."""
        row = f"{a} - {b}"
        if row not in pct.index:
            return np.inf
        vals = pd.to_numeric(pct.loc[row], errors="coerce").abs()
        return vals.min() if vals.notna().any() else np.inf

    rows, h2h = [], {}
    for c in contenders:
        wins, losses, ties, leads = 0, 0, 0, []
        for name, (res, delta, pct, summary, ahead, label) in results.items():
            for r in contenders:
                if r == c:
                    continue
                if (c, r) in ahead:
                    wins += 1; leads.append(lead_size(pct, c, r))
                    h2h[(name, c, r)] = f"ahead ({'N/F' if np.isinf(leads[-1]) else f'{leads[-1]:.1f}%'})"
                elif (r, c) in ahead:
                    losses += 1; h2h[(name, c, r)] = "behind"
                else:
                    ties += 1; h2h[(name, c, r)] = "level"
        weakest = min(leads) if leads else 0.0
        rows.append({"contender": c, "average rank": round(group_avg[c], 2),
                     "1st in (of 6)": sum(c in r[0]["top"].split(" = ") for r in results.values()),
                     "leads (wins)": wins, "behind": losses, "level/incomparable": ties,
                     "weakest lead (%)": "N/F" if np.isinf(weakest) else round(weakest, 1),
                     "_weak": weakest})
    table = pd.DataFrame(rows).set_index("contender")
    table = table.sort_values(["leads (wins)", "_weak", "average rank"], ascending=[False, False, True])
    return table, contenders, h2h


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

    # Load the project files (their own printing is switched off here)
    with contextlib.redirect_stdout(io.StringIO()):
        final_m = load_module("Final ranking.py")                # six_rankings() and final_ranking()
    topsis_m, vikor_m, prom1_m, prom2_m = final_m.topsis_m, final_m.vikor_m, final_m.prom1_m, final_m.prom2_m
    ahp = topsis_m.ahp

    data_path = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
    Xdf = topsis_m.load_data(data_path)                          # import the decision table from Excel
    crit, names, X = list(Xdf.columns), list(Xdf.index), Xdf.values

    # Weights from the weight files
    w_ahp = {e: quiet(ahp.ahp_weights, e).values for e in ahp.EXPERTS}
    w_critic = quiet(vikor_m.critic.critic_weights, Xdf).values
    w_entropy = quiet(prom1_m.entropy.entropy_weights, Xdf).values

    # Check: the fast scoring functions give exactly the same results as the method files
    for w in w_ahp.values():
        assert np.allclose(topsis_scores(X, w), quiet(topsis_m.topsis, Xdf, pd.Series(w, crit))["CC"].values)
    assert np.allclose(vikor_scores(X, w_critic), quiet(vikor_m.vikor, Xdf, pd.Series(w_critic, crit))["Q"].values)
    a = unicriterion_flows(X)
    assert np.allclose(a @ w_entropy, quiet(prom2_m.promethee2, Xdf, pd.Series(w_entropy, crit))["Phi net"].values)

    start = time.time()
    def progress(msg):
        print(f"\n[{time.time() - start:5.0f}s] {msg}", flush=True)

    results = {}
    print("\nRunning the sensitivity analysis on all six rankings. TOPSIS and VIKOR search step by step, "
          "so they take the longest.", flush=True)
    # 1-3) TOPSIS with each expert's AHP weights: numerical search
    for e, w in w_ahp.items():
        name = f"TOPSIS-{ahp.AHP_LABEL[e]}"
        progress(f"starting {name} ...")
        results[name] = sensitivity(name, X, names, w, crit, topsis_scores(X, w), True, search=(topsis_scores, X, w))
    # 4) PROMETHEE I with Entropy weights: PDF formula on both flows
    progress("starting PROMETHEE I-Entropy ...")
    results["PROMETHEE I-Entropy"] = sensitivity_promethee1("PROMETHEE I-Entropy", X, names, w_entropy, crit, prom1_m, Xdf)
    # 5) PROMETHEE II with Entropy weights: closed-form PDF formula
    progress("starting PROMETHEE II-Entropy ...")
    P = a @ w_entropy                                            # net flow = weighted sum of unicriterion flows
    results["PROMETHEE II-Entropy"] = sensitivity("PROMETHEE II-Entropy", X, names, w_entropy, crit, P, True, closed_form=(P, a))
    # 6) VIKOR with CRITIC weights: numerical search (lower Q = better)
    progress("starting VIKOR-CRITIC ...")
    results["VIKOR-CRITIC"] = sensitivity("VIKOR-CRITIC", X, names, w_critic, crit, vikor_scores(X, w_critic), False,
                                          search=(vikor_scores, X, w_critic))
    progress("all six done")

    # ---------------- Summary of the six analyses ----------------
    summary = pd.DataFrame([r[0] for r in results.values()]).set_index("method")
    summary[["PT %", "PA %"]] = summary[["PT %", "PA %"]].astype(float).round(1)
    show("SUMMARY: most critical criteria for each ranking", summary)
    counts = pd.DataFrame({"PT": summary["PT criterion"].value_counts(), "PA": summary["PA criterion"].value_counts()})
    show("How often each criterion is the most critical (of 6)", counts.reindex(crit).fillna(0).astype(int))

    # ---------------- Choosing the best alternative ----------------
    ranks, _, _, _ = final_m.six_rankings(Xdf)
    avg, final = final_m.final_ranking(ranks)
    _, label = group_identical(X, names)
    label_of = {names[i]: label[next(r for r in label if tuple(X[r]) == tuple(X[i]))] for i in range(len(names))}
    table, contenders, h2h = decide_best(results, avg, label_of)
    show("FINAL RANKING (average of the six ranks), top 8",
         pd.DataFrame({"average rank": avg.round(2), "final rank": final}).sort_values("final rank").head(8))
    show(f"Head-to-head between the contenders in each ranking "
         f"(ahead (x%) = a weight change of x% would reverse it; N/F = no single weight change can)",
         pd.DataFrame({name: {f"{c} vs {r}": h2h[(name, c, r)] for c in contenders for r in contenders if r != c}
                       for name in results}).rename(columns=final_m.SHORT))
    print(f"\nColumn labels: {final_m.LEGEND}")
    show("DECISION: contenders ranked by how often they lead their rivals, then by how hard their weakest lead is to reverse",
         table.drop(columns="_weak"))
    best = table.index[0]
    print(f"\nBest alternative: {best}")
    print(f"  final ranking: average rank {table.loc[best, 'average rank']}, first in {table.loc[best, '1st in (of 6)']} of 6 rankings")
    print(f"  ahead of the other contenders in {table.loc[best, 'leads (wins)']} of "
          f"{len(results) * (len(contenders) - 1)} head-to-head comparisons; "
          f"its weakest lead needs a weight change of {table.loc[best, 'weakest lead (%)']}% to reverse")
    print(f"\nAll done in {time.time() - start:.0f} seconds. Nothing was saved; scroll up to see each ranking's tables.")
