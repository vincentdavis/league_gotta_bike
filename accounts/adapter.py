import logfire
from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    """Custom account adapter to add logging for email operations."""

    def send_mail(self, template_prefix, email, context):
        """Override to add logging when emails are sent."""
        with logfire.span(
            "send_email_via_allauth",
            template=template_prefix,
            to=email,
        ):
            logfire.info(
                "Sending email via django-allauth",
                template_prefix=template_prefix,
                email=email,
                context_keys=list(context.keys()),
            )

            # Log the actual email content for debugging
            if 'code' in context:
                logfire.info("Email contains verification code", code=context['code'])
            if 'key' in context:
                logfire.info("Email contains verification key", key=context['key'])

            # Call the parent method to actually send the email
            result = super().send_mail(template_prefix, email, context)

            logfire.info("Email sent successfully", email=email)
            return result

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """Override to add specific logging for confirmation emails."""
        with logfire.span(
            "send_confirmation_email",
            email=emailconfirmation.email_address.email,
            is_signup=signup,
        ):
            logfire.info(
                "Sending confirmation email",
                email=emailconfirmation.email_address.email,
                is_signup=signup,
                key=emailconfirmation.key,
            )

            # Call the parent method
            result = super().send_confirmation_mail(request, emailconfirmation, signup)

            logfire.info("Confirmation email sent successfully")
            return result
