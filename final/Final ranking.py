"""
Final ranking: the six rankings and their average
Project: A Multi-Criteria Decision Framework for Ranking AIS Solutions in IoT Security
Team: Aila Rainelle Medina, Rohan Bhandari, Saroj Dahal

The six rankings (each one is calculated by its own script; nothing is re-written here):
    1  TOPSIS with AHP 1 (Claude) weights          "TOPSIS-AHP method.py"
    2  TOPSIS with AHP 2 (ChatGPT) weights         "TOPSIS-AHP method.py"
    3  TOPSIS with AHP 3 (Gemini) weights          "TOPSIS-AHP method.py"
    4  PROMETHEE I with Entropy weights            "PROMETHEE I-Entropy method.py"
    5  PROMETHEE II with Entropy weights           "PROMETHEE II-Entropy method.py"
    6  VIKOR with CRITIC weights                   "VIKOR-CRITIC method.py"

Final ranking = average of the six ranks (1 = best). PROMETHEE I gives levels, not ranks, so its
levels are turned into ranks first: alternatives on the same level share a rank and the next level
continues the count (levels 1, 2, 2, 3 -> ranks 1, 2, 2, 4). Then all six are on the same 1-20 scale.

Run:   python "Final ranking.py"
       python "Final ranking.py" other_data.xlsx
Output is printed in the terminal only (nothing is saved).
Needs: numpy, pandas, openpyxl (see README.md for setup)
"""
import sys                 # read the optional data-file name from the command line
import os                  # build file paths relative to this script's folder
import io                  # used to silence the step-by-step printing of the method files
import contextlib          # (same purpose as above)
import importlib.util      # load the method files, whose names contain spaces
import pandas as pd        # tables with labelled rows (studies) and columns (rankings)

pd.set_option("display.width", 200)     # print wide tables on one line
pd.set_option("display.max_columns", None)   # never hide columns with "..."
pd.set_option("display.precision", 4)   # show 4 decimal places

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


# Load the method files (each one also loads its own weight file)
with contextlib.redirect_stdout(io.StringIO()):
    topsis_m = load_module("TOPSIS-AHP method.py")            # topsis(), and ahp = "AHP weight.py"
    prom1_m = load_module("PROMETHEE I-Entropy method.py")    # promethee1(), and entropy = "Entropy weight.py"
    prom2_m = load_module("PROMETHEE II-Entropy method.py")   # promethee2()
    vikor_m = load_module("VIKOR-CRITIC method.py")           # vikor(), and critic = "CRITIC weight.py"

RANKINGS = ["TOPSIS-AHP 1 (Claude)", "TOPSIS-AHP 2 (ChatGPT)", "TOPSIS-AHP 3 (Gemini)",
            "PROMETHEE I-Entropy", "PROMETHEE II-Entropy", "VIKOR-CRITIC"]
# Short column labels so the wide tables fit in the terminal
SHORT = {"TOPSIS-AHP 1 (Claude)": "T-AHP1", "TOPSIS-AHP 2 (ChatGPT)": "T-AHP2", "TOPSIS-AHP 3 (Gemini)": "T-AHP3",
         "PROMETHEE I-Entropy": "P1-Ent", "PROMETHEE II-Entropy": "P2-Ent", "VIKOR-CRITIC": "V-CRITIC"}
LEGEND = ("T-AHP1/2/3 = TOPSIS with AHP 1 (Claude) / AHP 2 (ChatGPT) / AHP 3 (Gemini) weights; "
          "P1-Ent / P2-Ent = PROMETHEE I / II with Entropy weights; V-CRITIC = VIKOR with CRITIC weights")


def levels_to_ranks(level):
    """PROMETHEE I levels -> ranks: same level = same rank, the next level continues the count."""
    return level.rank(method="min").astype(int)               # e.g. levels 1, 2, 2, 3 -> ranks 1, 2, 2, 4


def six_rankings(X, v=0.5):
    """Run all six rankings on the decision table X (v = VIKOR strategy weight).
    Returns (ranks, weights, scores, PROMETHEE I result)."""
    ahp, critic, entropy = topsis_m.ahp, vikor_m.critic, prom1_m.entropy
    weights, ranks, scores = {}, {}, {}

    # 1-3: TOPSIS with each expert's AHP weights (higher CC = better)
    for expert in ahp.EXPERTS:
        w = quiet(ahp.ahp_weights, expert)
        res = quiet(topsis_m.topsis, X, w)
        name = f"TOPSIS-{ahp.AHP_LABEL[expert]}"
        weights[ahp.AHP_LABEL[expert]] = w
        ranks[name], scores[name] = res["Rank"], res["CC"]

    # 4-5: PROMETHEE I and II with Entropy weights
    w_entropy = quiet(entropy.entropy_weights, X)
    weights["Entropy"] = w_entropy
    p1, rel = quiet(prom1_m.promethee1, X, w_entropy)
    ranks["PROMETHEE I-Entropy"], scores["PROMETHEE I-Entropy"] = levels_to_ranks(p1["Level"]), p1["Level"]
    p2 = quiet(prom2_m.promethee2, X, w_entropy)
    ranks["PROMETHEE II-Entropy"], scores["PROMETHEE II-Entropy"] = p2["Rank"], p2["Phi net"]

    # 6: VIKOR with CRITIC weights (lower Q = better)
    w_critic = quiet(critic.critic_weights, X)
    weights["CRITIC"] = w_critic
    vk = quiet(vikor_m.vikor, X, w_critic, v)
    ranks["VIKOR-CRITIC"], scores["VIKOR-CRITIC"] = vk["Rank Q"], vk["Q"]

    return pd.DataFrame(ranks)[RANKINGS], pd.DataFrame(weights), pd.DataFrame(scores)[RANKINGS], p1


