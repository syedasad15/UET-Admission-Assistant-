import json
import re
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse, parse_qs


# ============================================================
# UET CHATBOT — ACTION REGISTRY BUILDER
# ============================================================
#
# Input:
#   data/inventory/admission/_pages_reviewed.json
#
# Output:
#   data/inventory/admission/_actions_registry.json
#
# Purpose:
#   Convert the preserved ACTION links (challan, login, apply
#   now, etc.) into a clean, chatbot-usable action registry.
#
#   Actions are NOT knowledge content. They have no paragraphs
#   to answer a question with — they are single navigational
#   links the chatbot should hand back to the student when the
#   student's intent matches (e.g. "I forgot my challan number"
#   -> forget_challan -> URL).
#
#   This is why actions get their OWN registry instead of being
#   force-fitted into a knowledge "book".
#
# Important policy:
#
#   Every action MUST have:
#       - a non-empty URL
#       - a non-empty title
#       - a valid action_type
#
#   Actions are grouped by action_type, similar to how
#   bookbuilder.py groups pages by book name.
#
#   Duplicate URLs are removed (first occurrence wins).
#
# ============================================================


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(r"D:\UET Chatbot")

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "inventory"
    / "admission"
)

INPUT_FILE = DATA_DIR / "_pages_reviewed.json"
OUTPUT_FILE = DATA_DIR / "_actions_registry.json"


# ============================================================
# CONSTANTS
# ============================================================

VALID_ACTION_TYPES = {
    "login",
    "account",
    "forget_challan",
    "create_challan",
    "module_action",
    "admission_action",
}

# Program codes found in the URL path, e.g. /UG-2026-1/...
PROGRAM_LABELS = {
    "UG": "Undergraduate",
    "MS": "Master's",
    "PHD": "PhD",
    "PG": "Postgraduate",
}


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(value):

    if value is None:
        return ""

    return str(value).strip()


def normalize_url(url):
    """
    Normalize URL for duplicate detection.

    Removes:
        - fragments
        - trailing slash
    """

    if not url:
        return ""

    url = str(url).strip()

    if not url:
        return ""

    url = url.split("#", 1)[0]

    return url.rstrip("/")


def normalize_action_type(value):

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
    )


# ============================================================
# PROGRAM / CONTEXT EXTRACTION
# ============================================================
#
# Several action URLs are identical in purpose (e.g. "forget
# challan") but belong to different admission programs
# (Undergraduate / Master's / PhD) and different contexts
# (APPLICATION / ADMIT_CARD / MERIT_LIST).
#
# Example:
#
#   .../UG-2026-1/account/forgetchallan
#   .../MS-2026-1/pg/account/forgetchallan?redirectFrom=APPLICATION
#   .../PHD-2026-1/pg/account/forgetchallan?redirectFrom=ADMIT_CARD
#
# Without extracting these, the registry would contain multiple
# entries with the exact same title and no way to tell them
# apart, making it impossible for the chatbot to pick the
# correct link for a specific student.
#
# ============================================================

PROGRAM_PATTERN = re.compile(
    r"/([A-Za-z]+)-\d{4}-\d+/"
)


def parse_program(url):
    """
    Extract the program code from the URL path.

    Example:
        /UG-2026-1/...  -> "UG"
        /MS-2026-1/...  -> "MS"
        /PHD-2026-1/... -> "PHD"

    Returns "" if no program segment is found (e.g. generic
    module URLs like /modules/EntryTest/...).
    """

    if not url:
        return ""

    match = PROGRAM_PATTERN.search(url)

    if not match:
        return ""

    return match.group(1).upper()


def program_label(program_code):
    """
    Convert a program code into a human-readable label.
    """

    if not program_code:
        return "General"

    return PROGRAM_LABELS.get(
        program_code,
        program_code,
    )


def parse_context(url):
    """
    Extract the redirectFrom query parameter, which indicates
    WHY the student is being sent to this action.

    Example:
        ?redirectFrom=APPLICATION  -> "APPLICATION"
        ?redirectFrom=ADMIT_CARD   -> "ADMIT_CARD"
        ?redirectFrom=MERIT_LIST   -> "MERIT_LIST"

    Returns "" if no redirectFrom parameter is present.
    """

    if not url:
        return ""

    query = urlparse(url).query

    if not query:
        return ""

    params = parse_qs(query)

    values = params.get("redirectFrom")

    if not values:
        return ""

    return values[0].strip().upper()


# ============================================================
# LOAD
# ============================================================

def load_pages_reviewed():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            "\nPages-reviewed file was not found:\n"
            f"{INPUT_FILE}\n\n"
            "Run pagereviewer.py first."
        )

    print()
    print("Reading:")
    print(INPUT_FILE)

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    return data


