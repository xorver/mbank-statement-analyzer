import functions_framework
from PyPDF2 import PdfFileReader, PdfFileWriter


@functions_framework.http
def loadHomePage(request):
    return {
        "action": {
            "navigations": [
                {
                    "pushCard": {
                        "header": {
                            "title": "Test"
                        },
                        "sections": [
                            {
                                "widgets": [
                                    {
                                        "textParagraph": {
                                            "text": "test"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }
    }


@functions_framework.http
def displayTax(request):
    print("GOT  REQUEST")
    print("------------")
    print(request.get_json(silent=True))
    print("------------")

    return {
        "action": {
            "navigations": [
                {
                    "pushCard": {
                        "header": {
                            "title": "Property tax"
                        },
                        "sections": [
                            {
                                "widgets": [
                                    {
                                        "textParagraph": {
                                            "text": "xxx"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }
    }

def decrypt_pdf_to_text(input_path, password):
    all_lines = []
    with open(input_path, 'rb') as input_file:
        reader = PdfFileReader(input_file)
        reader.decrypt(password)
        for i in range(reader.getNumPages()):
            all_lines += reader.getPage(i).extract_text().splitlines()
    return all_lines


if __name__ == '__main__':
    lines = decrypt_pdf_to_text('encrypted.pdf', '')
    print(lines)