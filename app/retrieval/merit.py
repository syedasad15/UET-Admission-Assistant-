
# import re
# import requests
# import fitz

# from pathlib import Path
# from datetime import datetime
# from urllib.parse import urljoin
# from html.parser import HTMLParser


# # ============================================================
# # UET CHATBOT
# # DYNAMIC MINIMUM MERIT RETRIEVER
# # ============================================================
# #
# # IMPORTANT
# # ----------
# # The UET Downloads page is structured as document sections.
# #
# # Example:
# #
# #   <h4>Minimum Merit – 3rd Merit List (Undergraduate Fall 2026)</h4>
# #   ...
# #   <a ...>Download</a>
# #
# #   <h4>Minimum Merit – 4th Merit List (Undergraduate Fall 2026)</h4>
# #   ...
# #   <a ...>Download</a>
# #
# # We DO NOT scan every PDF on the website.
# #
# # We:
# #
# #   1. Find "Minimum Merit" sections.
# #   2. Extract the merit-list number from each title.
# #   3. Select the HIGHEST number.
# #   4. Download ONLY that section's PDF.
# #
# # ============================================================


# # ============================================================
# # PROJECT PATHS
# # ============================================================

# PROJECT_ROOT = Path(r"D:\UET Chatbot")

# MERIT_DATA_DIR = (
#     PROJECT_ROOT
#     / "data"
#     / "merit"
# )

# LATEST_PDF = (
#     MERIT_DATA_DIR
#     / "latest_merit_list.pdf"
# )


# # ============================================================
# # UET CONFIGURATION
# # ============================================================

# UET_BASE_URL = "https://admission.uet.edu.pk"

# UET_DOWNLOADS_URL = (
#     "https://admission.uet.edu.pk/downloads"
# )

# REQUEST_TIMEOUT = 30


# # ============================================================
# # HTTP
# # ============================================================

# def create_session():

#     session = requests.Session()

#     session.headers.update({

#         "User-Agent":
#             (
#                 "Mozilla/5.0 "
#                 "(Windows NT 10.0; Win64; x64) "
#                 "AppleWebKit/537.36 "
#                 "(KHTML, like Gecko) "
#                 "Chrome/131.0 Safari/537.36"
#             ),

#         "Accept":
#             (
#                 "text/html,application/xhtml+xml,"
#                 "application/xml;q=0.9,"
#                 "image/avif,image/webp,"
#                 "image/apng,*/*;q=0.8"
#             ),

#         "Accept-Language":
#             "en-US,en;q=0.9",

#         "Referer":
#             UET_BASE_URL + "/",
#     })

#     return session


# # ============================================================
# # GENERAL HELPERS
# # ============================================================

# def normalize(value):

#     if value is None:
#         return ""

#     value = str(value)

#     value = value.replace(
#         "\xa0",
#         " ",
#     )

#     return re.sub(
#         r"\s+",
#         " ",
#         value,
#     ).strip()


# def normalize_url(
#     base_url,
#     url,
# ):

#     url = normalize(url)

#     if not url:
#         return ""

#     url = (
#         url
#         .replace("&amp;", "&")
#         .replace("&#x26;", "&")
#     )

#     if url.startswith("//"):
#         return "https:" + url

#     return urljoin(
#         base_url,
#         url,
#     )


# # ============================================================
# # HTML SECTION PARSER
# # ============================================================
# #
# # This parser follows the ACTUAL structure of the UET
# # Downloads page instead of trying to infer a title from
# # arbitrary surrounding HTML.
# #
# # Every <h4> starts a new download section.
# #
# # We collect:
# #
# #     h4 title
# #     text inside the section
# #     href of Download anchor
# #
# # until the next <h4>.
# #
# # ============================================================

# class UETDownloadsParser(HTMLParser):

#     def __init__(self):

#         super().__init__(
#             convert_charrefs=True
#         )

#         self.sections = []

#         self.current = None

#         self.current_tag = None

#         self.capture_heading = False

#         self.capture_anchor = False

#         self.anchor_href = ""

#     def handle_starttag(
#         self,
#         tag,
#         attrs,
#     ):

#         tag = tag.lower()

#         attrs_dict = dict(
#             attrs
#         )

#         # ----------------------------------------------------
#         # Every h4 represents a new download-card/section.
#         # ----------------------------------------------------

#         if tag == "h4":

#             self._finish_section()

#             self.current = {

#                 "title":
#                     "",

#                 "text":
#                     "",

#                 "url":
#                     "",
#             }

#             self.capture_heading = True

#             return

#         # ----------------------------------------------------
#         # If we are inside a section, capture anchor links.
#         # ----------------------------------------------------

#         if self.current is not None:

#             if tag == "a":

#                 href = attrs_dict.get(
#                     "href",
#                     "",
#                 )

#                 if href:

#                     href = normalize_url(
#                         UET_DOWNLOADS_URL,
#                         href,
#                     )

#                     # The UET page uses a Download anchor
#                     # inside each section.
#                     #
#                     # Keep the first useful link.
#                     if not self.current["url"]:

#                         self.current[
#                             "url"
#                         ] = href

#                     self.capture_anchor = True

#                     self.anchor_href = href

#             self.current_tag = tag

#     def handle_endtag(
#         self,
#         tag,
#     ):

#         tag = tag.lower()

#         if tag == "h4":

#             self.capture_heading = False

#         if tag == "a":

#             self.capture_anchor = False

#             self.anchor_href = ""

#         self.current_tag = None

#     def handle_data(
#         self,
#         data,
#     ):

#         data = normalize(
#             data
#         )

#         if not data:
#             return

#         if self.current is None:
#             return

#         # ----------------------------------------------------
#         # Heading.
#         # ----------------------------------------------------

#         if self.capture_heading:

#             self.current[
#                 "title"
#             ] += " " + data

#         # ----------------------------------------------------
#         # All section text.
#         # ----------------------------------------------------

#         self.current[
#             "text"
#         ] += " " + data

#     def _finish_section(self):

#         if self.current is None:
#             return

#         self.current["title"] = normalize(
#             self.current["title"]
#         )

#         self.current["text"] = normalize(
#             self.current["text"]
#         )

#         self.sections.append(
#             self.current
#         )

#         self.current = None

#         self.capture_heading = False

#         self.capture_anchor = False

#         self.anchor_href = ""

#     def close(self):

#         super().close()

#         self._finish_section()


# # ============================================================
# # MERIT LIST NUMBER
# # ============================================================

# def extract_merit_list_number(
#     text
# ):

#     text = normalize(
#         text
#     ).lower()

#     if not text:
#         return 0

#     patterns = [

#         # ----------------------------------------------------
#         # Exact UET structure:
#         #
#         # Minimum Merit – 4th Merit List
#         # Minimum Merit - 4th Merit List
#         # ----------------------------------------------------

#         r"""
#         \b
#         minimum\s+merit
#         \s*[-–—:]\s*
#         (\d+)
#         (?:st|nd|rd|th)?
#         \s+
#         merit\s+list
#         \b
#         """,

#         # ----------------------------------------------------
#         # 4th Merit List
#         # ----------------------------------------------------

#         r"""
#         \b
#         (\d+)
#         (?:st|nd|rd|th)
#         \s+
#         merit\s+list
#         \b
#         """,

#         # ----------------------------------------------------
#         # Merit List 4
#         # ----------------------------------------------------

#         r"""
#         \b
#         merit\s+list
#         \s*
#         (?:no\.?|number)?
#         \s*
#         [-:#]?
#         \s*
#         (\d+)
#         \b
#         """,

#         # ----------------------------------------------------
#         # Merit List No. 4
#         # ----------------------------------------------------

#         r"""
#         \b
#         merit\s+list
#         \s*
#         no\.?
#         \s*
#         (\d+)
#         \b
#         """,

#         # ----------------------------------------------------
#         # Merit-4
#         # ----------------------------------------------------

#         r"""
#         \b
#         merit
#         \s*[-_]
#         \s*
#         (\d+)
#         \b
#         """,
#     ]

#     for pattern in patterns:

#         match = re.search(
#             pattern,
#             text,
#             re.IGNORECASE |
#             re.VERBOSE,
#         )

#         if match:

#             try:

#                 return int(
#                     match.group(1)
#                 )

#             except (
#                 TypeError,
#                 ValueError,
#             ):

#                 pass

#     return 0


# # ============================================================
# # IS EXACT MINIMUM MERIT SECTION?
# # ============================================================

# def is_minimum_merit_section(
#     title
# ):

#     title = normalize(
#         title
#     ).lower()

#     if not title:
#         return False

#     # The current UET page uses:
#     #
#     # Minimum Merit – 4th Merit List
#     #
#     # We deliberately require "minimum merit".
#     # This prevents unrelated admission documents from
#     # being selected.
#     #

#     return (
#         "minimum merit" in title
#         and
#         "merit list" in title
#     )


# # ============================================================
# # DISCOVER MINIMUM MERIT SECTIONS
# # ============================================================

# def discover_minimum_merit_documents(
#     session
# ):

#     print()
#     print("=" * 80)
#     print("CHECKING UET DOWNLOADS PAGE")
#     print("=" * 80)

#     print()
#     print(
#         f"URL: {UET_DOWNLOADS_URL}"
#     )

#     response = session.get(
#         UET_DOWNLOADS_URL,
#         timeout=REQUEST_TIMEOUT,
#     )

