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

            # NOTE: Never log context['code'] or context['key'] -- these are live
            # authentication secrets (a verification code is effectively a login).

            # Call the parent method to actually send the email
            try:
                result = super().send_mail(template_prefix, email, context)
                logfire.info("Email sent successfully", email=email)
                return result
            except Exception as e:
                # Log, then re-raise: allauth must not proceed as if delivery
                # succeeded, or the user is sent to enter a code that never arrived.
                logfire.error("Email sending failed", email=email, error=str(e))
                raise

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """Override to add specific logging for confirmation emails."""
        with logfire.span(
            "send_confirmation_email",
            email=emailconfirmation.email_address.email,
            is_signup=signup,
        ):
            # NOTE: Do not log emailconfirmation.key -- it is the confirmation
            # secret and would leak into observability logs.
            logfire.info(
                "Sending confirmation email",
                email=emailconfirmation.email_address.email,
                is_signup=signup,
            )

            # Call the parent method
            try:
                result = super().send_confirmation_mail(request, emailconfirmation, signup)
                logfire.info("Confirmation email sent successfully")
                return result
            except Exception as e:
                # Re-raise so allauth surfaces the failure instead of silently
                # treating the confirmation email as sent.
                logfire.error("Confirmation email sending failed", error=str(e))
                raise
