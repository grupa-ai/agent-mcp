import unittest
import sys
import os

# Adjust Python path to include the parent directory (project root)
# This allows finding modules like payment_interface, l402_adapter, etc.
# when running the test file directly from the 'tests' directory.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from payment_interface import PaymentInterface
from l402_adapter import L402Adapter
from stripe_adapter import StripeAdapter
from paypal_adapter import PaypalAdapter
from coinbase_adapter import CoinbaseAdapter
from poof_adapter import PoofAdapter
from mcp_payment_adapter import MCPPaymentAdapter

class TestL402Adapter(unittest.TestCase):
    def setUp(self):
        self.adapter = L402Adapter()

    def test_interface_adherence(self):
        self.assertIsInstance(self.adapter, PaymentInterface)

    def test_initiate_payment(self):
        details = {'offer_id': 'offer_123', 'payment_request_url': 'https://example.com/l402/request'}
        response = self.adapter.initiate_payment(100.0, "SAT", details)
        self.assertEqual(response['status'], 'pending')
        self.assertTrue(response['payment_id'].startswith('mock_l402_payment_'))
        self.assertIn('payment_request_url', response['provider_response'])

    def test_initiate_payment_missing_details(self):
        details = {'offer_id': 'offer_123'} # Missing payment_request_url
        response = self.adapter.initiate_payment(100.0, "SAT", details)
        self.assertEqual(response['status'], 'failed')
        self.assertIn('error', response['provider_response'])

    def test_check_payment_status(self):
        response = self.adapter.check_payment_status("mock_l402_payment_id_123")
        self.assertEqual(response['status'], 'paid')
        self.assertIn('message', response['details'])

    def test_check_payment_status_failure_sim(self):
        response = self.adapter.check_payment_status("mock_l402_payment_id_fail_test")
        self.assertEqual(response['status'], 'failed')

    def test_process_refund(self):
        response = self.adapter.process_refund("mock_l402_payment_id_123", 50.0)
        self.assertEqual(response['status'], 'success') # Current mock is success
        self.assertTrue(response['refund_id'].startswith('mock_l402_refund_'))
        self.assertEqual(response['provider_response']['refunded_amount'], 50.0)


class TestStripeAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = StripeAdapter(api_key="sk_mock_test_EXAMPLEKEY")

    def test_interface_adherence(self):
        self.assertIsInstance(self.adapter, PaymentInterface)

    def test_initiate_payment(self):
        details = {'customer_id': 'cus_xyz', 'payment_method_id': 'pm_abc', 'description': 'Test Stripe Payment'}
        response = self.adapter.initiate_payment(20.00, "USD", details)
        self.assertEqual(response['status'], 'succeeded')
        self.assertTrue(response['payment_id'].startswith('pi_mock_'))
        self.assertIn('stripe_charge_id', response['provider_response'])
        self.assertEqual(response['provider_response']['amount_received'], 2000) # Cents

    def test_check_payment_status(self):
        response = self.adapter.check_payment_status("pi_mock_test")
        self.assertEqual(response['status'], 'paid') # 'paid' is our common status for 'succeeded'
        self.assertEqual(response['details']['stripe_status'], 'succeeded')

    def test_check_payment_status_failure_sim(self):
        response = self.adapter.check_payment_status("pi_mock_fail_test")
        self.assertEqual(response['status'], 'failed')

    def test_process_refund(self):
        response = self.adapter.process_refund("pi_mock_test", 10.00)
        self.assertEqual(response['status'], 'succeeded')
        self.assertTrue(response['refund_id'].startswith('re_mock_'))
        self.assertEqual(response['provider_response']['amount_refunded'], 1000) # Cents

    def test_process_refund_full(self):
        response = self.adapter.process_refund("pi_mock_test_full_refund")
        self.assertEqual(response['status'], 'succeeded')
        self.assertTrue(response['refund_id'].startswith('re_mock_'))
        self.assertEqual(response['provider_response']['amount_refunded'], 'full_amount_mocked')


class TestPaypalAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = PaypalAdapter(client_id="paypal_mock_id", client_secret="paypal_mock_secret")

    def test_interface_adherence(self):
        self.assertIsInstance(self.adapter, PaymentInterface)

    def test_initiate_payment(self):
        details = {
            'intent': 'CAPTURE',
            'application_context': {'return_url': 'https://example.com/return', 'cancel_url': 'https://example.com/cancel'}
        }
        response = self.adapter.initiate_payment(30.00, "EUR", details)
        self.assertEqual(response['status'], 'pending_approval')
        self.assertTrue(response['payment_id'].startswith('mock_paypal_order_'))
        self.assertIn('approval_url', response['provider_response'])
        self.assertEqual(response['provider_response']['paypal_status'], 'CREATED')

    def test_check_payment_status(self):
        response = self.adapter.check_payment_status("mock_paypal_order_test")
        self.assertEqual(response['status'], 'paid') # 'paid' for 'COMPLETED'
        self.assertEqual(response['details']['paypal_status'], 'COMPLETED')

    def test_check_payment_status_failure_sim(self):
        response = self.adapter.check_payment_status("mock_paypal_order_fail_test")
        self.assertEqual(response['status'], 'failed') # for 'VOIDED'

    def test_process_refund(self):
        response = self.adapter.process_refund("mock_paypal_order_test", 15.00)
        self.assertEqual(response['status'], 'succeeded')
        self.assertTrue(response['refund_id'].startswith('mock_paypal_refund_'))
        self.assertEqual(response['provider_response']['amount_refunded'], "15.00")

    def test_process_refund_full(self):
        response = self.adapter.process_refund("mock_paypal_order_test_full")
        self.assertEqual(response['status'], 'succeeded')
        self.assertTrue(response['refund_id'].startswith('mock_paypal_refund_'))
        self.assertEqual(response['provider_response']['amount_refunded'], "full_amount_mocked")


class TestCoinbaseAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = CoinbaseAdapter(api_key="coinbase_mock_key")

    def test_interface_adherence(self):
        self.assertIsInstance(self.adapter, PaymentInterface)

    def test_initiate_payment(self):
        details = {'name': 'Test Product', 'description': 'Coinbase Test', 'redirect_url': 'https://example.com/cb/success'}
        response = self.adapter.initiate_payment(25.00, "USD", details)
        self.assertEqual(response['status'], 'pending_payment')
        self.assertTrue(response['payment_id'].startswith('MOCKCB_'))
        self.assertIn('hosted_url', response['provider_response'])
        self.assertTrue(response['provider_response']['charge_id'].startswith('mock_coinbase_charge_id_'))

    def test_check_payment_status(self):
        response = self.adapter.check_payment_status("MOCKCB_test")
        self.assertEqual(response['status'], 'paid') # for 'COMPLETED'
        self.assertEqual(response['details']['coinbase_status'], 'COMPLETED')

    def test_check_payment_status_pending_sim(self):
        response = self.adapter.check_payment_status("MOCKCB_pending_test")
        self.assertEqual(response['status'], 'pending')

    def test_check_payment_status_failure_sim(self):
        response = self.adapter.check_payment_status("MOCKCB_fail_test")
        self.assertEqual(response['status'], 'failed') # for 'EXPIRED'

    def test_process_refund(self):
        response = self.adapter.process_refund("MOCKCB_test_refund", 10.00)
        self.assertEqual(response['status'], 'succeeded')
        self.assertTrue(response['refund_id'].startswith('mock_coinbase_refund_'))
        self.assertEqual(response['provider_response']['amount_refunded'], "10.00")


class TestPoofAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = PoofAdapter(api_key="poof_mock_auth_key")

    def test_interface_adherence(self):
        self.assertIsInstance(self.adapter, PaymentInterface)

    def test_initiate_payment(self):
        details = {'checkout_name': 'Poof Test Service', 'success_url': 'https://example.com/poof/done'}
        response = self.adapter.initiate_payment(12.50, "CAD", details)
        self.assertEqual(response['status'], 'pending_payment')
        self.assertTrue(response['payment_id'].startswith('mock_poof_checkout_'))
        self.assertIn('redirect_url', response['provider_response'])
        self.assertEqual(response['provider_response']['status'], 'pending')

    def test_check_payment_status(self):
        response = self.adapter.check_payment_status("mock_poof_checkout_test")
        self.assertEqual(response['status'], 'paid')
        self.assertEqual(response['details']['poof_status'], 'paid')
        self.assertTrue(response['details']['is_paid'])

    def test_check_payment_status_pending_sim(self):
        response = self.adapter.check_payment_status("mock_poof_checkout_pending_test")
        self.assertEqual(response['status'], 'pending')

    def test_check_payment_status_failure_sim(self):
        response = self.adapter.check_payment_status("mock_poof_checkout_fail_test")
        self.assertEqual(response['status'], 'failed')

    def test_process_refund(self):
        response = self.adapter.process_refund("mock_poof_checkout_test_refund", 5.00)
        self.assertEqual(response['status'], 'succeeded')
        self.assertTrue(response['refund_id'].startswith('mock_poof_refund_'))
        self.assertEqual(response['provider_response']['amount_refunded'], "5.00")


class TestMCPPaymentAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = MCPPaymentAdapter(mcp_service_url="https://mcp.example.com", mcp_client_credentials={'token': 'mock_mcp_token'})

    def test_interface_adherence(self):
        self.assertIsInstance(self.adapter, PaymentInterface)

    def test_initiate_payment(self):
        details = {'user_id': 'mcp_user_1', 'item_id': 'mcp_item_A'}
        response = self.adapter.initiate_payment(100.00, "XCoin", details) # XCoin as a generic crypto/token
        self.assertEqual(response['status'], 'pending')
        self.assertTrue(response['payment_id'].startswith('mcp_txn_'))
        self.assertIn('mcp_status', response['provider_response'])
        self.assertEqual(response['provider_response']['mcp_status'], 'PENDING_MCP_CONFIRMATION')

    def test_check_payment_status(self):
        response = self.adapter.check_payment_status("mcp_txn_test_status")
        self.assertEqual(response['status'], 'paid')
        self.assertEqual(response['details']['mcp_status'], 'COMPLETED_SUCCESS')

    def test_process_refund(self):
        response = self.adapter.process_refund("mcp_txn_test_for_refund", 40.00)
        self.assertEqual(response['status'], 'succeeded')
        self.assertTrue(response['refund_id'].startswith('mcp_refund_'))
        self.assertEqual(response['provider_response']['mcp_status'], 'REFUND_COMPLETED')

if __name__ == '__main__':
    unittest.main()