def extract_actions(data):

    if not isinstance(data, dict):

        raise ValueError(
            "Invalid _pages_reviewed.json structure."
        )

    actions = data.get("actions")

    if not isinstance(actions, list):

        raise ValueError(
            "Expected top-level key 'actions' "
            "to be a list, but it was not found "
            "or was the wrong type."
        )

    return actions


# ============================================================
# ACTION NORMALIZATION
# ============================================================

def normalize_action(raw_action):

    if not isinstance(raw_action, dict):
        return None

    url = normalize(
        raw_action.get("url")
    )

    title = normalize(
        raw_action.get("title")
    )

    action_type = normalize_action_type(
        raw_action.get("action_type")
    )

    reason = normalize(
        raw_action.get("reason")
    )

    priority = normalize(
        raw_action.get("priority")
    ) or "high"

    original_classification = normalize(
        raw_action.get("original_classification")
    )

    program_code = parse_program(url)

    context = parse_context(url)

    return {
        "title": title,
        "url": url,
        "action_type": action_type,
        "reason": reason,
        "priority": priority,
        "original_classification": original_classification,
        "program_code": program_code,
        "program": program_label(program_code),
        "context": context,
    }


# ============================================================
# VALIDATION / FILTERING
# ============================================================

def determine_usability(action):

    if not action.get("url"):

        return (
            False,
            "MISSING_URL",
        )

    if not action.get("title"):

        return (
            False,
            "MISSING_TITLE",
        )

    action_type = action.get("action_type")

    if not action_type:

        return (
            False,
            "MISSING_ACTION_TYPE",
        )

    if action_type not in VALID_ACTION_TYPES:

        return (
            False,
            f"UNKNOWN_ACTION_TYPE:{action_type}",
        )

    return (
        True,
        "USABLE",
    )


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_actions(actions):

    unique = []

    duplicates = []

    seen = {}

    for action in actions:

        url = normalize_url(
            action.get("url", "")
        )

        if not url:

            unique.append(action)
            continue

        if url not in seen:

            seen[url] = action
            unique.append(action)

        else:

            duplicates.append(
                {
                    "url": url,
                    "existing": seen[url],
                    "candidate": action,
                }
            )

    return unique, duplicates


# ============================================================
# BUILD REGISTRY
# ============================================================

def build_registry(actions):

    grouped = defaultdict(list)

    excluded = []

    usable_actions = []

    for action in actions:

        usable, reason = determine_usability(
            action
        )

        if not usable:

            excluded.append(
                {
                    "action": action,
                    "reason": reason,
                }
            )

            continue

        record = {

            "title": action["title"],

            "url": action["url"],

            "program": action["program"],

            "context": action["context"],

            "reason": action["reason"],

            "priority": action["priority"],
        }

        grouped[
            action["action_type"]
        ].append(record)

        usable_actions.append(action)

    return (
        dict(grouped),
        excluded,
        usable_actions,
    )


# ============================================================
# SORT REGISTRY
# ============================================================

def sort_registry(grouped):

    sorted_registry = {}

    for action_type in sorted(
        grouped.keys()
    ):

        entries = grouped[action_type]

        entries.sort(
            key=lambda item: (
                item.get("program", "").lower(),
                item.get("context", "").lower(),
                item.get("title", "").lower(),
            )
        )

        sorted_registry[action_type] = entries

    return sorted_registry


# ============================================================
# BUILD OUTPUT
# ============================================================

def build_output(
    input_count,
    unique_count,
    duplicate_count,
    registry,
    excluded,
    duplicate_records,
):

    total_actions = sum(
        len(entries)
        for entries in registry.values()
    )

    output = {

        "source":
            "UET Admissions Portal",

        "stage":
            "actions_registry",

        "input_file":
            str(INPUT_FILE),

        "output_file":
            str(OUTPUT_FILE),

        "counts": {

            "input_actions":
                input_count,

            "unique_actions":
                unique_count,

            "duplicates":
                duplicate_count,

            "usable_actions":
                total_actions,

            "excluded_actions":
                len(excluded),

            "action_types":
                len(registry),
        },

        "actions":
            registry,

        "duplicates": [

            {

                "url":
                    item["url"],

                "existing_title":
                    item["existing"].get(
                        "title",
                        ""
                    ),

                "candidate_title":
                    item["candidate"].get(
                        "title",
                        ""
                    ),
            }

            for item in duplicate_records
        ],

        "excluded": [

            {

                "title":
                    item["action"].get(
                        "title",
                        ""
                    ),

                "url":
                    item["action"].get(
                        "url",
                        ""
                    ),

                "action_type":
                    item["action"].get(
                        "action_type",
                        ""
                    ),

                "reason":
                    item["reason"],
            }

            for item in excluded
        ],
    }

    return output


# ============================================================
# VALIDATION
# ============================================================

