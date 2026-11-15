---
name: ropa-review
description: Criteria for judging whether each answer in a ROPA form submission gives enough information for a privacy review. Use for every ROPA submission review.
---

# ROPA review criteria

You judge one thing only: does each answer give enough detail for a privacy
reviewer to understand the processing without asking the submitter again?
Do not judge whether the processing is lawful or a good idea.

## 1. Pass criteria per question

For each question, mark `complete` when the answer meets the bar below,
`incomplete` when it is blank or too vague, and `unsure` per section 2.

| question_id | Complete when the answer... | Complete example | Incomplete example |
|---|---|---|---|
| business_department | names a specific team | "Customer Service, EMEA" | "Ops" |
| purpose_of_processing | says what the project does with the data | "Send order updates to customers by email" | "Business purposes" |
| reason_for_using_personal_data | explains why personal data is needed, not just wanted | "We need the email address to deliver the order update" | "To improve things" |
| markets | lists the countries or regions | "Germany, France, UK" | "Global" with no detail |
| data_subjects | names the groups of people | "Online customers and their delivery contacts" | "Users" |
| data_categories | lists the specific data fields | "Name, email, delivery address, order history" | "Customer data" |
| data_sources | says where each kind of data comes from | "Customers enter it at checkout" | "Systems" |
| data_recipients | names who receives the data, including vendors | "Shipping vendor DHL; internal finance team" | "Partners" |
| sharing_reason | explains why each recipient needs the data | "DHL needs the address to deliver the parcel" | "Business need" |
| retention_period | gives a specific period or a clear trigger | "2 years after the last order, then deleted" | "As long as needed" |
| security_measures | names concrete measures | "Encrypted database, access limited to 5 named roles" | "Industry standard" |

A blank answer is always `incomplete`.

## 2. When to say `unsure`

Use `unsure` only when you cannot decide, for example:

- The answer is so unclear you cannot tell what it means.
- Two answers contradict each other (for example, "no sharing" in one place
  but a vendor named in another).
- The criteria above do not cover the situation.

Explain the reason in `unsure_reason` in one sentence.

## 3. Priority for incomplete answers

- **High**: a privacy reviewer cannot start without it (blank answer, no
  data categories, no recipients, no retention period).
- **Medium**: the answer exists but is too vague to assess.
- **Low**: a small detail is missing; the reviewer could still start.

## 4. Writing rules

- `quoted_answer`: copy the submitter's exact words from that question's
  answer. Use an empty string if the answer is blank.
- `missing_detail`: tell the submitter what to add, in plain English, with
  an example. Start with a verb, e.g. "Please list...".
- `summary`: two or three sentences about the whole submission.
- Write for someone with no legal background. No legal terms or acronyms.
