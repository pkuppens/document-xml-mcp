# Assignment / Job Description Format

This template defines the expected structure of an assignment or job description used in the CV intelligence pipeline. Use it when:
- Preparing a job description to pass to `analyze_cv_gaps` or `write_motivation_letter` prompts
- Building tools that ingest assignments from external job boards
- Validating that an assignment description contains enough information for matching

---

## Standard Assignment Format

```
## Title
[Job title — e.g., "Senior Data Engineer", "ML Engineer (Healthcare)"]

## Organisation
[Company or client name]
[Industry / sector — e.g., "Healthcare", "FinTech", "Government"]
[Location — e.g., "Amsterdam, Netherlands" or "Remote"]

## Contract
[Type: Permanent | Freelance | Fixed-term]
[Duration: e.g., "6 months + extension" or "Indefinite"]
[Hours: e.g., "32–40 hours/week", "Fulltime"]
[Rate / Salary: e.g., "€600–750/day" or "€70,000–85,000 gross/year"]

## Role Summary
[2–4 sentences describing the role, team context, and primary mission]

## Responsibilities
- [Responsibility 1]
- [Responsibility 2]
- [Responsibility 3]

## Required Skills and Experience
- [Must-have skill or technology 1]
- [Must-have skill or technology 2]
- [Required years of experience — e.g., "5+ years Python"]
- [Required domain knowledge — e.g., "healthcare data regulations (HIPAA/GDPR)"]

## Nice-to-Have
- [Preferred skill or certification 1]
- [Preferred skill or certification 2]

## Education
[Required degree — e.g., "BSc or MSc in Computer Science or equivalent"]

## Language Requirements
[e.g., "Dutch (B2 or higher) and English (fluent)"]

## Additional Notes
[Any other relevant context: team culture, tech stack, interview process, deadlines]
```

---

## Minimal Format (when full details are unavailable)

At minimum, the prompts `analyze_cv_gaps` and `write_motivation_letter` need:

```
Title: [Job title]
Required skills: [Comma-separated list]
Description: [Free-form text describing the role]
```

---

## Field Definitions

| Field | Required | Notes |
|-------|----------|-------|
| Title | Yes | Used in the motivation letter opening |
| Organisation | Recommended | Personalises the letter |
| Role Summary | Yes | Core context for gap analysis |
| Responsibilities | Recommended | Enables specific matching |
| Required Skills | Yes | Primary input for gap analysis |
| Nice-to-Have | Optional | Used for Minor gap classification |
| Education | Optional | Checked against CV education section |
| Language Requirements | Optional | Checked against CV languages section |
