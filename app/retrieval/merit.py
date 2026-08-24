from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urljoin

import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

BASE_URL = "https://admission.uet.edu.pk/"
DOWNLOADS_URL = urljoin(BASE_URL, "downloads")

CACHE_DIR = Path(__file__).resolve().parent / "uet_cache"
CACHE_DIR.mkdir(exist_ok=True)

TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/131 Safari/537.36"
    )
}


# ---------------------------------------------------------------------------
# DATA MODEL
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MeritRecord:
    campus: str
    program: str
    category: str
    session: str
    admission_type: str
    closing_merit: float
    page: int = 0

    def display(self) -> str:
        return (
            f"{self.campus} | {self.program} | {self.category} | "
            f"{self.session} | {self.admission_type} | "
            f"{self.closing_merit:.5f}"
        )


# ---------------------------------------------------------------------------
# NORMALIZATION / ALIASES
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    text = str(text or "")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize(text).lower())


CAMPUS_ALIASES = {
    "lhr": "Main Campus (LHR)",
    "lahore": "Main Campus (LHR)",
    "main": "Main Campus (LHR)",
    "main campus": "Main Campus (LHR)",
    "main campus lhr": "Main Campus (LHR)",

    "ksk": "New Campus (KSK)",
    "new": "New Campus (KSK)",
    "new campus": "New Campus (KSK)",
    "new campus ksk": "New Campus (KSK)",

    "fsd": "Faislabad Campus",
    "faislabad": "Faislabad Campus",
    "faisalabad": "Faislabad Campus",
    "faislabad campus": "Faislabad Campus",
    "faisalabad campus": "Faislabad Campus",

    "grw": "Gujaranwala",
    "gujranwala": "Gujaranwala",
    "gujaranwala": "Gujaranwala",
    "gujranwala campus": "Gujaranwala",

    "nwl": "Narowal Campus (NWL)",
    "narowal": "Narowal Campus (NWL)",
    "narowal campus": "Narowal Campus (NWL)",
}


PROGRAM_ALIASES = {
    "cs": "Computer Science",
    "computer science": "Computer Science",
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "cyber": "Cybersecurity",
    "cyber security": "Cybersecurity",
    "cybersecurity": "Cybersecurity",
    "ds": "Data Science",
    "data science": "Data Science",
    "ee": "Electrical Engineering",
    "electrical": "Electrical Engineering",
    "electrical engineering": "Electrical Engineering",
    "ce": "Computer Engineering (NCEAC)",
    "computer engineering": "Computer Engineering (NCEAC)",
    "me": "Mechanical Engineering",
    "mechanical": "Mechanical Engineering",
    "mechanical engineering": "Mechanical Engineering",
    "civil": "Civil Engineering",
    "civil engineering": "Civil Engineering",
}


CATEGORY_ALIASES = {
    "a1": "A1",
    "a1m": "A1-M",
    "a1-m": "A1-M",
    "a2": "A2",
    "a2m": "A2-M",
    "a2-m": "A2-M",
    "ap1": "AP1",
    "ap1m": "AP1-M",
    "ap1-m": "AP1-M",
    "ap2": "AP2",
    "ap2m": "AP2-M",
    "ap2-m": "AP2-M",
    "m": "M",
    "nm": "NM",

    # Bug fix: single-letter quota codes present in the report (e.g.
    # Electrical/Mechanical/Civil "L/N/O/P/R/S/T") were missing entirely,
    # so filter_records(..., category="S") etc. silently matched nothing.
    "l": "L",
    "n": "N",
    "o": "O",
    "p": "P",
    "r": "R",
    "s": "S",
    "t": "T",
}


def canonical_campus(value: str) -> Optional[str]:
    raw = normalize(value).lower()
    if raw in CAMPUS_ALIASES:
        return CAMPUS_ALIASES[raw]

    c = compact(raw)
    for alias, canonical in CAMPUS_ALIASES.items():
        if compact(alias) == c:
            return canonical

    # Fall back: the PDF's campus cell text is already the canonical form
    # (e.g. "Faislabad Campus", "Gujaranwala", "Main Campus (LHR)").
    for canonical in set(CAMPUS_ALIASES.values()):
        if compact(canonical) == c:
            return canonical

    return None


