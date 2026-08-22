from pathlib import Path
import json

INPUT_FILE = Path(
    r"D:\UET Chatbot\data\inventory\admission\_content_targets.json"
)

print("=" * 70)
print("UET ADMISSION — CONTENT TARGET STRUCTURE INSPECTOR")
print("=" * 70)
print()

print("Reading:")
print(INPUT_FILE)
print()

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"File not found:\n{INPUT_FILE}"
    )

with INPUT_FILE.open("r", encoding="utf-8") as f:
    data = json.load(f)

print("TOP-LEVEL TYPE:")
print(type(data).__name__)
print()

if isinstance(data, dict):

    print("TOP-LEVEL KEYS:")
    for key in data.keys():
        value = data[key]

        if isinstance(value, list):
            print(
                f"  {key!r} -> list "
                f"({len(value)} items)"
            )

        elif isinstance(value, dict):
            print(
                f"  {key!r} -> dict "
                f"({len(value)} keys)"
            )

        else:
            print(
                f"  {key!r} -> "
                f"{type(value).__name__}"
            )

    print()
    print("=" * 70)
    print("SAMPLE CONTENT")
    print("=" * 70)

    for key, value in data.items():

        print()
        print(f"[KEY] {key}")

        if isinstance(value, list):

            print(f"Number of items: {len(value)}")

            for i, item in enumerate(value[:3], start=1):

                print()
                print(f"  ITEM {i} TYPE: {type(item).__name__}")

                if isinstance(item, dict):

                    print("  ITEM KEYS:")

                    for item_key in item.keys():
                        print(f"    - {item_key}")

                    print("  ITEM SAMPLE:")

                    for item_key, item_value in item.items():
                        print(
                            f"    {item_key}: "
                            f"{repr(item_value)[:300]}"
                        )

                else:
                    print(
                        "  VALUE:",
                        repr(item)[:500]
                    )

        elif isinstance(value, dict):

            print("Dictionary sample:")

            for i, (subkey, subvalue) in enumerate(
                value.items()
            ):

                if i >= 3:
                    break

                print(
                    f"  {subkey}: "
                    f"{repr(subvalue)[:500]}"
                )

        else:

            print(
                "VALUE:",
                repr(value)[:500]
            )

else:

    print("The JSON root is not a dictionary.")
    print()
    print("ROOT SAMPLE:")
    print(repr(data)[:2000])

print()
print("=" * 70)
print("DONE")
print("=" * 70)