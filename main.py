import functions_framework
from PyPDF2 import PdfFileReader, PdfFileWriter


@functions_framework.http
def hello(request):
    return "Hello world!"


def decrypt_pdf(input_path, output_path, password):
    with open(input_path, 'rb') as input_file, \
            open(output_path, 'wb') as output_file:
        reader = PdfFileReader(input_file)
        reader.decrypt(password)
        writer = PdfFileWriter()
        for i in range(reader.getNumPages()):
            writer.addPage(reader.getPage(i))
        writer.write(output_file)


if __name__ == '__main__':
    decrypt_pdf('encrypted.pdf', 'decrypted.pdf', '92010308593')