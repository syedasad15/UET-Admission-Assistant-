import json
from pathlib import Path


# ============================================================
# UET CHATBOT — ADMISSION SECTION CLASSIFIER
# ============================================================
#
# Purpose:
# Read sections discovered from the UET Admission homepage
# and classify them before crawling.
#
# IMPORTANT:
# This script DOES NOT crawl URLs.
#
# Pipeline:
#
# admissiondiscovery.py
#        ↓
# _sections.json
#        ↓
# admissionselection.py
#        ↓
# _selected_sections.json
#        ↓
# admissionmap.py
#        ↓
# _map.json
#
# ============================================================


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(r"D:\UET Chatbot")

DATA_DIR = PROJECT_ROOT / "data" / "inventory" / "admission"


# ============================================================
# INPUT / OUTPUT
# ============================================================

INPUT_FILE = DATA_DIR / "_sections.json"

OUTPUT_FILE = DATA_DIR / "_selected_sections.json"

ADMISSION_HOME = "https://admission.uet.edu.pk/"


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(text):
    """
    Normalize section names for comparison.
    """

    return " ".join(
        str(text).lower().strip().split()
    )


def normalize_url(url):
    """
    Normalize URLs for comparison.

    Also removes:
    - trailing slash
    - fragment
    """

    url = str(url).strip()

    if not url:
        return ""

    # Remove fragment such as #programs
    url = url.split("#", 1)[0]

    return url.rstrip("/")


# ============================================================
# CLASSIFICATION
# ============================================================
def classify_section(name, url):
    """
    Decide whether a discovered section is:

        KEEP
        SKIP
        REVIEW

    The crawler will only receive KEEP sections.
    """

    name_normalized = normalize_text(name)
    url_normalized = normalize_url(url)

    admission_home_normalized = normalize_url(
        ADMISSION_HOME
    )

    # --------------------------------------------------------
    # 1. IMPORTANT KNOWLEDGE SECTION
    # --------------------------------------------------------
    #
    # "All Programs" uses:
    #
    # https://admission.uet.edu.pk/#programs
    #
    # normalize_url() removes the #programs fragment,
    # which would otherwise make it look like the homepage.
    #
    # We therefore handle All Programs FIRST.
    # --------------------------------------------------------

    if name_normalized == "all programs":

        return (
            "KEEP",
            "admission knowledge content"
        )

    # --------------------------------------------------------
    # 2. Homepage / duplicate links
    # --------------------------------------------------------

    if url_normalized == admission_home_normalized:

        return (
            "SKIP",
            "homepage duplicate"
        )

    # --------------------------------------------------------
    # 3. Email / Cloudflare email protection
    # --------------------------------------------------------

    if "cdn-cgi/l/email-protection" in url_normalized:

        return (
            "SKIP",
            "email/contact endpoint"
        )

    # --------------------------------------------------------
    # 4. Action links
    # --------------------------------------------------------

    if name_normalized in {
        "apply now",
        "register complaint",
    }:

        return (
            "SKIP",
            "action link, not knowledge content"
        )

    # --------------------------------------------------------
    # 5. Admission knowledge sections
    # --------------------------------------------------------

    knowledge_sections = {
        "bachelors in sciences",
        "master",
        "ph.d",
        "associate degree program",
        "downloads",
        "foreign students",
        "news",
        "faqs",
    }

    if name_normalized in knowledge_sections:

        return (
            "KEEP",
            "admission knowledge content"
        )

    # --------------------------------------------------------
    # 6. Unknown sections
    # --------------------------------------------------------

    return (
        "REVIEW",
        "unknown admission section"
    )


# ============================================================
# LOAD DISCOVERY RESULTS
# ============================================================

def load_sections():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            "\nDiscovery file was not found:\n"
            f"{INPUT_FILE}\n\n"
            "Run admissiondiscovery.py first."
        )

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    # --------------------------------------------------------
    # IMPORTANT
    #
    # _sections.json has this structure:
    #
    # {
    #     "source": "...",
    #     "stage": "...",
    #     "sections": [...]
    # }
    #
    # Therefore we must extract "sections".
    # --------------------------------------------------------

    if isinstance(data, dict):

        sections = data.get(
            "sections",
            []
        )

    elif isinstance(data, list):

        sections = data

    else:

        raise ValueError(
            "Invalid _sections.json structure."
        )

    return sections


# ============================================================
# PROCESS SECTIONS
# ============================================================

def classify_sections(sections):

    selected = []

    skipped = []

    review = []

    for section in sections:

        # ----------------------------------------------------
        # Safety check
        # ----------------------------------------------------

        if not isinstance(section, dict):

            continue

        name = str(
            section.get("name", "")
        ).strip()

        url = str(
            section.get("url", "")
        ).strip()

        if not name or not url:

            continue

        decision, reason = classify_section(
            name,
            url
        )

        result = {
            "name": name,
            "url": url,
            "decision": decision,
            "reason": reason
        }

        if decision == "KEEP":

            selected.append(result)

        elif decision == "SKIP":

            skipped.append(result)

        else:

            review.append(result)

    return (
        selected,
        skipped,
        review
    )


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(
    selected,
    skipped,
    review
):

    # Make sure:

    # D:\UET Chatbot\data\inventory\admission

    # exists.

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    result = {

        "source": ADMISSION_HOME,

        "stage": "admission_section_selection",

        "crawl_policy": {

            "homepage_crawled": False,

            "selected_sections_crawled": False

        },

        "selected_sections": selected,

        "skipped_sections": skipped,

        "review_sections": review,

        "counts": {

            "selected": len(selected),

            "skipped": len(skipped),

            "review": len(review)

        }

    }

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# PRINT SECTION GROUP
# ============================================================

def print_section_group(
    title,
    sections
):

    print()

    print(title)

    print("=" * 70)

    if not sections:

        print("None")

        return

    for index, section in enumerate(
        sections,
        start=1
    ):

        print(
            f"[{index:02}] "
            f"{section['name']}"
        )

        print(
            f"{section['url']}"
        )

        print(
            f"Reason: "
            f"{section['reason']}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()

    print(
        "# UET ADMISSION — SECTION CLASSIFIER"
    )

    print()

    print(
        f"Project: {PROJECT_ROOT}"
    )

    print(
        f"Reading: {INPUT_FILE}"
    )

    print(
        f"Output:  {OUTPUT_FILE}"
    )

    print()

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    sections = load_sections()

    print(
        f"Discovered sections: "
        f"{len(sections)}"
    )

    # --------------------------------------------------------
    # Classify
    # --------------------------------------------------------

    selected, skipped, review = (
        classify_sections(sections)
    )

    # --------------------------------------------------------
    # Print
    # --------------------------------------------------------

    print_section_group(
        "# KEEP — WILL BE CRAWLED LATER",
        selected
    )

    print_section_group(
        "# SKIP — WILL NOT BE CRAWLED",
        skipped
    )

    print_section_group(
        "# REVIEW — NEEDS A DECISION",
        review
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()

    print("=" * 70)

    print(
        f"KEEP:   {len(selected)}"
    )

    print(
        f"SKIP:   {len(skipped)}"
    )

    print(
        f"REVIEW: {len(review)}"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_results(
        selected,
        skipped,
        review
    )

    print()

    print(
        f"Saved to: {OUTPUT_FILE}"
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "No URLs were crawled."
    )

    print(
        "This script only classifies discovered sections."
    )

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()