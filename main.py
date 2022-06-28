import functions_framework
from PyPDF2 import PdfFileReader
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from base64 import urlsafe_b64decode
from io import BytesIO
import json


def decrypt_pdf_to_text(input_stream, password):
    all_lines = []
    reader = PdfFileReader(input_stream)
    reader.decrypt(password)
    for i in range(reader.getNumPages()):
        all_lines += reader.getPage(i).extract_text().splitlines()
    return all_lines


@functions_framework.http
def loadHomePage(request):
    return {
        "action": {
            "navigations": [
                {
                    "pushCard": {
                        "header": {
                            "title": "Tax calculator"
                        },
                        "sections": [
                            {
                                "widgets": [
                                    {
                                        "textParagraph": {
                                            "text": "open the mbank monthly statement email"
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
    # prepare API
    message_id = request.get_json()['gmail']['messageId']
    message_token = request.get_json()['gmail']['accessToken']
    access_token = request.get_json()['authorizationEventObject']['userOAuthToken']
    creds = Credentials(access_token)
    service = build('gmail', 'v1', credentials=creds)

    # get email data
    request = service.users().messages().get(userId='me', id=message_id, format='full')
    request.headers = {'X-Goog-Gmail-Access-Token': message_token}
    message = request.execute()
    part0 = [p0 for p0 in message['payload']['parts'] if p0['partId'] == '0'].pop()
    part01 = [p01 for p01 in part0['parts'] if p01['partId'] == '0.1'].pop()
    attachment_id = part01['body']['attachmentId']

    # get bank statement attachment
    request = service.users().messages().attachments().get(userId='me', messageId=message_id, id=attachment_id)
    request.headers = {'X-Goog-Gmail-Access-Token': message_token}
    attachment = request.execute()
    base64url_data = attachment['data']
    binary_data = urlsafe_b64decode(base64url_data)
    stream_data = BytesIO(binary_data)

    # get text out of attachment
    email = [h['value'] for h in message['payload']['headers'] if h['name'] == 'Delivered-To'].pop()
    with open('/etc/secrets/email-to-pesel.json') as f:
        passwords = json.load(f)
    content = decrypt_pdf_to_text(stream_data, passwords[email])

    return {
        "action": {
            "navigations": [
                {
                    "pushCard": {
                        "header": {
                            "title": "Calculate taxes"
                        },
                        "sections": [
                            {
                                "widgets": [
                                    {
                                        "textParagraph": {
                                            "text": content[20]
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




if __name__ == '__main__':
    lines = decrypt_pdf_to_text('encrypted.pdf', '')
    print(lines)