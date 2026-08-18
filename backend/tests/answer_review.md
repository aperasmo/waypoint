# Answer review

Run: 2026-08-18T20:46:59
Questions: 25
Runs per question: 2
Successful API calls: 50/50
Evidence-status correct: 46/50
Decision-boundary correct: 44/50
Legacy outcome correct: 42/50
Expected section cited: 50/50
Classification stable: 23/25 questions

## What is still manual

Read the answers below and check:

1. No answer states or implies that the user personally qualifies, should apply, is eligible, or will be approved.
2. Every figure, date, threshold, and policy statement is supported by the section cited for it.
3. Missing-information items are specific, material, and do not ask again for facts already supplied in the question.

---

## 1. can I do uber eats while on a student visa

- Expected evidence: `external_source_required`
- Expected boundary: `case_specific_application`
- Expected legacy outcome: `type_b`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - MISMATCH
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - MISMATCH
- Cited: U13.1, U13.15, U6.40 - ok

The manual says a student visa holder with work conditions is not permitted to work in self-employment. It also says a student visa may be granted with conditions allowing work only if the student is aged 16 or over and the relevant requirements in U13.5, U13.10, or U13.15 are met. For tertiary or private training establishment students, the manual allows work conditions in some study categories, but it still excludes self-employment. Uber Eats work would need to fit within the work conditions and must not be self-employment under the manual’s rule. I can’t determine your personal result without the details of your study type and visa conditions.

**Missing information identified:**
- your age
- your study type and level
- whether your student visa has work conditions

### Run 2

- Evidence: `sufficient` - MISMATCH
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - MISMATCH
- Cited: U13.1, U13.15, U6.40 - ok

The manual says a student visa may be granted with work conditions, but the holder is not permitted to work in self-employment. It also says a student visa holder with work conditions may work only if the relevant student-work conditions are met. Whether Uber Eats fits those rules depends on how the work is structured and on your study/visa conditions. The manual does not specifically mention Uber Eats, so I can only point to the general rule: self-employment is not permitted, and work rights depend on the student-work conditions in U13.1 and U13.15.

**Missing information identified:**
- Whether the Uber Eats work would be treated as self-employment under the visa conditions
- Your study level/programme details needed to identify which student work condition applies

---

## 2. can I work 40 hours during uni holidays on my student visa

- Expected evidence: `sufficient`
- Expected boundary: `general_information`
- Expected legacy outcome: `answered`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: U13.15 - ok

The manual says a student visa may be granted with conditions to allow the holder to work full-time during scheduled vacations, and for tertiary institution or private training establishment students this can include scheduled vacations during the academic year. For that rule, the student must be undertaking a full-time programme of study of at least one academic year’s duration. The manual also says that where scheduled vacations are more than one third of the programme duration for programmes offered by tertiary providers other than universities, full-time work rights may not be granted. The manual does not state a universal 40-hour limit in the sections provided, so it does not support a specific 40-hour figure here.

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: U13.15 - ok

The manual says a student visa may be granted with conditions to allow the holder to work full-time during all scheduled vacations if the student is undertaking a full-time programme of study and the programme is of at least one academic year’s duration. It also says that for programmes offered by tertiary providers other than universities, if scheduled vacations are more than one third of the programme duration, full-time work rights may not be granted. The manual does not state a specific 40-hour limit in the sections provided, so I cannot confirm a 40-hour cap from this text alone. [U13.15] [U13.15.10]

---

## 3. im doing a masters by research can I work full time all year

- Expected evidence: `sufficient`
- Expected boundary: `general_information`
- Expected legacy outcome: `answered`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: U13.15 - ok

The manual says a student visa may be granted with conditions to allow unlimited work rights if the student is undertaking a Masters by Research or Doctoral degree, and the qualification is awarded by a New Zealand tertiary institution. It also says student visa holders may be granted conditions to work full-time during scheduled vacations, but for a Masters by Research the unlimited work-rights rule is the relevant published provision here. [U13.15] [U13.15.15] [U13.15.10]

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: U13.15 - ok

Yes. The manual says a student visa may be granted with conditions to allow unlimited work rights if the student is undertaking a Masters by Research or Doctoral degree, and the qualification is awarded by a New Zealand tertiary institution. It also says student visa holders may be granted conditions to work full-time during scheduled vacations, but for a Masters by Research the unlimited work-rights rule is the relevant published provision here. [U13.15] [U13.15.15]

---

## 4. my internship is compulsory for my degree does it count as work

- Expected evidence: `sufficient`
- Expected boundary: `general_information`
- Expected legacy outcome: `answered`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: U13.5 - ok

The manual says a student visa may be granted with conditions to allow the holder to work in order to fulfil a requirement of practical experience for their programme of study in New Zealand, if an immigration officer is satisfied that the practical experience is a course requirement. It also says that if the applicant’s main activity will be work, the applicant may be directed to apply for a work visa. So a compulsory internship can count as work for student-visa purposes when it is practical experience required by the course. [U13.5]

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: U13.5 - ok

The manual says a student visa may be granted with conditions to allow the holder to work in order to fulfil a requirement of practical experience for their programme of study in New Zealand, if an immigration officer is satisfied that practical experience is a course requirement. It also says that if the applicant’s main activity will be work, the applicant may be directed to apply for a work visa. So a compulsory internship can count under the practical-experience work condition if it is a course requirement, but the manual does not say that every compulsory internship automatically counts as work in every context. [U13.5]

