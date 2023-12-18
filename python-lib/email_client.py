from collections import namedtuple
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def SmtpConfig():
    # str, int, bool, bool, str, str
    return namedtuple("SmtpConfig", "smtp_host, smtp_port, smtp_use_tls, smtp_use_auth, smtp_user, smtp_pass",
                      defaults=[None, 25, False, False, None, None]
                      )


class SmtpEmailClient:
    """ Client for sending email - direct SMTP implementation """

    def __init__(self, smtp_config):
        self.smtp = smtplib.SMTP(smtp_config.smtp_host, port=smtp_config.smtp_port)

        # Use TLS if set
        if smtp_config.smtp_use_tls:
            self.smtp.starttls()

        # Use credentials if set
        if smtp_config.smtp_use_auth:
            self.smtp.login(str(smtp_config.smtp_user), str(smtp_config.smtp_pass))

    def send_email(self, sender, recipient, email_text, email_subject, mime_parts, body_encoding):
        """
        :param sender: sender email, str
        :param recipient: recipient email, str
        :param email_text: str
        :param email_subject: str
        :param mime_parts: attachments as list of MIMEApplication
        :param body_encoding: e.g. 'utf-8', 'us-ascii', 'latin-1'
        """
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = email_subject
        # Leave some space for proper displaying of the attachment
        msg.attach(MIMEText(email_text + '\n\n', 'plain', body_encoding))
        for a in mime_parts:
            msg.attach(a)
        self.smtp.sendmail(sender, [recipient], msg.as_string())

    def quit(self):
        """ Do any disconneciton needed"""
        self.smtp.quit()