def canonical_category(value: str) -> Optional[str]:
    raw = normalize(value).lower()
    return CATEGORY_ALIASES.get(raw)


def canonical_program(value: str) -> Optional[str]:
    raw = normalize(value).lower()
    if raw in PROGRAM_ALIASES:
        return PROGRAM_ALIASES[raw]
    return normalize(value)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def fetch(url: str, session: requests.Session) -> requests.Response:
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return response


# ---------------------------------------------------------------------------
# FIND LATEST MERIT PDF
# ---------------------------------------------------------------------------

@dataclass
class MeritDocument:
    url: str
    title: str
    list_number: int
    admission: str


_ORDINAL_WORDS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "eleventh": 11, "twelfth": 12,
}

# Programs unrelated to the UG closing-merit reports we care about, so we
# don't accidentally pick up a PG/M.Sc/Ph.D "merit list" document that
# happens to share wording.
_EXCLUDE_KEYWORDS = ("postgraduate", "m.sc", "ms ", "ph.d", "phd")


def _extract_list_number(combined_text: str) -> Optional[int]:
    """Bug fix: UET has not used consistent title wording across merit
    lists within the SAME admission cycle -- e.g. 'Merit List No. 1',
    'Second Merit List', 'Minimum Merit - 3rd Merit List' have all been
    used. Try digit-based patterns first, then fall back to spelled-out
    ordinals, so a future list isn't silently missed just because UET
    phrased the title differently than the last one did."""

    for pattern in (
        r"(\d+)\s*(?:st|nd|rd|th)?\s+merit\s*list",
        r"merit\s*list\s*(?:no\.?|number)?\s*[:\-]?\s*(\d+)",
    ):
        match = re.search(pattern, combined_text, re.I)
        if match:
            return int(match.group(1))

    word_match = re.search(
        r"\b(" + "|".join(_ORDINAL_WORDS) + r")\s+merit\s*list",
        combined_text,
        re.I,
    )
    if word_match:
        return _ORDINAL_WORDS[word_match.group(1).lower()]

    return None


def discover_merit_documents(session: requests.Session) -> list[MeritDocument]:
    response = fetch(DOWNLOADS_URL, session)
    soup = BeautifulSoup(response.text, "html.parser")

    documents: list[MeritDocument] = []

    for heading in soup.find_all(["h3", "h4", "h5"]):
        heading_text = normalize(heading.get_text(" ", strip=True))
        low = heading_text.lower()

        # Bug fix: the old filter required the literal substring
        # "minimum merit", which only matches SOME of UET's own titles
        # (e.g. it misses "Second Merit List Closing Merits" and
        # "Merit List No. 1" -- both real titles UET has used for this
        # same Fall 2026 cycle). Broaden to anything that looks like a
        # closing-merit / minimum-aggregate report tied to a merit list,
        # while excluding unrelated PG/Ph.D merit lists.
        looks_relevant = (
            "merit list" in low
            or ("minimum" in low and ("merit" in low or "aggregate" in low))
        )
        if not looks_relevant:
            continue
        if any(kw in low for kw in _EXCLUDE_KEYWORDS):
            continue

        for node in heading.find_all_next():
            if node is not heading and node.name in {"h3", "h4", "h5"}:
                break

            if node.name != "a":
                continue

            href = node.get("href")
            text = normalize(node.get_text(" ", strip=True))

            if not href:
                continue

            combined = f"{heading_text} {text}"
            list_number = _extract_list_number(combined)

            if list_number is None:
                continue

            url = urljoin(response.url, href)

            documents.append(
                MeritDocument(
                    url=url,
                    title=text or heading_text,
                    list_number=list_number,
                    admission=heading_text,
                )
            )

    unique = {}
    for doc in documents:
        unique[doc.url] = doc

    return list(unique.values())


def choose_latest_document(documents: list[MeritDocument]) -> MeritDocument:
    if not documents:
        raise RuntimeError(
            "Could not find a UET Minimum Merit PDF on the downloads page."
        )

    def key(doc: MeritDocument):
        years = [int(x) for x in re.findall(r"20\d{2}", doc.admission + " " + doc.title)]
        year = max(years) if years else 0
        return (year, doc.list_number)

    return max(documents, key=key)