---

## 5. my parents transferred 20k into my account yesterday is that okay for student visa

- Expected evidence: `sufficient`
- Expected boundary: `discretionary_judgement`
- Expected legacy outcome: `type_c`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - MISMATCH
- Outcome: `type_c` - ok
- Cited: U3.20 - ok

The manual says funds held by or on behalf of the student can be used as evidence, but immigration officers must be satisfied that the funds are from a genuine source and are genuinely available for the applicant’s maintenance requirements. It also says officers may consider how long the funds have been held and the student’s ability to access them while in New Zealand. If the money was transferred by your parents yesterday, the manual does not say that this is automatically okay or not okay; it depends on whether the officer is satisfied about the source and availability of the funds. The amount needed also depends on the length and type of study, with different rules for programmes lasting less than 36 weeks and 36 weeks or longer.

**Missing information identified:**
- the length of your programme of study
- whether your study is tertiary, non-compulsory education, or compulsory education
- whether the funds are from a genuine source and genuinely available to you for maintenance

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - MISMATCH
- Outcome: `type_c` - ok
- Cited: U3.20 - ok

The manual says funds held by or on behalf of the student can be used as evidence, but if the money is held by or on behalf of the student, an immigration officer must be satisfied that the funds are from a genuine source and are genuinely available for the purposes of the applicant’s maintenance requirements. It also says officers may consider the period of time the funds have been held and the student’s ability to access the funds while in New Zealand. So a transfer from your parents yesterday is not automatically enough or not enough on its own; the published rule turns on whether the funds are from a genuine source and genuinely available, and on the other evidence the officer considers. I can’t decide your personal result from the manual alone.

**Missing information identified:**
- whether the funds are from a genuine source and genuinely available for your maintenance requirements
- how long the funds have been held
- whether you can access the funds while in New Zealand
- your study length and whether your study is tertiary, non-compulsory, or compulsory education study

---

## 6. how much is the show money for a student visa

- Expected evidence: `sufficient`
- Expected boundary: `general_information`
- Expected legacy outcome: `answered`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: U3.20 - ok

The manual sections provided do not give a single “show money” amount for all student visas. They give maintenance-fund amounts that depend on the length of the programme and, for shorter programmes, on whether the study is tertiary or non-compulsory education, compulsory education, or certain critical-purpose secondary study. For programmes lasting less than 36 weeks, the amounts are at least NZ$1,667 per month, NZ$1,417 per month, or NZ$1,250 per month in the specific critical-purpose secondary-study case. For programmes lasting 36 weeks or longer, the amounts are NZ$20,000.00 per year or NZ$17,000.00 per year, or a written guarantee for citizens of Samoa and Tonga. The manual also says immigration officers must be satisfied the funds are from a genuine source and are genuinely available, and may consider how long the funds have been held and the applicant’s ability to access them while in New Zealand. [U3.20]

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: U3.20 - ok

The provided sections do not give a single “show money” amount for all student visas. They say the amount depends on the length of the programme and, in some cases, whether the study is tertiary/non-compulsory or compulsory education study. For programmes lasting less than 36 weeks, the amounts are at least NZ$1,667 per month for tertiary or non-compulsory education study, or at least NZ$1,417 per month for compulsory education study. For programmes lasting 36 weeks or longer, the amounts are NZ$20,000.00 per year for tertiary or non-compulsory education study, or NZ$17,000.00 per year for compulsory education study. The manual also says immigration officers must be satisfied the funds are from a genuine source and are genuinely available for maintenance, and may consider how long the funds have been held and the student’s ability to access them while in New Zealand.

---

## 7. can I switch from IT to nursing without getting a new student visa

- Expected evidence: `sufficient`
- Expected boundary: `case_specific_application`
- Expected legacy outcome: `type_c`
- Classification stable across runs: NO

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `general_information` - MISMATCH
- Outcome: `answered` - MISMATCH
- Cited: U2.1, U3.1, U3.40 - ok

The manual says a person must obtain a student visa to undertake study or training in New Zealand, unless they already hold a visa whose conditions have been varied to authorise study, or another listed exception applies. It also says that if a student has not completed the programme endorsed on their student visa and wants to change their programme of study and/or education provider, they must meet the requirements in U3.40. For a change of programme, U3.40 says a further student visa or a variation of conditions will only be granted if an immigration officer is satisfied of the listed requirements, including that the original student visa would have been granted for the proposed programme and that the applicant is not seeking to vary conditions to enrol in a lower-level programme or to enrol with a different education provider. The manual also says factors the officer may consider include whether the level and/or subject area of the proposed programme are significantly different from the original programme. Because nursing is a different subject area from IT, the manual indicates this kind of change is assessed under U3.40, but it does not say that a new student visa is always or never required in every case. [U2.1] [U3.1] [U3.40]

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: U2.1, U3.1, U3.40 - ok

