import asyncio
from liteparse import LiteParse

def test_parse():
    try:
        print("Initializing LiteParse...")
        parser = LiteParse(output_format="markdown")
        print("Parsing test.pdf locally...")
        result = parser.parse("test.pdf")
        print(f"Successfully parsed {len(result.pages)} pages!")
        if result.pages:
            print("First page preview:")
            print(result.pages[0].text[:100])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_parse()
