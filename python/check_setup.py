"""
Initial setup check: confirms Python, the packages and the data file are ready,
then runs a quick test of all three weight methods.
Run:  python check_setup.py
"""
import importlib
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ok = True

print(f"Python {sys.version.split()[0]}", end="  ")
if sys.version_info < (3, 9):
    print("-> too old, install Python 3.9 or newer"); ok = False
else:
    print("-> OK")

for pkg in ["numpy", "pandas", "openpyxl"]:
    try:
        mod = importlib.import_module(pkg)
        print(f"{pkg} {getattr(mod, '__version__', '')}  -> OK")
    except ImportError:
        print(f"{pkg}  -> MISSING (run: python -m pip install -r requirements.txt)"); ok = False

files = ["Sample_Table9_Prototype_Data.xlsx", "AHP weight.py", "CRITIC weight.py", "Entropy weight.py",
         "TOPSIS-AHP method.py", "VIKOR-CRITIC method.py", "PROMETHEE I-Entropy method.py", "PROMETHEE II-Entropy method.py", "Sensitivity analysis.py", "index.html", "run_frontend.py", "xlsx.full.min.js"]
for f in files:
    found = os.path.exists(os.path.join(HERE, f))
    print(f"{f}  -> {'found' if found else 'MISSING'}")
    ok = ok and found

if ok:
    import io, contextlib

    def load(name):
        spec = importlib.util.spec_from_file_location(name.replace(" ", "_")[:-3], os.path.join(HERE, name))
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

    with contextlib.redirect_stdout(io.StringIO()):
        ahp, critic, ent = load("AHP weight.py"), load("CRITIC weight.py"), load("Entropy weight.py")
        X = critic.load_data()
        tests = {"AHP": ahp.ahp_weights(ahp.AHP_LEVELS), "CRITIC": critic.critic_weights(X),
                 "Entropy": ent.entropy_weights(X)}
    print(f"\nTest data: {X.shape[0]} alternatives x {X.shape[1]} criteria imported")
    for name, w in tests.items():
        good = abs(w.sum() - 1) < 1e-9
        print(f"{name} weights sum to {w.sum():.4f}  -> {'OK' if good else 'PROBLEM'}")
        ok = ok and good

print("\nAll checks passed. You are ready to run the methods." if ok else "\nSome checks failed. Fix the items above and run this again.")
sys.exit(0 if ok else 1)
