---
section_code: "PENDING-SMC-2026"
title: "Pending changes to the Skilled Migrant Category Resident Visa and Work to Residence visas"
category: "Residence > Skilled Migrant Residence Instructions (PENDING, not yet in force)"
source_url: "https://www.immigration.govt.nz/about-us/news-centre/final-details-about-changes-to-the-skilled-migrant-category-resident-visa-and-work-to-residence-visa/"
related_source_url: "https://www.immigration.govt.nz/about-us/news-centre/changes-to-the-skilled-migrant-category-resident-visa-announced/"
published_date: "2026-06-18"
takes_effect_date: "2026-08-24"
fetched_date: "2026-08-09"
status: "PENDING -- not yet in force as of fetch date. Do not treat as current policy until on or after 24 August 2026."
---

# Pending changes to the Skilled Migrant Category Resident Visa and Work to Residence visas

**This is a news announcement, not an operational manual clause.** It describes changes that take effect **24 August 2026**. Until that date, the current SR3.x clauses already in this corpus (effective 09/03/2026) remain the correct answer. This file exists so the app can tell people what's *coming*, without misrepresenting it as already in force.

Originally announced 23 September 2025, with further detail released 5 March 2026, and these final details confirmed 18 June 2026.

## Two new SMC pathways (in addition to the existing points-based pathway)

- **Skilled Work Experience pathway** — for ANZSCO skill level 1-3 roles, at least 5 years directly relevant work experience, including 2 years in New Zealand at 1.1x the median wage.
- **Trades and Technician pathway** — relevant Level 4+ qualification on the NZQCF, at least 4 years post-qualification experience, including 18 months in New Zealand at or above the median wage. New Zealand qualifications need at least 120 credits (can combine a prerequisite lower qualification's credits to reach this). Overseas qualifications need an International Qualification Assessment (IQA) at Level 4 or higher; the 120-credit rule doesn't apply to these.
- Self-employment cannot count as directly relevant work experience under either new pathway.

## Points system change (existing points-based pathway)

- Points for a **bachelor's degree increase from 3 to 4**.
- Points for **Washington/Sydney Accord accredited qualifications also increase from 3 to 4**.
- Points for **master's and doctoral degrees remain unchanged** (i.e. this is NOT a blanket increase across all qualification levels, only bachelor's-level claims go up).
- Applicants claiming points for a Level 8 or Level 9 qualification must now also hold a supporting bachelor's degree (or equivalent), **except** those claiming the 5-point New Zealand master's, who don't need to separately prove a bachelor's.

## Wage threshold simplification

- Most SMC applicants will now only need to meet **one** wage threshold, instead of one rate during work experience and a potentially higher rate at residence application time.
- The applicable threshold is generally the one in effect when the applicant **started** accruing skilled work experience, not the one in effect when invited to apply for residence.
- A grace period applies: if skilled work experience starts within 5 months of the relevant work visa being granted, the threshold in effect on the visa grant date applies, even if the threshold has since increased.
- This same alignment applies to Work to Residence, Care Workforce Work to Residence, and Transport Work to Residence visas. The 24-months-of-work-experience-within-30-months requirement for these categories is unchanged.

## Genuine employment definition tightened

Immigration instructions now require offers of employment to be "available and ongoing" with a "genuine need to be based in New Zealand," broadly aligning the skilled-residence genuine employment test with the Accredited Employer Work Visa (AEWV) definition. INZ states most applications won't be affected; this mainly gives INZ clearer grounds to decline where employment genuineness is already in question.

## What this means for the app, specifically

Once the actual SR3.x manual clauses are updated by INZ on/around 24 August 2026, the update pipeline (`check_for_updates.py`) should catch the effective-date change automatically and re-embed them. This file should then be marked superseded (or deleted) once the real manual clauses reflect these changes, since at that point the manual itself becomes the authoritative source again, not this announcement.
