from typing import Dict, Optional
import uuid

from payment_interface import PaymentInterface

class L402Adapter(PaymentInterface):
    """
    An adapter for processing payments using the L402 protocol (simulated).
    """

    def initiate_payment(self, amount: float, currency: str, payment_details: Dict) -> Dict:
        """
        Initiates an L402 payment (simulated).

        This method simulates the L402 flow, requiring L402-specific details.
        Since there's no live L402 server, it returns a pending response
        with a mock payment ID and includes L402-specific details from payment_details.

        Args:
            amount: The amount to be paid (may not be directly used by L402 in all cases,
                    as the offer dictates the terms).
            currency: The currency of the payment (e.g., "USD", "EUR").
            payment_details: A dictionary containing L402-specific payment details.
                             Expected keys: 'offer_id', 'payment_request_url'.
                             Optional keys: 'payment_context_token'.
                             Example: {'offer_id': 'offer_123',
                                       'payment_request_url': 'https://example.com/l402/payment-request',
                                       'payment_context_token': 'pct_abc123xyz'}

        Returns:
            A dictionary containing the payment status and provider-specific response.
            Example: {'status': 'pending',
                      'payment_id': 'mock_l402_payment_id_xyz',
                      'provider_response': {
                          'payment_request_url': '...',
                          'payment_context_token': '...'
                      }}
        """
        offer_id = payment_details.get('offer_id')
        payment_request_url = payment_details.get('payment_request_url')
        payment_context_token = payment_details.get('payment_context_token')

        if not offer_id or not payment_request_url:
            return {
                'status': 'failed',
                'payment_id': None,
                'provider_response': {
                    'error': 'Missing offer_id or payment_request_url for L402 payment.'
                }
            }

        mock_payment_id = f"mock_l402_payment_{uuid.uuid4()}"

        provider_response = {
            'payment_request_url': payment_request_url,
        }
        if payment_context_token:
            provider_response['payment_context_token'] = payment_context_token

        return {
            'status': 'pending',  # L402 is pending until client completes the payment
            'payment_id': mock_payment_id,
            'provider_response': provider_response
        }

    def check_payment_status(self, payment_id: str) -> Dict:
        """
        Checks the status of an L402 payment (simulated).

        For simulation purposes, this method can return a mock status.
        A simple logic is used: if payment_id contains 'fail', it returns 'failed'.

        Args:
            payment_id: The unique identifier of the L402 payment.

        Returns:
            A dictionary containing the payment status and details.
            Example: {'status': 'paid',
                      'details': {'message': 'Payment successfully processed via L402.'}}
        """
        if "fail" in payment_id:
            return {
                'status': 'failed',
                'details': {'message': 'L402 payment processing failed (simulated).'}
            }

        # For L402, "paid" might mean a valid token/preimage was obtained and verified.
        return {
            'status': 'paid',
            'details': {'message': 'Payment successfully processed via L402 (simulated).'}
        }

    def process_refund(self, payment_id: str, amount: Optional[float] = None) -> Dict:
        """
        Processes a refund for a given L402 payment ID (simulated).

        The L402 protocol does not explicitly define a refund flow.
        This method simulates a refund or indicates it's not supported.

        Args:
            payment_id: The unique identifier of the payment to be refunded.
            amount: The amount to be refunded. If None, a full refund is implied.
                    (This may not be strictly applicable to L402 refunds).

        Returns:
            A dictionary confirming the refund status.
            Example: {'status': 'success',
                      'refund_id': 'mock_l402_refund_id_789',
                      'provider_response': {'message': 'L402 refund processed (simulated).'}}
            Alternatively: {'status': 'not_supported',
                           'provider_response': {
                               'message': 'Refunds are not directly supported by L402 standard.'
                           }}
        """
        # Option 1: Simulate success
        mock_refund_id = f"mock_l402_refund_{uuid.uuid4()}"
        return {
            'status': 'success',
            'refund_id': mock_refund_id,
            'provider_response': {
                'message': 'L402 refund processed (simulated).',
                'original_payment_id': payment_id,
                'refunded_amount': amount if amount is not None else 'full'
            }
        }
        # Option 2: Indicate not supported (choose based on desired simulation behavior)
        # return {
        #     'status': 'not_supported',
        #     'provider_response': {
        #         'message': 'Refunds are not directly supported by the L402 protocol in this adapter.',
        #         'original_payment_id': payment_id
        #     }
        # }
