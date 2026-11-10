

## Tools
- ChatGPT and Gemini for designing unit, API, and contract tests against SPEC.md.

## What AI got wrong
- Initial generated tests used string checking for CORS headers instead of strict equality against allowed origins.
- Missed validating the exact `application/problem+json` Content-Type on 409 responses.

## In my own words

1. Pick one mutant your first draft of tests did not kill. Why not, and what did you add?
My first draft did not kill M04 (urgent boundary moved) because I only tested cover days of 2 and 4. I added an explicit boundary test for cover_days = 3.0 with is_chronic = True to ensure it evaluates strictly to "high" and not "urgent".

2. Why is a test that only asserts `status_code == 409` weaker than one that asserts the problem `type`?
Asserting only status_code == 409 passes even if the endpoint fails for a completely wrong reason (e.g., item not found or unauthorized). Asserting the RFC 7807 problem `type` URI (e.g., `/problems/below-reserve`) proves that the API failed for the exact expected domain logic reason.
