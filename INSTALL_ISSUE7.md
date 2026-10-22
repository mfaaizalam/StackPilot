# Issue #7: Costing and Document tabs (split of the Deployment tab)

This zip is CUMULATIVE: it contains the Issue #9 files too (Issue #7 builds on them).
Unzip over your project root (folder with backend/ and frontend/). Files from Issue #9 are overwritten
with updated versions, so install this zip even if you already installed the Issue #9 one.

## NEW files for Issue #7
backend/app/models/expense.py                    expenses table
backend/app/models/deployment.py                 deployment_plans + deployment_docs tables
backend/app/schemas/expense.py, deployment.py    validation
backend/app/services/costing_calculator.py       category breakdown + activity roll-up (pure)
backend/app/services/costing_service.py          expense CRUD
backend/app/services/deployment_catalog.py       suggestions, pricing, document renderer (pure)
backend/app/services/deployment_service.py       versions + supporting documents
backend/app/routes/costing.py, deployment.py     API
backend/app/data/deployment_services.json        service price table (41 services, ALL verified:false)
backend/alembic/versions/0004_costing_deployment.py
backend/tests/test_costing.py, test_deployment.py
frontend/src/api/deployment.js
frontend/src/pages/DocumentPage.jsx              new "Document" tab
frontend/src/pages/CostingPage.jsx               REWRITTEN: "Costing" tab (2 sub-tabs)
frontend/src/components/costing/*                CategoryBreakdown, ActivityCostTable, ExpensePanel
frontend/src/components/deployment/*             DeploymentWizard, PlanView, SupportingDocs, mdComponents

## CHANGED files (small edits)
backend/app/services/gantt_calculator.py   finance_summary(..., extra_estimated, extra_actual)
backend/app/services/gantt_service.py      payload uses effective costs (+ expenses, categories); delete_activity detaches expenses/increments
backend/app/main.py                        + import models/routers, include_router(costing_router), include_router(deployment_router)
backend/alembic/env.py                     + deployment, expense in model imports
frontend/src/api/gantt.js                  + addExpense / updateExpense / deleteExpense
frontend/src/components/gantt/ActivityTable.jsx   cost fields locked when an activity's cost comes from expense lines
frontend/src/App.jsx                       + route /boards/:boardId/document
frontend/src/components/Sidebar.jsx        "Deployment Document" renamed "Costing"; + "Document" item

## Run
cd backend && pytest        # 232 tests: all pass (your 178 + 54 new)
Start the API: create_all builds the 3 new tables; nothing existing is altered.
(Optional) alembic upgrade head
cd frontend && npm run build   # passes; no new npm packages

## Add hosting cost to Costing (Document tab, one click)
Button "Add to Costing" under the generated document (project manager / admin only). It creates one estimated
"Hosting and infrastructure" expense per PAID service = monthly PKR x chosen months (3 to 36). Running it again
(for example after a new version) replaces the earlier "Deployment vN:" lines so nothing is counted twice;
lines that already have an actual amount are kept. Endpoint: POST /boards/{id}/deployment/plans/{plan_id}/add-to-costing
Note: it prices from the CURRENT price table, so update the table before using it if prices changed since generation.

## IMPORTANT: prices
Every service price in deployment_services.json is APPROXIMATE and verified:false. The UI shows a
"Price not verified" badge and the generated document carries a pricing warning until you check each
vendor page and set "verified": true, plus source and last_updated. The USD to PKR rate (280) is a placeholder.
