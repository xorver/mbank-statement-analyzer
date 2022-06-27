import functions_framework
from PyPDF2 import PdfFileReader
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


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
    message_id = request.get_json()['gmail']['messageId']
    message_token = request.get_json()['gmail']['accessToken']
    access_token = request.get_json()['authorizationEventObject']['userOAuthToken']

    creds = Credentials(access_token)
    service = build('gmail', 'v1', credentials=creds)
    request = service.users().messages().get(userId='me', id=message_id, format='metadata')
    request.headers = {'X-Goog-Gmail-Access-Token': message_token}
    results = request.execute()
    subject = [h['value'] for h in results['payload']['headers'] if h['name'] == 'Subject'].pop()
    return {
        "action": {
            "navigations": [
                {
                    "pushCard": {
                        "header": {
                            "title": "Display subject"
                        },
                        "sections": [
                            {
                                "widgets": [
                                    {
                                        "textParagraph": {
                                            "text": subject
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