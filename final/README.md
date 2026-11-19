# Ranking AIS Solutions for IoT Security – MCDM Framework

PRJ701 IT Capstone project *A Multi-Criteria Decision Framework for Ranking Artificial Immune System Solutions in IoT Security*.
Team: Aila Rainelle Medina (KIHE250150), Rohan Bhandari (KIHE250010), Saroj Dahal (KIHE250019).

The framework ranks the 20 AIS studies (S01–S20) in Table 9 of Aldhaheri et al. (2020) on seven AIS properties, using six rankings:

| # | Ranking | Weights |
|---|---|---|
| 1 | TOPSIS | AHP 1 – expert judgments from Claude |
| 2 | TOPSIS | AHP 2 – expert judgments from ChatGPT |
| 3 | TOPSIS | AHP 3 – expert judgments from Gemini |
| 4 | PROMETHEE I (partial ranking) | Entropy |
| 5 | PROMETHEE II (complete ranking) | Entropy |
| 6 | VIKOR | CRITIC |

The **final ranking** is the average of the six ranks. The **best alternative** is then decided by the sensitivity analysis (Triantaphyllou & Sánchez, 1997). Everything is calculated in Python and printed in the terminal; nothing is saved to files.

## Files

| File | What it does |
|---|---|
| `Table9_Data.xlsx` | Table 9 of Aldhaheri et al. (2020): 20 studies × 7 properties (✓ / ✗ / –), with algorithm and family |
| `AHP weight.py` | AHP weights from the three experts' pairwise judgments, with consistency check |
| `CRITIC weight.py` | CRITIC weights from spread and conflict between criteria |
| `Entropy weight.py` | Entropy weights from how unevenly each property is spread |
| `TOPSIS-AHP method.py` | TOPSIS ranking with each of the three AHP weight sets (rankings 1–3) |
| `PROMETHEE I-Entropy method.py` | PROMETHEE I partial ranking (Φ+ and Φ− compared separately) with Entropy weights (ranking 4) |
| `PROMETHEE II-Entropy method.py` | PROMETHEE II complete ranking (net flow) with Entropy weights (ranking 5) |
| `VIKOR-CRITIC method.py` | VIKOR ranking with CRITIC weights, with compromise check (ranking 6) |
| `Final ranking.py` | Runs all six rankings and averages them into the final ranking |
| `Sensitivity analysis.py` | Sensitivity analysis on all six rankings, then decides the best alternative |
| `index.html` | Web frontend: shows the data, weights, rankings, final ranking and sensitivity. It does no calculations itself |
| `run_frontend.py` | Starts the frontend on localhost, opens it in your browser, and answers the page's requests for results |
| `frontend_api.py` | Used by `run_frontend.py`: runs the functions in the scripts above and returns the results to the page |
| `check_setup.py` | Checks Python, packages and files, and test-runs the weights |
| `requirements.txt` | Packages needed: numpy, pandas, openpyxl |
| `setup.bat` / `setup.sh` | One-step setup for Windows / macOS and Linux |

## Initial setup

You need **Python 3.9 or newer**. Check with `python --version` (or `python3 --version` on macOS).

### Option A – one-step setup

- **Windows:** double-click `setup.bat`, or run it from Command Prompt in this folder.
- **macOS / Linux:** open Terminal in this folder and run `bash setup.sh`.

This creates a virtual environment in `.venv`, installs the packages and runs `check_setup.py`.

### Option B – manual setup

```bash
# 1. Open a terminal in this folder
# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux

# 3. Install the packages
python -m pip install -r requirements.txt

# 4. Check everything is ready
python check_setup.py
```

When it works you should see `All checks passed.`

## Running the analysis in the terminal

Activate the environment first (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on macOS/Linux), then:

```bash
# Weights (step by step)
python "AHP weight.py"                     # all three experts, with consistency ratio
python "CRITIC weight.py"
python "Entropy weight.py"

# Each ranking method (weights + ranking, step by step)
python "TOPSIS-AHP method.py"              # rankings 1-3 (Claude, ChatGPT, Gemini)
python "PROMETHEE I-Entropy method.py"     # ranking 4
python "PROMETHEE II-Entropy method.py"    # ranking 5
python "VIKOR-CRITIC method.py"            # ranking 6

# Final ranking (average of the six)
python "Final ranking.py"

# Sensitivity analysis on all six rankings + decision on the best alternative (about 1-3 minutes)
python "Sensitivity analysis.py"
python "Sensitivity analysis.py" --pdf-example   # re-checks the formula on the PDF's Mobile 1-4 example
```

The file names contain spaces, so keep the quotes. Each script prints every step as a table. Output is long: scroll up in the terminal, or copy it into a text file to keep a record.

To use a different data file with the same layout:

```bash
python "Final ranking.py" Other_Data.xlsx
```

The file needs a sheet named `Table 9 (ticks)`, headers on row 4, study names in column A, and the criteria codes `AD SL RES DEF ST LH DS` as column names. ✓ is read as 1; ✗ and – (not reported) as 0.

## How the final ranking and the best alternative are found

