import requests
from bs4 import BeautifulSoup


URL = "https://www.uet.edu.pk/home/"

HEADERS = {
    "User-Agent": (
        "UET-AI-Assistant-Research-Bot/0.1 "
        "(independent student research project)"
    )
}


def main():

    print("=" * 70)
    print("UET NAVIGATION INSPECTOR")
    print("=" * 70)

    print()
    print(f"Fetching: {URL}")

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=20
    )

    print(f"Status: {response.status_code}")

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    print()
    print("=" * 70)
    print("NAVIGATION ELEMENTS")
    print("=" * 70)

    # Find all navigation elements
    elements = soup.find_all(
        ["nav", "ul", "ol"]
    )

    for index, element in enumerate(
        elements,
        start=1
    ):

        links = element.find_all(
            "a",
            href=True
        )

        # Ignore tiny lists
        if len(links) < 3:
            continue

        print()
        print("-" * 70)

        print(
            f"[{index}] "
            f"TAG: {element.name}"
        )

        print(
            f"CLASS: "
            f"{element.get('class')}"
        )

        print(
            f"ID: "
            f"{element.get('id')}"
        )

        print(
            f"LINKS: "
            f"{len(links)}"
        )

        print()

        # Print first 30 links
        for link in links[:30]:

            text = link.get_text(
                " ",
                strip=True
            )

            href = link.get(
                "href"
            )

            if not text:
                continue

            print(
                f"  - {text}"
            )

            print(
                f"    {href}"
            )

    print()
    print("=" * 70)
    print("INSPECTION COMPLETE")
    print("=" * 70)

    print()
    print(
        "Only the homepage was requested."
    )

    print(
        "No discovered links were opened."
    )


if __name__ == "__main__":
    main()