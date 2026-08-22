
from pathlib import Path
import json
from collections import Counter, defaultdict
from urllib.parse import urlparse


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(r"D:\UET Chatbot")

ADMISSION_ROOT = (
    PROJECT_ROOT
    / "data"
    / "inventory"
    / "admission"
)

INPUT_FILE = ADMISSION_ROOT / "_map.json"
OUTPUT_FILE = ADMISSION_ROOT / "_map_inspection.txt"


# ============================================================
# HELPERS
# ============================================================

def write_line(f, text=""):
    f.write(str(text) + "\n")


def shorten(text, length=180):
    text = str(text).replace("\n", " ").strip()
    if len(text) > length:
        return text[:length - 3] + "..."
    return text


def get_url(obj):
    if isinstance(obj, dict):
        for key in ("url", "href", "link"):
            value = obj.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def get_title(obj):
    if isinstance(obj, dict):
        for key in ("title", "name", "label", "text"):
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def looks_like_file(url):
    if not url:
        return False

    path = urlparse(url).path.lower()

    extensions = (
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".zip",
        ".csv",
        ".txt",
        ".jpg",
        ".jpeg",
        ".png",
    )

    return path.endswith(extensions)


def is_external(url):
    if not url:
        return False

    host = urlparse(url).netloc.lower()

    return host and "admission.uet.edu.pk" not in host


# ============================================================
# LOAD
# ============================================================

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Could not find:\n{INPUT_FILE}"
    )

with INPUT_FILE.open("r", encoding="utf-8") as f:
    data = json.load(f)


# ============================================================
# BASIC STRUCTURE
# ============================================================