def validate_output(output):

    errors = []

    registry = output.get(
        "actions",
        {}
    )

    counts = output.get(
        "counts",
        {}
    )

    for action_type, entries in registry.items():

        if not isinstance(
            entries,
            list
        ):

            errors.append(
                f"Action type '{action_type}' "
                "is not a list."
            )

        if action_type not in VALID_ACTION_TYPES:

            errors.append(
                f"Unknown action type "
                f"'{action_type}'."
            )

        for entry in entries:

            if not entry.get("url"):

                errors.append(
                    "Missing URL in "
                    f"action type '{action_type}'."
                )

            if not entry.get("title"):

                errors.append(
                    "Missing title in "
                    f"action type '{action_type}'."
                )

    actual_usable = sum(
        len(entries)
        for entries in registry.values()
    )

    if actual_usable != counts.get(
        "usable_actions",
        actual_usable
    ):

        errors.append(
            "Usable action count does not "
            "match registry contents."
        )

    return errors


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "UET ADMISSION — ACTION REGISTRY BUILDER"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    data = load_pages_reviewed()

    raw_actions = extract_actions(data)

    print()
    print(
        f"Actions available: {len(raw_actions)}"
    )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    actions = []

    for raw_action in raw_actions:

        action = normalize_action(
            raw_action
        )

        if action is not None:

            actions.append(action)

    print(
        f"Actions normalized: {len(actions)}"
    )

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    print()
    print(
        "Deduplicating actions..."
    )

    (
        unique_actions,
        duplicate_records
    ) = deduplicate_actions(
        actions
    )

    print(
        f"Unique actions: "
        f"{len(unique_actions)}"
    )

    print(
        f"Duplicates: "
        f"{len(duplicate_records)}"
    )

    # --------------------------------------------------------
    # Build
    # --------------------------------------------------------

    print()
    print(
        "Building action registry..."
    )

    (
        registry,
        excluded,
        usable_actions,
    ) = build_registry(
        unique_actions
    )

    registry = sort_registry(
        registry
    )

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "ACTION REGISTRY BUILD RESULT"
    )
    print("=" * 70)

    print()
    print(
        f"Input actions: "
        f"{len(actions)}"
    )

    print(
        f"Unique actions: "
        f"{len(unique_actions)}"
    )

    print(
        f"Duplicates: "
        f"{len(duplicate_records)}"
    )

    print(
        f"Usable: "
        f"{len(usable_actions)}"
    )

    print(
        f"Excluded: "
        f"{len(excluded)}"
    )

    # --------------------------------------------------------
    # Registry
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "ACTION REGISTRY"
    )
    print("=" * 70)

    if not registry:

        print(
            "No action types were created."
        )

    else:

        for action_type, entries in registry.items():

            print()
            print(
                f"[{action_type}]"
            )

            print(
                f"Entries: "
                f"{len(entries)}"
            )

            for index, entry in enumerate(
                entries,
                start=1
            ):

                print(
                    f"  [{index:03d}] "
                    f"{entry['title']}"
                )

                print(
                    f"        "
                    f"{entry['url']}"
                )

                print(
                    f"        Program: "
                    f"{entry['program']} | "
                    f"Context: "
                    f"{entry['context'] or '-'}"
                )

    # --------------------------------------------------------
    # Duplicates
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "DUPLICATES"
    )
    print("=" * 70)

    if not duplicate_records:

        print("None")

    else:

        for item in duplicate_records:

            print()
            print(
                f"DUPLICATE: "
                f"{item['url']}"
            )

            print(
                f"  Existing: "
                f"{item['existing'].get('title', '')}"
            )

            print(
                f"  Candidate: "
                f"{item['candidate'].get('title', '')}"
            )

    # --------------------------------------------------------
    # Excluded
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "EXCLUDED"
    )
    print("=" * 70)

    if not excluded:

        print("None")

    else:

        for item in excluded:

            action = item["action"]

            print()
            print(
                f" — "
                f"{action.get('title', '')}"
            )

            print(
                action.get(
                    'url',
                    ''
                )
            )

            print(
                f"Reason: "
                f"{item['reason']}"
            )

    # --------------------------------------------------------
    # Build output
    # --------------------------------------------------------

    output = build_output(

        input_count=len(
            actions
        ),

        unique_count=len(
            unique_actions
        ),

        duplicate_count=len(
            duplicate_records
        ),

        registry=registry,

        excluded=excluded,

        duplicate_records=
            duplicate_records,
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "VALIDATION"
    )
    print("=" * 70)

    validation_errors = validate_output(
        output
    )

    if validation_errors:

        print(
            "INVALID"
        )

        for error in validation_errors:

            print(
                f"ERROR: {error}"
            )

        raise ValueError(
            "Action registry validation failed."
        )

    else:

        print(
            "VALID"
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )

    # --------------------------------------------------------
    # Saved
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "SAVED"
    )
    print("=" * 70)

    print()
    print(
        OUTPUT_FILE
    )

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()