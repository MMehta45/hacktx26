# Live Nessie customer dashboard progress

## Implemented

- Expanded the fictional profile to Maya Rodriguez, age 29, an hourly employee in
  Austin, Texas.
- Added an idempotent backend-only Nessie seeder for a checking account, merchants,
  72 purchases, 13 weekly deposits, four withdrawals, and five pending bills.
- Added safe account regeneration through `npm run seed:customer:reset` and an ignored
  ID-only manifest at `backend/.local/nessie-seed.json`.
- Normalized purchases, deposits, withdrawals, bills, accounts, and provenance into the
  versioned customer snapshot contract.
- Added category totals, three-month averages, percentages, transaction counts,
  recurring/irregular amounts, and essential/discretionary labels.
- Added explicit weekly income entries and a date-specific 30-day cash-flow baseline.
- Added dashboard sections for customer/account overview, filtered transaction history,
  spending, bills, income, and the cash-flow timeline.
- Preserved preview-only labels for all future graph, research, question, and plan areas.

## Seeded ledger target

| Resource | Intended count/value |
| --- | ---: |
| Purchases | 72 totaling $7,250 |
| Deposits | 13 totaling $8,320 |
| Withdrawals | 4 totaling $1,070 |
| Pending bills | 5 |
| Final checking balance | $310 |

Historical credits and debits both total $8,320. The fixture follows the same ledger and
is always labeled as a fixture.

## Verification

- Backend Ruff: passed.
- Backend tests: 7 passed.
- Frontend Vitest: 2 passed.
- TypeScript: passed.
- ESLint: passed.
- Production Next.js build: passed.
- Local backend health, frontend page, and frontend-to-backend snapshot proxy: HTTP 200
  on ports 8010/3010.
- Live Nessie seed: passed. The first run created the resources and the second reported
  reuse with the same 72 purchases, 13 deposits, four withdrawals, and five bills.
- Live frontend proxy readback: passed with 89 transactions, five Nessie bills, a $310
  live balance, and 31 daily cash-flow points.
- Wage isolation: passed. Changing the hourly wage from $20 to $25 kept all 89 Nessie
  transaction IDs unchanged while weekly gross moved from $800 to $1,000 and estimated
  take-home moved from $640 to $800.

## Live Nessie results

| Result | Readback |
| --- | --- |
| Customer ID | `99a9007d-cfd0-42ed-9973-64314bb66c94` |
| Account ID | `9ec6b70d-c0e5-42c8-bedd-043aff2335b6` |
| Purchases | 72 |
| Deposits | 13 |
| Withdrawals | 4 |
| Bills | 5 |
| Final Nessie balance | $310.00 |

The bill readback preserved `pending` status, `payment_date`,
`upcoming_payment_date`, `recurring_date`, and `payment_amount` for all five resources.
The tested purchase, deposit, withdrawal, and bill routes worked with the documented
fields. No live API discrepancy was observed in this seed. The normalizer still accepts
either documented bill date field and sanitized failures because sandbox behavior can
change.

## Local configuration

The ignored `backend/.env` is configured with permission mode `0600` and strict Nessie
mode. To regenerate the live account and its history intentionally, run:

```bash
npm run seed:customer:reset
```

The ignored manifest contains resource IDs only. No credentials are stored in this report,
source code, frontend environment, or browser bundle.