def download_pdf(doc: MeritDocument, session: requests.Session) -> Path:
    response = fetch(doc.url, session)

    content = response.content
    if not content.startswith(b"%PDF"):
        raise RuntimeError(f"Downloaded URL is not a PDF: {doc.url}")

    filename = CACHE_DIR / f"merit_list_{doc.list_number}.pdf"
    filename.write_bytes(content)
    return filename


# ---------------------------------------------------------------------------
# PDF EXTRACTION
# ---------------------------------------------------------------------------
#
# IMPORTANT (bug fix): this report is a real PDF *table*, not a text flow.
# PyMuPDF's page.get_text("text") does NOT return one line per table row.
# It returns one line per *table cell*, in row-major reading order:
#
#   'Faislabad Campus'
#   'Chemical Engineering'
#   'A1'
#   'Morning'
#   'ECAT'
#   '64.43113'
#   'Faislabad Campus'
#   'Computer Engineering (NCEAC)'
#   ...
#
# The previous implementation assumed each table row was a single text
# line ("Faislabad Campus Chemical Engineering A1 Morning ECAT 64.43113")
# and tried to reverse-parse that line with regexes anchored at the end.
# Since no such combined line ever exists in the extracted text, every
# call to parse_row() returned None and load_data()/load_latest_merit()
# always raised "No merit rows were extracted from the PDF."
#
# The fix: after stripping repeated header/footer noise, group the
# remaining per-cell lines into consecutive chunks of 6
# (Campus, Discipline, Category, Session, Type, Closing Merit) and build
# a MeritRecord straight from those 6 values -- no reverse-engineering
# needed, and it no longer depends on program names never containing a
# session/category/type-like word.

# Bug fix: the report also uses single-letter quota codes (L, N, O, P, R,
# S, T, ...) alongside the merit-based A1/A2/AP1/AP2/M/NM codes. The old
# pattern only recognized the latter, so any row whose category was one
# of those single letters failed validation and desynced the (already
# broken) line-based row parser.
CATEGORY_RE = r"(?:A1-M|A2-M|AP1-M|AP2-M|A1|A2|AP1|AP2|NM|M|[A-Z]{1,2})"

# Bug fix: the report also contains "Afternoon" sessions (e.g. Business
# Administration / BBIT / Remote Sensing rows), which the old
# Morning|Evening-only pattern silently dropped.
SESSION_VALUES = {"morning": "Morning", "evening": "Evening", "afternoon": "Afternoon"}
TYPE_VALUES = {"ecat": "ECAT", "non-ecat": "Non-ECAT"}

_HEADER_CELL_LABELS = {
    "campus", "discipline", "category", "session", "type", "closing merit",
}


def is_header_or_noise(line: str) -> bool:
    low = line.lower()

    if low in _HEADER_CELL_LABELS:
        return True
    if "closing merit report" in low:
        return True
    if low.startswith("campus discipline"):
        return True
    if "university of engineering" in low:
        return True
    if low.startswith("ug-") and "page" in low:
        return True
    if low.startswith("admission:"):
        return True
    if low.startswith("merit list no"):
        return True

    return False


def build_record(
    campus_raw: str,
    program_raw: str,
    category_raw: str,
    session_raw: str,
    type_raw: str,
    merit_raw: str,
    page: int,
) -> Optional[MeritRecord]:
    """Build a MeritRecord from one 6-cell (row) group, validating each
    field against the values we actually expect in that column. Returns
    None if the cells don't look like a real row (used to resync the
    grouping if a page ever has stray/blank lines)."""

    session = SESSION_VALUES.get(normalize(session_raw).lower())
    if session is None:
        return None

    admission_type = TYPE_VALUES.get(normalize(type_raw).lower())
    if admission_type is None:
        return None

    category = normalize(category_raw)
    if not re.fullmatch(CATEGORY_RE, category, re.I):
        return None

    merit_text = normalize(merit_raw)
    try:
        closing_merit = float(merit_text)
    except ValueError:
        return None

    if not (0 <= closing_merit <= 100):
        return None

    campus = canonical_campus(campus_raw) or normalize(campus_raw)
    program = normalize(program_raw)

    if not program:
        return None

    return MeritRecord(
        campus=campus,
        program=program,
        category=category.upper(),
        session=session,
        admission_type=admission_type,
        closing_merit=closing_merit,
        page=page,
    )


