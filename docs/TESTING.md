# Testing Strategy & Automated Test Suite

---

## 1. Overview & Testing Philosophy

The platform's testing strategy enforces high rigor across three distinct operational layers:
1. **Deterministic Accuracy**: Mathematical verification of all nutritional calculations, cooked yields, and volume conversions against laboratory INDB benchmarks.
2. **Safety & Uncertainty Guardrails**: Guaranteeing medical disclaimers, rejection of eating disorder prompts, and confidence score degradation for generic volume fallbacks.
3. **Agent State Graph & Reflection**: Verifying the LangGraph tool-calling loop and ensuring the post-action reflection node catches invalid numbers and evaluates goal impacts before replying.

---

## 2. Test Suite Breakdown

All 19 automated tests are located in `backend/tests/`:

| Test Module | Tests Count | Focus & Invariants Verified |
| :--- | :--- | :--- |
| `test_unit_converter.py` | 3 | Food-specific densities (e.g. 1 cup cooked rice = 150g, 1 cup dal = 240g), serving unit conversions, and fallback confidence degradation to $\le 0.65$. |
| `test_nutrition_engine.py` | 2 | Per 100g scaling, Method C cooked recipe yields, raw vs cooked densities, zero LLM arithmetic. |
| `test_auth_and_isolation.py` | 2 | Bcrypt authentication, JWT lifecycle, and strict isolation preventing User A from accessing User B's meals/recipes. |
| `test_uncertainty_and_safety.py` | 2 | Rejection of medical diagnosis, eating disorder safeguards, medical disclaimer attachment, multiple-choice clarification generation. |
| `test_agent_tools.py` | 2 | Execution of all 20 deterministic tools, argument parsing, error handling, and database integration. |
| `test_post_action_reflection.py` | 2 | LangGraph post-action reflection node: range checks ($0 \le \text{cal} \le 5000$), macro conservation balance, remaining goal tracking, uncertainty propagation. |
| `test_health_and_energy_balance.py` | 2 | Telemetry ingestion from Health Connect, Energy Balance calculation ($E_{balance} = C_{in} - C_{out}$), deficit/surplus classification. |
| `test_proactive_notifications.py` | 2 | Scheduled meal unlogged detection, quiet hours suppression, user-configurable meal schedule times. |
| `test_analytics.py` | 2 | Daily macro progress rings/bars, weekly/monthly period reports, period delta comparison metrics. |

**Current Test Status:** **19 / 19 PASSED (100% Success Rate)**

---

## 3. How to Run the Test Suite

```powershell
# Navigate to backend directory
cd "E:\BMSCE\3rd Sem\AAI\Nutrition_Manager\backend"

# Execute full pytest suite with verbose output
.venv\Scripts\pytest.exe -v
```

### Running Specific Test Modules
```powershell
# Run post-action reflection tests:
.venv\Scripts\pytest.exe tests/test_post_action_reflection.py -v

# Run health and energy balance tests:
.venv\Scripts\pytest.exe tests/test_health_and_energy_balance.py -v

# Run unit converter tests:
.venv\Scripts\pytest.exe tests/test_unit_converter.py -v
```