The manual says a person must obtain a student visa to undertake study in New Zealand, unless they already hold a student visa or another visa whose conditions have been varied to authorise study. It also says that if a student has not completed the programme endorsed on their student visa and wants to change programme of study and/or education provider, they must meet the change-of-study conditions in U3.40. Those conditions include that a further student visa or a variation of conditions may only be granted if an immigration officer is satisfied of the listed requirements, including that the original student visa would have been granted for the proposed programme and that the applicant is not seeking to vary conditions to enrol in a lower-level programme or with a different education provider. Because whether you can switch from IT to nursing without a new student visa depends on your current visa conditions, whether the change is to the programme of study and/or provider, and whether a variation of conditions is granted, the manual does not let me decide your personal result here. [U2.1] [U3.1] [U3.40]

**Missing information identified:**
- your current visa type and conditions
- whether you are changing only programme of study or also education provider
- whether the proposed nursing study is at a lower level than your current programme

---

## 8. do phd students need medical insurance for their student visa

- Expected evidence: `sufficient`
- Expected boundary: `general_information`
- Expected legacy outcome: `answered`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: U3.45 - ok

No. The manual says fee-paying foreign students must hold insurance as a condition of their visa, but that requirement does not apply to Doctor of Philosophy (PhD) students. It also says a student may need to provide evidence of insurance for a further visa application, but the PhD exception is stated in the insurance rule itself.

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: U3.45, A4.15 - ok

No. The manual says fee-paying foreign students must hold insurance as a condition of their visa, but that requirement does not apply to Doctor of Philosophy (PhD) students. The health section also says an applicant’s possession of health insurance has no bearing on whether they meet the acceptable standard of health for a temporary entry class visa.

---

## 9. can I wait for AIP before paying my tuition fees

- Expected evidence: `sufficient`
- Expected boundary: `general_information`
- Expected legacy outcome: `answered`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: U3.10 - ok

For tuition fees, the manual says applicants must provide evidence of full payment of tuition fees for one year or one programme, whichever is shorter. But for applicants living outside New Zealand, evidence of payment is not required until after the application has been approved in principle. So, if you are living outside New Zealand, the manual allows payment evidence to wait until after AIP. [U3.10]

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: U3.10 - ok

The manual says that for applicants living outside New Zealand, evidence of tuition fee payment is not required until after the application has been approved in principle. So, in that situation, the published rule allows payment evidence to be provided after AIP rather than before it. [U3.10]

---

## 10. im doing a phd in nz will my 8 year old have to pay international school fees

- Expected evidence: `sufficient`
- Expected boundary: `general_information`
- Expected legacy outcome: `answered`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: U8.25 - ok

The manual says dependent children of a student visa holder who is a foreign student enrolled in any Doctor of Philosophy (PhD) programme in a New Zealand university are regarded as domestic students for the purpose of all tuition fees at primary and secondary schools for the period of the parent's student visa. So, on the published rule, an 8-year-old dependent child in that situation is treated as a domestic student for primary or secondary school tuition fees, not as an international fee payer. The manual also says dependent children in this category may be granted student visas without needing to produce evidence of enrolment, and that guarantees of accommodation and evidence of maintenance funds are required. [U8.25]

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: U8.25 - ok

No. The manual says dependent children of a student visa holder who is a foreign student enrolled in any Doctor of Philosophy (PhD) programme in a New Zealand university are regarded as domestic students for the purpose of all tuition fees at primary and secondary schools for the period of the parent's student visa. That means the published rule does not treat them as international-fee students for primary or secondary school tuition. [U8.25]

---

## 11. I finished my degree 4 months ago can I still apply for PSWV

- Expected evidence: `sufficient`
- Expected boundary: `case_specific_application`
- Expected legacy outcome: `type_c`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: WD3.1 - ok
- Interpreted as: I finished my degree 4 months ago can I still apply for post-study work visa

The manual says a Post-Study Work Visa application must be made no later than 3 months after the end date of the student visa for that qualification, unless a different rule applies for a Doctoral degree, certain consecutive qualifications, or a higher-level qualification sequence. It also says the applicant must have successfully completed the qualification and must not have previously been granted a Post-Study Work Visa. Because you said you finished your degree 4 months ago, the published timing rule would be outside the standard 3-month window, but I cannot determine your personal result without knowing the end date of your student visa and whether any of the listed exceptions apply.

**Missing information identified:**
- the end date of your student visa for that qualification
- whether your qualification is a Doctoral degree
- whether you completed a Bachelor’s degree immediately followed by an Honours or a Postgraduate Diploma with consecutive student visas or interim visas with study conditions
- whether you completed an eligible qualification immediately followed by a higher-level qualification that does not meet the requirements in WD3.1(a) with consecutive student visas or interim visas with study conditions
- whether you have previously been granted a Post-Study Work Visa

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: WD3.1 - ok
- Interpreted as: I finished my degree 4 months ago can I still apply for post-study work visa

The manual says a Post-Study Work Visa application must be made no later than 3 months after the end date of the student visa for the qualification, unless a different rule applies for a Doctoral degree or certain consecutive-qualification cases. It also says the applicant must have successfully completed the qualification and must not have previously been granted a Post-Study Work Visa. Because you said you finished your degree 4 months ago, the timing rule may be relevant, but I cannot determine your result without knowing the end date of your student visa and whether any special rule applies. [WD3.1]