#     response.raise_for_status()

#     html = response.text

#     print()
#     print(
#         f"Downloaded HTML: "
#         f"{len(html):,} characters"
#     )

#     # --------------------------------------------------------
#     # Parse actual h4-based sections.
#     # --------------------------------------------------------

#     parser = UETDownloadsParser()

#     parser.feed(
#         html
#     )

#     parser.close()

#     sections = parser.sections

#     print()
#     print(
#         f"Download sections discovered: "
#         f"{len(sections)}"
#     )

#     documents = []

#     for section in sections:

#         title = normalize(
#             section.get(
#                 "title",
#                 "",
#             )
#         )

#         if not is_minimum_merit_section(
#             title
#         ):

#             continue

#         merit_number = (
#             extract_merit_list_number(
#                 title
#             )
#         )

#         if merit_number <= 0:

#             print()
#             print(
#                 "WARNING: Minimum Merit "
#                 "section found but its number "
#                 "could not be detected:"
#             )

#             print(
#                 title
#             )

#             continue

#         url = normalize_url(
#             UET_DOWNLOADS_URL,
#             section.get(
#                 "url",
#                 "",
#             ),
#         )

#         if not url:

#             print()
#             print(
#                 "WARNING: No download link "
#                 "found for:"
#             )

#             print(
#                 title
#             )

#             continue

#         documents.append({

#             "title":
#                 title,

#             "url":
#                 url,

#             "text":
#                 normalize(
#                     section.get(
#                         "text",
#                         "",
#                     )
#                 ),

#             "merit_number":
#                 merit_number,
#         })

#     # --------------------------------------------------------
#     # Remove duplicate URLs.
#     # --------------------------------------------------------

#     unique = {}

#     for document in documents:

#         url = document[
#             "url"
#         ]

#         if url not in unique:

#             unique[url] = document

#     documents = list(
#         unique.values()
#     )

#     # --------------------------------------------------------
#     # Sort by merit number.
#     # --------------------------------------------------------

#     documents.sort(
#         key=lambda item: (
#             item["merit_number"],
#             item["title"],
#         )
#     )

#     print()
#     print(
#         f"Minimum Merit documents found: "
#         f"{len(documents)}"
#     )

#     for document in documents:

#         print()
#         print(
#             f"Merit List Number: "
#             f"{document['merit_number']}"
#         )

#         print(
#             f"Title: "
#             f"{document['title']}"
#         )

#         print(
#             f"Download URL: "
#             f"{document['url']}"
#         )

#     return documents


# # ============================================================
# # GET HIGHEST MINIMUM MERIT DOCUMENT
# # ============================================================

# def get_latest_merit_document(
#     documents
# ):

#     if not documents:

#         raise RuntimeError(
#             "UET website did not expose any "
#             "recognizable Minimum Merit documents "
#             "on the Downloads page."
#         )

#     highest_number = max(
#         document["merit_number"]
#         for document in documents
#     )

#     latest = [

#         document

#         for document in documents

#         if (
#             document["merit_number"]
#             == highest_number
#         )
#     ]

#     if not latest:

#         raise RuntimeError(
#             "Could not select the highest "
#             "Minimum Merit document."
#         )

#     # --------------------------------------------------------
#     # There should normally be exactly one.
#     #
#     # We use the first section with the highest number.
#     #
#     # --------------------------------------------------------

#     selected = latest[0]

#     print()
#     print("=" * 80)
#     print(
#         "SELECTED LATEST MINIMUM MERIT"
#     )
#     print("=" * 80)

#     print()
#     print(
#         f"Merit List Number: "
#         f"{selected['merit_number']}"
#     )

#     print(
#         f"Title: "
#         f"{selected['title']}"
#     )

#     print(
#         f"URL: "
#         f"{selected['url']}"
#     )

#     return selected


# # ============================================================
# # DOWNLOAD PDF
# # ============================================================

# def download_pdf(
#     session,
#     url,
# ):

#     MERIT_DATA_DIR.mkdir(
#         parents=True,
#         exist_ok=True,
#     )

#     print()
#     print("=" * 80)
#     print(
#         "DOWNLOADING SELECTED MERIT PDF"
#     )
#     print("=" * 80)

#     print()
#     print(
#         url
#     )

#     response = session.get(
#         url,
#         timeout=REQUEST_TIMEOUT,
#     )

#     response.raise_for_status()

#     content = response.content

#     content_type = (
#         response.headers.get(
#             "Content-Type",
#             "",
#         )
#     )

#     print()
#     print(
#         f"Content-Type: "
#         f"{content_type}"
#     )

#     print(
#         f"Downloaded bytes: "
#         f"{len(content):,}"
#     )

#     # --------------------------------------------------------
#     # Validate PDF.
#     # --------------------------------------------------------

#     if not content.startswith(
#         b"%PDF"
#     ):

#         raise ValueError(
#             "The selected UET download link "
#             "did not return a valid PDF. "
#             f"Content-Type: {content_type}"
#         )

#     with open(
#         LATEST_PDF,
#         "wb",
#     ) as file:

#         file.write(
#             content
#         )

#     print()
#     print(
#         "PDF downloaded successfully."
#     )

#     print(
#         f"Saved to: "
#         f"{LATEST_PDF}"
#     )

#     return LATEST_PDF


# # ============================================================
# # EXTRACT ALL PDF TEXT
# # ============================================================

# def extract_all_pdf_text(
#     pdf_file
# ):

#     doc = fitz.open(
#         str(pdf_file)
#     )

#     pages = []

#     for page_number, page in enumerate(
#         doc,
#         start=1,
#     ):

#         text = page.get_text(
#             "text"
#         )

#         pages.append({

#             "page":
#                 page_number,

#             "text":
#                 text,
#         })

#     doc.close()

#     return pages


# # ============================================================
# # PDF TEXT DEBUGGER
# # ============================================================

# def print_pdf_sample(
#     pdf_file,
#     max_pages=3,
# ):

#     print()
#     print("=" * 80)
#     print(
#         "PDF TEXT SAMPLE"
#     )
#     print("=" * 80)

#     try:

#         doc = fitz.open(
#             str(pdf_file)
#         )

#         total = len(doc)

#         print()
#         print(
#             f"PDF pages: {total}"
#         )

#         for index, page in enumerate(
#             doc
#         ):

#             if index >= max_pages:
#                 break

#             text = page.get_text(
#                 "text"
#             )

#             print()
#             print(
#                 f"--- PAGE {index + 1} ---"
#             )

#             print(
#                 text[:5000]
#             )

#         doc.close()

#     except Exception as exc:

#         print(
#             f"Could not print PDF sample: "
#             f"{exc}"
#         )


# # ============================================================
# # CAMPUS ALIASES
# # ============================================================

# CAMPUS_ALIASES = {

#     "lahore":
#         "Main Campus (LHR)",

#     "lhr":
#         "Main Campus (LHR)",

#     "lahore campus":
#         "Main Campus (LHR)",

#     "main campus":
#         "Main Campus (LHR)",

#     "main campus lahore":
#         "Main Campus (LHR)",

#     "main campus lhr":
#         "Main Campus (LHR)",

#     "ksk":
#         "New Campus (KSK)",

#     "kala shah kaku":
#         "New Campus (KSK)",

#     "kala shah kaku campus":
#         "New Campus (KSK)",

#     "new campus":
#         "New Campus (KSK)",

#     "new campus ksk":
#         "New Campus (KSK)",

#     "faisalabad":
#         "Faislabad Campus",

#     "faislabad":
#         "Faislabad Campus",

#     "faisalabad campus":
#         "Faislabad Campus",

#     "faislabad campus":
#         "Faislabad Campus",

#     "gujranwala":
#         "Gujar anwala",

#     "gujaranwala":
#         "Gujar anwala",

#     "gujranwala campus":
#         "Gujar anwala",

#     "narowal":
#         "Narowal Campus (NWL)",

#     "nwl":
#         "Narowal Campus (NWL)",

#     "narowal campus":
#         "Narowal Campus (NWL)",
# }


# def normalize_campus_name(
#     campus
# ):

#     value = normalize(
#         campus
#     ).lower()

#     if value in CAMPUS_ALIASES:

#         return CAMPUS_ALIASES[
#             value
#         ]

#     return normalize(
#         campus
#     )


# # ============================================================
# # PROGRAM / DEPARTMENT NORMALIZATION
# # ============================================================

# PROGRAM_ALIASES = {

#     "cs":
#         "Computer Science",

#     "computer science":
#         "Computer Science",

#     "computer sciences":
#         "Computer Science",

#     "computing":
#         "Computer Science",
# }


# def normalize_program_name(
#     program
# ):

#     value = normalize(
#         program
#     ).lower()

#     if value in PROGRAM_ALIASES:

#         return PROGRAM_ALIASES[
#             value
#         ]

#     return normalize(
#         program
#     )


# def is_computer_science(
#     text
# ):

#     text = normalize(
#         text
#     ).lower()

#     text = re.sub(
#         r"[-_/]+",
#         " ",
#         text,
#     )

#     text = re.sub(
#         r"\s+",
#         " ",
#         text,
#     )

#     return bool(
#         re.search(
#             r"\bcomputer\s+science\b",
#             text,
#             re.IGNORECASE,
#         )
#     )


# # ============================================================
# # CATEGORY / SESSION / TYPE
# # ============================================================