def extract_all_rows(pdf_path: Path) -> list[MeritRecord]:
    document = fitz.open(pdf_path)
    records: list[MeritRecord] = []

    try:
        for page_index in range(len(document)):
            page = document[page_index]
            text = page.get_text("text")

            cells = [normalize(l) for l in text.splitlines()]
            cells = [c for c in cells if c and not is_header_or_noise(c)]

            i = 0
            n = len(cells)
            while i + 6 <= n:
                record = build_record(*cells[i:i + 6], page=page_index + 1)
                if record:
                    records.append(record)
                    i += 6
                else:
                    # Not a valid 6-cell row starting here (e.g. stray
                    # line) -- shift by one cell and try to resync
                    # instead of silently dropping the rest of the page.
                    i += 1

            if i != n:
                print(
                    f"Warning: page {page_index + 1} had "
                    f"{n - i} trailing unparsed cell(s): {cells[i:]}"
                )
    finally:
        document.close()

    # Deduplicate using the actual identity of a merit row.
    unique: dict[tuple, MeritRecord] = {}

    for record in records:
        key = (
            record.campus.lower(),
            record.program.lower(),
            record.category.upper(),
            record.session.lower(),
            record.admission_type.lower(),
        )
        unique.setdefault(key, record)

    return sorted(
        unique.values(),
        key=lambda r: (
            r.campus.lower(),
            r.program.lower(),
            r.category,
            r.session.lower(),
            r.admission_type.lower(),
        ),
    )


# ---------------------------------------------------------------------------
# DATA VALIDATION
# ---------------------------------------------------------------------------

def validate_records(records: list[MeritRecord]) -> None:
    if not records:
        raise RuntimeError("No merit rows were extracted from the PDF.")

    bad = [
        r for r in records
        if not r.program or not (0 <= r.closing_merit <= 100)
    ]

    if bad:
        print(f"Warning: {len(bad)} suspicious records were extracted.")

    campuses = sorted({r.campus for r in records})
    programs = sorted({r.program for r in records})

    print(f"Extracted records : {len(records)}")
    print(f"Campuses          : {len(campuses)}")
    print(f"Programs           : {len(programs)}")


# ---------------------------------------------------------------------------
# SEARCH / QUERY ENGINE
# ---------------------------------------------------------------------------

def text_match(value: str, query: str) -> bool:
    q = normalize(query).lower()
    v = normalize(value).lower()

    if not q:
        return True

    return q in v or compact(q) in compact(v)


def find_program(records: list[MeritRecord], query: str) -> list[MeritRecord]:
    q = normalize(query).lower()

    if q in PROGRAM_ALIASES:
        q = PROGRAM_ALIASES[q].lower()

    exact = [
        r for r in records
        if r.program.lower() == q
    ]

    if exact:
        return exact

    return [
        r for r in records
        if text_match(r.program, q)
    ]


def filter_records(
    records: list[MeritRecord],
    campus: Optional[str] = None,
    program: Optional[str] = None,
    category: Optional[str] = None,
    session: Optional[str] = None,
    admission_type: Optional[str] = None,
) -> list[MeritRecord]:

    canonical_c = canonical_campus(campus) if campus else None
    canonical_cat = canonical_category(category) if category else None

    canonical_p = None
    if program:
        canonical_p = canonical_program(program)

    result = records

    if canonical_c:
        result = [
            r for r in result
            if r.campus == canonical_c
        ]

    if canonical_p:
        result = [
            r for r in result
            if (
                r.program.lower() == canonical_p.lower()
                or text_match(r.program, canonical_p)
            )
        ]

    if canonical_cat:
        result = [
            r for r in result
            if r.category.upper() == canonical_cat.upper()
        ]

    if session:
        result = [
            r for r in result
            if r.session.lower() == session.lower()
        ]

    if admission_type:
        result = [
            r for r in result
            if r.admission_type.lower() == admission_type.lower()
        ]

    return result


