from typing import Dict, Optional
import uuid
import datetime

from payment_interface import PaymentInterface

# Placeholder for a potential Coinbase Commerce SDK client
class CoinbaseClientMock:
    def __init__(self, api_key: str):
        self.api_key = api_key
        print(f"CoinbaseClientMock initialized with API key: {api_key[:8]}...")

    def create_charge(self, name: str, description: str, pricing_type: str, local_price: Dict, redirect_url: str, cancel_url: str) -> Dict:
        # Simulate Coinbase Commerce Create Charge API
        charge_code = f"MOCKCB_{uuid.uuid4().hex[:8].upper()}"
        charge_id = f"mock_coinbase_charge_id_{uuid.uuid4()}"
        hosted_url = f"https://commerce.coinbase.com/charges/{charge_code}"

        return {
            'id': charge_id,
            'code': charge_code,
            'hosted_url': hosted_url,
            'name': name,
            'description': description,
            'pricing_type': pricing_type,
            'pricing': {'local': local_price},
            'redirect_url': redirect_url,
            'cancel_url': cancel_url,
            'timeline': [{'status': 'NEW', 'time': datetime.datetime.utcnow().isoformat()}],
            'addresses': { # Mocked crypto addresses
                'bitcoin': f"mock_btc_addr_{uuid.uuid4().hex}",
                'ethereum': f"mock_eth_addr_{uuid.uuid4().hex}",
            }
        }

    def get_charge_status(self, charge_code_or_id: str) -> Dict:
        # Simulate Coinbase Commerce Get Charge API
        now_iso = datetime.datetime.utcnow().isoformat()
        if "fail" in charge_code_or_id:
            return {'code': charge_code_or_id, 'timeline': [{'status': 'EXPIRED', 'time': now_iso}]}
        if "pending" in charge_code_or_id:
             return {'code': charge_code_or_id, 'timeline': [{'status': 'PENDING', 'time': now_iso}]}

        # Simulate a completed charge
        return {
            'code': charge_code_or_id,
            'id': f"mock_charge_id_for_{charge_code_or_id}",
            'timeline': [
                {'status': 'NEW', 'time': (datetime.datetime.utcnow() - datetime.timedelta(minutes=5)).isoformat()},
                {'status': 'PENDING_CONFIRMATIONS', 'time': (datetime.datetime.utcnow() - datetime.timedelta(minutes=2)).isoformat()},
                {'status': 'COMPLETED', 'time': now_iso}
            ],
            'payments': [{'status': 'CONFIRMED', 'value': {'local': {'amount': '10.00', 'currency': 'USD'}}}],
            'pricing': {'local': {'amount': '10.00', 'currency': 'USD'}}
        }

    def initiate_refund(self, charge_id: str, amount_str: Optional[str] = None, reason: Optional[str] = None) -> Dict:
        # Simulate Coinbase refund process (highly simplified)
        refund_id = f"mock_coinbase_refund_{uuid.uuid4()}"
        return {
            'id': refund_id,
            'status': 'success', # Assuming direct success for simulation
            'message': 'Coinbase refund processed (simulated).',
            'charge_id': charge_id,
            'amount_refunded': amount_str if amount_str else 'full_amount_mocked'
        }


