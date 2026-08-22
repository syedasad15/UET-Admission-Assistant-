# import os
# from pathlib import Path
# from collections import Counter

# PROJECT_PATH = Path(r"D:\UET Chatbot")
# OUTPUT_FILE = PROJECT_PATH / "PROJECT_STRUCTURE.txt"

# if not PROJECT_PATH.exists():
#     print(f"❌ Project folder not found: {PROJECT_PATH}")
#     exit()

# files = []
# folders = []

# # Scan project
# for root, dirs, filenames in os.walk(PROJECT_PATH):
#     root_path = Path(root)

#     for directory in dirs:
#         folders.append(root_path / directory)

#     for filename in filenames:
#         file_path = root_path / filename

#         # Don't include our generated report itself
#         if file_path != OUTPUT_FILE:
#             files.append(file_path)

# # File extensions
# extensions = Counter()

# for file in files:
#     ext = file.suffix.lower()
#     extensions[ext if ext else "[no extension]"] += 1

# # Total size
# total_size = sum(file.stat().st_size for file in files)
# total_size_mb = total_size / (1024 * 1024)

# with open(OUTPUT_FILE, "w", encoding="utf-8") as report:

#     report.write("=" * 70 + "\n")
#     report.write("UET CHATBOT PROJECT STRUCTURE\n")
#     report.write("=" * 70 + "\n\n")

#     report.write(f"Project path: {PROJECT_PATH}\n")
#     report.write(f"Total files: {len(files)}\n")
#     report.write(f"Total folders: {len(folders)}\n")
#     report.write(f"Total size: {total_size_mb:.2f} MB\n\n")

#     # --------------------------------------------------
#     # Folder and file tree
#     # --------------------------------------------------

#     report.write("=" * 70 + "\n")
#     report.write("FOLDER / FILE TREE\n")
#     report.write("=" * 70 + "\n\n")

#     all_items = sorted(
#         folders + files,
#         key=lambda x: (len(x.parts), str(x).lower())
#     )

#     for item in all_items:
#         relative = item.relative_to(PROJECT_PATH)

#         depth = len(relative.parts) - 1
#         indent = "    " * depth

#         if item.is_dir():
#             report.write(f"{indent}📁 {item.name}/\n")
#         else:
#             size_kb = item.stat().st_size / 1024
#             report.write(
#                 f"{indent}📄 {item.name} ({size_kb:.2f} KB)\n"
#             )

#     # --------------------------------------------------
#     # File types
#     # --------------------------------------------------

#     report.write("\n")
#     report.write("=" * 70 + "\n")
#     report.write("FILE TYPES\n")
#     report.write("=" * 70 + "\n\n")

#     for extension, count in extensions.most_common():
#         report.write(f"{extension}: {count} files\n")

#     # --------------------------------------------------
#     # Detailed file list
#     # --------------------------------------------------

#     report.write("\n")
#     report.write("=" * 70 + "\n")
#     report.write("DETAILED FILE LIST\n")
#     report.write("=" * 70 + "\n\n")

#     for file in sorted(files):
#         relative = file.relative_to(PROJECT_PATH)
#         size_kb = file.stat().st_size / 1024

#         report.write(
#             f"{relative}\n"
#             f"    Size: {size_kb:.2f} KB\n"
#             f"    Extension: {file.suffix or '[none]'}\n\n"
#         )

# print("✅ Project scan completed!")
# print()
# print(f"📁 Project: {PROJECT_PATH}")
# print(f"📄 Files: {len(files)}")
# print(f"📁 Folders: {len(folders)}")
# print(f"💾 Size: {total_size_mb:.2f} MB")
# print()
# print(f"📋 Report created at:")
# print(OUTPUT_FILE)
from pathlib import Path
import ast
from collections import Counter

PROJECT = Path(r"D:\UET Chatbot")

python_files = list(PROJECT.rglob("*.py"))

imports = Counter()

for file in python_files:
    # Skip virtual environments and cache
    if "__pycache__" in file.parts:
        continue

    try:
        source = file.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for node in ast.walk(tree):

            if isinstance(node, ast.Import):
                for name in node.names:
                    imports[name.name.split(".")[0]] += 1

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports[node.module.split(".")[0]] += 1

    except Exception as e:
        print(f"Could not read: {file}")
        print(f"Reason: {e}")

print("=" * 70)
print("UET CHATBOT - PYTHON PROJECT ANALYSIS")
print("=" * 70)

print(f"\nPython files found: {len(python_files)}")

print("\n" + "=" * 70)
print("IMPORTED MODULES")
print("=" * 70)

for module, count in imports.most_common():
    print(f"{module:<30} {count}")

print("\n" + "=" * 70)
print("PYTHON FILES")
print("=" * 70)

for file in sorted(python_files):
    relative = file.relative_to(PROJECT)
    print(relative)

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)