def parse_query_filters(query: str):
    """Extract easy structured tokens from natural language."""

    low = normalize(query).lower()

    campus = None
    for alias, canonical in sorted(
        CAMPUS_ALIASES.items(),
        key=lambda x: len(x[0]),
        reverse=True,
    ):
        if re.search(rf"\b{re.escape(alias)}\b", low):
            campus = canonical
            break

    category = None
    for alias, canonical in sorted(
        CATEGORY_ALIASES.items(),
        key=lambda x: len(x[0]),
        reverse=True,
    ):
        if re.search(rf"\b{re.escape(alias)}\b", low):
            category = canonical
            break

    session = None
    if re.search(r"\bafternoon\b", low):
        session = "Afternoon"
    elif re.search(r"\bevening\b", low):
        session = "Evening"
    elif re.search(r"\bmorning\b", low):
        session = "Morning"

    admission_type = None
    if re.search(r"\bnon[- ]?ecat\b", low):
        admission_type = "Non-ECAT"
    elif re.search(r"\becat\b", low):
        admission_type = "ECAT"

    program = None
    for alias, canonical in sorted(
        PROGRAM_ALIASES.items(),
        key=lambda x: len(x[0]),
        reverse=True,
    ):
        if re.search(rf"\b{re.escape(alias)}\b", low):
            program = canonical
            break

    return campus, program, category, session, admission_type


# ---------------------------------------------------------------------------
# COMMANDS
# ---------------------------------------------------------------------------

def print_records(records: list[MeritRecord], limit: int = 100) -> None:
    if not records:
        print("\nNo matching records found.")
        return

    shown = records[:limit]

    print()
    print(
        f"{'Campus':<24} "
        f"{'Program':<38} "
        f"{'Cat':<6} "
        f"{'Session':<9} "
        f"{'Type':<10} "
        f"{'Merit':>9}"
    )
    print("-" * 105)

    for r in shown:
        print(
            f"{r.campus:<24.24} "
            f"{r.program:<38.38} "
            f"{r.category:<6} "
            f"{r.session:<9} "
            f"{r.admission_type:<10} "
            f"{r.closing_merit:>9.5f}"
        )

    if len(records) > limit:
        print(f"\nShowing {limit} of {len(records)} records.")


def check_aggregate(
    records: list[MeritRecord],
    aggregate: float,
) -> None:
    print(f"\nYour aggregate: {aggregate:.5f}")
    print("Comparison against matching closing merits:\n")

    for r in records:
        difference = aggregate - r.closing_merit
        status = "ABOVE" if difference >= 0 else "BELOW"

        print(
            f"{status:>5}  "
            f"{r.campus} | {r.program} | {r.category} | "
            f"{r.session} | {r.admission_type} | "
            f"merit={r.closing_merit:.5f} | "
            f"difference={difference:+.5f}"
        )


def extract_user_aggregate(query: str) -> Optional[float]:
    numbers = re.findall(r"\b\d{1,3}(?:\.\d+)?\b", query)

    for n in numbers:
        value = float(n)
        if 0 <= value <= 100:
            if "." in n or value >= 50:
                return value

    return None


