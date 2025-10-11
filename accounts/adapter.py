import logging
from allauth.account.adapter import DefaultAccountAdapter

logger = logging.getLogger(__name__)


class AccountAdapter(DefaultAccountAdapter):
    """Custom account adapter to add logging for email operations."""

    def send_mail(self, template_prefix, email, context):
        """Override to add logging when emails are sent."""
        logger.info("=" * 80)
        logger.info("SENDING EMAIL via django-allauth")
        logger.info(f"Template prefix: {template_prefix}")
        logger.info(f"To: {email}")
        logger.info(f"Context keys: {list(context.keys())}")

        # Log the actual email content for debugging
        if 'code' in context:
            logger.info(f"Verification code in context: {context['code']}")
        if 'key' in context:
            logger.info(f"Verification key in context: {context['key']}")

        logger.info("=" * 80)

        # Call the parent method to actually send the email
        result = super().send_mail(template_prefix, email, context)

        logger.info(f"Email send completed for {email}")
        return result

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """Override to add specific logging for confirmation emails."""
        logger.info("=" * 80)
        logger.info("SENDING CONFIRMATION EMAIL")
        logger.info(f"Email: {emailconfirmation.email_address.email}")
        logger.info(f"Is signup: {signup}")
        logger.info(f"Key: {emailconfirmation.key}")
        logger.info("=" * 80)

        # Call the parent method
        result = super().send_confirmation_mail(request, emailconfirmation, signup)

        logger.info("Confirmation email send completed")
        return result
