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
    # str, str, str (application or text), bytes
    return namedtuple("SmtpConfig", "file_name, mime_type, mime_subtype, data",
                      defaults=[None, "application", None, None]
                      )
# class ChannelClient:
#     def __init__(self, project_id, send_html=True):
#
#
#     def send_email(self, sender, recipient, email_body, email_subject, attachment_files):
#
#     def quit(self):
#         pass


class SmtpEmailClient:
    """ Client for sending email - direct SMTP implementation """

    def __init__(self, smtp_config, send_html=False):
        self.smtp = smtplib.SMTP(smtp_config.smtp_host, port=smtp_config.smtp_port)
        self.send_html = send_html
        # Use TLS if set
        if smtp_config.smtp_use_tls:
            self.smtp.starttls()

        # Use credentials if set
        if smtp_config.smtp_use_auth:
            self.smtp.login(str(smtp_config.smtp_user), str(smtp_config.smtp_pass))

    def send_email(self, sender, recipient, email_body, email_subject, attachment_files):
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
        # Attach email body in appropriate format, leaving some space for proper displaying of the attachments
        if self.send_html:
            msg.attach(MIMEText(email_body + '</b></b>', 'html', body_encoding))
        else:
            msg.attach(MIMEText(email_body + '\n\n', 'plain', body_encoding))

        for attachment_file in attachment_files:
            if attachment_file.mime_type == "application":
                mime_app = MIMEApplication(attachment_file.data, _subtype=attachment_file.mime_subtype)
            else:
                mime_app = MIMEText(attachment_file.data, _subtype=attachment_file.mime_subtype, _charset="utf-8")
            mime_app.add_header("Content-Disposition", 'attachment', filename=attachment_file.file_name)
            msg.attach(mime_app)
        self.smtp.sendmail(sender, [recipient], msg.as_string())

    def quit(self):
        """ Do any disconnection needed"""
        self.smtp.quit()
