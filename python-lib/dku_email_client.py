import dataiku
import logging
from abc import ABC, abstractmethod
import smtplib
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

class SmtpConfig:
    """
    SMTP config for sending to an SMTP connection configured by the users
    :param smtp_host: str, smtp host eg. sandbox.smtp.mailtrap.io
    :param smtp_port: int, smtp port
    :param smtp_use_tls: bool, whether to use tls
    :param smtp_use_auth: bool, whether to have authentication and provide username and password
    :param smtp_user: str, username of smtp server auth
    :param smtp_pass: str, password for smtp server auth
    """
    def __init__(self, smtp_host, smtp_port, smtp_use_tls, smtp_use_auth, smtp_user, smtp_pass):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_use_tls = smtp_use_tls
        self.smtp_use_auth = smtp_use_auth
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass


class AttachmentFile:
    """
    :param file_name: str, name of file including extension
    :param mime_type: main maime type str before / ('application' or 'text')
    :param mime_subtype: str -mime type bit after /, e.g. csv in text/csv
    :param data: bytes, actual data of attachment
    """
    def __init__(self, file_name, mime_type, mime_subtype, data):
        self.file_name = file_name
        self.mime_type = mime_type
        self.mime_subtype = mime_subtype
        self.data = data


class AbstractMessageClient(ABC):
    def __init__(self, plain_text):
        self.plain_text = plain_text

    @abstractmethod
    def send_email(self,  sender, recipiens, email_body, email_subject, attachment_files):
        """
        :param sender: sender email, str - is ignored if a sender configured for the channel
        :param recipients: recipients email, Seq
        :param email_subject: str
        :param email_body: body of either plain text or html, str
        :param attachment_files:attachments as list of  AttachmentFile
        """
        pass

    def login(self):
        """
        Perform any login or other initialisation if needed
        """
        pass

    def quit(self):
        """
        Perform any logout or resource cleanup if needed
        """
        pass


class ChannelClient(AbstractMessageClient):
    """ Impl using DSS channels that requires DSS 12.6 or later """
    def __init__(self, plain_text, channel_id):
        super().__init__(plain_text)

        dss_api_client = dataiku.api_client()
        self.project_id = dataiku.default_project_key()
        self.channel = dss_api_client.get_messaging_channel(channel_id)

        logging.info(f"Configured channel messaging client with channel {channel_id} - type: {self.channel.type}, "
                     f"sender: {self.channel.sender}, plain_text? {self.plain_text}")

    def send_email(self, sender, recipients, email_subject, email_body, attachment_files):

        files = [(a.file_name, a.data, f"{a.mime_type}/{a.mime_subtype}") for a in attachment_files]

        sender_to_use = None if self.channel.sender else sender
        self.channel.send(self.project_id, recipients, email_subject, email_body, attachments=files, plain_text=self.plain_text, sender=sender_to_use)


class SmtpEmailClient(AbstractMessageClient):
    """ Client for sending email - direct SMTP implementation
    :param plain_text: bool, wther the email client will interpret and send the emails body as plain text
    :param smtp_config: SmtpConfig, stmp config to use
    """

    def __init__(self, plain_text, smtp_config):
        super().__init__(plain_text)
        self.smtp = smtplib.SMTP(smtp_config.smtp_host, port=smtp_config.smtp_port)
        self.smtp_config = smtp_config

        logging.info(f"Configured an STMP mail client with host: {smtp_config.smtp_host}, port: {smtp_config.smtp_port}, "
                     f"tls? {smtp_config.smtp_use_tls}, auth? {smtp_config.smtp_use_auth}, plain_text? {self.plain_text}")


    def login(self):
        # Use TLS if set
        if self.smtp_config.smtp_use_tls:
            self.smtp.starttls()
            logging.info("SMTP TLS started")
        # Use credentials if set
        if self.smtp_config.smtp_use_auth:
            self.smtp.login(str(self.smtp_config.smtp_user), str(self.smtp_config.smtp_pass))
            logging.info(f"Authenticated against STMP mail client")


    def send_email(self, sender, recipients, email_subject, email_body, attachment_files):
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = email_subject
        body_encoding = "utf-8"
        text_type = 'plain' if self.plain_text else 'html'
        msg.attach(MIMEText(email_body, text_type, body_encoding))
        for attachment_file in attachment_files:
            if attachment_file.mime_type == "application":
                mime_app = MIMEApplication(attachment_file.data, _subtype=attachment_file.mime_subtype)
            elif attachment_file.mime_type == "text":
                mime_app = MIMEText(attachment_file.data, _subtype=attachment_file.mime_subtype, _charset="utf-8")
            else:
                raise Exception(f'Cannot handle mime type {attachment_file.mime_type}')
            mime_app.add_header("Content-Disposition", 'attachment', filename=attachment_file.file_name)
            msg.attach(mime_app)
        self.smtp.sendmail(sender, recipients, msg.as_string())

    def quit(self):
        """ Do any disconnection needed"""
        self.smtp.quit()
