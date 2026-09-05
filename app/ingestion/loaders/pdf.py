import logfire
from pypdf import PdfReader

def parse_pdf(file_path: str):
    with logfire.span("PDF Parsing", filename=file_path):
        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            logfire.info(f"Found {total_pages} pages in {file_path}")

            text_parts: list[str] = []  
            blank_pages:list[int] = []  
        
            for i, page in enumerate[PageObject](reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    text_parts.append(text)
                else:
                    blank_pages.append(i+1)

                #fallback
                if blank_pages:
                    logfire.warning(f"Found {len(blank_pages)} blank pages in {file_path}: {blank_pages}")
                    try:
                        import pdfplumber
                        with pdfplumber.open(file_path) as pdf:
                            for page_number in blank_pages:
                                page = pdf.pages[page_number-1]
                                text = page.extract_text() or ""
                                if text.strip():
                                    text_parts.append(text)
                                else:
                                    blank_pages.append(page_number)
                    except Exception as e:
                        logfire.warning(f"Error parsing PDF: {e}", exc_info=True)
                
                full_text = "\n".join(text_parts)
                if not full_text.strip():
                    logfire.warning(f"No text found in {file_path}")
                else:
                    logfire.info(f"Found {len(text_parts)} parts in {file_path}")

            return full_text
        except Exception as e:
            logfire.error(f"Error parsing PDF: {e}", exc_info=True)
            raise e