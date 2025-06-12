from typing import Dict, Optional
import uuid
import datetime

from payment_interface import PaymentInterface

# Placeholder for a Poof.io API client/wrapper
class PoofClientMock:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Poof.io uses "Authorization" header with the key directly
        print(f"PoofClientMock initialized with API key: {api_key[:8]}...")

    def create_checkout(self, name: str, description: str, amount_str: str, currency_code: str, success_url: str, cancel_url: str) -> Dict:
        # Simulate Poof.io Create Checkout API
        checkout_id = f"mock_poof_checkout_{uuid.uuid4()}"
        redirect_url = f"https://www.poof.io/checkout/{checkout_id}" # Example redirect URL

        return {
            'id': checkout_id,
            'url': redirect_url,
            'name': name,
            'description': description,
            'amount': amount_str, # Poof API expects string for amount
            'currency': currency_code.upper(),
            'success_url': success_url,
            'cancel_url': cancel_url,
            'status': 'pending', # Initial status
            'created_at': datetime.datetime.utcnow().isoformat(),
        }

    def get_checkout_or_transaction_status(self, checkout_or_txn_id: str) -> Dict:
        # Simulate Poof.io Get Checkout/Transaction Status API
        now_iso = datetime.datetime.utcnow().isoformat()
        if "fail" in checkout_or_txn_id:
            return {'id': checkout_or_txn_id, 'status': 'failed', 'paid': False, 'created_at': now_iso}
        if "pending" in checkout_or_txn_id:
             return {'id': checkout_or_txn_id, 'status': 'pending', 'paid': False, 'created_at': now_iso}

        # Simulate a paid checkout/transaction
        return {
            'id': checkout_or_txn_id,
            'status': 'paid', # Or 'completed', 'confirmed' depending on Poof's exact terminology
            'paid': True,
            'amount': "10.00", # Mocked
            'currency': "USD",  # Mocked
            'transaction_id': f"mock_poof_txn_for_{checkout_or_txn_id}", # If it's a checkout, it might have a related txn ID
            'created_at': (datetime.datetime.utcnow() - datetime.timedelta(minutes=5)).isoformat(),
            'paid_at': now_iso
        }

    def initiate_refund(self, transaction_id: str, amount_str: Optional[str] = None) -> Dict:
        # Simulate Poof.io Refund process (highly simplified as API docs are not explicit on this)
        refund_id = f"mock_poof_refund_{uuid.uuid4()}"
        return {
            'id': refund_id,
            'status': 'succeeded', # Assuming direct success for simulation
            'message': 'Poof.io refund processed (simulated).',
            'transaction_id': transaction_id,
            'amount_refunded': amount_str if amount_str else 'full_amount_mocked'
        }


