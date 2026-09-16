# Hospital Deployment Risk Diagnostic

One-page Streamlit prototype for choosing a hospital deployment approach. It ports the workbook’s standard, phased and foundations-first choices. The top shows the recommendation, scope, trade-off, conditions that change the choice and unfinished launch work. Case-study detail and optional timing are expandable. Synthetic examples are editable, with separate saved inputs per example in the current session. It does not replace a vendor’s deployment playbook or predict hospital launch success.

## Run

Use Python 3.11 or later. From this folder:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

Upload this folder to a GitHub repository. In Streamlit Community Cloud, choose the repository and `hospital_diagnostic/app.py` (or `app.py` if this folder is the repository root). Set Python 3.11+. No secrets or external services are required. No deployment has been performed by this task.

## Dataset contract

The default `My assessment` is unanswered, with no invented baseline. Fictional examples remain optional. HR/payroll build status and usable connections are separate form fields; their combination feeds the internal approach rule. A task independent of a concurrent HR/payroll build is assessed as a smaller rollout rather than automatically waiting for the entire build. The swimlane separates hospital operations, IT/HR/payroll and the deployment team, with explicit rule, interface and practice return paths. Customer outcome values are hospital inputs. Desired reduction is baseline minus target; measured reduction is baseline minus observed. Neither is a causal estimate. Record a consistent population and measurement period.

`cases.json` separates source observations from proposed rule interpretations:

- `cases`: organization, primary source URL/type, profile, finding IDs, observations/interventions, reported duration and transfer limitations. Missing details stay null or explicitly unknown.
- `rules`: condition, affected stage, proposed priority, exact case/finding references, interpretation, actions, owners and completion evidence. `delay_weeks` remains null until comparable timing evidence exists.
- `stages`: a dependency graph. Workflows and interfaces run in parallel after discovery; testing depends on both.

`model.py` holds no hospital-type penalties, probabilities or invented baseline durations. Profile variables are contextual. Actual rule/data/ownership checks trigger flags. Unknown means confirm, not completed. Choice rules and launch checks are explicitly proposed judgment, not statistically inferred from cases. New HR/payroll requires workflow rules before source build and connections, so its timeline is sequential rather than parallel at that step. Payroll reconciliation applies only to payroll-dependent first launch. No finished checklist automatically approves a launch.

The evidence-only estimate is intentionally unavailable. Ochsner reports four months for a 38-campus expansion, approximately 17.4 weeks using 52.18 weeks/year divided by 12. That endpoint is not contract-to-first-go-live and is not used as a baseline. The optional planning editor uses user-provided stage durations. Its lower/upper critical paths are assumption ranges, not confidence intervals. Durations must include waits and interventions; there is no duplicate delay summation.

Add a case only after checking its original source. Reference exact finding IDs from each rule. Do not infer infrastructure, union status or timing from organization identity. To calibrate time-to-go-live, collect comparable start/end definitions, rollout scope, completed stage timings and interruptions across multiple deployments first.

No patient data is collected. Do not enter confidential customer information into a public demo. An obscure URL or noindex tag is not access control; use restricted sharing if confidentiality matters.

## Tests

```sh
python -m unittest discover -s . -p 'test_*.py'
```

The UI test is skipped if Streamlit is not installed.
