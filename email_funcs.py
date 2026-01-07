from pathlib import Path
import mimetypes
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.message import EmailMessage


def send_email(sender, password, recipients: list, subject, body, attachments: list = None):
    message = EmailMessage()
    message['From'] = sender
    message['Subject'] = subject
    message.set_content(body)

    # Add attachments if provided
    if attachments:
        for file_path in attachments:
            file_path = Path(file_path)

            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = "application/octet-stream"

            maintype, subtype = mime_type.split("/", 1)

            with open(file_path, "rb") as f:
                message.add_attachment(
                    f.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=file_path.name
                )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp_server:
        smtp_server.login(sender, password)
        for recipient in recipients:
            smtp_server.sendmail(sender, recipient, message.as_string())



def send_emails(subject, body, recipients, sender_email, sender_password):
    """
    Send an email to multiple recipients separately.

    Parameters:
    subject (str): Subject of the email.
    body (str): Body of the email.
    recipients (list): List of recipient email addresses.
    sender_email (str): Sender's email address.
    sender_password (str): Sender's email password.
    smtp_server (str): SMTP server address.
    smtp_port (int): SMTP server port.
    """
    
    # Set up the server
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, sender_password)
    
    # Create the email
    for recipient in recipients:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send the email
        server.sendmail(sender_email, recipient, msg.as_string())
        # print(f"Email sent to {recipient}")
    
    # Quit the server
    server.quit()




def send_email_with_table(subject, sender, recipient, smtp_server, smtp_port, smtp_user, smtp_password):
    # Create the email message
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    # HTML content with a table
    html_content = """
    <html>
        <body>
            <h1>Your HTML Table</h1>
            <table border="1">
                <tr>
                    <th>Header 1</th>
                    <th>Header 2</th>
                </tr>
                <tr>
                    <td>Row 1 Col 1</td>
                    <td>Row 1 Col 2</td>
                </tr>
                <tr>
                    <td>Row 2 Col 1</td>
                    <td>Row 2 Col 2</td>
                </tr>
            </table>
        </body>
    </html>
    """
    
    msg.add_alternative(html_content, subtype='html')

    # Send the email
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(smtp_user, smtp_password)
        server.send_message(msg)