class PoofAdapter(PaymentInterface):
    """
    An adapter for processing payments using the Poof.io API (simulated).
    """

    def __init__(self, api_key: str):
        """
        Initializes the PoofAdapter with the Poof.io API key.

        Args:
            api_key: The Poof.io "Authorization key".
        """
        self.api_key = api_key
        # self.poof_client = PoofAPIWrapper(api_key) # If a wrapper exists
        self.poof_client = PoofClientMock(api_key) # Using mock client

    def initiate_payment(self, amount: float, currency: str, payment_details: Dict) -> Dict:
        """
        Initiates a Poof.io payment by creating a Checkout (simulated).

        Args:
            amount: The amount to be paid.
            currency: The currency of the payment (e.g., "USD", "EUR").
            payment_details: A dictionary containing Poof.io-specific payment details.
                             Example: {'checkout_name': 'Service Payment',
                                       'checkout_description': 'Payment for service X',
                                       # amount_str & currency_code can be derived
                                       'success_url': 'https://example.com/success',
                                       'cancel_url': 'https://example.com/cancel'}

        Returns:
            A dictionary containing the payment status, payment ID (checkout ID),
            and provider-specific response including a redirect URL.
            Example: {'status': 'pending_payment',
                      'payment_id': 'mock_poof_checkout_id_123',
                      'provider_response': {'checkout_id': '...', 'redirect_url': '...'}}
        """
        checkout_name = payment_details.get('checkout_name', 'Service/Product Purchase')
        checkout_description = payment_details.get('checkout_description', f'Payment of {amount} {currency}')
        # Poof.io API expects amount as a string
        amount_str = payment_details.get('amount_str', f"{amount:.2f}")
        currency_code = payment_details.get('currency_code', currency.upper())

        # Ensure top-level amount/currency are used if not detailed
        amount_str = f"{amount:.2f}"
        currency_code = currency.upper()

        success_url = payment_details.get('success_url', 'https://example.com/poof/success')
        cancel_url = payment_details.get('cancel_url', 'https://example.com/poof/cancel')

        try:
            # checkout_data = self.poof_client.checkouts.create(...) # Example SDK-like call
            checkout_data = self.poof_client.create_checkout(
                name=checkout_name,
                description=checkout_description,
                amount_str=amount_str,
                currency_code=currency_code,
                success_url=success_url,
                cancel_url=cancel_url
            )

            if checkout_data.get('id') and checkout_data.get('url'):
                return {
                    'status': 'pending_payment', # User needs to complete payment via redirect
                    'payment_id': checkout_data['id'], # Use Poof.io checkout ID as payment_id
                    'provider_response': {
                        'checkout_id': checkout_data['id'],
                        'redirect_url': checkout_data['url'],
                        'status': checkout_data.get('status'),
                        'created_at': checkout_data.get('created_at')
                    }
                }
            else:
                return {
                    'status': 'failed',
                    'payment_id': None,
                    'provider_response': {'error': 'Failed to create Poof.io checkout or missing redirect_url/id.', 'details': checkout_data}
                }
        except Exception as e: # pylint: disable=broad-except
            return {
                'status': 'failed',
                'payment_id': None,
                'provider_response': {'error': str(e)}
            }

    def check_payment_status(self, payment_id: str) -> Dict:
        """
        Checks the status of a Poof.io checkout/transaction (simulated).

        Args:
            payment_id: The Poof.io checkout ID or transaction ID.

        Returns:
            A dictionary containing the payment status and details.
            Example: {'status': 'paid',
                      'details': {'message': 'Payment successfully processed by Poof.io.',
                                  'poof_status': 'paid', ...}}
        """
        try:
            # status_data = self.poof_client.checkouts.get(payment_id) or self.poof_client.transactions.get(payment_id)
            status_data = self.poof_client.get_checkout_or_transaction_status(payment_id)

            poof_status = status_data.get('status')
            is_paid = status_data.get('paid', False) # Poof uses 'paid': true/false

            # Map Poof.io status to our common statuses
            if is_paid or poof_status == 'paid': # 'paid' seems to be a common status for them
                status = 'paid'
            elif poof_status in ['pending', 'processing', 'initiated']: # Example pending statuses
                status = 'pending'
            elif poof_status in ['failed', 'expired', 'cancelled', 'error']:
                status = 'failed'
            else: # UNKNOWN or other statuses
                status = 'unknown'

            return {
                'status': status,
                'details': {
                    'message': f'Poof.io payment status: {poof_status}',
                    'poof_id': payment_id, # What was passed in
                    'poof_status': poof_status,
                    'is_paid': is_paid,
                    'transaction_id': status_data.get('transaction_id'),
                    'paid_at': status_data.get('paid_at'),
                    'created_at': status_data.get('created_at')
                }
            }
        except Exception as e: # pylint: disable=broad-except
            return {
                'status': 'error',
                'details': {'message': f'Error checking Poof.io status: {str(e)}', 'poof_id': payment_id}
            }

    def process_refund(self, payment_id: str, amount: Optional[float] = None) -> Dict:
        """
        Processes a refund for a Poof.io payment (simulated).

        The Poof.io API docs are not explicit about a direct refund API. This simulates an idealized scenario.
        It's assumed `payment_id` might correspond to a transaction ID that can be refunded.

        Args:
            payment_id: The Poof.io transaction ID or checkout ID associated with the payment.
            amount: The amount to be refunded. If None, a full refund is implied.

        Returns:
            A dictionary confirming the refund status.
            Example: {'status': 'succeeded',
                      'refund_id': 'mock_poof_refund_id_789',
                      'provider_response': {'message': 'Poof.io refund processed (simulated).'}}
        """
        # For simulation, we might need a transaction ID. If payment_id is a checkout_id,
        # a real system would first fetch the transaction_id from the checkout.
        # For this mock, we can assume payment_id can be used or derive one.
        mock_transaction_id_for_refund = payment_id
        if not payment_id.startswith("mock_poof_txn_"): # If it looks like a checkout ID
            mock_transaction_id_for_refund = f"mock_poof_txn_for_{payment_id}"


        amount_str = f"{amount:.2f}" if amount is not None else None

        try:
            refund_data = self.poof_client.initiate_refund(
                transaction_id=mock_transaction_id_for_refund,
                amount_str=amount_str
            )

            if refund_data.get('status') == 'succeeded': # Mock specific status
                return {
                    'status': 'succeeded',
                    'refund_id': refund_data['id'],
                    'provider_response': {
                        'message': refund_data['message'],
                        'poof_refund_id': refund_data['id'],
                        'original_transaction_id': mock_transaction_id_for_refund,
                        'amount_refunded': refund_data.get('amount_refunded')
                    }
                }
            else:
                return {
                    'status': 'failed',
                    'refund_id': refund_data.get('id'),
                    'provider_response': {
                        'message': 'Poof.io refund simulation indicated not fully successful.',
                        'poof_refund_id': refund_data.get('id'),
                        'original_transaction_id': mock_transaction_id_for_refund,
                        'details': refund_data
                    }
                }
        except Exception as e: # pylint: disable=broad-except
            return {
                'status': 'failed',
                'refund_id': None,
                'provider_response': {'error': str(e), 'original_transaction_id': mock_transaction_id_for_refund}
            }
