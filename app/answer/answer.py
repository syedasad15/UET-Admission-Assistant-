
import json
import os
import sys
from pathlib import Path

from google import genai
from google.genai import types


# ============================================================
# UET CHATBOT — GEMINI ANSWER GENERATION
# ============================================================
#
# Input:
#   data/retrieval/last_retrieval.json
#
# API key:
#   app/retrieval/keyy.env
#
# Model:
#   "gemini-3.6-flash"
#
# Flow:
#
#   User Question
#        ↓
#   Retrieval Results
#        ↓
#   Retrieved PDF / Webpage Evidence
#        ↓
#   Gemini
#        ↓
#   Grounded Answer + Source Reference
#
# IMPORTANT:
#   Gemini is NOT allowed to invent information.
#   It must answer only from retrieved evidence.
#
# ============================================================


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(r"D:\UET Chatbot")

RETRIEVAL_FILE = (
    PROJECT_ROOT
    / "data"
    / "retrieval"
    / "last_retrieval.json"
)

ENV_FILE = (
    PROJECT_ROOT
    / "app"
    / "retrieval"
    / "keyy.env"
)


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

MODEL_NAME = "gemini-3.6-flash"

MAX_CONTEXT_RESULTS = 8

MAX_DOCUMENT_CHARS = 12000


# ============================================================
# LOAD ENV FILE
# ============================================================

def load_env_file():

    if not ENV_FILE.exists():

        raise FileNotFoundError(
            "\nGemini API key file was not found:\n"
            f"{ENV_FILE}\n\n"
            "Create the file with:\n"
            "VITE_GEMINI_API_KEY=your_actual_key_here"
        )

    with ENV_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:

        for raw_line in file:

            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split(
                "=",
                1,
            )

            key = key.strip()
            value = value.strip()

            # Remove optional surrounding quotes.
            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in ('"', "'")
            ):
                value = value[1:-1]

            os.environ[key] = value


def get_api_key():

    load_env_file()

    api_key = os.getenv(
        "VITE_GEMINI_API_KEY"
    )

    # Also support the standard Google variable.
    if not api_key:

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

    if not api_key:

        raise RuntimeError(
            "\nGemini API key was not found.\n\n"
            f"Checked:\n{ENV_FILE}\n\n"
            "Expected:\n"
            "VITE_GEMINI_API_KEY=your_actual_key_here"
        )

    return api_key


# ============================================================
# LOAD RETRIEVAL RESULT
# ============================================================

def load_retrieval():

    if not RETRIEVAL_FILE.exists():

        raise FileNotFoundError(
            "\nRetrieval file was not found:\n"
            f"{RETRIEVAL_FILE}\n\n"
            "Run retrieval.py first."
        )

    with RETRIEVAL_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    return data


# ============================================================
# GET QUESTION
# ============================================================

def get_question(data):

    if isinstance(data, dict):

        for key in (
            "query",
            "question",
            "user_question",
        ):

            value = data.get(key)

            if value:

                return str(value).strip()

    return ""


# ============================================================
# GET RETRIEVAL RESULTS
# ============================================================

def get_results(data):

    if isinstance(data, dict):

        results = data.get(
            "results",
            []
        )

        if isinstance(results, list):
            return results

        results = data.get(
            "documents",
            []
        )

        if isinstance(results, list):
            return results

    if isinstance(data, list):

        return data

    return []


# ============================================================
# FORMAT SOURCE
# ============================================================

def format_source(result, index):

    title = (
        result.get("title")
        or "Unknown source"
    )

    source_type = (
        result.get("source_type")
        or "unknown"
    )

    url = (
        result.get("url")
        or ""
    )

    pdf_file = (
        result.get("pdf_file")
        or ""
    )

    page = result.get(
        "page"
    )

    lines = []

    lines.append(
        f"[SOURCE {index}]"
    )

    lines.append(
        f"Title: {title}"
    )

    lines.append(
        f"Source type: {source_type}"
    )

    if pdf_file:

        lines.append(
            f"PDF file: {pdf_file}"
        )

    if page not in (
        None,
        "",
        0,
        "0",
    ):

        lines.append(
            f"Page: {page}"
        )

    if url:

        lines.append(
            f"URL: {url}"
        )

    return "\n".join(lines)