# CATEGORY_PATTERN = (
#     r"A1-M|A2-M|A1|A2|NM"
# )

# SESSION_PATTERN = (
#     r"Morning|Evening"
# )

# TYPE_PATTERN = (
#     r"ECAT|Non-ECAT|Non ECAT"
# )


# # ============================================================
# # CLEAN NUMERIC VALUE
# # ============================================================

# def clean_number(
#     value
# ):

#     value = normalize(
#         value
#     )

#     value = value.replace(
#         "%",
#         "",
#     )

#     try:

#         return float(
#             value
#         )

#     except (
#         TypeError,
#         ValueError,
#     ):

#         return None


# # ============================================================
# # EXTRACT AGGREGATES FROM TEXT
# # ============================================================

# def extract_aggregate_candidates(
#     text
# ):

#     text = normalize(
#         text
#     )

#     candidates = []

#     # --------------------------------------------------------
#     # Typical closing merit:
#     #
#     # 89.1234
#     # 89.12345%
#     #
#     # --------------------------------------------------------

#     matches = re.findall(
#         r"\b(?:100|[0-9]{1,2})\.\d{1,6}\s*%?",
#         text,
#         re.IGNORECASE,
#     )

#     for match in matches:

#         value = clean_number(
#             match
#         )

#         if value is None:
#             continue

#         if (
#             0 <= value <= 100
#         ):

#             candidates.append(
#                 value
#             )

#     return candidates


# # ============================================================
# # GENERIC CS ROW PARSER
# # ============================================================

# def parse_cs_row(
#     row,
#     page_number,
# ):

#     row = normalize(
#         row
#     )

#     if not row:
#         return None

#     if not is_computer_science(
#         row
#     ):
#         return None

#     normalized_row = re.sub(
#         r"\s+",
#         " ",
#         row,
#     ).strip()

#     # --------------------------------------------------------
#     # Aggregate is normally the final numeric value.
#     # --------------------------------------------------------

#     aggregate_match = re.search(
#         r"(\d{1,3}(?:\.\d+)?)\s*%?\s*$",
#         normalized_row,
#         re.IGNORECASE,
#     )

#     if not aggregate_match:

#         # Try a less strict approach.
#         values = extract_aggregate_candidates(
#             normalized_row
#         )

#         if not values:
#             return None

#         aggregate = values[-1]

#         aggregate_start = (
#             normalized_row.rfind(
#                 str(
#                     aggregate
#                 )
#             )
#         )

#         if aggregate_start < 0:
#             return None

#         before_aggregate = (
#             normalized_row[
#                 :aggregate_start
#             ].strip()
#         )

#     else:

#         aggregate = clean_number(
#             aggregate_match.group(1)
#         )

#         if aggregate is None:
#             return None

#         before_aggregate = (
#             normalized_row[
#                 :aggregate_match.start()
#             ].strip()
#         )

#     if not (
#         0 <= aggregate <= 100
#     ):
#         return None

#     # --------------------------------------------------------
#     # Category
#     # --------------------------------------------------------

#     category_match = re.search(
#         rf"\b({CATEGORY_PATTERN})\b",
#         before_aggregate,
#         re.IGNORECASE,
#     )

#     if category_match:

#         category = normalize(
#             category_match.group(1)
#         ).upper()

#         before_category = (
#             before_aggregate[
#                 :category_match.start()
#             ].strip()
#         )

#     else:

#         category = ""

#         before_category = (
#             before_aggregate
#         )

#     # --------------------------------------------------------
#     # Session
#     # --------------------------------------------------------

#     session_match = re.search(
#         rf"\b({SESSION_PATTERN})\b",
#         before_category,
#         re.IGNORECASE,
#     )

#     if session_match:

#         session = normalize(
#             session_match.group(1)
#         )

#         before_session = (
#             before_category[
#                 :session_match.start()
#             ].strip()
#         )

#     else:

#         session = ""

#         before_session = (
#             before_category
#         )

#     # --------------------------------------------------------
#     # Admission type
#     # --------------------------------------------------------

#     type_match = re.search(
#         rf"\b({TYPE_PATTERN})\b",
#         before_session,
#         re.IGNORECASE,
#     )

#     if type_match:

#         admission_type = normalize(
#             type_match.group(1)
#         )

#         before_type = (
#             before_session[
#                 :type_match.start()
#             ].strip()
#         )

#     else:

#         admission_type = ""

#         before_type = (
#             before_session
#         )

#     # --------------------------------------------------------
#     # Find Computer Science.
#     # --------------------------------------------------------

#     cs_match = re.search(
#         r"computer\s+science",
#         before_type,
#         re.IGNORECASE,
#     )

#     if not cs_match:
#         return None

#     campus = normalize(
#         before_type[
#             :cs_match.start()
#         ]
#     )

#     # --------------------------------------------------------
#     # Remove common table artifacts.
#     # --------------------------------------------------------

#     campus = re.sub(
#         r"[\|\t]+",
#         " ",
#         campus,
#     )

#     campus = re.sub(
#         r"^\d+\s+",
#         "",
#         campus,
#     )

#     campus = normalize(
#         campus
#     )

#     # --------------------------------------------------------
#     # If campus is empty, do not create a bogus record.
#     # --------------------------------------------------------

#     if not campus:
#         return None

#     if len(campus) > 100:
#         return None

#     return {

#         "page":
#             page_number,

#         "campus":
#             campus,

#         "program":
#             "Computer Science",

#         "category":
#             category,

#         "session":
#             session,

#         "type":
#             admission_type,

#         "minimum_aggregate":
#             aggregate,
#     }


# # ============================================================
# # EXTRACT CS DATA
# # ============================================================

# def extract_merit_data(
#     pdf_file
# ):

#     pages = extract_all_pdf_text(
#         pdf_file
#     )

#     results = []

#     print()
#     print(
#         f"Total PDF pages: "
#         f"{len(pages)}"
#     )

#     # ========================================================
#     # STRATEGY 1
#     # Individual lines
#     # ========================================================

#     for page_data in pages:

#         page_number = page_data[
#             "page"
#         ]

#         text = page_data[
#             "text"
#         ]

#         lines = text.splitlines()

#         for line in lines:

#             line = normalize(
#                 line
#             )

#             if not is_computer_science(
#                 line
#             ):
#                 continue

#             record = parse_cs_row(
#                 line,
#                 page_number,
#             )

#             if record:

#                 results.append(
#                     record
#                 )

#     # ========================================================
#     # STRATEGY 2
#     # Nearby-line windows
#     # ========================================================

#     for page_data in pages:

#         page_number = page_data[
#             "page"
#         ]

#         lines = [

#             normalize(line)

#             for line in
#             page_data["text"].splitlines()

#             if normalize(line)
#         ]

#         for index, line in enumerate(
#             lines
#         ):

#             if not is_computer_science(
#                 line
#             ):
#                 continue

#             for window_size in (
#                 2,
#                 3,
#                 4,
#                 5,
#                 6,
#                 7,
#             ):

#                 start = max(
#                     0,
#                     index - 3,
#                 )

#                 end = min(
#                     len(lines),
#                     index
#                     + window_size,
#                 )

#                 window = normalize(
#                     " ".join(
#                         lines[
#                             start:end
#                         ]
#                     )
#                 )

#                 record = parse_cs_row(
#                     window,
#                     page_number,
#                 )

#                 if record:

#                     results.append(
#                         record
#                     )

#     # ========================================================
#     # STRATEGY 3
#     # Computer Science followed by nearby numeric values.
#     #
#     # This helps when PDF text extraction destroys the table
#     # columns.
#     # ========================================================

#     for page_data in pages:

#         page_number = page_data[
#             "page"
#         ]

#         lines = [

#             normalize(line)

#             for line in
#             page_data["text"].splitlines()

#             if normalize(line)
#         ]

#         for index, line in enumerate(
#             lines
#         ):

#             if not is_computer_science(
#                 line
#             ):
#                 continue

#             start = max(
#                 0,
#                 index - 5,
#             )

#             end = min(
#                 len(lines),
#                 index + 8,
#             )

#             window_lines = lines[
#                 start:end
#             ]

#             window = normalize(
#                 " ".join(
#                     window_lines
#                 )
#             )

#             # ------------------------------------------------
#             # Only attempt this strategy if an aggregate
#             # appears nearby.
#             # ------------------------------------------------

#             values = extract_aggregate_candidates(
#                 window
#             )

#             if not values:
#                 continue

#             aggregate = values[-1]

#             cs_position = re.search(
#                 r"computer\s+science",
#                 window,
#                 re.IGNORECASE,
#             )

#             if not cs_position:
#                 continue

#             before_cs = normalize(
#                 window[
#                     :cs_position.start()
#                 ]
#             )

#             # ------------------------------------------------
#             # Try to identify the campus from the text before
#             # Computer Science.
#             # ------------------------------------------------

#             campus = before_cs

#             campus = re.sub(
#                 r"^\d+\s+",
#                 "",
#                 campus,
#             )

#             campus = normalize(
#                 campus
#             )

#             if not campus:
#                 continue

#             if len(campus) > 100:
#                 continue

#             category_match = re.search(
#                 rf"\b({CATEGORY_PATTERN})\b",
#                 window,
#                 re.IGNORECASE,
#             )

#             session_match = re.search(
#                 rf"\b({SESSION_PATTERN})\b",
#                 window,
#                 re.IGNORECASE,
#             )