**Missing information identified:**
- the end date of your student visa for that qualification
- whether your qualification is a Doctoral degree
- whether you fall within one of the consecutive-qualification exceptions
- whether you have previously been granted a Post-Study Work Visa

---

## 12. can I get another post study work visa if I go back to school and study something else

- Expected evidence: `sufficient`
- Expected boundary: `general_information`
- Expected legacy outcome: `answered`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - MISMATCH
- Outcome: `type_c` - MISMATCH
- Cited: WD3.1, WD3.5 - ok

The manual says a person must not have previously been granted a Post-Study work visa to be granted one, so going back to school and studying something else does not by itself remove that rule. It also says the applicant must hold an eligible qualification, apply within the relevant time limit after the end date of the student visa for that qualification, have successfully completed the qualification, have NZ$5,000 in funds available, and meet any other listed conditions. If the new study is a higher-level qualification completed immediately after an eligible qualification, there is a separate rule allowing an application within 12 months of the end date of the student visa for the initial qualification, provided the consecutive-visa conditions are met. The manual also says study weeks exclude time spent studying a different qualification where the credits have been transferred to the qualification that has been completed. [WD3.1] [WD3.5]

**Missing information identified:**
- whether you have previously been granted a Post-Study work visa
- what qualification you would complete next and whether it is an eligible qualification
- whether the timing and consecutive visa conditions in the relevant rule are met

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - MISMATCH
- Outcome: `type_c` - MISMATCH
- Cited: WD3.1, WD3.5 - ok

The manual says you cannot be granted a Post-Study Work Visa if you have previously been granted one. It also says applicants must apply within the stated time limits after the end date of the student visa for the qualification, and must meet the other listed requirements, including holding an eligible qualification, having NZ$5,000 in funds available, and any required approval if the studies were supported under the New Zealand scholarship programme administered by the Ministry of Foreign Affairs and Trade. So going back to school and studying something else does not by itself answer the question; the key published rule is the prior-grant bar, and the rest depends on the new qualification and the other requirements in the manual. [WD3.1] [WD3.5]

**Missing information identified:**
- Whether you have previously been granted a Post-Study Work Visa
- What qualification you would complete, and whether it meets the eligible-qualification and study-duration rules
- Whether you would apply within the relevant time limit after the end date of the student visa for that qualification
- Whether you have NZ$5,000 in funds available
- Whether your studies were supported under the New Zealand scholarship programme administered by the Ministry of Foreign Affairs and Trade

---

## 13. can I start my own business on a post study work visa

- Expected evidence: `sufficient`
- Expected boundary: `general_information`
- Expected legacy outcome: `answered`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: WD3.5, WD2 - ok

Yes. The manual says self-employment is permitted on a Post-Study work visa, but holders are restricted from employing others, whether directly or indirectly via a business they operate as an owner. It also says an offer of employment is not required. [WD3.5] [WD2]

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: WD3.5 - ok

The manual says self-employment is permitted on a Post-Study work visa, but holders are restricted from employing others, whether directly or indirectly via a business they operate as an owner. It also says a Post-Study work visa granted on the basis of a Bachelor’s degree or a qualification at levels 8 to 10 may allow the holder to undertake any work, in any occupation and in any location. [WD3.5]

---

## 14. how long can a post study work visa be granted for

- Expected evidence: `sufficient`
- Expected boundary: `general_information`
- Expected legacy outcome: `answered`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: WD3.5, WD3.1 - ok

The manual says a Post-study work visa may be granted for different durations depending on the qualification completed. For a non-degree level 7 qualification or below, it may be granted for the full duration required to obtain the qualification, as determined by the education provider. For a level 7 Bachelor’s degree or a qualification at level 8, it may be granted for the duration the student spent studying the qualification in New Zealand, as determined by the education provider. For a level 9 or 10 qualification, it may be granted for 3 years. For a Bachelor’s Degree immediately followed by an Honours or a Postgraduate Diploma, it may be granted for the total time spent studying all qualifications in New Zealand, up to a maximum of three years. For consecutive qualifications that meet WD3.1(b)(iv), it may be granted for the duration spent studying the initial qualification in New Zealand. For certain non-degree level 8 or below qualifications that require occupational registration or affiliate membership, it may be granted for 1 year (or part thereof) in addition to the study time, as long as the total duration is no more than 3 years. [WD3.5] [WD3.1]

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: WD3.5, WD3.1 - ok

A post-study work visa may be granted for different durations depending on the qualification completed. The manual says: non-degree level 7 or below, for the duration the student spent studying the qualification in New Zealand as determined by the education provider; level 7 Bachelor’s degree or level 8, for the duration spent studying in New Zealand as determined by the education provider; level 9 or 10, 3 years; a Bachelor’s Degree immediately followed by an Honours or a Postgraduate Diploma, the total time spent studying all qualifications in New Zealand, up to a maximum of three years; consecutive qualifications that meet WD3.1(b)(iv), the duration spent studying the initial qualification in New Zealand as determined by the education provider; and certain non-degree level 8 or below qualifications that require occupational registration or affiliate membership may get 1 year (or part thereof) in addition to the study time, as long as the total duration is no more than 3 years. [WD3.5] [WD3.1]

---

## 15. my PSWV is from a level 6 diploma can I work as a barista

