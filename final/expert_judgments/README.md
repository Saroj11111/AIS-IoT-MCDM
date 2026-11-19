# AHP expert judgments

The three AHP weight sets in `AHP weight.py` come from three language models acting as experts.
Each model got the same prompt (`question_prompt.txt`) in a new chat. Their full replies are saved here unchanged.

| File | Expert | Used as | Priority order | CR |
|---|---|---|---|---|
| `claude_ahp.txt` | Claude | AHP 1 | LH > ST > AD > DS > SL > DEF > RES | 0.025 |
| `chatgpt_ahp.txt` | ChatGPT | AHP 2 | LH > ST > DEF > RES > AD > DS > SL | 0.018 |
| `gemini_ahp.txt` | Gemini | AHP 3 | LH > DS > ST > AD > SL > DEF > RES | 0.039 |

CR is worked out by `AHP weight.py` (run `python "AHP weight.py"` in the `final` folder). All three are under 0.10, so all three are consistent.

Note on the Gemini reply: it came back with no line breaks, so the last judgment and the matrix heading run together ("LH vs DS = 37x7 Pairwise..."). The value is 3, which matches Gemini's own matrix (LH row, DS column = 3).

The 21 values from each reply are typed into `EXPERTS` near the top of `AHP weight.py`.