# ============================================================
# BUILD RETRIEVAL CONTEXT
# ============================================================

def build_context(results):

    selected_results = results[
        :MAX_CONTEXT_RESULTS
    ]

    context_blocks = []

    for index, result in enumerate(
        selected_results,
        start=1,
    ):

        if not isinstance(result, dict):
            continue

        text = (
            result.get("text")
            or result.get("document")
            or ""
        )

        text = str(text).strip()

        if not text:
            continue

        if len(text) > MAX_DOCUMENT_CHARS:

            text = (
                text[:MAX_DOCUMENT_CHARS]
                + "\n[TEXT TRUNCATED]"
            )

        source = format_source(
            result,
            index,
        )

        block = (
            f"{source}\n\n"
            f"EVIDENCE:\n"
            f"{text}"
        )

        context_blocks.append(
            block
        )

    separator = (
        "\n\n"
        + ("-" * 70)
        + "\n\n"
    )

    return separator.join(
        context_blocks
    )


# ============================================================
# SYSTEM INSTRUCTION
# ============================================================

SYSTEM_INSTRUCTION = """
You are the answer-generation component of the UET Admissions
Chatbot.

Your job is to answer the user's question using ONLY the
retrieved evidence provided to you.

STRICT GROUNDING RULES:

1. Never invent information.

2. Never use outside knowledge.

3. Never guess missing numbers, program names, dates, fees,
   deadlines, eligibility rules, or admission requirements.

4. If the evidence does not contain enough information, clearly
   say that the available retrieved information is insufficient.

5. Prefer the most relevant and specific retrieved source.

6. If multiple sources support the same answer, combine them
   carefully.

7. If sources conflict, mention the conflict.

8. Preserve exact numerical values from the evidence.

9. For "how many" questions, count only explicitly supported
   items.

10. For program-list questions, provide actual program names
    from the evidence only.

11. Do not manufacture program names.

12. If a PDF is the source, provide:
       - PDF title
       - page number when available
       - PDF URL when available

13. If a webpage is the source, provide:
       - webpage title
       - webpage URL

14. Never cite a source that was not included in the retrieved
    evidence.

15. Keep answers concise and useful.

16. Preserve the admission session/year from the evidence.

17. If evidence says Fall 2026, mention Fall 2026 where
    appropriate.

18. Answer the user directly first.

SOURCE FORMAT:

After the answer, provide:

Source:
- Title: ...
- Page: ...
- URL: ...

For multiple important sources:

Sources:
1. ...
2. ...

IMPORTANT FOR LIST/COUNT QUESTIONS:

If the user asks something like:

"How many BS programs are offered?"

Do NOT answer based on similarity alone.

First determine whether the retrieved evidence actually contains
the program list or an explicit count.

If the evidence explicitly says there are 20 programs, answer 20.

If the evidence contains 20 actual program entries, count them
and provide the list.

If the retrieved evidence does not contain enough information
to establish the count, say so instead of guessing.
"""


# ============================================================
# GENERATE ANSWER
# ============================================================

