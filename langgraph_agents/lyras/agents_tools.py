
import sys, os
import logging

from langchain_core.tools import tool

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


## logger instance for this module
logger = logging.getLogger(f'langgraph_agents.lyras.tools')


@tool
def send_email_lyfx(flag_user:bool, subject:str, message:str) -> str:
    """
    Sends an email to the lyfX.ai team
    """

    logger.info(f"flag_user currently set as {flag_user}")

    # last line of defense...
    if flag_user:
        logger.info(f"Not sending anything")    # even if forced to come here, we are refusing to send the email
        return ("flag_user was set to True, so no email was sent.")

    # Gmail address and the App Password
    gmail_user = 'a.moreira@lyfx.ai'
    gmail_app_password = os.environ.get("LYFX_EMAIL_KEY", "")  # app password (generated in the gmail account)
    if not gmail_app_password:
        return("No email password available, could not send the email.")
    
    # open the connection to the email server
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(gmail_user, gmail_app_password)

    recipient = "a.moreira@lyfx.ai"
    # Create and send the email
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = 'Andre Moreira <a.moreira@lyfx.ai>'
        msg['Reply-To'] = 'Andre Moreira <a.moreira@lyfx.ai>'
        msg['To'] = recipient
        msg.attach(MIMEText(message, 'plain'))
        server.sendmail(gmail_user, recipient, msg.as_string())
        server.quit()
        return(f"Sent email successfully")
    except Exception as e:
        logger.info(f'Unable to send email: error {e}.')
        server.quit()
        return(f"Unable to send email: error {e}.")