#             type_match = re.search(
#                 rf"\b({TYPE_PATTERN})\b",
#                 window,
#                 re.IGNORECASE,
#             )

#             category = ""

#             if category_match:

#                 category = (
#                     category_match
#                     .group(1)
#                     .upper()
#                 )

#             session = ""

#             if session_match:

#                 session = normalize(
#                     session_match.group(1)
#                 )

#             admission_type = ""

#             if type_match:

#                 admission_type = normalize(
#                     type_match.group(1)
#                 )

#             results.append({

#                 "page":
#                     page_number,

#                 "campus":
#                     campus,

#                 "program":
#                     "Computer Science",

#                 "category":
#                     category,

#                 "session":
#                     session,

#                 "type":
#                     admission_type,

#                 "minimum_aggregate":
#                     aggregate,
#             })

#     # ========================================================
#     # REMOVE DUPLICATES
#     # ========================================================

#     unique = {}

#     for record in results:

#         key = (

#             normalize(
#                 record.get(
#                     "campus",
#                     "",
#                 )
#             ).lower(),

#             normalize(
#                 record.get(
#                     "program",
#                     "",
#                 )
#             ).lower(),

#             normalize(
#                 record.get(
#                     "category",
#                     "",
#                 )
#             ).lower(),

#             normalize(
#                 record.get(
#                     "session",
#                     "",
#                 )
#             ).lower(),

#             normalize(
#                 record.get(
#                     "type",
#                     "",
#                 )
#             ).lower(),

#             round(
#                 float(
#                     record[
#                         "minimum_aggregate"
#                     ]
#                 ),
#                 5,
#             ),
#         )

#         if key not in unique:

#             unique[key] = record

#     results = list(
#         unique.values()
#     )

#     # ========================================================
#     # SORT
#     # ========================================================

#     results.sort(
#         key=lambda record: (

#             normalize(
#                 record.get(
#                     "campus",
#                     "",
#                 )
#             ),

#             normalize(
#                 record.get(
#                     "category",
#                     "",
#                 )
#             ),

#             normalize(
#                 record.get(
#                     "session",
#                     "",
#                 )
#             ),

#             normalize(
#                 record.get(
#                     "type",
#                     "",
#                 )
#             ),

#         )
#     )

#     print()
#     print(
#         f"Computer Science records found: "
#         f"{len(results)}"
#     )

#     return results


# # ============================================================
# # GET CS DATA
# # ============================================================

# def get_cs_data(
#     data,
#     campus=None,
#     category=None,
# ):

#     results = []

#     normalized_campus = None

#     if campus:

#         normalized_campus = (
#             normalize_campus_name(
#                 campus
#             )
#         ).lower()

#     normalized_category = None

#     if category:

#         normalized_category = (
#             normalize(
#                 category
#             ).lower()
#         )

#     for item in data:

#         program = normalize_program_name(
#             item.get(
#                 "program",
#                 "",
#             )
#         )

#         if program.lower() != (
#             "computer science"
#         ):

#             continue

#         item_campus = normalize(
#             item.get(
#                 "campus",
#                 "",
#             )
#         ).lower()

#         if normalized_campus:

#             if (
#                 item_campus
#                 != normalized_campus
#             ):

#                 if (
#                     normalized_campus
#                     not in item_campus
#                     and
#                     item_campus
#                     not in normalized_campus
#                 ):

#                     continue

#         if normalized_category:

#             item_category = normalize(
#                 item.get(
#                     "category",
#                     "",
#                 )
#             ).lower()

#             if (
#                 item_category
#                 != normalized_category
#             ):

#                 continue

#         results.append(
#             item
#         )

#     return results


# # ============================================================
# # CHECK STUDENT
# # ============================================================

# def check_student(
#     data,
#     aggregate,
#     campus,
#     category=None,
# ):

#     records = get_cs_data(
#         data,
#         campus=campus,
#         category=category,
#     )

#     results = []

#     for record in records:

#         merit = float(
#             record[
#                 "minimum_aggregate"
#             ]
#         )

#         difference = (
#             float(aggregate)
#             - merit
#         )

#         results.append({

#             **record,

#             "student_aggregate":
#                 float(aggregate),

#             "selected":
#                 float(aggregate)
#                 >= merit,

#             "difference":
#                 round(
#                     difference,
#                     5,
#                 ),
#         })

#     return results


# # ============================================================
# # LOAD LATEST MERIT
# # ============================================================

# def load_latest_merit():

#     session = create_session()

#     # --------------------------------------------------------
#     # STEP 1:
#     # Find ONLY Minimum Merit sections.
#     # --------------------------------------------------------

#     documents = (
#         discover_minimum_merit_documents(
#             session
#         )
#     )

#     # --------------------------------------------------------
#     # STEP 2:
#     # Select highest merit-list number.
#     # --------------------------------------------------------

#     selected = (
#         get_latest_merit_document(
#             documents
#         )
#     )

#     # --------------------------------------------------------
#     # STEP 3:
#     # Download ONLY the selected document.
#     # --------------------------------------------------------

#     pdf_file = download_pdf(
#         session,
#         selected["url"],
#     )

#     # --------------------------------------------------------
#     # STEP 4:
#     # Extract Computer Science records.
#     # --------------------------------------------------------

#     data = extract_merit_data(
#         pdf_file
#     )

#     if not data:

#         print_pdf_sample(
#             pdf_file,
#             max_pages=3,
#         )

#         raise RuntimeError(
#             f"Merit List "
#             f"{selected['merit_number']} "
#             "was downloaded successfully, "
#             "but Computer Science merit records "
#             "could not be extracted from the PDF."
#         )

#     # --------------------------------------------------------
#     # STEP 5:
#     # Return complete result.
#     # --------------------------------------------------------

#     return {

#         "data":
#             data,

#         "pdf_file":
#             str(pdf_file),

#         "source_url":
#             selected["url"],

#         "merit_list_number":
#             selected["merit_number"],

#         "title":
#             selected["title"],

#         "checked_at":
#             datetime.now().isoformat(),
#     }


# # ============================================================
# # PRINT MERIT
# # ============================================================

# def print_merit(
#     records
# ):

#     print()
#     print("=" * 90)
#     print(
#         "COMPUTER SCIENCE — CURRENT MERIT"
#     )
#     print("=" * 90)

#     if not records:

#         print(
#             "No matching Computer Science "
#             "records found."
#         )

#         return

#     for record in records:

#         print()

#         print(
#             f'Campus       : '
#             f'{record.get("campus", "")}'
#         )

#         print(
#             f'Program      : '
#             f'{record.get("program", "")}'
#         )

#         print(
#             f'Category     : '
#             f'{record.get("category", "")}'
#         )

#         print(
#             f'Session      : '
#             f'{record.get("session", "")}'
#         )

#         print(
#             f'Type         : '
#             f'{record.get("type", "")}'
#         )

#         print(
#             f'Current Merit: '
#             f'{float(record["minimum_aggregate"]):.5f}'
#         )

#         print(
#             f'PDF Page     : '
#             f'{record.get("page", "")}'
#         )


# # ============================================================
# # INTERACTIVE MODE
# # ============================================================

# def interactive_mode(
#     merit
# ):

#     data = merit[
#         "data"
#     ]

#     print()
#     print("=" * 90)
#     print(
#         "UET MERIT CHECKER"
#     )
#     print("=" * 90)

#     print()

#     print(
#         f'Merit List: '
#         f'{merit.get("merit_list_number")}'
#     )

#     print(
#         f'Title: '
#         f'{merit.get("title")}'
#     )

#     print()

#     print(
#         f'Source: '
#         f'{merit.get("source_url")}'
#     )

#     print()
#     print(
#         "Examples:"
#     )

#     print(
#         "  lahore"
#     )

#     print(
#         "  90 lahore"
#     )

#     print(
#         "  90 lahore A1"
#     )

#     print(
#         "  exit"
#     )

#     while True:

#         try:

#             user_input = input(
#                 "\nQuery: "
#             ).strip()

#         except (
#             KeyboardInterrupt,
#             EOFError,
#         ):

#             print()

#             break

#         if not user_input:
#             continue

#         if user_input.lower() in {
#             "exit",
#             "quit",
#             "q",
#         }:

#             break

#         # ----------------------------------------------------
#         # Aggregate
#         # ----------------------------------------------------

#         aggregate_match = re.search(
#             r"\b(\d+(?:\.\d+)?)\b",
#             user_input,
#         )

#         aggregate = None

#         if aggregate_match:

#             try:

#                 aggregate = float(
#                     aggregate_match.group(1)
#                 )

#             except ValueError:

#                 aggregate = None

#         # ----------------------------------------------------
#         # Campus
#         # ----------------------------------------------------

#         lower = user_input.lower()

#         campus = None

#         aliases = sorted(
#             CAMPUS_ALIASES.keys(),
#             key=len,
#             reverse=True,
#         )

#         for alias in aliases:

#             if alias in lower:

#                 campus = (
#                     CAMPUS_ALIASES[
#                         alias
#                     ]
#                 )

#                 break

#         # ----------------------------------------------------
#         # Category
#         # ----------------------------------------------------

#         category = None

#         category_match = re.search(
#             rf"\b({CATEGORY_PATTERN})\b",
#             user_input,
#             re.IGNORECASE,
#         )

#         if category_match:

#             category = (
#                 category_match
#                 .group(1)
#                 .upper()
#             )