def generate_answer(
    client,
    question,
    context,
):

    prompt = f"""
USER QUESTION:

{question}


RETRIEVED UET ADMISSIONS EVIDENCE:

{context}


TASK:

Answer the user's question strictly from the retrieved evidence.

Do not use external knowledge.

Do not invent missing information.

If the answer is supported by a PDF, include the PDF title,
page number when available, and URL.

If the answer is supported by a webpage, include the webpage
title and URL.

Give the direct answer first.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.1,
            max_output_tokens=1200,
        ),
    )

    if not response.text:

        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return response.text.strip()


# ============================================================
# PRINT SOURCE AUDIT
# ============================================================

def print_source_audit(results):

    print()
    print("=" * 78)
    print("RETRIEVED SOURCE REFERENCES")
    print("=" * 78)

    for index, result in enumerate(
        results[:MAX_CONTEXT_RESULTS],
        start=1,
    ):

        if not isinstance(result, dict):
            continue

        title = (
            result.get("title")
            or "Unknown source"
        )

        source_type = (
            result.get("source_type")
            or ""
        )

        url = (
            result.get("url")
            or ""
        )

        pdf_file = (
            result.get("pdf_file")
            or ""
        )

        page = result.get(
            "page"
        )

        print()
        print(
            f"[{index}] {title}"
        )

        if source_type:

            print(
                f"    Type : {source_type}"
            )

        if pdf_file:

            print(
                f"    PDF  : {pdf_file}"
            )

        if page not in (
            None,
            "",
            0,
            "0",
        ):

            print(
                f"    Page : {page}"
            )

        if url:

            print(
                f"    URL  : {url}"
            )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 78)
    print(
        "UET ADMISSION — GEMINI ANSWER GENERATION"
    )
    print("=" * 78)

    print()
    print(
        f"Retrieval file:"
    )

    print(
        RETRIEVAL_FILE
    )

    print()
    print(
        f"API key file:"
    )

    print(
        ENV_FILE
    )

    print()
    print(
        f"Model: {MODEL_NAME}"
    )

    # --------------------------------------------------------
    # API KEY
    # --------------------------------------------------------

    try:

        api_key = get_api_key()

    except Exception as error:

        print()
        print(
            "API KEY ERROR:"
        )

        print(
            error
        )

        sys.exit(1)

    # --------------------------------------------------------
    # GEMINI CLIENT
    # --------------------------------------------------------

    try:

        client = genai.Client(
            api_key=api_key
        )

    except Exception as error:

        print()
        print(
            "GEMINI CLIENT ERROR:"
        )

        print(
            error
        )

        sys.exit(1)

    print()
    print(
        "Gemini client ready."
    )

    # --------------------------------------------------------
    # LOAD RETRIEVAL
    # --------------------------------------------------------

    try:

        retrieval_data = load_retrieval()

    except Exception as error:

        print()
        print(
            "RETRIEVAL FILE ERROR:"
        )

        print(
            error
        )

        sys.exit(1)

    question = get_question(
        retrieval_data
    )

    results = get_results(
        retrieval_data
    )

    if not question:

        print()
        print(
            "ERROR: User question was not found."
        )

        sys.exit(1)

    if not results:

        print()
        print(
            "ERROR: No retrieval results were found."
        )

        print()
        print(
            "Run retrieval.py first."
        )

        sys.exit(1)

    # --------------------------------------------------------
    # QUESTION
    # --------------------------------------------------------

    print()
    print("=" * 78)
    print("QUESTION")
    print("=" * 78)

    print()
    print(
        question
    )

    print()
    print(
        f"Retrieved evidence: {len(results)} result(s)"
    )

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = build_context(
        results
    )

    if not context:

        print()
        print(
            "ERROR: Retrieved results contain no usable text."
        )

        sys.exit(1)

    # --------------------------------------------------------
    # GENERATE
    # --------------------------------------------------------

    print()
    print("=" * 78)
    print("GENERATING ANSWER")
    print("=" * 78)

    print()
    print(
        f"Sending grounded context to {MODEL_NAME}..."
    )

    try:

        answer = generate_answer(
            client,
            question,
            context,
        )

    except Exception as error:

        print()
        print(
            "GEMINI ERROR:"
        )

        print(
            error
        )

        sys.exit(1)

    # --------------------------------------------------------
    # FINAL ANSWER
    # --------------------------------------------------------

    print()
    print("=" * 78)
    print("FINAL ANSWER")
    print("=" * 78)

    print()
    print(
        answer
    )

    # --------------------------------------------------------
    # SOURCE AUDIT
    # --------------------------------------------------------

    print_source_audit(
        results
    )

    print()
    print("=" * 78)
    print("DONE")
    print("=" * 78)
    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
