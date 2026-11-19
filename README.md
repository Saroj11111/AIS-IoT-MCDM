# AIS-IoT-MCDM

PRJ701 IT Capstone project: *A Multi-Criteria Decision Framework for Ranking Artificial Immune System Solutions in IoT Security*.
Team: Aila Rainelle Medina, Rohan Bhandari, Saroj Dahal.

| Folder | What it is |
|---|---|
| [`final/`](final/) | **Final system (Sprint 3).** Six rankings on the real Table 9 of Aldhaheri et al. (2020), the final ranking, the sensitivity analysis and the decision on the best alternative. Start here. |
| [`python/`](python/) | Sprint 2 prototype on a sample table (kept for the project history). |

To run the final system, open the `final` folder and follow its [README](final/README.md):

```bash
cd final
python -m pip install -r requirements.txt
python "Final ranking.py"
python "Sensitivity analysis.py"
python run_frontend.py
```

Sprint board: [Trello](https://trello.com/b/Tz4NyhS6/ais-iot-mcdm-sprints-retrospectives)
