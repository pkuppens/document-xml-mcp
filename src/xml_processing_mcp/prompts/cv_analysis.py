"""Analysis prompt templates: gap analysis and Q&A over CV XML."""


def analyze_cv_gaps_prompt(cv_xml: str, job_description: str) -> list[dict]:
    """Instruct the LLM to identify skill and experience gaps between a CV and a job description.

    Returns a list of PromptMessage dicts consumed by the MCP client.
    The LLM performs the analysis; this function provides the instruction template.
    """
    return [
        {
            "role": "user",
            "content": (
                "You are an expert career coach and recruiter. Analyze the CV below against"
                " the job description and identify gaps.\n\n"
                f"## CV (XML format)\n{cv_xml}\n\n"
                f"## Job Description\n{job_description}\n\n"
                "## Your task\n"
                "1. List skills or technologies mentioned in the job description that are absent"
                " or underrepresented in the CV.\n"
                "2. List experience requirements (years, domains, seniority) that the CV does"
                " not clearly meet.\n"
                "3. List any certifications, degrees, or qualifications required but not present.\n"
                "4. For each gap, rate its severity: Critical (deal-breaker), Important (weakens"
                " candidacy), or Minor (nice-to-have).\n"
                "5. Suggest 2–3 concrete actions the candidate can take to address the most"
                " critical gaps.\n\n"
                "Be specific. Quote evidence from both the CV and the job description."
                " Do not invent gaps that do not exist."
            ),
        }
    ]


def answer_cv_questions_prompt(cv_xml: str, question: str) -> list[dict]:
    """Instruct the LLM to answer a specific question about the CV content.

    Suitable for interactive exploration: "How many years of Python experience?",
    "What is the candidate's highest degree?", "Which companies did they work for?".
    """
    return [
        {
            "role": "user",
            "content": (
                "You are a helpful assistant with access to a candidate's CV. Answer the question"
                " below based strictly on the CV content. Do not infer or assume information"
                " not present in the CV.\n\n"
                f"## CV (XML format)\n{cv_xml}\n\n"
                f"## Question\n{question}\n\n"
                "If the answer is not present in the CV, say so explicitly rather than guessing."
            ),
        }
    ]
