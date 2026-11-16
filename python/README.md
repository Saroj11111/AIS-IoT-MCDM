# Ranking AIS Solutions for IoT Security – Python Prototype

Prototype for the PRJ701 IT Capstone project *A Multi-Criteria Decision Framework for Ranking Artificial Immune System Solutions in IoT Security*.
Team: Aila Rainelle Medina (KIHE250150), Rohan Bhandari (KIHE250010), Saroj Dahal (KIHE250019).

The prototype ranks AIS solutions on seven criteria from Table 9 of Aldhaheri et al. (2020) using three weighting methods and four rankings (TOPSIS, VIKOR, PROMETHEE I and PROMETHEE II). It currently runs on a **sample test table** (8 hypothetical alternatives, A–H). The real 20 studies (S01–S20) go in during Week 11.

## Files

| File | What it does |
|---|---|
| `Sample_Table9_Prototype_Data.xlsx` | Prototype test data, laid out like Table 9 (✓ / ✗) |
| `AHP weight.py` | AHP weights from pairwise judgments, with consistency check |
| `CRITIC weight.py` | CRITIC weights from spread and conflict between criteria |
| `Entropy weight.py` | Entropy weights from how unevenly each property is spread |
| `TOPSIS-AHP method.py` | TOPSIS ranking using AHP weights |
| `VIKOR-CRITIC method.py` | VIKOR ranking using CRITIC weights, with compromise check |
| `PROMETHEE I-Entropy method.py` | PROMETHEE I partial ranking (Φ+ and Φ− compared separately) using Entropy weights |
| `PROMETHEE II-Entropy method.py` | PROMETHEE II complete ranking (net flow) using Entropy weights |
| `Sensitivity analysis.py` | Triantaphyllou & Sánchez sensitivity analysis for all three methods; saves `sensitivity_results.xlsx` |
| `index.html` | Web frontend: data, weights, rankings and sensitivity, all calculated in the browser |
| `run_frontend.py` | Starts the frontend on localhost and opens it in your browser |
| `xlsx.full.min.js` | Excel reader used by the frontend (SheetJS, Apache-2.0 licence in `xlsx.LICENSE.txt`) |
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

## Running the prototype

Activate the environment first (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on macOS/Linux), then:

```bash
# Weights only
python "AHP weight.py"
python "CRITIC weight.py"
python "Entropy weight.py"

# Full method (weights + ranking)
python "TOPSIS-AHP method.py"
python "VIKOR-CRITIC method.py"
python "PROMETHEE I-Entropy method.py"
python "PROMETHEE II-Entropy method.py"

# Sensitivity analysis (all three methods, about 15 seconds)
python "Sensitivity analysis.py"
python "Sensitivity analysis.py" --pdf-example   # re-checks the formula on the PDF's Mobile 1-4 example
```

The file names contain spaces, so keep the quotes. Each script prints every step as a table and ends with the final weights or ranking.

To use a different data file with the same layout (for example the real Table 9 data):

```bash
python "TOPSIS-AHP method.py" Real_Table9_Data.xlsx
```

The file needs a sheet named `Sample Table 9 (ticks)`, headers on row 4, alternatives in column A and the criteria codes `AD SL RES DEF ST LH DS` as column names. ✓ is read as 1; ✗ and – (not reported) as 0.

## Running the web frontend on localhost

```bash
python run_frontend.py          # opens http://localhost:8000
python run_frontend.py 8080     # use another port if 8000 is busy
```

Stop it with **Ctrl + C**. The page loads `Sample_Table9_Prototype_Data.xlsx` from this folder (the same file the Python scripts use), so editing that file and refreshing the browser updates the page. It works offline; only the fonts need internet, and the page falls back to system fonts without it.

The tabs are Overview, Data (click a ✓/✗ to change it, or import another Excel file), Weights (AHP sliders), Rankings (VIKOR v slider), Sensitivity and Method. All results match the Python scripts.

Opening `index.html` directly by double-clicking also works, but browsers block it from reading the Excel file, so it falls back to the built-in sample data. Use `run_frontend.py` to load the file.

## Changing the AHP judgments

AHP weights come from judgments, not from the data. Edit `AHP_LEVELS` near the top of `AHP weight.py` (higher number = more important). TOPSIS picks up the new weights automatically. Keep the consistency ratio below 0.10.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` not found | Install Python from python.org and tick **Add Python to PATH** (Windows). On macOS use `python3`. |
| `ModuleNotFoundError` | Activate `.venv`, then run `python -m pip install -r requirements.txt` |
| `FileNotFoundError` for the .xlsx | Run the scripts from this folder and keep all files together |
| Script cannot find a weight file | Keep all `.py` files in the same folder; the ranking scripts load the weight files by name |
| Frontend shows "Using the built-in sample data" | Start it with `python run_frontend.py` instead of double-clicking `index.html` |
| PowerShell blocks activation | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use Command Prompt instead |

## Sensitivity analysis

`Sensitivity analysis.py` follows the method in *Validation based on Sensitivity Analysis Approach* (Triantaphyllou & Sánchez, 1997):

- δ(k,i,j) = smallest change in weight w_k that reverses alternatives Ai and Aj; δ′ = δ × 100 / w_k (%).
- PROMETHEE II net flow is a weighted sum, so the PDF formula δ = (Pj − Pi) / (ajk − aik), feasible if δ ≤ w_k, is used exactly.
- TOPSIS and VIKOR are not weighted sums, so δ is found by moving w_k step by step until the pair swaps (same definition, numerical search).
- Percent-Top (PT) and Percent-Any (PA) identify the most critical criterion for each method.
