# ScenarioForge Backend Audit Report

> **Audited:** 2026-04-16 | **Django 5.0.1** | **5 Django Apps** | **SQLite (not PostgreSQL)**

---

## Project Structure Found

```
Risk Simulator/
├── Config/           # Django project settings (ROOT_URLCONF)
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py / asgi.py
├── Account/          # Custom user + auth
├── core/             # Organisation, UserProfile, dashboard
├── vendors/          # Vendor, IncidentHistory, Certifications, Contacts
├── assessments/      # VendorAssessment, Questions, Templates, Evidence
├── simulations/      # BusinessProcess, ScenarioTemplate, Simulation, Results, Engine
├── manage.py
├── requirements.txt
└── .env
```

---

## 1. Users & Organisations App

| # | Requirement | Status | Details |
|---|-------------|--------|---------|
| 1.1 | Custom User model extending AbstractUser | ✅ | [CustomUser](file:///c:/Users/Admin/Desktop/Risk%20Simulator/Account/models.py#L34-L49) in `Account/models.py`. Email-based auth (`username = None`), UUID PK, `is_verified`, timestamps. |
| 1.2 | Organisation association (ForeignKey on User) | ⚠️ | **Not directly on `CustomUser`.** Organisation link is on [UserProfile](file:///c:/Users/Admin/Desktop/Risk%20Simulator/core/models.py#L35-L78) (`core/models.py`) as `OneToOneField(User)` → `ForeignKey(Organization)`. This is a profile-based indirection, not a direct FK on the User model as spec requires. Functionally works via `request.user.profile.organization`. |
| 1.3 | Role field (admin, analyst, viewer) | ✅ | [UserProfile.role](file:///c:/Users/Admin/Desktop/Risk%20Simulator/core/models.py#L40-L45) with choices: `admin`, `analyst`, `viewer`, `manager`. |
| 1.4 | Organisation model (name, industry, config JSONField) | ✅ | [Organization](file:///c:/Users/Admin/Desktop/Risk%20Simulator/core/models.py#L6-L32) has `name`, `industry`, `size`, `country`, `config` (JSONField). |
| 1.5 | Multi-tenancy support (queries scoped to org) | ✅ | All views consistently use `profile.organization` to scope queries. See [vendor_list_create](file:///c:/Users/Admin/Desktop/Risk%20Simulator/vendors/views.py#L28-L91), [simulation_list_create](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/views.py#L460-L520). |
| 1.6 | JWT authentication (simplejwt) | ✅ | [settings.py](file:///c:/Users/Admin/Desktop/Risk%20Simulator/Config/settings.py#L146-L201): `djangorestframework-simplejwt` configured with access (1h) and refresh (7d) tokens, blacklisting, Bearer auth. |
| 1.7 | Registration endpoint | ✅ | [auth/register/](file:///c:/Users/Admin/Desktop/Risk%20Simulator/Account/views.py#L28-L62) — creates user, sends verification email. |
| 1.8 | Login endpoint | ✅ | [auth/login/](file:///c:/Users/Admin/Desktop/Risk%20Simulator/Account/views.py#L68-L102) — returns JWT access + refresh tokens. |
| 1.9 | Logout endpoint | ✅ | [auth/logout/](file:///c:/Users/Admin/Desktop/Risk%20Simulator/Account/views.py#L109-L121) — blacklists refresh token. |
| 1.10 | Role-based access control | ✅ | Enforced in views: `profile.role not in ['admin', 'analyst', 'manager']` checks throughout. [Permissions endpoint](file:///c:/Users/Admin/Desktop/Risk%20Simulator/core/views.py#L406-L426) returns user capabilities. |

---

## 2. Vendor Management App

| # | Requirement | Status | Details |
|---|-------------|--------|---------|
| 2.1 | Vendor model — basic info (name, industry, services, contact) | ✅ | [Vendor](file:///c:/Users/Admin/Desktop/Risk%20Simulator/vendors/models.py#L7-L136) has `name`, `industry`, `services_provided`, `contact_name`, `contact_email`, `contact_phone`, `website`, `country`, etc. |
| 2.2 | Vendor — risk score field (calculated, stored) | ✅ | `overall_risk_score` (FloatField, editable=False) + `risk_level` (CharField). Auto-calculated on `save()`. |
| 2.3 | Vendor — Organisation ForeignKey (multi-tenancy) | ✅ | `organization = ForeignKey(Organization)` on Vendor model. |
| 2.4 | Self-referential M2M for vendor dependencies | ✅ | [dependent_vendors](file:///c:/Users/Admin/Desktop/Risk%20Simulator/vendors/models.py#L69-L74) = `ManyToManyField('self', symmetrical=False)` with `get_dependency_chain()` method. |
| 2.5 | VendorAssessment model with ForeignKey to Vendor | ✅ | [VendorAssessment](file:///c:/Users/Admin/Desktop/Risk%20Simulator/assessments/models.py#L7-L167) has `vendor = ForeignKey(Vendor)`. |
| 2.6 | Questionnaire responses (JSONField) | ✅ | [responses](file:///c:/Users/Admin/Desktop/Risk%20Simulator/assessments/models.py#L37-L40) = `JSONField(default=dict)`. |
| 2.7 | Six scored risk factors per spec | ⚠️ | **Schema differs from spec.** The spec requires 6 factors: Security Posture (0–100), Data Sensitivity (1–5), Service Criticality (1–5), Incident History (0–100), Compliance Status (0–50), Third-Party Dependencies (0–50). **What's actually on the Vendor model directly:** `security_posture_score` (0–100), `data_sensitivity_level` (1–5), `service_criticality_level` (1–5), `incident_history_score` (0–100), `compliance_score` (0–100 ≠ spec's 0–50), `third_party_dependencies_score` (0–100 ≠ spec's 0–50). The VendorAssessment model instead uses 7 security category scores (access_control, data_protection, network_security, etc.), which doesn't match the spec's 6-factor model. The spec's factors live on the **Vendor** model, not the assessment. |
| 2.8 | Weighted risk formula implementation | ⚠️ | [calculate_risk_score](file:///c:/Users/Admin/Desktop/Risk%20Simulator/vendors/models.py#L101-L132) implements a weighted formula with compliance factor `[1 − (CS/100)]`. However: (a) normalizes DS and SC to 0–100 scale before weighting (reasonable), (b) inverts incident_history_score (debatable — depends on interpretation), (c) compliance_score max is 100 instead of 50. The formula structure matches the spec pattern `base × [1 − (CS/100)]` but parameter ranges differ. |
| 2.9 | Risk categories (Low 0–25, Medium 26–50, etc.) | ✅ | Implemented in [calculate_risk_score](file:///c:/Users/Admin/Desktop/Risk%20Simulator/vendors/models.py#L123-L130). Matches spec thresholds exactly. |
| 2.10 | CRUD API endpoints for Vendors | ✅ | [vendor_list_create](file:///c:/Users/Admin/Desktop/Risk%20Simulator/vendors/views.py#L28-L91) (GET/POST), [vendor_detail](file:///c:/Users/Admin/Desktop/Risk%20Simulator/vendors/views.py#L98-L147) (GET/PUT/PATCH/DELETE). |
| 2.11 | API endpoint to submit/retrieve assessments | ✅ | [assessment_list_create](file:///c:/Users/Admin/Desktop/Risk%20Simulator/assessments/views.py#L31-L94) (GET/POST), [assessment_detail](file:///c:/Users/Admin/Desktop/Risk%20Simulator/assessments/views.py#L101-L153) (GET/PUT/PATCH/DELETE). |
| 2.12 | API endpoint for vendor risk score + category | ✅ | Risk returned via [vendor_detail](file:///c:/Users/Admin/Desktop/Risk%20Simulator/vendors/views.py#L98) response. Dedicated [recalculate_vendor_risk](file:///c:/Users/Admin/Desktop/Risk%20Simulator/vendors/views.py#L151-L172) endpoint. |

---

## 3. Business Process App

| # | Requirement | Status | Details |
|---|-------------|--------|---------|
| 3.1 | BusinessProcess model (name, description, criticality 1–5) | ✅ | [BusinessProcess](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/models.py#L9-L75) in `simulations/models.py`. Has `name`, `description`, `criticality_level` (1–5 choices). |
| 3.2 | M2M to Vendors (dependency mapping) | ✅ | [dependent_vendors](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/models.py#L49-L53) = `ManyToManyField(Vendor)`. |
| 3.3 | Organisation ForeignKey | ✅ | `organization = ForeignKey(Organization)`. |
| 3.4 | CRUD API endpoints | ✅ | [process_list_create](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/views.py#L37-L88) (GET/POST), [process_detail](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/views.py#L95-L136) (GET/PUT/PATCH/DELETE). |
| 3.5 | API endpoint for dependency map | ⚠️ | Vendor dependencies are retrievable via [vendor_dependencies](file:///c:/Users/Admin/Desktop/Risk%20Simulator/vendors/views.py#L210-L242). But there's **no dedicated endpoint** that returns the full vendor → business process dependency map (e.g., "show all processes and which vendors they depend on"). The `BusinessProcessSerializer` only returns `dependent_vendor_names`, not a full graph structure. |

> [!NOTE]
> `BusinessProcess` lives in the `simulations` app rather than its own separate `business_processes` app. This is acceptable for the project scope but differs from the spec's suggestion of a separate app.

---

## 4. Simulation Engine App

### 4.1 Scenario Templates

| # | Requirement | Status | Details |
|---|-------------|--------|---------|
| 4.1.1 | ScenarioTemplate model (type, params schema, description) | ✅ | [ScenarioTemplate](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/models.py#L78-L120) with `scenario_type`, `default_parameters` (JSONField), `calculation_config` (JSONField), `description`. |
| 4.1.2 | All 5 scenario types supported | ✅ | `data_breach`, `ransomware`, `service_disruption`, `supply_chain`, `multi_vendor`. |
| 4.1.3 | Pre-seeded fixture data for all 5 types | ✅ | [seed_scenario_templates.py](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/management/commands/seed_scenario_templates.py) management command creates all 5 templates with default parameters and calculation configs. |

### 4.2 Simulation Execution

| # | Requirement | Status | Details |
|---|-------------|--------|---------|
| 4.2.1 | Simulation model (FK to Vendor, FK to Template, params, status, org, timestamps) | ✅ | [Simulation](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/models.py#L123-L206) has all required fields: `target_vendor`, `scenario_template`, `parameters` (JSONField), `status` (pending/running/completed/failed), `organization`, `started_at`, `completed_at`, `execution_time`. |
| 4.2.2 | SimulationResult model — financial breakdown as JSON | ✅ | [SimulationResult](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/models.py#L209-L350) has `direct_costs`, `operational_costs`, `regulatory_costs`, `reputational_costs`, `total_financial_impact` as separate DecimalFields (better than JSON for querying). Plus `impact_breakdown` JSONField for detailed breakdown. |
| 4.2.3 | Recovery time estimate | ✅ | `estimated_recovery_time_hours` + `recovery_complexity` fields on SimulationResult. |
| 4.2.4 | Cascading impact results | ✅ | `cascading_vendor_impacts` (JSONField) + `total_cascading_impact` (DecimalField) + `affected_processes` (M2M to BusinessProcess). |
| 4.2.5 | Monte Carlo outputs (P50, P90, P95, expected value) | ✅ | `monte_carlo_results` (JSONField) storing mean, median, std_dev, percentiles (50/75/90/95/99), confidence intervals, distribution sample. |

### 4.3 Impact Prediction Algorithms

| # | Requirement | Status | Details |
|---|-------------|--------|---------|
| 4.3.1 | Financial impact calculation per scenario type | ✅ | [SimulationEngine](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/engine.py#L15-L714) implements `_simulate_data_breach()`, `_simulate_ransomware()`, `_simulate_service_disruption()`, `_simulate_supply_chain_compromise()`, `_simulate_multi_vendor_failure()`. Each calculates direct, operational, regulatory, and reputational costs. |
| 4.3.2 | Operational impact calculator (affected processes, productivity losses) | ✅ | All scenario methods query `BusinessProcess.objects.filter(dependent_vendors=self.vendor)` and calculate `productivity_loss_percentage`, `downtime_hours`. |
| 4.3.3 | Recovery time estimator: Base × Complexity × Resource Factor | ⚠️ | Recovery time is calculated using `RECOVERY_TIME_MULTIPLIERS` from settings (per scenario type) and backup availability, but **does not explicitly implement** the three-factor formula `Base Recovery Time × Complexity Factor × Resource Availability Factor` as a named, reusable function. The `estimate_recovery_time()` utility in [utils.py](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/utils.py#L77-L98) exists but is **not called** by the engine — the engine inlines its own calculations. |
| 4.3.4 | Cascading impact modeller (vendor dependency graph) | ✅ | [_calculate_cascading_impacts](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/engine.py#L530-L563) traverses `dependent_vendors` and calculates per-vendor cascade impact. [CascadeAnalyzer](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/utils.py#L173-L250) utility class also provides `trace_dependency_chain()` and `calculate_cascade_probability()`. |

### 4.4 Monte Carlo Simulation

| # | Requirement | Status | Details |
|---|-------------|--------|---------|
| 4.4.1 | Monte Carlo engine (1,000–10,000 iterations) | ✅ | [_run_monte_carlo_simulation](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/engine.py#L608-L668) uses NumPy. Iterations configurable 100–10,000 (model validators). |
| 4.4.2 | Variable parameters sampled from probability distributions | ⚠️ | Currently uses `np.random.normal(1.0, 0.15)` to vary the total cost by ±30%. This is a **single-variable** variation (total cost). The spec implies **each parameter** should be sampled independently from its own distribution. Currently it's a "vary the total" approach, not a "vary each input and re-simulate" approach. |
| 4.4.3 | Output: P50/P90/P95, confidence intervals, expected value | ✅ | Outputs percentiles (50/75/90/95/99), confidence intervals (90%, 95%), mean, median, std_dev, min, max, distribution sample. |

### 4.5 Simulation API Endpoints

| # | Requirement | Status | Details |
|---|-------------|--------|---------|
| 4.5.1 | `POST /simulations/` — create and trigger simulation | ⚠️ | [simulation_list_create](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/views.py#L460-L520) creates the simulation (POST) but does **not auto-trigger execution**. Execution requires a separate `POST /{id}/execute/` call. This is a 2-step process (create → execute) vs spec's single-step. |
| 4.5.2 | `GET /simulations/{id}/` — retrieve status and results | ✅ | [simulation_detail](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/views.py#L523-L547) returns full detail including nested result. |
| 4.5.3 | `GET /simulations/` — list history for vendor/org | ✅ | Supports filtering by `status`, `scenario_type`, `vendor_id`. |
| 4.5.4 | `POST /simulations/{id}/rerun/` — re-run with modified params | ⚠️ | No explicit `/rerun/` endpoint. The [execute_simulation](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/views.py#L550-L601) endpoint supports `force_rerun=true`, but uses the **same parameters**. For modified parameters, the [what_if_analysis](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/views.py#L608-L652) endpoint clones with changes. Not exactly a "rerun with modified params on the same simulation" — it creates a new simulation. |

---

## 5. What-If Analysis

| # | Requirement | Status | Details |
|---|-------------|--------|---------|
| 5.1 | Clone existing simulation with adjusted params | ✅ | [what_if_analysis](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/views.py#L608-L652) clones a simulation with `parameter_changes` overlay. Tags it with `['what-if-analysis', 'base:{id}']`. |
| 5.2 | Side-by-side comparison of two simulation results | ✅ | [compare_simulations](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/views.py#L659-L730) accepts list of simulation IDs, returns comparison_data with financial breakdowns and summary_statistics. |
| 5.3 | Endpoint to compare mitigation strategies | ⚠️ | The compare endpoint provides raw comparison data, but there's **no dedicated mitigation comparison logic** (e.g., "simulate with control X vs without control X"). Users must manually create two what-if scenarios and compare. No mitigation-specific interpretation. |

---

## 6. Analytics & Reporting App

| # | Requirement | Status | Details |
|---|-------------|--------|---------|
| 6.1 | Vendor risk dashboard data endpoint | ✅ | [get_dashboard_overview](file:///c:/Users/Admin/Desktop/Risk%20Simulator/core/views.py#L337-L401) returns summary stats, high-risk vendors, recent simulations, total impact, etc. [get_organization_stats](file:///c:/Users/Admin/Desktop/Risk%20Simulator/core/views.py#L277-L332) returns risk distribution. |
| 6.2 | Simulation history + aggregate statistics | ✅ | [simulation_summary](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/views.py#L733-L795) returns totals, by_scenario_type, by_vendor, highest_impact, avg_recovery. |
| 6.3 | Dependency map data endpoint | ⚠️ | [vendor_dependencies](file:///c:/Users/Admin/Desktop/Risk%20Simulator/vendors/views.py#L210-L242) returns per-vendor dependency chain. But **no single endpoint** returns the full graph structure (all vendors → vendors → business processes) as the spec requires. |
| 6.4 | PDF report generation | ❌ | **Not implemented.** No ReportLab or WeasyPrint dependency. No PDF generation code. The [ReportGenerator](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/utils.py#L353-L430) class generates executive summaries as JSON, not PDF. |
| 6.5 | Risk heatmap data endpoint | ❌ | **No dedicated heatmap endpoint.** Dashboard returns `vendors_by_risk_level` counts, but no structured heatmap data (e.g., vendor × risk-factor matrix). |

---

## 7. Infrastructure & Configuration

| # | Requirement | Status | Details |
|---|-------------|--------|---------|
| 7.1 | PostgreSQL configured | ❌ | [settings.py L93-98](file:///c:/Users/Admin/Desktop/Risk%20Simulator/Config/settings.py#L93-L98): **Using SQLite** (`django.db.backends.sqlite3`). `psycopg2-binary` is in requirements.txt but not configured. |
| 7.2 | DRF installed and configured (pagination, auth, permissions) | ✅ | [REST_FRAMEWORK config](file:///c:/Users/Admin/Desktop/Risk%20Simulator/Config/settings.py#L146-L178): pagination (25/page), JWT auth, IsAuthenticated default, filters, throttling. |
| 7.3 | CORS configured (django-cors-headers) | ✅ | [CORS settings](file:///c:/Users/Admin/Desktop/Risk%20Simulator/Config/settings.py#L220-L227): Specific origins + `CORS_ALLOW_ALL_ORIGINS = True`. |
| 7.4 | NumPy, Pandas, SciPy installed and used | ⚠️ | All three in `requirements.txt`. **NumPy** is actively used in Monte Carlo. **SciPy** is installed but **not imported anywhere** in the codebase. **Pandas** is installed but **not imported anywhere**. |
| 7.5 | Environment variables for secrets | ⚠️ | `SECRET_KEY` uses `os.getenv()` via `.env`. But `.env` file contains the key in **plain text** and the key itself uses `django-insecure-` prefix. `DEBUG`, `ALLOWED_HOSTS`, database credentials are **not** sourced from env vars. |
| 7.6 | URL routing complete for all apps | ✅ | Root [urls.py](file:///c:/Users/Admin/Desktop/Risk%20Simulator/Config/urls.py) includes `Account`, `core`, `vendors`, `assessments`, `simulations`. All app URLs define `app_name` and proper patterns. |
| 7.7 | Admin panel configured for all models | ✅ | All models registered: [Account admin](file:///c:/Users/Admin/Desktop/Risk%20Simulator/Account/admin.py), [core admin](file:///c:/Users/Admin/Desktop/Risk%20Simulator/core/admin.py), [vendors admin](file:///c:/Users/Admin/Desktop/Risk%20Simulator/vendors/admin.py), [assessments admin](file:///c:/Users/Admin/Desktop/Risk%20Simulator/assessments/admin.py), [simulations admin](file:///c:/Users/Admin/Desktop/Risk%20Simulator/simulations/admin.py). |

---

## Summary Scoreboard

| Area | ✅ Done | ⚠️ Partial | ❌ Missing | Total |
|------|---------|------------|-----------|-------|
| 1. Users & Orgs | 9 | 1 | 0 | 10 |
| 2. Vendor Management | 10 | 2 | 0 | 12 |
| 3. Business Process | 4 | 1 | 0 | 5 |
| 4. Simulation Engine | 12 | 4 | 0 | 16 |
| 5. What-If Analysis | 2 | 1 | 0 | 3 |
| 6. Analytics & Reporting | 2 | 1 | 2 | 5 |
| 7. Infrastructure | 4 | 2 | 1 | 7 |
| **TOTAL** | **43** | **12** | **3** | **58** |

> **Overall: 74% fully implemented, 21% partially implemented, 5% missing.**

---

## Critical Gaps Blocking Core Functionality

> [!WARNING]
> ### 1. SQLite Instead of PostgreSQL
> The project spec explicitly requires PostgreSQL. The current SQLite configuration (`db.sqlite3`) isn't suitable for production and lacks JSON operators, full-text search, and concurrent write support that the simulation engine may need at scale.

> [!IMPORTANT]
> ### 2. No PDF Report Generation
> This is a **complete feature gap**. No library (ReportLab/WeasyPrint) is installed, no generation code exists. The `ReportGenerator` utility only produces JSON summaries.

> [!IMPORTANT]
> ### 3. Monte Carlo Varies Total, Not Individual Parameters
> The current Monte Carlo applies a single normal distribution multiplier to the total cost. The spec implies each variable parameter should be sampled independently from its own distribution and the simulation re-run per iteration. This is a sophistication gap that affects the scientific validity of the probabilistic analysis.

---

## Recommended Next 5 Tasks (Priority Order)

### 1. 🔴 Switch Database to PostgreSQL
**Why:** Spec requirement, production readiness, and JSON query support.
**What:** Update `DATABASES` in `settings.py` to use `psycopg2-binary` with env vars for host/port/name/user/password. Run `migrate`.

### 2. 🔴 Implement PDF Report Generation
**Why:** Completely missing spec feature with high visibility.
**What:** Add `reportlab` or `weasyprint` to requirements. Create a `reports/` module or endpoint (`GET /simulations/{id}/report/pdf/`) that renders simulation results as a branded PDF with financial breakdown, charts, and executive summary.

### 3. 🟠 Enhance Monte Carlo to Vary Individual Parameters
**Why:** Current approach lacks scientific rigour — a single-variable normal distribution on the total doesn't model parameter uncertainty.
**What:** In `_run_monte_carlo_simulation()`, vary each input parameter (records_compromised, downtime_hours, etc.) independently from appropriate distributions (normal, lognormal, triangular), then re-run the financial calculation per iteration.

### 4. 🟠 Add Risk Heatmap & Full Dependency Map Endpoints
**Why:** Two spec-required analytics endpoints are missing.
**What:**
- `GET /core/organization/heatmap/` — return vendor × risk-factor matrix data
- `GET /simulations/processes/dependency-map/` — return full graph of vendors → vendors → business processes

### 5. 🟡 Align VendorAssessment Schema With Spec's 6 Risk Factors
**Why:** The assessment model uses 7 generic security categories instead of the spec's 6 specific risk factors (Security Posture, Data Sensitivity, Service Criticality, Incident History, Compliance Status, Third-Party Dependencies).
**What:** Either add the 6 spec factors to `VendorAssessment` as scored fields, or document the mapping between the current 7 categories and the 6 factors. Ensure the weighted formula from the spec is applied on assessment completion.

---

## Bonus Observations

| Item | Note |
|------|------|
| `ENV/` directory | Empty directory in project root — unused |
| `SciPy` + `Pandas` | In requirements but never imported. Consider using SciPy for distribution fitting and Pandas for data aggregation in analytics |
| `CORS_ALLOW_ALL_ORIGINS = True` | Security risk — overrides `CORS_ALLOWED_ORIGINS`. Remove for production |
| `ALLOWED_HOSTS = []` | Must be set for production deployment |
| `db.sqlite3` committed | 663KB database file in repo root |
| `SimulationScenario` + `SimulationComparison` models | Defined but have **no views or URL endpoints** — unused models |
| `ImpactCalculator` utilities | Defined in `utils.py` but **not called** by the engine — engine has inline calculations |
| Vendor compliance_score range | Model allows 0–100, spec says 0–50 |
| Vendor third_party_dependencies_score range | Model allows 0–100, spec says 0–50 |
