# Use this code to make an SMS PIN verification request and then report the code using the Verification API and Python SDK.
from sinch import SinchClient
from sinch.domains.verification.exceptions import VerificationException
from sinch.domains.verification.models import VerificationIdentity

sinch_client = SinchClient(application_key="YOUR_application_key", application_secret="YOUR_application_secret")


def start_verification(phone_number):
    response = sinch_client.verification.verifications.start_sms(
        identity=VerificationIdentity(type="number", endpoint=phone_number)
    )
    return response


def report_code(id, code):
    response = sinch_client.verification.verifications.report_by_id(id=id, verification_report_request={"code": code})
    return response


def main():
    print("Enter a phone number to start verification or enter CTRL+C to quit.")
    phone_number = input("Phone number: ")
    try:
        verification_response = start_verification(phone_number)
    except VerificationException:
        print("Invalid number? Check traceback information:")
        raise

    print("Enter a verification code or enter CTRL+C to quit.")
    verification_code = input("Verification code: ")
    try:
        report_verification_code_response = report_code(verification_response.id, verification_code)
    except VerificationException:
        print("Invalid number? Check traceback information:")
        raise

    print(report_verification_code_response)


if __name__ == "__main__":
    main()