with OUTPUT_FILE.open("w", encoding="utf-8") as out:

    write_line(out, "=" * 80)
    write_line(out, "UET ADMISSION _map.json — STRUCTURAL INSPECTION")
    write_line(out, "=" * 80)
    write_line(out)

    write_line(out, f"Input:  {INPUT_FILE}")
    write_line(out, f"Output: {OUTPUT_FILE}")
    write_line(out)

    write_line(out, "ROOT JSON TYPE")
    write_line(out, "-" * 80)
    write_line(out, type(data).__name__)
    write_line(out)

    # --------------------------------------------------------
    # TOP LEVEL
    # --------------------------------------------------------

    write_line(out, "TOP-LEVEL STRUCTURE")
    write_line(out, "-" * 80)

    if isinstance(data, dict):

        for key, value in data.items():
            if isinstance(value, list):
                write_line(
                    out,
                    f"{key}: list ({len(value)} items)"
                )
            elif isinstance(value, dict):
                write_line(
                    out,
                    f"{key}: dict ({len(value)} keys)"
                )
            else:
                write_line(
                    out,
                    f"{key}: {type(value).__name__} = {shorten(value)}"
                )

    elif isinstance(data, list):

        write_line(out, f"List items: {len(data)}")

    write_line(out)

    # --------------------------------------------------------
    # FIND RECORDS RECURSIVELY
    # --------------------------------------------------------

    records = []

    def walk(obj, path="root"):

        if isinstance(obj, dict):

            # A likely page record
            if "url" in obj:
                records.append((path, obj))

            for key, value in obj.items():
                walk(value, f"{path}.{key}")

        elif isinstance(obj, list):

            for i, value in enumerate(obj):
                walk(value, f"{path}[{i}]")

    walk(data)

    write_line(out, "URL-BEARING RECORDS")
    write_line(out, "-" * 80)
    write_line(out, f"Records containing 'url': {len(records)}")
    write_line(out)

    # --------------------------------------------------------
    # URL STATISTICS
    # --------------------------------------------------------

    urls = []

    for _, record in records:
        url = get_url(record)
        if url:
            urls.append(url)

    unique_urls = set(urls)

    write_line(out, "URL STATISTICS")
    write_line(out, "-" * 80)
    write_line(out, f"Total URL occurrences: {len(urls)}")
    write_line(out, f"Unique URLs:            {len(unique_urls)}")
    write_line(out, f"Duplicate occurrences:  {len(urls) - len(unique_urls)}")
    write_line(out)

    # --------------------------------------------------------
    # FILES
    # --------------------------------------------------------

    file_urls = [
        url for url in unique_urls
        if looks_like_file(url)
    ]

    write_line(out, "FILES")
    write_line(out, "-" * 80)
    write_line(out, f"Unique file URLs: {len(file_urls)}")
    write_line(out)

    file_extensions = Counter()

    for url in file_urls:
        suffix = Path(urlparse(url).path).suffix.lower()
        file_extensions[suffix or "[no extension]"] += 1

    write_line(out, "File extensions:")
    for ext, count in file_extensions.most_common():
        write_line(out, f"  {ext}: {count}")

    write_line(out)

    write_line(out, "FILE URL SAMPLE (first 100)")
    write_line(out, "-" * 80)

    for url in sorted(file_urls)[:100]:
        write_line(out, url)

    write_line(out)

    # --------------------------------------------------------
    # EXTERNAL
    # --------------------------------------------------------

    external_urls = [
        url for url in unique_urls
        if is_external(url)
    ]

    write_line(out, "EXTERNAL URLs")
    write_line(out, "-" * 80)
    write_line(out, f"Unique external URLs: {len(external_urls)}")
    write_line(out)

    external_domains = Counter()

    for url in external_urls:
        domain = urlparse(url).netloc.lower()
        external_domains[domain] += 1

    write_line(out, "External domains:")
    for domain, count in external_domains.most_common(100):
        write_line(out, f"  {domain}: {count}")

    write_line(out)

    write_line(out, "EXTERNAL URL SAMPLE (first 100)")
    write_line(out, "-" * 80)

    for url in sorted(external_urls)[:100]:
        write_line(out, url)

    write_line(out)

    # --------------------------------------------------------
    # INTERNAL PAGE URLs
    # --------------------------------------------------------

    internal_urls = [
        url for url in unique_urls
        if not is_external(url) and not looks_like_file(url)
    ]

    write_line(out, "INTERNAL PAGE URLs")
    write_line(out, "-" * 80)
    write_line(out, f"Unique internal page URLs: {len(internal_urls)}")
    write_line(out)

    # --------------------------------------------------------
    # URL PATH PATTERNS
    # --------------------------------------------------------

    path_patterns = Counter()

    for url in internal_urls:

        parsed = urlparse(url)
        path = parsed.path

        if not path:
            pattern = "/"
        else:
            parts = path.strip("/").split("/")

            if parts:
                pattern = "/" + parts[0]
            else:
                pattern = "/"

        path_patterns[pattern] += 1

    write_line(out, "INTERNAL URL FIRST-PATH PATTERNS")
    write_line(out, "-" * 80)

    for pattern, count in path_patterns.most_common():
        write_line(out, f"{pattern}: {count}")

    write_line(out)

    # --------------------------------------------------------
    # DEPTH
    # --------------------------------------------------------

    depths = Counter()

    for _, record in records:

        depth = record.get("depth")

        if isinstance(depth, int):
            depths[depth] += 1
        elif isinstance(depth, str) and depth.isdigit():
            depths[int(depth)] += 1

    write_line(out, "DEPTH DISTRIBUTION")
    write_line(out, "-" * 80)

    if depths:
        for depth, count in sorted(depths.items()):
            write_line(out, f"Depth {depth}: {count}")
    else:
        write_line(out, "No 'depth' field found.")

    write_line(out)

    # --------------------------------------------------------
    # TITLES
    # --------------------------------------------------------

    titles = []

    for _, record in records:
        title = get_title(record)
        if title:
            titles.append(title)

    write_line(out, "TITLES")
    write_line(out, "-" * 80)
    write_line(out, f"Records with titles/names/labels: {len(titles)}")
    write_line(out)

    title_counts = Counter(titles)

    write_line(out, "Most common titles:")
    for title, count in title_counts.most_common(100):
        write_line(
            out,
            f"{count:4} | {shorten(title, 200)}"
        )

    write_line(out)

    # --------------------------------------------------------
    # POSSIBLE NOISE
    # --------------------------------------------------------

    noise_keywords = (
        "login",
        "forgetchallan",
        "challan",
        "account",
        "application",
        "create-challan",
        "admit_card",
        "admit-card",
        "redirectfrom",
    )

    possible_noise = []

    for _, record in records:

        url = get_url(record)

        if not url:
            continue

        lower = url.lower()

        matched = [
            keyword
            for keyword in noise_keywords
            if keyword in lower
        ]

        if matched:
            possible_noise.append(
                (url, matched, record)
            )

    write_line(out, "POSSIBLE APPLICATION / PORTAL NOISE")
    write_line(out, "-" * 80)
    write_line(out, f"Matching URLs: {len(possible_noise)}")
    write_line(out)

    for url, matched, record in possible_noise[:200]:

        title = get_title(record)

        write_line(out, f"URL:   {url}")
        write_line(out, f"Match: {', '.join(matched)}")

        if title:
            write_line(out, f"Title: {title}")

        write_line(out)

    # --------------------------------------------------------
    # RECORD SCHEMA SAMPLES
    # --------------------------------------------------------

    write_line(out, "RECORD SCHEMA SAMPLES")
    write_line(out, "-" * 80)

    sample_records = records[:20]

    for i, (path, record) in enumerate(sample_records, 1):

        write_line(out, f"[SAMPLE {i}]")
        write_line(out, f"JSON path: {path}")
        write_line(out, "Keys:")

        for key in record.keys():
            write_line(out, f"  - {key}")

        write_line(out)

    # --------------------------------------------------------
    # COMPLETE RECORD SAMPLES
    # --------------------------------------------------------

    write_line(out, "COMPLETE RECORD SAMPLES")
    write_line(out, "-" * 80)

    for i, (path, record) in enumerate(sample_records[:10], 1):

        write_line(out, f"[RECORD {i}]")
        write_line(out, f"JSON path: {path}")
        write_line(out)

        pretty = json.dumps(
            record,
            indent=2,
            ensure_ascii=False
        )

        write_line(out, pretty)
        write_line(out)

    # --------------------------------------------------------
    # SECTION DETECTION
    # --------------------------------------------------------

    write_line(out, "POSSIBLE SECTION / ROOT INFORMATION")
    write_line(out, "-" * 80)

    if isinstance(data, dict):

        for key, value in data.items():

            key_lower = key.lower()

            if (
                "section" in key_lower
                or "root" in key_lower
                or "course" in key_lower
                or "map" in key_lower
                or "tree" in key_lower
            ):
                write_line(
                    out,
                    f"{key}: {type(value).__name__}"
                )

                if isinstance(value, list):
                    write_line(
                        out,
                        f"  Items: {len(value)}"
                    )

                elif isinstance(value, dict):
                    write_line(
                        out,
                        f"  Keys: {list(value.keys())[:30]}"
                    )

    write_line(out)

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    write_line(out, "=" * 80)
    write_line(out, "END OF INSPECTION")
    write_line(out, "=" * 80)


print()
print("=" * 70)
print("INSPECTION COMPLETE")
print("=" * 70)
print()
print(f"Input:")
print(INPUT_FILE)
print()
print(f"Inspection saved to:")
print(OUTPUT_FILE)
print()
print("Open this file and paste its contents here.")
print("=" * 70)