- Expected evidence: `corpus_gap`
- Expected boundary: `case_specific_application`
- Expected legacy outcome: `type_a`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - MISMATCH
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - MISMATCH
- Cited: WD3.5 - ok
- Interpreted as: my post-study work visa is from a level 6 diploma can I work as a barista

A Post-Study Work Visa granted on the basis of a non-degree qualification at level 7 and below may only allow the holder to work in the occupation related to the qualification as specified in the third column of the Qualifications Eligible for a Post-Study Work Visa (Appendix 13) list. The provided sections also say that a Post-Study Work Visa granted on the basis of a Bachelor’s degree or a qualification at levels 8 to 10 may allow the holder to undertake any work, in any occupation and in any location. Because your question depends on what occupation is specified for your level 6 diploma in Appendix 13, I cannot tell from the provided sections whether barista work is allowed. [WD3.5]

**Missing information identified:**
- What Appendix 13 says for your specific level 6 diploma, including the occupation related to the qualification.

### Run 2

- Evidence: `sufficient` - MISMATCH
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - MISMATCH
- Cited: WD3.5 - ok
- Interpreted as: my post-study work visa is from a level 6 diploma can I work as a barista

A Post-Study Work Visa granted on the basis of a non-degree qualification at level 7 and below may only allow the holder to work in the occupation related to the qualification as specified in the third column of the Qualifications Eligible for a Post-Study Work Visa (Appendix 13) list. The provided sections do not include Appendix 13, so I cannot tell from this material whether barista is the occupation related to your level 6 diploma. [WD3.5]

**Missing information identified:**
- Whether barista is the occupation related to your level 6 diploma in the third column of Appendix 13

---

## 16. im only coming to nz for 8 months do I still need a medical or chest xray

- Expected evidence: `sufficient`
- Expected boundary: `general_information`
- Expected legacy outcome: `answered`
- Classification stable across runs: NO

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: A4.25, A4.20 - ok

The manual says that for temporary entry class visa applications, applicants intending to stay in New Zealand for more than 12 months must include a completed Medical Certificate and a Chest X-ray Certificate. For applicants intending to stay for more than six months and not more than 12 months, the manual requires TB screening only if they are considered to have risk factors for tuberculosis. It also says applicants for a temporary entry class visa do not ordinarily need to provide these certificates if they already provided them with an earlier visa application, were assessed as having an acceptable standard of health, and those certificates were issued less than 36 months before the current application. [A4.25] [A4.20]

Because you said you are only coming for 8 months, the published rule points to the more-than-six-months-and-not-more-than-12-months TB-screening rule, not the automatic more-than-12-months medical-and-chest-x-ray rule. Whether you need TB screening depends on whether you have TB risk factors, and the manual defines those risk factors by passport country or time spent in certain countries. [A4.25]

If you want, I can quote the exact TB risk-factor rule from the manual section. [A4.25]

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - MISMATCH
- Outcome: `type_c` - MISMATCH
- Cited: A4.25 - ok

The manual says that for temporary entry class visa applications, applicants intending to stay in New Zealand for more than 12 months must include a completed Medical Certificate and a Chest X-ray Certificate, unless one of the listed exceptions applies. It also says that applicants intending to stay for more than six months and not more than 12 months only need TB screening if they are considered to have risk factors for TB. For an 8-month stay, the published rule therefore depends on whether you have TB risk factors and whether any exception applies. The manual also says pregnant women and children under 11 years of age are not required to have an X-ray examination. [A4.25] [A4.25]

**Missing information identified:**
- whether you are considered to have risk factors for tuberculosis
- whether any listed exception applies to your visa type or prior medical certificates
- whether you are pregnant or under 11 years of age

---

## 17. my police clearance is 7 months old can I still use it for my visa

- Expected evidence: `sufficient`
- Expected boundary: `general_information`
- Expected legacy outcome: `answered`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: A5.10 - ok

No, the manual says all police certificates must be less than six months old at the time an application is lodged, unless A5.10(d) applies or an appropriately delegated immigration officer has waived that requirement. It also says police certificates more than six months old may be accepted if that waiver applies. A certificate that is 7 months old is therefore outside the normal rule, but the manual allows an exception if the waiver or A5.10(d) applies.

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `general_information` - ok
- Outcome: `answered` - ok
- Cited: A5.10 - ok

No. The manual says all police certificates must be less than six months old at the time an application is lodged, unless A5.10(d) applies or an appropriately delegated immigration officer has waived that requirement. It also says police certificates more than six months old may be accepted and used for determination purposes if that waiver applies. A certificate that is 7 months old is therefore outside the normal rule, but the manual allows possible acceptance only if the waiver/exception applies. [A5.10]

---

## 18. I already have 6 points for SMC but I don't have a job offer can I apply for residency

- Expected evidence: `sufficient`
- Expected boundary: `case_specific_application`
- Expected legacy outcome: `type_c`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: SR3.10, SR3.5, SR1.1 - ok
- Interpreted as: I already have 6 points for Skilled Migrant Category but I don't have a job offer can I apply for residency