#         # ----------------------------------------------------
#         # Lookup
#         # ----------------------------------------------------

#         if aggregate is None:

#             records = get_cs_data(
#                 data,
#                 campus=campus,
#                 category=category,
#             )

#             print_merit(
#                 records
#             )

#             continue

#         # ----------------------------------------------------
#         # Student check
#         # ----------------------------------------------------

#         if campus is None:

#             print()

#             print(
#                 "Please specify a campus."
#             )

#             print(
#                 "Example: 90 Lahore"
#             )

#             continue

#         results = check_student(
#             data,
#             aggregate,
#             campus,
#             category,
#         )

#         print()
#         print("=" * 90)
#         print(
#             "STUDENT MERIT CHECK"
#         )
#         print("=" * 90)

#         if not results:

#             print(
#                 "No matching Computer Science "
#                 "merit record found."
#             )

#             continue

#         for result in results:

#             if result[
#                 "selected"
#             ]:

#                 status = (
#                     "SELECTED / ABOVE CURRENT MERIT"
#                 )

#             else:

#                 status = (
#                     "BELOW CURRENT MERIT"
#                 )

#             print()

#             print(
#                 f'Campus        : '
#                 f'{result["campus"]}'
#             )

#             print(
#                 f'Category      : '
#                 f'{result["category"]}'
#             )

#             print(
#                 f'Session       : '
#                 f'{result["session"]}'
#             )

#             print(
#                 f'Type          : '
#                 f'{result["type"]}'
#             )

#             print(
#                 f'Student       : '
#                 f'{result["student_aggregate"]:.5f}'
#             )

#             print(
#                 f'Current Merit : '
#                 f'{result["minimum_aggregate"]:.5f}'
#             )

#             print(
#                 f'Difference    : '
#                 f'{result["difference"]:+.5f}'
#             )

#             print(
#                 f'Status        : '
#                 f'{status}'
#             )


# # ============================================================
# # MAIN
# # ============================================================

# def main():

#     print()
#     print("=" * 90)
#     print(
#         "UET CHATBOT — DYNAMIC MINIMUM MERIT DATA"
#     )
#     print("=" * 90)

#     print()
#     print(
#         "Checking UET Downloads page..."
#     )

#     try:

#         merit = load_latest_merit()

#         print()
#         print("=" * 90)
#         print(
#             "LATEST MERIT SOURCE"
#         )
#         print("=" * 90)

#         print()

#         print(
#             f'Merit List: '
#             f'{merit["merit_list_number"]}'
#         )

#         print()

#         print(
#             f'Title: '
#             f'{merit["title"]}'
#         )

#         print()

#         print(
#             f'PDF: '
#             f'{merit["source_url"]}'
#         )

#         print()

#         print(
#             f'CS records: '
#             f'{len(merit["data"])}'
#         )

#         print()

#         # ----------------------------------------------------
#         # Show Lahore records.
#         # ----------------------------------------------------

#         lahore = get_cs_data(
#             merit["data"],
#             campus="Lahore",
#         )

#         print_merit(
#             lahore
#         )

#         interactive_mode(
#             merit
#         )

#     except Exception as exc:

#         print()
#         print("=" * 90)
#         print(
#             "MERIT RETRIEVAL ERROR"
#         )
#         print("=" * 90)

#         print()

#         print(
#             str(exc)
#         )

#         raise


# # ============================================================
# # ENTRY POINT
# # ============================================================

# if __name__ == "__main__":

#     main()






import re
import requests
import fitz

from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin
from html.parser import HTMLParser


# ============================================================
# UET CHATBOT
# DYNAMIC MINIMUM MERIT RETRIEVER
# ============================================================
#
# IMPORTANT
# ----------
# The UET Downloads page is structured as document sections.
#
# Example:
#
#   <h4>Minimum Merit – 3rd Merit List (Undergraduate Fall 2026)</h4>
#   ...
#   <a ...>Download</a>
#
#   <h4>Minimum Merit – 4th Merit List (Undergraduate Fall 2026)</h4>
#   ...
#   <a ...>Download</a>
#
# We DO NOT scan every PDF on the website.
#
# We:
#
#   1. Find "Minimum Merit" sections.
#   2. Extract the merit-list number from each title.
#   3. Select the HIGHEST number.
#   4. Download ONLY that section's PDF.
#
# ============================================================


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

MERIT_DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "merit"
)

LATEST_PDF = (
    MERIT_DATA_DIR
    / "latest_merit_list.pdf"
)


# ============================================================
# UET CONFIGURATION
# ============================================================

UET_BASE_URL = "https://admission.uet.edu.pk"

UET_DOWNLOADS_URL = (
    "https://admission.uet.edu.pk/downloads"
)

REQUEST_TIMEOUT = 30


# ============================================================
# HTTP
# ============================================================

def create_session():

    session = requests.Session()

    session.headers.update({

        "User-Agent":
            (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/131.0 Safari/537.36"
            ),

        "Accept":
            (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,"
                "image/avif,image/webp,"
                "image/apng,*/*;q=0.8"
            ),

        "Accept-Language":
            "en-US,en;q=0.9",

        "Referer":
            UET_BASE_URL + "/",
    })

    return session


# ============================================================
# GENERAL HELPERS
# ============================================================