def final_ranking(ranks):
    """Average of the six ranks, and the final rank of that average (1 = best; ties share a rank)."""
    avg = ranks.mean(axis=1)
    final = avg.round(10).rank(method="min").astype(int)
    return avg, final


def study_info(path=None):
    """AIS algorithm and family of each study, read from the same data file (for labelling only)."""
    path = path or os.path.join(HERE, topsis_m.DATA_FILE)
    raw = pd.read_excel(path, sheet_name=topsis_m.DATA_SHEET, header=3, index_col=0)
    raw = raw[raw.index.notna()]
    raw.index = raw.index.astype(str)
    cols = [c for c in ("AIS algorithm", "AIS family") if c in raw.columns]
    return raw[cols]                                          # rows not in the table (the key) are dropped by the caller


if __name__ == "__main__":
    data_path = sys.argv[1] if len(sys.argv) > 1 else None
    X = topsis_m.load_data(data_path)                         # import the decision table from Excel
    show("Decision table (1 = present, 0 = absent)", X.astype(int).assign(Score=X.sum(axis=1).astype(int)))

    ranks, weights, scores, p1 = six_rankings(X)
    show("Step 1: weights used by the six rankings", weights)
    print(f"\nColumn labels: {LEGEND}")
    show("Step 2: score of each study in each ranking  (CC: higher = better; PROMETHEE I: level; "
         "Phi net: higher = better; Q: lower = better)", scores.rename(columns=SHORT))
    show("Step 3: PROMETHEE I levels turned into ranks (same level = same rank)",
         pd.DataFrame({"Level": p1["Level"], "Rank": ranks["PROMETHEE I-Entropy"]}).sort_values("Rank").T)
    show("Step 4: the six rankings (1 = best)", ranks.rename(columns=SHORT))

    avg, final = final_ranking(ranks)
    info = study_info(data_path).reindex(X.index)              # only the studies in the decision table
    family = info[["AIS family"]] if "AIS family" in info.columns else info.iloc[:, :0]
    table = pd.concat([family, ranks.rename(columns=SHORT), pd.DataFrame({"Average": avg.round(2), "FINAL": final})], axis=1)
    table = table.sort_values(["FINAL", "Average"])
    show("Step 5: FINAL RANKING = average of the six ranks (1 = best)", table)

    # How often each study is first, and how much its rank changes between methods
    spread = pd.DataFrame({
        "times 1st (of 6)": (ranks == 1).sum(axis=1),
        "best rank": ranks.min(axis=1),
        "worst rank": ranks.max(axis=1),
        "average": avg.round(2),
        "FINAL": final,
    }).sort_values(["FINAL", "average"])
    show("Step 6: consistency of each study across the six rankings", spread)

    # Who is first in each ranking
    winners = pd.Series({r: " / ".join(ranks.index[ranks[r] == 1]) for r in RANKINGS}, name="1st place")
    show("Step 7: first place in each ranking", winners.to_frame())

    # Agreement between the rankings (Spearman rank correlation; 1 = identical order)
    show("Step 8: agreement between the six rankings (Spearman rank correlation)",
         ranks.rename(columns=SHORT).corr(method="spearman").round(2))

    if "AIS family" in info.columns:                          # summary by AIS algorithm family
        fam = pd.concat([info["AIS family"], avg.rename("average rank"), final.rename("final rank")], axis=1)
        fam = fam.groupby("AIS family").agg(studies=("final rank", "size"),
                                            best_final_rank=("final rank", "min"),
                                            mean_average_rank=("average rank", "mean")).sort_values("mean_average_rank")
        show("Step 9: summary by AIS algorithm family", fam.round(2))

    top = table.index[table["FINAL"] == 1]
    print(f"\nFinal ranking leader: {', '.join(top)} (average rank {avg[top[0]]:.2f}). "
          f"Run \"Sensitivity analysis.py\" to check how stable this result is.")
