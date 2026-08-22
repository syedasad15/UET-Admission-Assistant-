import json
from pathlib import Path


PROJECT_ROOT = Path(r"D:\UET Chatbot")

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "inventory"
    / "admission"
    / "_knowledge_base.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "inventory"
    / "admission"
    / "program_list_only.txt"
)


def main():

    with INPUT_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    chunks = data.get("chunks", [])

    matches = []

    for chunk in chunks:

        title = str(
            chunk.get("title", "")
        ).lower()

        text = str(
            chunk.get("text", "")
        )

        text_lower = text.lower()

        # Strong indicators of an actual program-list section.
        strong_title = any(
            x in title
            for x in [
                "programs",
                "degree programs",
                "bachelor of science",
                "bachelor of sciences",
                "undergraduate programs",
                "disciplines",
            ]
        )

        strong_text = any(
            x in text_lower
            for x in [
                "following programs",
                "programs offered",
                "programmes offered",
                "degree programs offered",
                "bachelor of science programs",
                "bachelor of sciences programs",
                "list of programs",
                "disciplines offered",
            ]
        )

        # Need either strong title OR strong list wording.
        if strong_title or strong_text:

            origin = (
                chunk.get("origin", {})
                or {}
            )

            matches.append({
                "id": chunk.get("id", ""),
                "title": chunk.get("title", ""),
                "book": chunk.get("book", ""),
                "page": origin.get("page", ""),
                "text": text,
            })


    # Remove duplicates based on exact text.
    unique = []

    seen = set()

    for item in matches:

        key = item["text"].strip()

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)


    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as out:

        out.write(
            "UET PROGRAM LIST — TARGETED INSPECTION\n"
        )

        out.write(
            "=" * 80 + "\n"
        )

        out.write(
            f"Total KB chunks: {len(chunks)}\n"
        )

        out.write(
            f"Matched chunks: {len(unique)}\n"
        )

        for number, item in enumerate(
            unique,
            start=1
        ):

            out.write(
                "\n"
                + "=" * 80
                + "\n"
            )

            out.write(
                f"MATCH #{number}\n"
            )

            out.write(
                f"ID: {item['id']}\n"
            )

            out.write(
                f"TITLE: {item['title']}\n"
            )

            out.write(
                f"BOOK: {item['book']}\n"
            )

            out.write(
                f"PAGE: {item['page']}\n"
            )

            out.write(
                "\nTEXT:\n"
            )

            # Limit each chunk so the inspection file stays small.
            text = item["text"]

            if len(text) > 4000:
                text = text[:4000] + "\n...[TRUNCATED]..."

            out.write(text)
            out.write("\n")


    print(
        f"Total KB chunks: {len(chunks)}"
    )

    print(
        f"Matched unique chunks: {len(unique)}"
    )

    print()
    print(
        "Created:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()