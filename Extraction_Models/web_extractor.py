from bs4 import BeautifulSoup

def extract_text_from_html(content):
    try:
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text(separator="\n")
        lines = [t.strip() for t in text.splitlines() if t.strip()]
        return lines if lines else ["No data found in this document (empty HTML)"]
    except Exception as e:
        print(f" HTML parse failed: {str(e)}")
        return [f"No data found in this document (HTML error)"]