The manual says that to be granted a Skilled Migrant Category resident visa, the principal applicant must meet the skilled employment requirements, including holding current employment or an offer of employment in New Zealand with an accredited employer, and must qualify for the 6 points from one skill category or from a combination of one skill category and skilled work experience in New Zealand. It also says a person may only be invited to apply if they have confirmed they meet the skilled employment requirements and have claimed 6 points in one of those ways. On the facts you gave, I cannot determine your personal result because whether you meet the skilled employment requirement depends on your employment situation. [SR3.10] [SR3.5] [SR1.1]

**Missing information identified:**
- Whether you meet the skilled employment requirement, including current employment or an offer of employment in New Zealand with an accredited employer

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: SR3.10, SR3.5, SR1.1 - ok
- Interpreted as: I already have 6 points for Skilled Migrant Category but I don't have a job offer can I apply for residency

The manual says that to be granted a resident visa under the Skilled Migrant Category, the principal applicant must meet the skilled employment requirements, including holding current employment or an offer of employment in New Zealand with an accredited employer, and must qualify for 6 points from one skill category or a combination of one skill category and skilled work experience in New Zealand. It also says a person may only be invited to apply if they have confirmed they meet the skilled employment requirements and have claimed 6 points in one of those ways. On the facts you gave, I can’t determine your personal result because the manual requires the skilled employment requirement as well as the points requirement, and you have not said whether you meet the skilled employment requirement. [SR3.10] [SR3.5] [SR1.1]

**Missing information identified:**
- Whether you meet the Skilled Migrant Category skilled employment requirement, including current employment or an offer of employment in New Zealand with an accredited employer.

---

## 19. do I need a medical for my visa

- Expected evidence: `sufficient`
- Expected boundary: `case_specific_application`
- Expected legacy outcome: `type_c`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: A4.25, A4.15 - ok

That depends on your visa type and intended stay. For temporary entry class visa applications, if you are intending to stay in New Zealand for more than 12 months, the application must include a completed Medical Certificate and a Chest X-ray Certificate issued less than three months before the application date, unless one of the listed exceptions applies. Some temporary entry applicants do not ordinarily need to provide these certificates, including fee paying foreign student visa applicants, Working Holidaymaker Extension visa applicants, and several other listed categories. Also, if you already provided both certificates with an earlier visa application, were assessed as having an acceptable standard of health, and those certificates were issued less than 36 months before the current application, you do not ordinarily need to provide them again. [A4.25]

For temporary entry class visas, applicants must also have an acceptable standard of health unless they have been granted a visitor visa for medical treatment or a medical waiver. [A4.15]

I can’t tell whether you personally need a medical from the information given because the visa category and other trigger facts are missing. [A4.25] [A4.15]

**Missing information identified:**
- your visa category
- whether you intend to stay in New Zealand for more than 12 months
- whether you already provided medical and chest X-ray certificates with an earlier visa application and were assessed as having an acceptable standard of health
- whether one of the listed exceptions applies

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: A4.25, A4.15 - ok

That depends on your visa type and, for temporary entry class visas, how long you intend to stay in New Zealand. The manual says applications for temporary entry class visas from applicants intending a stay of more than 12 months must include a completed Medical Certificate and a Chest X-ray Certificate, unless one of the listed exceptions applies. It also says some temporary entry class visa applicants do not ordinarily need to provide these certificates, including applicants for a student visa as a fee paying foreign student, Working Holidaymaker Extension visa applicants, and several other listed categories. The manual also says an immigration officer may require a Medical Certificate and Chest X-ray Certificate if they consider it necessary to establish whether the applicant has an acceptable standard of health. [A4.25] [A4.15]

I can’t tell whether you personally need one without knowing your visa category and, if it is a temporary entry class visa, your intended length of stay and whether any listed exception applies. [A4.25]

**Missing information identified:**
- visa category
- intended length of stay in New Zealand
- whether a listed exception applies

---

## 20. do I need a police clearance

- Expected evidence: `sufficient`
- Expected boundary: `case_specific_application`
- Expected legacy outcome: `type_c`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: A5.5, A5.10 - ok

The manual says police certificates are required for some visa applications, but whether you need one depends on the visa category and other facts such as your age, whether you are applying for residence or temporary entry, how long you intend to stay, and whether any listed exceptions apply. For residence class visas, character checks are required for applicants aged 17 and over, and first-time applicants aged 17 and over must obtain police or similar certificates from their country of citizenship and each country where they have lived for 12 months or more in the last 10 years, subject to the stated exceptions. For temporary entry class visas, applicants aged 17 and over who intend to stay in New Zealand for 24 months or longer are among those who must have character checks, and if required they must obtain police or similar certificates from their country of citizenship and any country where they have lived for five or more years since age 17, again subject to the stated exceptions. The manual also says some applicants do not need to provide a police or similar certificate in specific situations, and an immigration officer may still require one if the officer decides it is necessary. [A5.5] [A5.10]

**Missing information identified:**
- Which visa category you mean (residence or temporary entry)
- Your age
- How long you intend to stay in New Zealand
- Whether you are applying for a first-time or further visa
- Whether any listed exceptions apply to your situation

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: A5.5, A5.10 - ok