def run_query(records: list[MeritRecord], query: str) -> None:
    low = normalize(query).lower()

    if (
        ("program" in low or "programs" in low)
        and ("all" in low or "show" in low or "list" in low)
    ):
        campus, _, _, _, _ = parse_query_filters(query)

        if campus:
            campus_records = filter_records(records, campus=campus)
            programs = sorted({r.program for r in campus_records})

            print(f"\nPrograms at {campus}:")
            for p in programs:
                print(f"  - {p}")
            print(f"\nTotal programs: {len(programs)}")
            return

    threshold_match = re.search(
        r"\b(?:below|under|less than|above|over|greater than)\s+"
        r"(\d{1,3}(?:\.\d+)?)",
        low,
    )

    if threshold_match:
        threshold = float(threshold_match.group(1))
        campus, program, category, session, admission_type = parse_query_filters(query)

        filtered = filter_records(
            records,
            campus=campus,
            program=program,
            category=category,
            session=session,
            admission_type=admission_type,
        )

        if re.search(r"\b(?:below|under|less than)\b", low):
            filtered = [r for r in filtered if r.closing_merit < threshold]
        else:
            filtered = [r for r in filtered if r.closing_merit > threshold]

        print_records(filtered)
        return

    campus, program, category, session, admission_type = parse_query_filters(query)

    if not program:
        q = re.sub(
            r"\b(?:what|what is|show|find|merit|closing|minimum|for|at|the|"
            r"campus|morning|evening|afternoon|ecat|non[- ]?ecat)\b",
            " ",
            low,
        )
        q = re.sub(
            r"\b(?:a1m|a2m|ap1m|ap2m|a1|a2|ap1|ap2|nm|m)\b",
            " ",
            q,
        )
        q = normalize(q)

        if q:
            candidates = find_program(records, q)
            if len(candidates) > 0:
                program_names = sorted({r.program for r in candidates})
                if len(program_names) == 1:
                    program = program_names[0]

    filtered = filter_records(
        records,
        campus=campus,
        program=program,
        category=category,
        session=session,
        admission_type=admission_type,
    )

    aggregate = extract_user_aggregate(query)

    if aggregate is not None and filtered:
        check_aggregate(filtered, aggregate)
    else:
        print_records(filtered)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def load_data() -> tuple[list[MeritRecord], MeritDocument, Path]:
    session = get_session()

    print("Checking UET for the latest Minimum Merit list...")

    documents = discover_merit_documents(session)
    latest = choose_latest_document(documents)

    print(f"Latest list: Merit List {latest.list_number}")
    print(f"Admission : {latest.admission}")
    print(f"Source    : {latest.url}")

    pdf_path = download_pdf(latest, session)

    print(f"PDF       : {pdf_path}")

    records = extract_all_rows(pdf_path)
    validate_records(records)

    return records, latest, pdf_path


def load_latest_merit() -> dict:

    session = get_session()

    documents = discover_merit_documents(session)
    latest = choose_latest_document(documents)
    pdf_path = download_pdf(latest, session)
    records = extract_all_rows(pdf_path)
    validate_records(records)

    data = [
        {
            "campus": r.campus,
            "program": r.program,
            "category": r.category,
            "session": r.session,
            "type": r.admission_type,
            "minimum_aggregate": r.closing_merit,
            "page": r.page,
        }
        for r in records
    ]

    return {
        "data": data,
        "pdf_file": str(pdf_path),
        "source_url": latest.url,
        "merit_list_number": latest.list_number,
        "title": latest.admission,
        "checked_at": datetime.now().isoformat(),
    }


def main() -> None:
    try:
        records, latest, pdf_path = load_data()
    except Exception as exc:
        print(f"\nERROR: {exc}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("UET GENERAL MERIT QUERY")
    print("=" * 70)
    print("Examples:")
    print("  Computer Science Lahore A1")
    print("  CS KSK")
    print("  Electrical Engineering Narowal")
    print("  show all programs at Lahore")
    print("  Mechanical Engineering A2-M")
    print("  programs below 70 at KSK")
    print("  Computer Science Lahore A1 with 87.5")
    print("  type 'help' for more examples")
    print("  type 'exit' to quit")
    print()

    while True:
        try:
            query = input("UET> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not query:
            continue

        if query.lower() in {"exit", "quit", "q"}:
            print("Goodbye.")
            break

        if query.lower() == "help":
            print("""
GENERAL QUERIES

Program:
  Computer Science Lahore A1
  CS KSK
  Electrical Engineering Narowal
  Mechanical Engineering A2-M

Campus:
  show all programs at Lahore
  show all programs at KSK

Filters:
  Computer Science Morning
  Computer Science ECAT
  Computer Science A1-M Lahore

Aggregate:
  Computer Science Lahore A1 with 87.5
  CS KSK 84.2

Thresholds:
  programs below 70 at KSK
  programs above 85 at Lahore

Aliases:
  LHR = Main Campus
  KSK = New Campus
  FSD = Faislabad Campus
  GRW = Gujaranwala
  NWL = Narowal
  CS = Computer Science
  AI = Artificial Intelligence
  EE = Electrical Engineering
  ME = Mechanical Engineering
""")
            continue

        try:
            run_query(records, query)
        except Exception as exc:
            print(f"Query error: {exc}")


if __name__ == "__main__":
    main()
