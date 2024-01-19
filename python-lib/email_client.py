import dataiku
import logging
from abc import ABC, abstractmethod
from collections import namedtuple
import smtplib
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart


def SmtpConfig():
    # str, int, bool, bool, str, str
    return namedtuple("SmtpConfig", "smtp_host, smtp_port, smtp_use_tls, smtp_use_auth, smtp_user, smtp_pass",
                      defaults=[None, 25, False, False, None, None]
                      )


def AttachmentFile():
    """ Format for an attachment file with the info broken down nicely for both the client classes """
    # str, str, str ('application' or 'text'), bytes
    return namedtuple("SmtpConfig", "file_name, mime_type, mime_subtype, data",
                      defaults=[None, "application", None, None]
                      )


class AbstractMessageClient(ABC):
    def __init__(self, plain_text):
        self.plain_text = plain_text

    def send_email(self, sender, recipient, email_body, email_subject, attachment_files):
        if self.plain_text:
            email_body_to_send = email_body + '\n\n'

        self.send_email_impl(sender, recipient, email_body_to_send, email_subject, attachment_files)

    @abstractmethod
    def send_email_impl(self,  sender, recipient, email_body, email_subject, attachment_files):
        pass


class ChannelClient(AbstractMessageClient):
    def __init__(self, plain_text, channel_id):
        super().__init__(plain_text)
        self.dss_client = dataiku.api_client()
        self.project_id = dataiku.default_project_key()
        self.channel = self.dss_client.get_integration_channel(channel_id)

    def send_email_impl(self, sender, recipient, email_body, email_subject, attachment_files):
        files = [(a.file_name, a.data, f"{a.mime_type}/{a.mime_subtype}") for a in attachment_files]
        self.channel.send(self.project_id, sender, email_subject, email_body, [recipient], attachments=files, plain_text=not self.plain_text)

    def quit(self):
        pass


class SmtpEmailClient(AbstractMessageClient):
    """ Client for sending email - direct SMTP implementation """

    def __init__(self, plain_text, smtp_config):
        super().__init__(plain_text)
        self.smtp = smtplib.SMTP(smtp_config.smtp_host, port=smtp_config.smtp_port)

        # Use TLS if set
        if smtp_config.smtp_use_tls:
            self.smtp.starttls()

        # Use credentials if set
        if smtp_config.smtp_use_auth:
            self.smtp.login(str(smtp_config.smtp_user), str(smtp_config.smtp_pass))

    def send_email_impl(self, sender, recipient, email_body, email_subject, attachment_files):
        """
        :param sender: sender email, str
        :param recipient: recipient email, str
        :param email_body: body of either plain text or html, str
        :param email_subject: str
        :param attachment_files: attachments as list of  AttachmentFile
        """
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = email_subject
        body_encoding = "utf-8"

        msg.attach(MIMEText(email_body + '</b></b>', 'plain' if self.plain_text else 'html', body_encoding))
        for attachment_file in attachment_files:
            if attachment_file.mime_type == "application":
                mime_app = MIMEApplication(attachment_file.data, _subtype=attachment_file.mime_subtype)
            elif attachment_file.mime_type == "text":
                mime_app = MIMEText(attachment_file.data, _subtype=attachment_file.mime_subtype, _charset="utf-8")
            else:
                raise Exception(f'Cannot handle mime type {attachment_file.mime_type}')
            mime_app.add_header("Content-Disposition", 'attachment', filename=attachment_file.file_name)
            msg.attach(mime_app)
        self.smtp.sendmail(sender, [recipient], msg.as_string())

    def quit(self):
        """ Do any disconnection needed"""
        self.smtp.quit()
