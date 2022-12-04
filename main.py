import re

import functions_framework
from PyPDF2 import PdfFileReader
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from base64 import urlsafe_b64decode
from io import BytesIO
from decimal import Decimal
import json
import logging

RENTERS = [
    r'Adam .* SWIFT',
    r'MZURI SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ.*',
    r'.*MASZ LA.*'
]

INCOMMING_OPERATION_TYPES = [
    'PRZELEW ZEWNĘTRZNY PRZYCHODZĄCY',
    'PRZELEW WEWNĘTRZNY PRZYCHODZĄCY'
]

def decrypt_pdf_to_text(input_stream, password):
    all_lines = []
    reader = PdfFileReader(input_stream)
    reader.decrypt(password)
    for i in range(reader.getNumPages()):
        all_lines += reader.getPage(i).extract_text().splitlines()
    return all_lines


def is_date(text):
    return re.fullmatch('\d\d-\d\d-\d\d\d\d', text)


def to_decimal(amount):
    return Decimal(re.sub(r' ', '', re.sub(r',', '.', amount)))


def get_amounts(text):
    NOISY_SUBJECTS = ['górska 10/25']
    cleaned = text
    for noise in NOISY_SUBJECTS:
        cleaned = cleaned.replace(noise, '')
    match = re.search(r'(-?\d+( \d\d\d)*,\d\d) (-?\d+( \d\d\d)*,\d\d)', cleaned)
    if match:
        return [to_decimal(match.group(1)), to_decimal(match.group(3))]

class Transaction:
    def __init__(self, lines):
        self.lines = lines
        self.date = lines[0]
        if re.search(r'PRZELEW NA TWOJE CELE', lines[1]):
            self.kind = 'PRZELEW NA TWOJE CELE'
            self.amount = get_amounts(lines[1])[0]
            self.balance = get_amounts(lines[1])[1]
            self.sender = None
        elif re.search(r'PRZELEW WALUTOWY PRZYCHODZĄCY', lines[1]):
            self.kind = 'PRZELEW WALUTOWY PRZYCHODZĄCY'
            self.amount = get_amounts(lines[1])[0]
            self.balance = get_amounts(lines[1])[1]
            self.sender = None
        elif re.search(r'UZNANIE NATYCH. TRANSAKCJA WALUT.', lines[1]):
            self.kind = 'TRANSAKCJA WALUTOWA'
            self.amount = get_amounts(lines[1])[0]
            self.balance = get_amounts(lines[1])[1]
            self.sender = None
        else:
            self.kind = lines[1][10:]
            self.amount = get_amounts(lines[-1])[0]
            self.balance = get_amounts(lines[-1])[1]
            self.sender = lines[2] if len(lines) > 2 else None

    def __str__(self):
        return f'{self.amount} - from: "{self.sender}"\n\t{self.lines}'


def extract_transactions(text_lines):
    LINE_DENY_LIST = [
        r'księgowaniaOpis operacji  Kwota Saldo po operacji',
        r'.*Data operacji.*',
        r'xxx',
        r'Środki zgromadzone na rachunku.*',
        r'Niniejszy dokument sporządzono na podstawie.*',
        r'Nie wymaga podpisu ani stempla.',
        r'W przypadku wystąpienia niezgodności.*',
        r'kontakt z mLinią.*',
        r'[0-9]+/[0-9]+',
        r'',
        r'mBank S.A. ul. Prosta 18.*',
        r'.*posiadający numer identyfikacji podatkowej NIP: 526-021-50-88.*',
        r'Saldo końcowe:.*'
    ]

    # clear lines out of noise
    lines_without_prefix = text_lines[text_lines.index('księgowaniaOpis operacji  Kwota Saldo po operacji') + 1:]
    cleared_lines = [line for line in lines_without_prefix if
                     not any([re.fullmatch(pattern, line) for pattern in LINE_DENY_LIST])]

    # extract transactions
    operation = None
    operations = []
    for line in cleared_lines:
        if is_date(line):
            operation = [line]
            operations.append(operation)
        else:
            operation.append(line)
    transactions = []
    failed = []
    for o in operations:
        try:
            transactions.append(Transaction(o))
        except:
            logging.exception(f'failed to parse operation: ${o}')
            failed.append(' '.join(o))
    return (transactions, failed)


def fetch_property_transactions(lines):
    (transactions, failed) = extract_transactions(lines)
    failed_property_operations = [o for o in failed if is_property_operation(o)]
    if failed_property_operations:
        raise RuntimeError(f'Failed to parse property operations ${failed_property_operations}')
    return extract_property_transactions(transactions)


def extract_property_transactions(transactions):
    return [t for t in transactions if t.kind in INCOMMING_OPERATION_TYPES
            and any([re.search(pattern, t.sender) for pattern in RENTERS])]


def is_property_operation(operation):
    return any([re.search(pattern, operation) for pattern in RENTERS]) and \
           any([re.search(pattern, operation) for pattern in INCOMMING_OPERATION_TYPES])


def action(text):
    return {
        "action": {
            "navigations": [
                {
                    "pushCard": {
                        "header": {
                            "title": "mBank rent tax calculator"
                        },
                        "sections": [
                            {
                                "widgets": [
                                    {
                                        "textParagraph": {
                                            "text": text
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
def loadHomePage(request):
    return action("Please open email entitled 'mBank - elektroniczne zestawienie operacji za {miesiac} {rok}'.")


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

    # error if email does not have the mbank statement
    subject = [h['value'] for h in message['payload']['headers'] if h['name'] == 'Subject'][0]
    if not re.match(r'mBank - elektroniczne zestawienie operacji.*', subject):
        return action("Please open email entitled 'mBank - elektroniczne zestawienie operacji za {miesiac} {rok}'.")

    # get bank statement attachment ID
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
    lines = decrypt_pdf_to_text(stream_data, passwords[email])

    # fetch transactions
    property_transactions = fetch_property_transactions(lines)

    # calculate income and tax
    income = sum([t.amount for t in property_transactions])
    tax = (income * Decimal(0.085)).quantize(Decimal('0.01'))
    return action('\n\n'.join([str(t) for t in property_transactions] + [f'{income} (Income) * 8.5% (Tax) = {tax}']))

# For testing the addon locally, provide the password before execution
if __name__ == '__main__':
    with open('password.txt', 'rb') as password:
        with open('encrypted.pdf', 'rb') as f:
            lines = decrypt_pdf_to_text(f, password.readlines()[0])
    property_transactions = fetch_property_transactions(lines)
    income = sum([t.amount for t in property_transactions])
    tax = (income * Decimal(0.085)).quantize(Decimal('0.01'))
    for t in property_transactions:
        print(str(t))
    print(f'{income} (Income) * 8.5% (Tax) = {tax}')
