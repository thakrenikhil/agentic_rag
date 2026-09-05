import logfire
from unstructured.partition.auto import partition


def parse_office(file_path: str):
    with logfire.span("Office Parsing", filename=file_path):
        try:
            elements = partition(file_path)
            full_text = "\n".join([str(el) for el in elements])

            if not full_text.strip():
                logfire.warning(f"No text found in {file_path}")
            else:
                logfire.info(f"Found {len(elements)} elements in {file_path}")
            
            return full_text
        except Exception as e:
            logfire.error(f"Error parsing Office: {e}")
            raise e