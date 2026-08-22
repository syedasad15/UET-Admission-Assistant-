import json
from pathlib import Path
from collections import Counter


BASE_DIR = Path(r"D:\UET Chatbot\data\inventory\admission")
INPUT_FILE = BASE_DIR / "_knowledge_base.json"

SAMPLE_COUNT = 10


def print_line(char="=", width=90):
    print(char * width)


def safe_preview(value, max_len=500):
    if value is None:
        return None

    if isinstance(value, str):
        value = value.replace("\n", "\\n")
        if len(value) > max_len:
            return value[:max_len] + "..."
        return value

    return value


def main():

    print_line()
    print("KNOWLEDGE BASE STRUCTURE / METADATA INSPECTION")
    print_line()

    print()
    print("Input:")
    print(INPUT_FILE)

    print()
    print("IMPORTANT:")
    print("READ ONLY")
    print("No JSON file will be modified.")

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Knowledge base not found:\n{INPUT_FILE}"
        )

    print()
    print_line()
    print("1. FILE INFORMATION")
    print_line()

    print(f"File size: {INPUT_FILE.stat().st_size:,} bytes")

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    print()
    print_line()
    print("2. ROOT STRUCTURE")
    print_line()

    print("Root type:", type(data).__name__)

    if isinstance(data, list):
        records = data

    elif isinstance(data, dict):
        print()
        print("Root dictionary keys:")

        for key in data.keys():
            print(f"  - {key}")

        # Try common container keys
        possible_keys = [
            "chunks",
            "records",
            "documents",
            "knowledge",
            "items",
            "data",
        ]

        records = None

        for key in possible_keys:
            if isinstance(data.get(key), list):
                records = data[key]
                print()
                print(f"Using records from root key: {key}")
                break

        if records is None:
            raise ValueError(
                "Could not find a list of knowledge records "
                "inside the root dictionary."
            )

    else:
        raise ValueError(
            f"Unsupported root type: {type(data).__name__}"
        )

    print()
    print("Total knowledge records:", len(records))

    if not records:
        print("[FAIL] Knowledge base contains zero records.")
        return

    print()
    print_line()
    print("3. RECORD TYPE CHECK")
    print_line()

    record_types = Counter(type(x).__name__ for x in records)

    for record_type, count in record_types.items():
        print(f"{record_type:20} : {count}")

    dict_records = [x for x in records if isinstance(x, dict)]

    if len(dict_records) != len(records):
        print()
        print(
            "[WARNING] Some records are not dictionaries."
        )

    if not dict_records:
        raise ValueError("No dictionary records found.")

    print()
    print_line()
    print("4. ALL FIELDS FOUND")
    print_line()

    field_counter = Counter()

    for record in dict_records:
        field_counter.update(record.keys())

    for field, count in field_counter.most_common():
        percentage = (count / len(dict_records)) * 100

        print(
            f"{field:35} : "
            f"{count:5} / {len(dict_records)} "
            f"({percentage:6.2f}%)"
        )

    print()
    print_line()
    print("5. FIELD VALUE TYPES")
    print_line()

    all_fields = sorted(field_counter.keys())

    for field in all_fields:

        types = Counter()

        for record in dict_records:
            if field in record:
                value = record[field]
                types[type(value).__name__] += 1

        type_text = ", ".join(
            f"{name}={count}"
            for name, count in types.items()
        )

        print(f"{field:35} : {type_text}")

    print()
    print_line()
    print("6. SOURCE TYPE DISTRIBUTION")
    print_line()

    source_fields = [
        "source_type",
        "source",
        "type",
        "kind",
    ]

    source_field_used = None

    for field in source_fields:
        if field in field_counter:
            source_field_used = field
            break

    if source_field_used:

        counter = Counter(
            str(record.get(source_field_used))
            for record in dict_records
        )

        print(f"Source field: {source_field_used}")
        print()

        for value, count in counter.most_common():
            print(f"{str(value):40} : {count}")

    else:
        print("No obvious source/type field found.")

    print()
    print_line()
    print("7. ID / STABLE ID AUDIT")
    print_line()

    id_fields = [
        "id",
        "chunk_id",
        "stable_id",
        "source_id",
        "document_id",
    ]

    for field in id_fields:

        if field not in field_counter:
            continue

        values = [
            record.get(field)
            for record in dict_records
            if record.get(field) is not None
        ]

        duplicates = len(values) - len(set(map(str, values)))

        print()
        print(f"Field: {field}")
        print(f"Present: {len(values)} / {len(dict_records)}")
        print(f"Duplicates: {duplicates}")

        if values:
            print("Samples:")

            for value in values[:5]:
                print(f"  {value}")

    print()
    print_line()
    print("8. SOURCE / PDF METADATA AUDIT")
    print_line()

    metadata_fields = [
        "pdf_file",
        "page",
        "canonical_url",
        "canonical_title",
        "all_urls",
        "sha256",
        "url",
        "title",
        "source",
    ]

    for field in metadata_fields:

        if field not in field_counter:
            print(f"{field:25} : NOT FOUND")
            continue

        present = 0
        empty = 0

        for record in dict_records:

            if field not in record:
                continue

            value = record.get(field)

            if value is None:
                empty += 1

            elif isinstance(value, str) and not value.strip():
                empty += 1

            elif isinstance(value, list) and not value:
                empty += 1

            else:
                present += 1

        print(
            f"{field:25} : "
            f"present={present}, "
            f"empty={empty}"
        )

    print()
    print_line()
    print("9. PAGE / PDF DISTRIBUTION")
    print_line()

    pdf_counter = Counter()
    page_counter = Counter()

    for record in dict_records:

        pdf_file = record.get("pdf_file")

        if pdf_file:
            pdf_counter[str(pdf_file)] += 1

        page = record.get("page")

        if page is not None:
            page_counter[str(page)] += 1

    print()
    print("Unique PDF files:", len(pdf_counter))

    if pdf_counter:
        print()
        print("Top PDF files by chunk count:")

        for pdf_file, count in pdf_counter.most_common(15):
            print(f"  {count:5} : {pdf_file}")

    print()
    print("Unique page values:", len(page_counter))

    print()
    print_line()
    print("10. TEXT FIELD AUDIT")
    print_line()

    text_fields = [
        "text",
        "content",
        "page_text",
        "chunk_text",
        "document",
    ]

    for field in text_fields:

        if field not in field_counter:
            continue

        non_empty = 0
        empty = 0
        total_chars = 0

        for record in dict_records:

            value = record.get(field)

            if isinstance(value, str) and value.strip():

                non_empty += 1
                total_chars += len(value)

            else:
                empty += 1

        avg_chars = (
            total_chars / non_empty
            if non_empty
            else 0
        )

        print()
        print(f"Text field: {field}")
        print(f"Non-empty: {non_empty}")
        print(f"Empty: {empty}")
        print(f"Average characters: {avg_chars:,.1f}")
        print(f"Total characters: {total_chars:,}")

    print()
    print_line()
    print("11. URL AUDIT")
    print_line()

    url_fields = [
        "canonical_url",
        "all_urls",
        "url",
        "source_url",
    ]

    for field in url_fields:

        if field not in field_counter:
            continue

        valid = 0
        empty = 0

        for record in dict_records:

            value = record.get(field)

            if isinstance(value, str):

                if value.strip():
                    valid += 1
                else:
                    empty += 1

            elif isinstance(value, list):

                if value:
                    valid += 1
                else:
                    empty += 1

            elif value is None:

                empty += 1

            else:

                valid += 1

        print(
            f"{field:25} : "
            f"non-empty={valid}, "
            f"empty={empty}"
        )

    print()
    print_line()
    print("12. SAMPLE RECORDS")
    print_line()

    for i, record in enumerate(dict_records[:SAMPLE_COUNT], start=1):

        print()
        print(f"---------------- SAMPLE {i} ----------------")

        for key, value in record.items():

            print(
                f"{key}: "
                f"{safe_preview(value)}"
            )

    print()
    print_line()
    print("13. SAMPLE SOURCE LINKS")
    print_line()

    shown = 0

    for record in dict_records:

        url = record.get("canonical_url")

        if not url:
            continue

        print()
        print(f"Record index : {records.index(record)}")
        print(f"Title        : {record.get('canonical_title')}")
        print(f"PDF          : {record.get('pdf_file')}")
        print(f"Page         : {record.get('page')}")
        print(f"URL          : {url}")

        all_urls = record.get("all_urls")

        if all_urls:
            print(f"All URLs     : {safe_preview(all_urls)}")

        shown += 1

        if shown >= 10:
            break

    if shown == 0:
        print("[WARNING] No canonical URLs found in samples.")

    print()
    print_line()
    print("INSPECTION COMPLETE")
    print_line()

    print()
    print("No JSON file was modified.")


if __name__ == "__main__":
    main()