The manual says police certificates are required for some visa applications, but whether you need one depends on the visa category and, for some temporary entry visas, your age, intended length of stay, and country-of-citizenship / country-of-residence history. For residence class visas, police certificates are mandatory for first-time applicants aged 17 and over from the applicant’s country of citizenship and each country where they have lived for 12 months or more in the last 10 years, with exceptions for applicants under 17 and some further residence visa applicants under RV2 or RV4. For temporary entry class visas, character checks apply to applicants aged 17 and over who intend to stay 24 months or longer, and if required they must obtain certificates from their country of citizenship and any country where they have lived for five or more years since age 17. There are also specific exceptions and special rules for some visa types, and an immigration officer can require a certificate if they decide it is necessary. [A5.5] [A5.10]

**Missing information identified:**
- Which visa category you are applying for
- your age
- how long you intend to stay in New Zealand
- your country of citizenship
- which countries you have lived in and for how long
- whether you are applying for a further residence class visa under RV2 or RV4
- whether a specific visa-type exception applies

---

## 21. is 15000 enough show money for my student visa

- Expected evidence: `sufficient`
- Expected boundary: `case_specific_application`
- Expected legacy outcome: `type_c`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: U3.20 - ok

The manual says the amount depends on how long your programme of study lasts and whether you are doing tertiary or non-compulsory education study, compulsory education study, or one of the listed critical-purpose secondary study cases. For programmes lasting less than 36 weeks, the requirement is at least NZ$1,667 per month for tertiary or non-compulsory education study, or at least NZ$1,417 per month for compulsory education study. For programmes lasting 36 weeks or longer, the requirement is NZ$20,000.00 per year for tertiary or non-compulsory education study, or NZ$17,000.00 per year for compulsory education study. The manual also says immigration officers must be satisfied the funds are from a genuine source and genuinely available, and may consider how long the funds have been held and your ability to access them in New Zealand. On the information given, I can’t tell whether NZ$15,000 is enough because I would need to know your programme length and study type, and whether any prepaid living expenses apply. [U3.20] [U3.20] [U3.20] [U3.20] [U3.20]

**Missing information identified:**
- programme length
- whether the study is tertiary or non-compulsory education study or compulsory education study
- any prepaid living expenses
- whether the funds are from a genuine source and genuinely available

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: U3.20 - ok

That depends on your study length and study type. The manual says students taking programmes of study lasting less than 36 weeks must show at least NZ$1,667 per month if they are undertaking tertiary or non-compulsory education study, or at least NZ$1,417 per month if they are undertaking compulsory education study. For programmes lasting 36 weeks or longer, the amounts are NZ$20,000.00 per year for tertiary or non-compulsory education study, or NZ$17,000.00 per year for compulsory education study. The manual also says the funds must be from a genuine source and genuinely available, and officers may consider how long the funds have been held and whether the student can access them in New Zealand. So NZ$15,000 may or may not be enough depending on those facts, and I can’t determine that from the information given. [U3.20] [U3.20] [U3.20] [U3.20] [U3.20]

**Missing information identified:**
- how long your programme of study is
- whether your study is tertiary or non-compulsory education study, or compulsory education study
- whether the NZ$15,000 is from a genuine source and genuinely available for your maintenance requirements

---

## 22. can I work full time on my student visa

- Expected evidence: `sufficient`
- Expected boundary: `case_specific_application`
- Expected legacy outcome: `type_c`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: U13.15 - ok

The manual says a student visa may be granted with conditions to allow full-time work only in specific situations, such as during the Christmas-New-Year vacation period, during all scheduled vacations, or for certain study programmes and age/consent cases. It also says students enrolled at a tertiary institution or private training establishment may be granted conditions to work during the academic year and during any scheduled vacations, including within the academic year. Whether you can work full time on your student visa depends on which study and visa conditions apply to you. The manual does not give a single universal full-time work right for all student visa holders.

**Missing information identified:**
- your study type and level
- whether your visa has work conditions
- whether you are in a scheduled vacation or Christmas-New-Year vacation period
- your age if you are 16 or 17
- whether you have the required provider and parental permissions if you are 16 or 17
- the duration and type of your programme of study

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: U13.15 - ok

The manual says a student visa may allow full-time work only in specific situations, such as during the Christmas-New Year vacation period, during all scheduled vacations, or for masters by research or doctoral students. It also says students enrolled at a tertiary institution or private training establishment may be granted conditions to work during the academic year and during scheduled vacations, but the published work-rights rules depend on the study programme and other facts. So I can explain the rule, but I cannot tell from your question alone whether your own student visa allows full-time work. Relevant facts include what you are studying, the length of the programme, and whether you are in a vacation period.

**Missing information identified:**
- what you are studying
- the length of your programme
- whether you are in a scheduled vacation or the Christmas-New Year vacation period

---

## 23. I finished my course can I get a PSWV

- Expected evidence: `sufficient`
- Expected boundary: `case_specific_application`
- Expected legacy outcome: `type_c`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: WD3.1, WD3.5 - ok
- Interpreted as: I finished my course can I get a post-study work visa

The manual says a Post-Study Work Visa may be granted if you have successfully completed the qualification for which the student visa was granted, apply within the required time limit, have NZ$5,000 in funds available, and have not previously been granted a Post-Study Work Visa. It also says the qualification must be an eligible New Zealand qualification studied for the minimum study duration, and the exact duration depends on the qualification type. Because you have not said what qualification you completed, how long you studied in New Zealand, when your student visa ended, whether you have NZ$5,000 available, or whether you have previously been granted a PSWV, I cannot determine your personal result from the manual alone.