def normalize(value):

    if value is None:
        return ""

    value = str(value)

    value = value.replace(
        "\xa0",
        " ",
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def normalize_url(
    base_url,
    url,
):

    url = normalize(url)

    if not url:
        return ""

    url = (
        url
        .replace("&amp;", "&")
        .replace("&#x26;", "&")
    )

    if url.startswith("//"):
        return "https:" + url

    return urljoin(
        base_url,
        url,
    )


# ============================================================
# HTML SECTION PARSER
# ============================================================
#
# This parser follows the ACTUAL structure of the UET
# Downloads page instead of trying to infer a title from
# arbitrary surrounding HTML.
#
# Every <h4> starts a new download section.
#
# We collect:
#
#     h4 title
#     text inside the section
#     href of Download anchor
#
# until the next <h4>.
#
# ============================================================

class UETDownloadsParser(HTMLParser):

    def __init__(self):

        super().__init__(
            convert_charrefs=True
        )

        self.sections = []

        self.current = None

        self.current_tag = None

        self.capture_heading = False

        self.capture_anchor = False

        self.anchor_href = ""

    def handle_starttag(
        self,
        tag,
        attrs,
    ):

        tag = tag.lower()

        attrs_dict = dict(
            attrs
        )

        # ----------------------------------------------------
        # Every h4 represents a new download-card/section.
        # ----------------------------------------------------

        if tag == "h4":

            self._finish_section()

            self.current = {

                "title":
                    "",

                "text":
                    "",

                "url":
                    "",
            }

            self.capture_heading = True

            return

        # ----------------------------------------------------
        # If we are inside a section, capture anchor links.
        # ----------------------------------------------------

        if self.current is not None:

            if tag == "a":

                href = attrs_dict.get(
                    "href",
                    "",
                )

                if href:

                    href = normalize_url(
                        UET_DOWNLOADS_URL,
                        href,
                    )

                    # The UET page uses a Download anchor
                    # inside each section.
                    #
                    # Keep the first useful link.
                    if not self.current["url"]:

                        self.current[
                            "url"
                        ] = href

                    self.capture_anchor = True

                    self.anchor_href = href

            self.current_tag = tag

    def handle_endtag(
        self,
        tag,
    ):

        tag = tag.lower()

        if tag == "h4":

            self.capture_heading = False

        if tag == "a":

            self.capture_anchor = False

            self.anchor_href = ""

        self.current_tag = None

    def handle_data(
        self,
        data,
    ):

        data = normalize(
            data
        )

        if not data:
            return

        if self.current is None:
            return

        # ----------------------------------------------------
        # Heading.
        # ----------------------------------------------------

        if self.capture_heading:

            self.current[
                "title"
            ] += " " + data

        # ----------------------------------------------------
        # All section text.
        # ----------------------------------------------------

        self.current[
            "text"
        ] += " " + data

    def _finish_section(self):

        if self.current is None:
            return

        self.current["title"] = normalize(
            self.current["title"]
        )

        self.current["text"] = normalize(
            self.current["text"]
        )

        self.sections.append(
            self.current
        )

        self.current = None

        self.capture_heading = False

        self.capture_anchor = False

        self.anchor_href = ""

    def close(self):

        super().close()

        self._finish_section()


# ============================================================
# MERIT LIST NUMBER
# ============================================================

def extract_merit_list_number(
    text
):

    text = normalize(
        text
    ).lower()

    if not text:
        return 0

    patterns = [

        # ----------------------------------------------------
        # Exact UET structure:
        #
        # Minimum Merit – 4th Merit List
        # Minimum Merit - 4th Merit List
        # ----------------------------------------------------

        r"""
        \b
        minimum\s+merit
        \s*[-–—:]\s*
        (\d+)
        (?:st|nd|rd|th)?
        \s+
        merit\s+list
        \b
        """,

        # ----------------------------------------------------
        # 4th Merit List
        # ----------------------------------------------------

        r"""
        \b
        (\d+)
        (?:st|nd|rd|th)
        \s+
        merit\s+list
        \b
        """,

        # ----------------------------------------------------
        # Merit List 4
        # ----------------------------------------------------

        r"""
        \b
        merit\s+list
        \s*
        (?:no\.?|number)?
        \s*
        [-:#]?
        \s*
        (\d+)
        \b
        """,

        # ----------------------------------------------------
        # Merit List No. 4
        # ----------------------------------------------------

        r"""
        \b
        merit\s+list
        \s*
        no\.?
        \s*
        (\d+)
        \b
        """,

        # ----------------------------------------------------
        # Merit-4
        # ----------------------------------------------------

        r"""
        \b
        merit
        \s*[-_]
        \s*
        (\d+)
        \b
        """,
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE |
            re.VERBOSE,
        )

        if match:

            try:

                return int(
                    match.group(1)
                )

            except (
                TypeError,
                ValueError,
            ):

                pass

    return 0


# ============================================================
# IS EXACT MINIMUM MERIT SECTION?
# ============================================================

def is_minimum_merit_section(
    title
):

    title = normalize(
        title
    ).lower()

    if not title:
        return False

    # The current UET page uses:
    #
    # Minimum Merit – 4th Merit List
    #
    # We deliberately require "minimum merit".
    # This prevents unrelated admission documents from
    # being selected.
    #

    return (
        "minimum merit" in title
        and
        "merit list" in title
    )


# ============================================================
# DISCOVER MINIMUM MERIT SECTIONS
# ============================================================

def discover_minimum_merit_documents(
    session
):

    print()
    print("=" * 80)
    print("CHECKING UET DOWNLOADS PAGE")
    print("=" * 80)

    print()
    print(
        f"URL: {UET_DOWNLOADS_URL}"
    )

    response = session.get(
        UET_DOWNLOADS_URL,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    html = response.text

    print()
    print(
        f"Downloaded HTML: "
        f"{len(html):,} characters"
    )

    # --------------------------------------------------------
    # Parse actual h4-based sections.
    # --------------------------------------------------------

    parser = UETDownloadsParser()

    parser.feed(
        html
    )

    parser.close()

    sections = parser.sections

    print()
    print(
        f"Download sections discovered: "
        f"{len(sections)}"
    )

    documents = []

    for section in sections:

        title = normalize(
            section.get(
                "title",
                "",
            )
        )

        if not is_minimum_merit_section(
            title
        ):

            continue

        merit_number = (
            extract_merit_list_number(
                title
            )
        )

        if merit_number <= 0:

            print()
            print(
                "WARNING: Minimum Merit "
                "section found but its number "
                "could not be detected:"
            )

            print(
                title
            )

            continue

        url = normalize_url(
            UET_DOWNLOADS_URL,
            section.get(
                "url",
                "",
            ),
        )

        if not url:

            print()
            print(
                "WARNING: No download link "
                "found for:"
            )

            print(
                title
            )

            continue

        documents.append({

            "title":
                title,

            "url":
                url,

            "text":
                normalize(
                    section.get(
                        "text",
                        "",
                    )
                ),

            "merit_number":
                merit_number,
        })

    # --------------------------------------------------------
    # Remove duplicate URLs.
    # --------------------------------------------------------

    unique = {}

    for document in documents:

        url = document[
            "url"
        ]

        if url not in unique:

            unique[url] = document

    documents = list(
        unique.values()
    )

    # --------------------------------------------------------
    # Sort by merit number.
    # --------------------------------------------------------

    documents.sort(
        key=lambda item: (
            item["merit_number"],
            item["title"],
        )
    )

    print()
    print(
        f"Minimum Merit documents found: "
        f"{len(documents)}"
    )

    for document in documents:

        print()
        print(
            f"Merit List Number: "
            f"{document['merit_number']}"
        )

        print(
            f"Title: "
            f"{document['title']}"
        )

        print(
            f"Download URL: "
            f"{document['url']}"
        )

    return documents


# ============================================================
# GET HIGHEST MINIMUM MERIT DOCUMENT
# ============================================================

def get_latest_merit_document(
    documents
):

    if not documents:

        raise RuntimeError(
            "UET website did not expose any "
            "recognizable Minimum Merit documents "
            "on the Downloads page."
        )

    highest_number = max(
        document["merit_number"]
        for document in documents
    )

    latest = [

        document

        for document in documents

        if (
            document["merit_number"]
            == highest_number
        )
    ]

    if not latest:

        raise RuntimeError(
            "Could not select the highest "
            "Minimum Merit document."
        )

    # --------------------------------------------------------
    # There should normally be exactly one.
    #
    # We use the first section with the highest number.
    #
    # --------------------------------------------------------

    selected = latest[0]

    print()
    print("=" * 80)
    print(
        "SELECTED LATEST MINIMUM MERIT"
    )
    print("=" * 80)

    print()
    print(
        f"Merit List Number: "
        f"{selected['merit_number']}"
    )

    print(
        f"Title: "
        f"{selected['title']}"
    )

    print(
        f"URL: "
        f"{selected['url']}"
    )

    return selected


# ============================================================
# DOWNLOAD PDF
# ============================================================

def download_pdf(
    session,
    url,
):

    MERIT_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 80)
    print(
        "DOWNLOADING SELECTED MERIT PDF"
    )
    print("=" * 80)

    print()
    print(
        url
    )

    response = session.get(
        url,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    content = response.content

    content_type = (
        response.headers.get(
            "Content-Type",
            "",
        )
    )

    print()
    print(
        f"Content-Type: "
        f"{content_type}"
    )

    print(
        f"Downloaded bytes: "
        f"{len(content):,}"
    )

    # --------------------------------------------------------
    # Validate PDF.
    # --------------------------------------------------------

    if not content.startswith(
        b"%PDF"
    ):

        raise ValueError(
            "The selected UET download link "
            "did not return a valid PDF. "
            f"Content-Type: {content_type}"
        )

    with open(
        LATEST_PDF,
        "wb",
    ) as file:

        file.write(
            content
        )

    print()
    print(
        "PDF downloaded successfully."
    )

    print(
        f"Saved to: "
        f"{LATEST_PDF}"
    )

    return LATEST_PDF


# ============================================================
# EXTRACT ALL PDF TEXT
# ============================================================

def extract_all_pdf_text(
    pdf_file
):

    doc = fitz.open(
        str(pdf_file)
    )

    pages = []

    for page_number, page in enumerate(
        doc,
        start=1,
    ):

        text = page.get_text(
            "text"
        )

        pages.append({

            "page":
                page_number,

            "text":
                text,
        })

    doc.close()

    return pages


# ============================================================
# PDF TEXT DEBUGGER
# ============================================================

def print_pdf_sample(
    pdf_file,
    max_pages=3,
):

    print()
    print("=" * 80)
    print(
        "PDF TEXT SAMPLE"
    )
    print("=" * 80)

    try:

        doc = fitz.open(
            str(pdf_file)
        )

        total = len(doc)

        print()
        print(
            f"PDF pages: {total}"
        )

        for index, page in enumerate(
            doc
        ):

            if index >= max_pages:
                break

            text = page.get_text(
                "text"
            )

            print()
            print(
                f"--- PAGE {index + 1} ---"
            )

            print(
                text[:5000]
            )

        doc.close()

    except Exception as exc:

        print(
            f"Could not print PDF sample: "
            f"{exc}"
        )


# ============================================================
# CAMPUS ALIASES
# ============================================================

CAMPUS_ALIASES = {

    "lahore":
        "Main Campus (LHR)",

    "lhr":
        "Main Campus (LHR)",

    "lahore campus":
        "Main Campus (LHR)",

    "main campus":
        "Main Campus (LHR)",

    "main campus lahore":
        "Main Campus (LHR)",

    "main campus lhr":
        "Main Campus (LHR)",

    "ksk":
        "New Campus (KSK)",

    "kala shah kaku":
        "New Campus (KSK)",

    "kala shah kaku campus":
        "New Campus (KSK)",

    "new campus":
        "New Campus (KSK)",

    "new campus ksk":
        "New Campus (KSK)",

    "faisalabad":
        "Faislabad Campus",

    "faislabad":
        "Faislabad Campus",

    "faisalabad campus":
        "Faislabad Campus",

    "faislabad campus":
        "Faislabad Campus",

    "gujranwala":
        "Gujar anwala",

    "gujaranwala":
        "Gujar anwala",

    "gujranwala campus":
        "Gujar anwala",

    "narowal":
        "Narowal Campus (NWL)",

    "nwl":
        "Narowal Campus (NWL)",

    "narowal campus":
        "Narowal Campus (NWL)",
}


def normalize_campus_name(
    campus
):

    value = normalize(
        campus
    ).lower()

    if value in CAMPUS_ALIASES:

        return CAMPUS_ALIASES[
            value
        ]

    return normalize(
        campus
    )


# ============================================================
# PROGRAM / DEPARTMENT NORMALIZATION
# ============================================================

PROGRAM_ALIASES = {

    "cs":
        "Computer Science",

    "computer science":
        "Computer Science",

    "computer sciences":
        "Computer Science",

    "computing":
        "Computer Science",
}


def normalize_program_name(
    program
):

    value = normalize(
        program
    ).lower()

    if value in PROGRAM_ALIASES:

        return PROGRAM_ALIASES[
            value
        ]

    return normalize(
        program
    )


def is_computer_science(
    text
):

    text = normalize(
        text
    ).lower()

    text = re.sub(
        r"[-_/]+",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return bool(
        re.search(
            r"\bcomputer\s+science\b",
            text,
            re.IGNORECASE,
        )
    )


# ============================================================
# CATEGORY / SESSION / TYPE
# ============================================================

CATEGORY_PATTERN = (
    r"A1-M|A2-M|A1|A2|NM"
)

SESSION_PATTERN = (
    r"Morning|Evening"
)

TYPE_PATTERN = (
    r"ECAT|Non-ECAT|Non ECAT"
)


# ============================================================
# CLEAN NUMERIC VALUE
# ============================================================

def clean_number(
    value
):

    value = normalize(
        value
    )

    value = value.replace(
        "%",
        "",
    )

    try:

        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return None


# ============================================================
# EXTRACT AGGREGATES FROM TEXT
# ============================================================

def extract_aggregate_candidates(
    text
):

    text = normalize(
        text
    )

    candidates = []

    # --------------------------------------------------------
    # Typical closing merit:
    #
    # 89.1234
    # 89.12345%
    #
    # --------------------------------------------------------

    matches = re.findall(
        r"\b(?:100|[0-9]{1,2})\.\d{1,6}\s*%?",
        text,
        re.IGNORECASE,
    )

    for match in matches:

        value = clean_number(
            match
        )

        if value is None:
            continue

        if (
            0 <= value <= 100
        ):

            candidates.append(
                value
            )

    return candidates


# ============================================================
# GENERIC CS ROW PARSER
# ============================================================

def parse_cs_row(
    row,
    page_number,
):

    row = normalize(
        row
    )

    if not row:
        return None

    if not is_computer_science(
        row
    ):
        return None

    normalized_row = re.sub(
        r"\s+",
        " ",
        row,
    ).strip()

    # --------------------------------------------------------
    # Aggregate is normally the final numeric value.
    # --------------------------------------------------------

    aggregate_match = re.search(
        r"(\d{1,3}(?:\.\d+)?)\s*%?\s*$",
        normalized_row,
        re.IGNORECASE,
    )

    if not aggregate_match:

        # Try a less strict approach.
        values = extract_aggregate_candidates(
            normalized_row
        )

        if not values:
            return None

        aggregate = values[-1]

        aggregate_start = (
            normalized_row.rfind(
                str(
                    aggregate
                )
            )
        )

        if aggregate_start < 0:
            return None

        before_aggregate = (
            normalized_row[
                :aggregate_start
            ].strip()
        )

    else:

        aggregate = clean_number(
            aggregate_match.group(1)
        )

        if aggregate is None:
            return None

        before_aggregate = (
            normalized_row[
                :aggregate_match.start()
            ].strip()
        )

    if not (
        0 <= aggregate <= 100
    ):
        return None

    # --------------------------------------------------------
    # Category
    # --------------------------------------------------------

    category_match = re.search(
        rf"\b({CATEGORY_PATTERN})\b",
        before_aggregate,
        re.IGNORECASE,
    )

    if category_match:

        category = normalize(
            category_match.group(1)
        ).upper()

        before_category = (
            before_aggregate[
                :category_match.start()
            ].strip()
        )

    else:

        category = ""

        before_category = (
            before_aggregate
        )

    # --------------------------------------------------------
    # Session
    # --------------------------------------------------------

    session_match = re.search(
        rf"\b({SESSION_PATTERN})\b",
        before_category,
        re.IGNORECASE,
    )

    if session_match:

        session = normalize(
            session_match.group(1)
        )

        before_session = (
            before_category[
                :session_match.start()
            ].strip()
        )

    else:

        session = ""

        before_session = (
            before_category
        )

    # --------------------------------------------------------
    # Admission type
    # --------------------------------------------------------

    type_match = re.search(
        rf"\b({TYPE_PATTERN})\b",
        before_session,
        re.IGNORECASE,
    )

    if type_match:

        admission_type = normalize(
            type_match.group(1)
        )

        before_type = (
            before_session[
                :type_match.start()
            ].strip()
        )

    else:

        admission_type = ""

        before_type = (
            before_session
        )

    # --------------------------------------------------------
    # Find Computer Science.
    # --------------------------------------------------------

    cs_match = re.search(
        r"computer\s+science",
        before_type,
        re.IGNORECASE,
    )

    if not cs_match:
        return None

    campus = normalize(
        before_type[
            :cs_match.start()
        ]
    )

    # --------------------------------------------------------
    # Remove common table artifacts.
    # --------------------------------------------------------

    campus = re.sub(
        r"[\|\t]+",
        " ",
        campus,
    )

    campus = re.sub(
        r"^\d+\s+",
        "",
        campus,
    )

    campus = normalize(
        campus
    )

    # --------------------------------------------------------
    # If campus is empty, do not create a bogus record.
    # --------------------------------------------------------

    if not campus:
        return None

    if len(campus) > 100:
        return None

    return {

        "page":
            page_number,

        "campus":
            campus,

        "program":
            "Computer Science",

        "category":
            category,

        "session":
            session,

        "type":
            admission_type,

        "minimum_aggregate":
            aggregate,
    }


# ============================================================
# EXTRACT CS DATA
# ============================================================

def extract_merit_data(
    pdf_file
):

    pages = extract_all_pdf_text(
        pdf_file
    )

    results = []

    print()
    print(
        f"Total PDF pages: "
        f"{len(pages)}"
    )

    # ========================================================
    # STRATEGY 1
    # Individual lines
    # ========================================================

    for page_data in pages:

        page_number = page_data[
            "page"
        ]

        text = page_data[
            "text"
        ]

        lines = text.splitlines()

        for line in lines:

            line = normalize(
                line
            )

            if not is_computer_science(
                line
            ):
                continue

            record = parse_cs_row(
                line,
                page_number,
            )

            if record:

                results.append(
                    record
                )

    # ========================================================
    # STRATEGY 2
    # Nearby-line windows
    # ========================================================

    for page_data in pages:

        page_number = page_data[
            "page"
        ]

        lines = [

            normalize(line)

            for line in
            page_data["text"].splitlines()

            if normalize(line)
        ]

        for index, line in enumerate(
            lines
        ):

            if not is_computer_science(
                line
            ):
                continue

            for window_size in (
                2,
                3,
                4,
                5,
                6,
                7,
            ):

                start = max(
                    0,
                    index - 3,
                )

                end = min(
                    len(lines),
                    index
                    + window_size,
                )

                window = normalize(
                    " ".join(
                        lines[
                            start:end
                        ]
                    )
                )

                record = parse_cs_row(
                    window,
                    page_number,
                )

                if record:

                    results.append(
                        record
                    )

    # ========================================================
    # STRATEGY 3
    # Computer Science followed by nearby numeric values.
    #
    # This helps when PDF text extraction destroys the table
    # columns.
    # ========================================================

    for page_data in pages:

        page_number = page_data[
            "page"
        ]

        lines = [

            normalize(line)

            for line in
            page_data["text"].splitlines()

            if normalize(line)
        ]

        for index, line in enumerate(
            lines
        ):

            if not is_computer_science(
                line
            ):
                continue

            start = max(
                0,
                index - 5,
            )

            end = min(
                len(lines),
                index + 8,
            )

            window_lines = lines[
                start:end
            ]

            window = normalize(
                " ".join(
                    window_lines
                )
            )

            # ------------------------------------------------
            # Only attempt this strategy if an aggregate
            # appears nearby.
            # ------------------------------------------------

            values = extract_aggregate_candidates(
                window
            )

            if not values:
                continue

            aggregate = values[-1]

            cs_position = re.search(
                r"computer\s+science",
                window,
                re.IGNORECASE,
            )

            if not cs_position:
                continue

            before_cs = normalize(
                window[
                    :cs_position.start()
                ]
            )

            # ------------------------------------------------
            # Try to identify the campus from the text before
            # Computer Science.
            # ------------------------------------------------

            campus = before_cs

            campus = re.sub(
                r"^\d+\s+",
                "",
                campus,
            )

            campus = normalize(
                campus
            )

            if not campus:
                continue

            if len(campus) > 100:
                continue

            category_match = re.search(
                rf"\b({CATEGORY_PATTERN})\b",
                window,
                re.IGNORECASE,
            )

            session_match = re.search(
                rf"\b({SESSION_PATTERN})\b",
                window,
                re.IGNORECASE,
            )

            type_match = re.search(
                rf"\b({TYPE_PATTERN})\b",
                window,
                re.IGNORECASE,
            )

            category = ""

            if category_match:

                category = (
                    category_match
                    .group(1)
                    .upper()
                )

            session = ""

            if session_match:

                session = normalize(
                    session_match.group(1)
                )

            admission_type = ""

            if type_match:

                admission_type = normalize(
                    type_match.group(1)
                )

            results.append({

                "page":
                    page_number,

                "campus":
                    campus,

                "program":
                    "Computer Science",

                "category":
                    category,

                "session":
                    session,

                "type":
                    admission_type,

                "minimum_aggregate":
                    aggregate,
            })

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    unique = {}

    for record in results:

        key = (

            normalize(
                record.get(
                    "campus",
                    "",
                )
            ).lower(),

            normalize(
                record.get(
                    "program",
                    "",
                )
            ).lower(),

            normalize(
                record.get(
                    "category",
                    "",
                )
            ).lower(),

            normalize(
                record.get(
                    "session",
                    "",
                )
            ).lower(),

            normalize(
                record.get(
                    "type",
                    "",
                )
            ).lower(),

            round(
                float(
                    record[
                        "minimum_aggregate"
                    ]
                ),
                5,
            ),
        )

        if key not in unique:

            unique[key] = record

    results = list(
        unique.values()
    )

    # ========================================================
    # SORT
    # ========================================================

    results.sort(
        key=lambda record: (

            normalize(
                record.get(
                    "campus",
                    "",
                )
            ),

            normalize(
                record.get(
                    "category",
                    "",
                )
            ),

            normalize(
                record.get(
                    "session",
                    "",
                )
            ),

            normalize(
                record.get(
                    "type",
                    "",
                )
            ),

        )
    )

    print()
    print(
        f"Computer Science records found: "
        f"{len(results)}"
    )

    return results


# ============================================================
# GET CS DATA
# ============================================================

def get_cs_data(
    data,
    campus=None,
    category=None,
):

    results = []

    normalized_campus = None

    if campus:

        normalized_campus = (
            normalize_campus_name(
                campus
            )
        ).lower()

    normalized_category = None

    if category:

        normalized_category = (
            normalize(
                category
            ).lower()
        )

    for item in data:

        program = normalize_program_name(
            item.get(
                "program",
                "",
            )
        )

        if program.lower() != (
            "computer science"
        ):

            continue

        item_campus = normalize(
            item.get(
                "campus",
                "",
            )
        ).lower()

        if normalized_campus:

            if (
                item_campus
                != normalized_campus
            ):

                if (
                    normalized_campus
                    not in item_campus
                    and
                    item_campus
                    not in normalized_campus
                ):

                    continue

        if normalized_category:

            item_category = normalize(
                item.get(
                    "category",
                    "",
                )
            ).lower()

            if (
                item_category
                != normalized_category
            ):

                continue

        results.append(
            item
        )

    return results


# ============================================================
# CHECK STUDENT
# ============================================================

def check_student(
    data,
    aggregate,
    campus,
    category=None,
):

    records = get_cs_data(
        data,
        campus=campus,
        category=category,
    )

    results = []

    for record in records:

        merit = float(
            record[
                "minimum_aggregate"
            ]
        )

        difference = (
            float(aggregate)
            - merit
        )

        results.append({

            **record,

            "student_aggregate":
                float(aggregate),

            "selected":
                float(aggregate)
                >= merit,

            "difference":
                round(
                    difference,
                    5,
                ),
        })

    return results


# ============================================================
# LOAD LATEST MERIT
# ============================================================

def load_latest_merit():

    session = create_session()

    # --------------------------------------------------------
    # STEP 1:
    # Find ONLY Minimum Merit sections.
    # --------------------------------------------------------

    documents = (
        discover_minimum_merit_documents(
            session
        )
    )

    # --------------------------------------------------------
    # STEP 2:
    # Select highest merit-list number.
    # --------------------------------------------------------

    selected = (
        get_latest_merit_document(
            documents
        )
    )

    # --------------------------------------------------------
    # STEP 3:
    # Download ONLY the selected document.
    # --------------------------------------------------------

    pdf_file = download_pdf(
        session,
        selected["url"],
    )

    # --------------------------------------------------------
    # STEP 4:
    # Extract Computer Science records.
    # --------------------------------------------------------

    data = extract_merit_data(
        pdf_file
    )

    if not data:

        print_pdf_sample(
            pdf_file,
            max_pages=3,
        )

        raise RuntimeError(
            f"Merit List "
            f"{selected['merit_number']} "
            "was downloaded successfully, "
            "but Computer Science merit records "
            "could not be extracted from the PDF."
        )

    # --------------------------------------------------------
    # STEP 5:
    # Return complete result.
    # --------------------------------------------------------

    return {

        "data":
            data,

        "pdf_file":
            str(pdf_file),

        "source_url":
            selected["url"],

        "merit_list_number":
            selected["merit_number"],

        "title":
            selected["title"],

        "checked_at":
            datetime.now().isoformat(),
    }


# ============================================================
# PRINT MERIT
# ============================================================

def print_merit(
    records
):

    print()
    print("=" * 90)
    print(
        "COMPUTER SCIENCE — CURRENT MERIT"
    )
    print("=" * 90)

    if not records:

        print(
            "No matching Computer Science "
            "records found."
        )

        return

    for record in records:

        print()

        print(
            f'Campus       : '
            f'{record.get("campus", "")}'
        )

        print(
            f'Program      : '
            f'{record.get("program", "")}'
        )

        print(
            f'Category     : '
            f'{record.get("category", "")}'
        )

        print(
            f'Session      : '
            f'{record.get("session", "")}'
        )

        print(
            f'Type         : '
            f'{record.get("type", "")}'
        )

        print(
            f'Current Merit: '
            f'{float(record["minimum_aggregate"]):.5f}'
        )

        print(
            f'PDF Page     : '
            f'{record.get("page", "")}'
        )


# ============================================================
# INTERACTIVE MODE
# ============================================================

def interactive_mode(
    merit
):

    data = merit[
        "data"
    ]

    print()
    print("=" * 90)
    print(
        "UET MERIT CHECKER"
    )
    print("=" * 90)

    print()

    print(
        f'Merit List: '
        f'{merit.get("merit_list_number")}'
    )

    print(
        f'Title: '
        f'{merit.get("title")}'
    )

    print()

    print(
        f'Source: '
        f'{merit.get("source_url")}'
    )

    print()
    print(
        "Examples:"
    )

    print(
        "  lahore"
    )

    print(
        "  90 lahore"
    )

    print(
        "  90 lahore A1"
    )

    print(
        "  exit"
    )

    while True:

        try:

            user_input = input(
                "\nQuery: "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError,
        ):

            print()

            break

        if not user_input:
            continue

        if user_input.lower() in {
            "exit",
            "quit",
            "q",
        }:

            break

        # ----------------------------------------------------
        # Aggregate
        # ----------------------------------------------------

        aggregate_match = re.search(
            r"\b(\d+(?:\.\d+)?)\b",
            user_input,
        )

        aggregate = None

        if aggregate_match:

            try:

                aggregate = float(
                    aggregate_match.group(1)
                )

            except ValueError:

                aggregate = None

        # ----------------------------------------------------
        # Campus
        # ----------------------------------------------------

        lower = user_input.lower()

        campus = None

        aliases = sorted(
            CAMPUS_ALIASES.keys(),
            key=len,
            reverse=True,
        )

        for alias in aliases:

            if alias in lower:

                campus = (
                    CAMPUS_ALIASES[
                        alias
                    ]
                )

                break

        # ----------------------------------------------------
        # Category
        # ----------------------------------------------------

        category = None

        category_match = re.search(
            rf"\b({CATEGORY_PATTERN})\b",
            user_input,
            re.IGNORECASE,
        )

        if category_match:

            category = (
                category_match
                .group(1)
                .upper()
            )

        # ----------------------------------------------------
        # Lookup
        # ----------------------------------------------------

        if aggregate is None:

            records = get_cs_data(
                data,
                campus=campus,
                category=category,
            )

            print_merit(
                records
            )

            continue

        # ----------------------------------------------------
        # Student check
        # ----------------------------------------------------

        if campus is None:

            print()

            print(
                "Please specify a campus."
            )

            print(
                "Example: 90 Lahore"
            )

            continue

        results = check_student(
            data,
            aggregate,
            campus,
            category,
        )

        print()
        print("=" * 90)
        print(
            "STUDENT MERIT CHECK"
        )
        print("=" * 90)

        if not results:

            print(
                "No matching Computer Science "
                "merit record found."
            )

            continue

        for result in results:

            if result[
                "selected"
            ]:

                status = (
                    "SELECTED / ABOVE CURRENT MERIT"
                )

            else:

                status = (
                    "BELOW CURRENT MERIT"
                )

            print()

            print(
                f'Campus        : '
                f'{result["campus"]}'
            )

            print(
                f'Category      : '
                f'{result["category"]}'
            )

            print(
                f'Session       : '
                f'{result["session"]}'
            )

            print(
                f'Type          : '
                f'{result["type"]}'
            )

            print(
                f'Student       : '
                f'{result["student_aggregate"]:.5f}'
            )

            print(
                f'Current Merit : '
                f'{result["minimum_aggregate"]:.5f}'
            )

            print(
                f'Difference    : '
                f'{result["difference"]:+.5f}'
            )

            print(
                f'Status        : '
                f'{status}'
            )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 90)
    print(
        "UET CHATBOT — DYNAMIC MINIMUM MERIT DATA"
    )
    print("=" * 90)

    print()
    print(
        "Checking UET Downloads page..."
    )

    try:

        merit = load_latest_merit()

        print()
        print("=" * 90)
        print(
            "LATEST MERIT SOURCE"
        )
        print("=" * 90)

        print()

        print(
            f'Merit List: '
            f'{merit["merit_list_number"]}'
        )

        print()

        print(
            f'Title: '
            f'{merit["title"]}'
        )

        print()

        print(
            f'PDF: '
            f'{merit["source_url"]}'
        )

        print()

        print(
            f'CS records: '
            f'{len(merit["data"])}'
        )

        print()

        # ----------------------------------------------------
        # Show Lahore records.
        # ----------------------------------------------------

        lahore = get_cs_data(
            merit["data"],
            campus="Lahore",
        )

        print_merit(
            lahore
        )

        interactive_mode(
            merit
        )

    except Exception as exc:

        print()
        print("=" * 90)
        print(
            "MERIT RETRIEVAL ERROR"
        )
        print("=" * 90)

        print()

        print(
            str(exc)
        )

        raise


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
