"""Generation prompt templates: motivation letter writing and CV rewriting."""


def write_motivation_letter_prompt(cv_xml: str, assignment: str, tone: str = "professional") -> list[dict]:
    """Instruct the LLM to write a tailored motivation letter for a specific assignment.

    The tone parameter controls style: "professional", "enthusiastic", "concise".
    The server provides the template; the LLM generates the letter.
    """
    tone_guidance = {
        "professional": "formal and measured, emphasising track record and value delivered",
        "enthusiastic": "warm and energetic, showing genuine excitement for the role",
        "concise": "tight and direct — maximum 250 words, no filler sentences",
    }.get(tone.lower(), "professional and clear")

    return [
        {
            "role": "user",
            "content": (
                "You are an expert career writer. Write a compelling motivation letter for the"
                " assignment below, drawing only on the candidate's actual experience from the CV.\n\n"
                f"## CV (XML format)\n{cv_xml}\n\n"
                f"## Assignment / Job Description\n{assignment}\n\n"
                f"## Style\nTone: {tone_guidance}\n\n"
                "## Requirements\n"
                '- Address the letter to the hiring manager (use "Dear Hiring Manager" if no name'
                " is available).\n"
                "- Opening: 1–2 sentences connecting the candidate's background to the specific role.\n"
                "- Body: 2–3 paragraphs. For each, pick the most relevant experience or skill from"
                " the CV and link it directly to a requirement in the job description."
                " Quote specific achievements where possible.\n"
                "- Closing: 1 sentence expressing enthusiasm and availability for an interview.\n"
                "- Do NOT invent experience, certifications, or achievements not present in the CV.\n"
                '- Length: 300–450 words unless the "concise" tone is selected.'
            ),
        }
    ]


def rewrite_cv_for_assignment_prompt(cv_xml: str, assignment: str, target_format: str = "xml") -> list[dict]:
    """Instruct the LLM to rewrite and tailor a CV for a specific assignment.

    The rewritten CV emphasises experience most relevant to the assignment.
    target_format controls the output: "xml" (same structure as input) or "markdown".
    """
    format_instruction = (
        "Return the rewritten CV in the same XML format as the input CV."
        if target_format.lower() == "xml"
        else "Return the rewritten CV as clean Markdown with headings and bullet points."
    )

    return [
        {
            "role": "user",
            "content": (
                "You are an expert CV writer and career strategist. Rewrite the CV below to be"
                " maximally relevant to the target assignment. Do not fabricate experience —"
                " only reorder, emphasise, and rephrase what is already there.\n\n"
                f"## Original CV (XML format)\n{cv_xml}\n\n"
                f"## Target Assignment / Job Description\n{assignment}\n\n"
                "## Instructions\n"
                "1. Reorder sections and bullet points to lead with the most relevant experience.\n"
                "2. Strengthen the summary/profile to directly address the role's core requirements.\n"
                "3. Rephrase bullet points to use keywords from the job description where the"
                " underlying experience genuinely matches.\n"
                "4. De-emphasise or shorten sections irrelevant to this role.\n"
                "5. Do NOT add skills, certifications, companies, or achievements not in the original CV.\n\n"
                f"## Output format\n{format_instruction}"
            ),
        }
    ]