class CoinbaseAdapter(PaymentInterface):
    """
    An adapter for processing payments using Coinbase Commerce API (simulated).
    """

    def __init__(self, api_key: str):
        """
        Initializes the CoinbaseAdapter with the API key.

        Args:
            api_key: The Coinbase Commerce API key.
        """
        self.api_key = api_key
        # In a real implementation, use:
        # from coinbase_commerce.client import Client
        # self.coinbase_client = Client(api_key=self.api_key)
        self.coinbase_client = CoinbaseClientMock(api_key)

    def initiate_payment(self, amount: float, currency: str, payment_details: Dict) -> Dict:
        """
        Initiates a Coinbase Commerce payment (simulated).

        Args:
            amount: The amount to be paid.
            currency: The currency of the payment (e.g., "USD", "EUR").
            payment_details: A dictionary containing Coinbase-specific payment details.
                             Example: {'name': 'Product Name',
                                       'description': 'Product Description',
                                       'pricing_type': 'fixed_price',
                                       # local_price can be derived from amount & currency
                                       'redirect_url': 'https://example.com/success',
                                       'cancel_url': 'https://example.com/cancel'}

        Returns:
            A dictionary containing the payment status, payment ID (charge code),
            and provider-specific response including a hosted checkout URL.
            Example: {'status': 'pending_payment',
                      'payment_id': 'MOCKCODE',
                      'provider_response': {'charge_id': '...', 'hosted_url': '...', 'code': '...'}}
        """
        name = payment_details.get('name', 'Unnamed Product')
        description = payment_details.get('description', 'Payment for service/product')
        pricing_type = payment_details.get('pricing_type', 'fixed_price')
        local_price = payment_details.get('local_price', {'amount': f"{amount:.2f}", 'currency': currency.upper()})
        # Ensure top-level amount/currency are used if local_price is not detailed
        if 'amount' not in local_price or 'currency' not in local_price:
            local_price = {'amount': f"{amount:.2f}", 'currency': currency.upper()}
        else: # Standardize from args
            local_price['amount'] = f"{amount:.2f}"
            local_price['currency'] = currency.upper()

        redirect_url = payment_details.get('redirect_url', 'https://example.com/coinbase/success')
        cancel_url = payment_details.get('cancel_url', 'https://example.com/coinbase/cancel')

        try:
            # charge_data = self.coinbase_client.charge.create(...) # Example SDK call
            charge_data = self.coinbase_client.create_charge(
                name=name,
                description=description,
                pricing_type=pricing_type,
                local_price=local_price,
                redirect_url=redirect_url,
                cancel_url=cancel_url
            )

            if charge_data.get('code') and charge_data.get('hosted_url'):
                return {
                    'status': 'pending_payment', # User needs to complete payment via hosted URL
                    'payment_id': charge_data['code'], # Use charge code as the primary payment_id
                    'provider_response': {
                        'charge_id': charge_data['id'],
                        'code': charge_data['code'],
                        'hosted_url': charge_data['hosted_url'],
                        'addresses': charge_data.get('addresses'),
                        'timeline': charge_data.get('timeline')
                    }
                }
            else:
                return {
                    'status': 'failed',
                    'payment_id': None,
                    'provider_response': {'error': 'Failed to create Coinbase charge or missing hosted_url/code.', 'details': charge_data}
                }
        except Exception as e: # pylint: disable=broad-except
            return {
                'status': 'failed',
                'payment_id': None,
                'provider_response': {'error': str(e)}
            }

    def check_payment_status(self, payment_id: str) -> Dict:
        """
        Checks the status of a Coinbase Commerce charge (simulated).

        Args:
            payment_id: The Coinbase Commerce charge code or ID.

        Returns:
            A dictionary containing the payment status and details.
            Example: {'status': 'paid',
                      'details': {'message': 'Payment successfully processed by Coinbase.',
                                  'coinbase_status': 'COMPLETED', ...}}
        """
        try:
            # charge_info = self.coinbase_client.charge.retrieve(payment_id) # Example SDK call
            charge_info = self.coinbase_client.get_charge_status(payment_id)

            timeline = charge_info.get('timeline', [])
            coinbase_status = timeline[-1].get('status') if timeline else 'UNKNOWN'

            # Map Coinbase status to our common statuses
            if coinbase_status == 'COMPLETED':
                status = 'paid'
            elif coinbase_status in ['NEW', 'PENDING_CONFIRMATIONS', 'PENDING']: # PENDING is a general state
                status = 'pending'
            elif coinbase_status == 'UNRESOLVED': # e.g. overpayment/underpayment
                status = 'error' # Or a specific status like 'unresolved'
            elif coinbase_status in ['CANCELED', 'EXPIRED']:
                status = 'failed'
            elif coinbase_status == 'REFUNDED':
                status = 'refunded'
            else: # UNKNOWN or other statuses
                status = 'unknown'

            return {
                'status': status,
                'details': {
                    'message': f'Coinbase charge status: {coinbase_status}',
                    'coinbase_charge_code_or_id': payment_id, # What was passed in
                    'coinbase_charge_id': charge_info.get('id'),
                    'coinbase_charge_code': charge_info.get('code'),
                    'coinbase_status': coinbase_status,
                    'timeline': timeline,
                    'payments': charge_info.get('payments')
                }
            }
        except Exception as e: # pylint: disable=broad-except
            return {
                'status': 'error',
                'details': {'message': f'Error checking Coinbase status: {str(e)}', 'coinbase_charge_code_or_id': payment_id}
            }

    def process_refund(self, payment_id: str, amount: Optional[float] = None) -> Dict:
        """
        Processes a refund for a Coinbase Commerce payment (simulated).

        Coinbase Commerce refunds are often manual. This simulates an idealized scenario.

        Args:
            payment_id: The Coinbase Commerce charge code or ID associated with the payment.
            amount: The amount to be refunded. If None, a full refund is implied.

        Returns:
            A dictionary confirming the refund status.
            Example: {'status': 'succeeded',
                      'refund_id': 'mock_coinbase_refund_id_789',
                      'provider_response': {'message': 'Coinbase refund processed (simulated).'}}
        """
        # For simulation, we assume 'payment_id' is the charge_id needed for refund.
        # Actual Coinbase API might require more specific handling or might not support all refunds programmatically.

        amount_str = f"{amount:.2f}" if amount is not None else None

        try:
            # This is a highly simplified mock. Real refund might involve reasons, etc.
            refund_data = self.coinbase_client.initiate_refund(charge_id=payment_id, amount_str=amount_str)

            if refund_data.get('status') == 'success': # Mock specific status
                return {
                    'status': 'succeeded',
                    'refund_id': refund_data['id'],
                    'provider_response': {
                        'message': refund_data['message'],
                        'coinbase_refund_id': refund_data['id'],
                        'original_charge_id': payment_id,
                        'amount_refunded': refund_data.get('amount_refunded')
                    }
                }
            else:
                # Fallback for other simulated refund statuses
                return {
                    'status': 'failed', # Or 'manual_action_required' depending on how we want to sim
                    'refund_id': refund_data.get('id'),
                    'provider_response': {
                        'message': 'Coinbase refund simulation indicated not fully successful or requires manual action.',
                        'coinbase_refund_id': refund_data.get('id'),
                        'original_charge_id': payment_id,
                        'details': refund_data
                    }
                }
        except Exception as e: # pylint: disable=broad-except
            return {
                'status': 'failed',
                'refund_id': None,
                'provider_response': {'error': str(e), 'original_charge_id': payment_id}
            }
