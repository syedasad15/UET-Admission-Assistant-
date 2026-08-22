from pathlib import Path

ROOT = Path(r"D:\UET Chatbot")


def print_tree(path, prefix=""):
    items = sorted(
        path.iterdir(),
        key=lambda p: (p.is_file(), p.name.lower())
    )

    for index, item in enumerate(items):
        is_last = index == len(items) - 1

        branch = "└── " if is_last else "├── "
        print(prefix + branch + item.name)

        if item.is_dir():
            extension = "    " if is_last else "│   "
            print_tree(item, prefix + extension)


def main():
    if not ROOT.exists():
        print(f"Directory not found: {ROOT}")
        return

    if not ROOT.is_dir():
        print(f"Not a directory: {ROOT}")
        return

    print(ROOT)
    print_tree(ROOT)


if __name__ == "__main__":
    main()