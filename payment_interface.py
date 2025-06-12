from abc import ABC, abstractmethod
from typing import Dict, Optional

class PaymentInterface(ABC):
    """
    An abstract base class for payment processing.
    """

    @abstractmethod
    def initiate_payment(self, amount: float, currency: str, payment_details: Dict) -> Dict:
        """
        Initiates a payment.

        Args:
            amount: The amount to be paid.
            currency: The currency of the payment (e.g., "USD", "EUR").
            payment_details: A dictionary containing provider-specific payment details.
                             Examples: L402 might need offer details, while Stripe
                             might need a customer ID or payment method ID.

        Returns:
            A dictionary containing the payment status and any provider-specific response.
            Example: {'status': 'success'/'pending'/'failed', 'provider_response': {...}}
        """
        pass

    @abstractmethod
    def check_payment_status(self, payment_id: str) -> Dict:
        """
        Checks the status of a payment.

        Args:
            payment_id: The unique identifier of the payment.

        Returns:
            A dictionary containing the payment status and details.
            Example: {'status': 'paid'/'pending'/'failed'/'refunded', 'details': {...}}
        """
        pass

    @abstractmethod
    def process_refund(self, payment_id: str, amount: Optional[float] = None) -> Dict:
        """
        Processes a refund for a given payment ID.

        Args:
            payment_id: The unique identifier of the payment to be refunded.
            amount: The amount to be refunded. If None, a full refund is implied.

        Returns:
            A dictionary confirming the refund status.
            Example: {'status': 'success'/'failed', 'refund_id': '...', 'provider_response': {...}}
        """
        pass