1. **Six rankings.** PROMETHEE I gives levels, not ranks, so its levels are turned into ranks first: studies on the same level share a rank and the next level continues the count (levels 1, 2, 2, 3 → ranks 1, 2, 2, 4). All six are then on the same 1–20 scale.
2. **Final ranking** = rank of the average of the six ranks (ties share a rank).
3. **Sensitivity analysis** on each ranking: for every pair of studies and every criterion, the smallest change in that criterion's weight that swaps the pair (δ′, % of the weight). PT and PA show the most critical criterion for first place and for any pair.
4. **Best alternative.** Contenders are the top 3 of the final ranking plus every study that is first in at least one ranking. For each pair of contenders and each ranking: who is ahead, and how big a weight change would reverse it. The best alternative leads its rivals most often; a tie is broken by whose weakest lead needs the larger weight change.

Studies with identical rows (for example S11 and S16) always score the same in every method, so they are analysed as one group (S11/S16).

## Running the web frontend on localhost

```bash
python run_frontend.py          # opens http://localhost:8000
python run_frontend.py 8080     # use another port if 8000 is busy
```

Stop it with **Ctrl + C**. Keep the terminal open while you use the page.

All calculations are done in Python. The page sends the table to `run_frontend.py`, which calls `frontend_api.py`. That file imports the scripts above and runs the same functions you run in the terminal, so there is only one copy of every formula. The page only draws the results.

The tabs are:

- **Overview** – final ranking, first place in each of the six rankings, and the best alternative once the sensitivity analysis has run
- **Data** – Table 9; click a ✓/✗ to try a change, **Reload data file** to go back, or import another Excel file
- **Weights** – the three AHP experts' matrices and consistency, CRITIC and Entropy
- **Rankings** – TOPSIS (pick the expert), VIKOR (with the v slider), PROMETHEE I and II
- **Sensitivity** – PT/PA for all six rankings, the decision, and the full δ′ table for each ranking (takes about a minute; the rest of the page stays usable)
- **Method** – the steps of each method

Opening `index.html` directly by double-clicking does not work, because the page needs the Python server for every result. Always start it with `run_frontend.py`.

## The AHP expert judgments

The three AHP weight sets come from language models acting as experts. Each was asked the same question, in a new chat, to compare the seven criteria pairwise on the Saaty scale (1–9) for choosing an AIS solution for resource-constrained IoT networks. The 21 judgments from each are in `EXPERTS` near the top of `AHP weight.py`:

| Expert | Priority order | CR |
|---|---|---|
| AHP 1 – Claude | LH > ST > AD > DS > SL > DEF > RES | 0.025 |
| AHP 2 – ChatGPT | LH > ST > DEF > RES > AD > DS > SL | 0.018 |
| AHP 3 – Gemini | LH > DS > ST > AD > SL > DEF > RES | 0.039 |

All three are consistent (CR < 0.10). To change a judgment, edit the value in `EXPERTS`; every script picks it up.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` not found | Install Python from python.org and tick **Add Python to PATH** (Windows). On macOS use `python3`. |
| `ModuleNotFoundError` | Activate `.venv`, then run `python -m pip install -r requirements.txt` |
| `FileNotFoundError` for the .xlsx | Run the scripts from this folder and keep all files together |
| Script cannot find another `.py` file | Keep all `.py` files in the same folder; the scripts load each other by name |
| Sensitivity analysis seems stuck | It is still working (TOPSIS and VIKOR search step by step). Watch the `[  12s] starting ...` progress lines; do not press Ctrl + C |
| Frontend says it needs the Python server | Start it with `python run_frontend.py` instead of double-clicking `index.html`, and keep that terminal open |
| PowerShell blocks activation | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use Command Prompt instead |
| VS Code Run button gives a PowerShell `ParserError` | Type the command in the terminal instead, e.g. `python "Final ranking.py"` |

## Sensitivity analysis method

`Sensitivity analysis.py` follows *Validation based on Sensitivity Analysis Approach* (Triantaphyllou & Sánchez, 1997):

- δ(k,i,j) = smallest change in weight w_k that reverses alternatives Ai and Aj; δ′ = δ × 100 / w_k (%).
- PROMETHEE II net flow is a weighted sum, so the PDF formula δ = (Pj − Pi) / (ajk − aik), feasible if δ < w_k, is used exactly.
- PROMETHEE I: Ai outranks Aj only while it is at least as good on Φ+ and on Φ−. Each flow is a weighted sum, so the same formula is applied to each flow; the pair changes when either flow reverses.
- TOPSIS and VIKOR are not weighted sums, so δ is found by moving w_k step by step until the pair swaps (same definition, numerical search).
- Percent-Top (PT) and Percent-Any (PA) identify the most critical criterion for each ranking.

## References

- Aldhaheri, S., Alghazzawi, D., Cheng, L., Barnawi, A., & Alzahrani, B. A. (2020). Artificial immune systems approaches to secure the internet of things: A systematic review of the literature and recommendations for future research. *Journal of Network and Computer Applications, 157*, 102537.
- Triantaphyllou, E., & Sánchez, A. (1997). A sensitivity analysis approach for some deterministic multi-criteria decision-making methods. *Decision Sciences, 28*(1), 151–194.