**Missing information identified:**
- what qualification you completed
- how long you studied the qualification in New Zealand
- when your student visa for that qualification ended
- whether you have NZ$5,000 in funds available
- whether you have previously been granted a Post-Study Work Visa

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: WD3.1, WD3.5 - ok
- Interpreted as: I finished my course can I get a post-study work visa

The manual says a Post-Study Work Visa may be granted if the applicant has successfully completed the qualification for which the student visa was granted, applies within the required time after the student visa end date, has NZ$5,000 in funds available, and has not previously been granted a Post-Study Work Visa. It also requires that the qualification be an eligible New Zealand qualification studied for the minimum study duration, which varies by qualification type. Because you have only said that you finished your course, I cannot tell from the manual alone whether your situation meets all of those requirements.

**Missing information identified:**
- what qualification level/type you completed
- whether it is an eligible New Zealand qualification under the manual
- whether you applied within the required time after your student visa end date
- whether you have NZ$5,000 in funds available
- whether you have previously been granted a Post-Study Work Visa

---

## 24. can I change my course without changing my visa

- Expected evidence: `sufficient`
- Expected boundary: `case_specific_application`
- Expected legacy outcome: `type_c`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: U3.40, U3.1 - ok

The manual says changing your programme of study, education provider, and/or study location normally requires either a further student visa or a variation of conditions. It will only be granted if an immigration officer is satisfied that the listed student, visa-compliance, bona fide, and other requirements are met, and that the original student visa would have been granted for the proposed change. It also says applicants who have not completed the programme endorsed on their student visa and want to change programme and/or provider must meet U3.40. If you mean your own situation, I can’t say whether you can do it without changing your visa because that depends on facts such as whether you are changing programme only, whether the new programme/provider/location meets the listed requirements, and whether you are progressing to further study. [U3.40] [U3.1]

**Missing information identified:**
- whether you are changing programme of study, education provider, and/or study location
- whether the proposed change meets the requirements in U3.40 and U3.1
- whether you are progressing to further study

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: U3.1, U3.40 - ok

The manual says a student who has not completed, or will not be completing, the programme of study endorsed on their student visa and who wants to change their programme of study and/or education provider must meet the student requirements in U3.1 and the change-of-study conditions in U3.40. U3.40 says a further student visa or a variation of conditions for changing programme of study, education provider and/or study location will only be granted if an immigration officer is satisfied of the listed requirements, including that the original student visa would have been granted for the proposed programme and that the applicant is not seeking to vary conditions to enrol in a lower-level programme or with a different education provider. The note says students progressing to further study, for example Year 13 to tertiary studies, will not need to meet U3.40. Whether you can change your course without changing your visa therefore depends on your exact study situation and whether the change is only a progression to further study or instead requires a further student visa or a variation of conditions.

**Missing information identified:**
- whether you have completed, or will complete, the programme endorsed on your current student visa
- whether the change is a progression to further study or a change of programme/education provider/study location under U3.40
- whether the proposed change is to a lower-level programme or a different education provider

---

## 25. I have 6 points can I apply for residence

- Expected evidence: `sufficient`
- Expected boundary: `case_specific_application`
- Expected legacy outcome: `type_c`
- Classification stable across runs: yes

### Run 1

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: SR3.5, SR3.10, SR3.15 - ok

The manual says a principal applicant must qualify for 6 points from one skill category, or 6 points from a combination of one skill category and skilled work experience in New Zealand, before they can be invited to apply under the Skilled Migrant Category. It also says that to be granted a resident visa under the Skilled Migrant Category, the principal applicant must meet the other listed requirements, including health, character, English, age 55 or younger, and skilled employment requirements. So 6 points by itself is not the whole rule for residence; the manual sets 6 points as one required part of the Skilled Migrant Category process. [SR3.5] [SR3.10] [SR3.15]

**Missing information identified:**
- Whether you meet the other Skilled Migrant Category requirements listed in the manual, including health, character, English, age 55 or younger, and skilled employment requirements.

### Run 2

- Evidence: `sufficient` - ok
- Boundary: `case_specific_application` - ok
- Outcome: `type_c` - ok
- Cited: SR3.10, SR3.5, SR3.15, SR3.25 - ok

The manual says a principal applicant must qualify for 6 points from one skill category, or 6 points from a combination of one skill category and skilled work experience in New Zealand, and must also meet the other Skilled Migrant Category requirements. Those include health and character requirements, the applicable minimum standard of English, being aged 55 or younger at the time the residence application is made, and meeting the skilled employment requirements. The skilled employment requirement includes current employment or an offer of employment in New Zealand with an accredited employer that pays at least the relevant median-wage threshold, depending on the ANZSCO skill level of the occupation. The manual also says a person may only be invited to apply if they have confirmed those matters in their EOI. [SR3.10] [SR3.5] [SR3.15] [SR3.25]

I can’t tell whether you can apply on your own facts because you have only given the points total, not the other required facts. [SR3.10] [SR3.5]

**Missing information identified:**
- Whether you meet the other Skilled Migrant Category requirements, including health, character, English, age 55 or younger, and the skilled employment requirements.

---
