from typing import Dict, Optional

from payment_agent_discovery import PaymentAgentDiscovery
from payment_interface import PaymentInterface # For type hinting, though discovery handles instance types

class PaymentProcessor:
    """
    Processes payments by delegating tasks to registered payment agents.
    """

    def __init__(self, agent_discovery: PaymentAgentDiscovery):
        """
        Initializes the PaymentProcessor with a PaymentAgentDiscovery instance.

        Args:
            agent_discovery: An instance of PaymentAgentDiscovery that holds
                             the registered payment agents.
        """
        if not isinstance(agent_discovery, PaymentAgentDiscovery):
            raise TypeError("agent_discovery must be an instance of PaymentAgentDiscovery")
        self.agent_discovery = agent_discovery

    def initiate_payment(self, agent_name: str, amount: float, currency: str, payment_details: Dict) -> Dict:
        """
        Initiates a payment through the specified payment agent.

        Args:
            agent_name: The name of the payment agent to use (e.g., "stripe", "l402").
            amount: The amount to be paid.
            currency: The currency of the payment (e.g., "USD", "EUR").
            payment_details: A dictionary containing provider-specific payment details.

        Returns:
            A dictionary containing the payment status and any provider-specific response,
            or an error response if the agent is not found.
        """
        agent: Optional[PaymentInterface] = self.agent_discovery.get_agent(agent_name)
        if not agent:
            return {'status': 'error', 'message': f"Payment agent '{agent_name}' not found."}

        try:
            return agent.initiate_payment(amount=amount, currency=currency, payment_details=payment_details)
        except Exception as e: # pylint: disable=broad-except
            # Log the exception e
            return {'status': 'error', 'message': f"Error during '{agent_name}' payment initiation: {str(e)}"}

    def check_payment_status(self, agent_name: str, payment_id: str) -> Dict:
        """
        Checks the status of a payment using the specified payment agent.

        Args:
            agent_name: The name of the payment agent.
            payment_id: The unique identifier of the payment.

        Returns:
            A dictionary containing the payment status and details,
            or an error response if the agent is not found.
        """
        agent: Optional[PaymentInterface] = self.agent_discovery.get_agent(agent_name)
        if not agent:
            return {'status': 'error', 'message': f"Payment agent '{agent_name}' not found."}

        try:
            return agent.check_payment_status(payment_id=payment_id)
        except Exception as e: # pylint: disable=broad-except
            # Log the exception e
            return {'status': 'error', 'message': f"Error during '{agent_name}' payment status check: {str(e)}"}


    def process_refund(self, agent_name: str, payment_id: str, amount: Optional[float] = None) -> Dict:
        """
        Processes a refund for a given payment ID using the specified payment agent.

        Args:
            agent_name: The name of the payment agent.
            payment_id: The unique identifier of the payment to be refunded.
            amount: The amount to be refunded. If None, a full refund is implied.

        Returns:
            A dictionary confirming the refund status,
            or an error response if the agent is not found.
        """
        agent: Optional[PaymentInterface] = self.agent_discovery.get_agent(agent_name)
        if not agent:
            return {'status': 'error', 'message': f"Payment agent '{agent_name}' not found."}

        try:
            return agent.process_refund(payment_id=payment_id, amount=amount)
        except Exception as e: # pylint: disable=broad-except
            # Log the exception e
            return {'status': 'error', 'message': f"Error during '{agent_name}' refund processing: {str(e)}"}

if __name__ == "__main__":
    # Setup discovery and register agents
    # Ensure necessary adapter files are available in the Python path
    try:
        from payment_agent_discovery import PaymentAgentDiscovery
        # Dynamically try to import adapters to make example more robust
        # to environment where not all adapters might be present
        L402Adapter = None
        StripeAdapter = None
        PaypalAdapter = None
        CoinbaseAdapter = None
        PoofAdapter = None

        try:
            from l402_adapter import L402Adapter
        except ImportError:
            print("Warning: L402Adapter not found for example.")
        try:
            from stripe_adapter import StripeAdapter
        except ImportError:
            print("Warning: StripeAdapter not found for example.")
        try:
            from paypal_adapter import PaypalAdapter
        except ImportError:
            print("Warning: PaypalAdapter not found for example.")
        # Add other adapters if they are part of a more comprehensive test

        discovery = PaymentAgentDiscovery()

        # Minimal registration for example
        if L402Adapter:
            try:
                l402_agent = L402Adapter() # Assumes no init args for L402Adapter mock
                discovery.register_agent("l402", l402_agent)
            except Exception as e:
                 print(f"Could not init/register L402Adapter: {e}")
        if StripeAdapter:
            try:
                stripe_agent = StripeAdapter(api_key="sk_mock_EXAMPLE_KEY_PROCESSOR")
                discovery.register_agent("stripe", stripe_agent)
            except Exception as e:
                 print(f"Could not init/register StripeAdapter: {e}")
        if PaypalAdapter:
            try:
                paypal_agent = PaypalAdapter(client_id="paypal_mock_id_PROC", client_secret="paypal_mock_secret_PROC")
                discovery.register_agent("paypal", paypal_agent)
            except Exception as e:
                print(f"Could not init/register PaypalAdapter: {e}")


        if not discovery.list_agents():
            print("No payment agents were registered. Example will be limited.")
            # Optionally, exit or skip tests if no agents are available
            # exit()

        processor = PaymentProcessor(agent_discovery=discovery)

        # 1. Initiate Payment
        print("\n--- Initiating Payments ---")
        if "l402" in discovery.list_agents():
            l402_payment_details = {'offer_id': 'offer_789', 'payment_request_url': 'https://example.com/l402/payreq'}
            l402_init_response = processor.initiate_payment("l402", 7.0, "SAT", l402_payment_details) # Assuming SAT for L402
            print(f"L402 Initiate Payment Response: {l402_init_response}")
            l402_payment_id = l402_init_response.get('payment_id') if l402_init_response.get('status') not in ['error', 'failed'] else None
        else:
            l402_payment_id = None
            print("L402 agent not registered, skipping L402 initiation test.")

        if "stripe" in discovery.list_agents():
            stripe_payment_details = {'customer_id': 'cus_abc', 'payment_method_id': 'pm_def', 'description': 'Test Stripe Payment via Processor'}
            stripe_init_response = processor.initiate_payment("stripe", 15.0, "EUR", stripe_payment_details)
            print(f"Stripe Initiate Payment Response: {stripe_init_response}")
            stripe_payment_id = stripe_init_response.get('payment_id') if stripe_init_response.get('status') not in ['error', 'failed'] else None
        else:
            stripe_payment_id = None
            print("Stripe agent not registered, skipping Stripe initiation test.")

        if "paypal" in discovery.list_agents():
            paypal_payment_details = {
                'intent': 'CAPTURE',
                'purchase_units': [{'amount': {'currency_code': 'USD', 'value': '20.00'}}],
                'application_context': {'return_url': 'https://example.com/paypal_return', 'cancel_url': 'https://example.com/paypal_cancel'}
            }
            paypal_init_response = processor.initiate_payment("paypal", 20.0, "USD", paypal_payment_details)
            print(f"Paypal Initiate Payment Response: {paypal_init_response}")
            paypal_payment_id = paypal_init_response.get('payment_id') if paypal_init_response.get('status') not in ['error', 'failed'] else None
        else:
            paypal_payment_id = None
            print("Paypal agent not registered, skipping Paypal initiation test.")


        # Attempt with a non-existent agent
        non_existent_init_response = processor.initiate_payment("unknown_agent", 1.0, "JPY", {})
        print(f"Unknown Agent Initiate Payment Response: {non_existent_init_response}")

        # 2. Check Payment Status
        print("\n--- Checking Payment Statuses ---")
        if l402_payment_id:
            l402_status_response = processor.check_payment_status("l402", l402_payment_id)
            print(f"L402 Check Status Response: {l402_status_response}")

        if stripe_payment_id:
            stripe_status_response = processor.check_payment_status("stripe", stripe_payment_id)
            print(f"Stripe Check Status Response: {stripe_status_response}")

        if paypal_payment_id:
            paypal_status_response = processor.check_payment_status("paypal", paypal_payment_id)
            print(f"Paypal Check Status Response: {paypal_status_response}")


        # 3. Process Refund
        print("\n--- Processing Refunds ---")
        if stripe_payment_id:
            # Assuming Stripe payment was 'succeeded'/'paid' and can be refunded
            # (mock adapter usually returns this, a real one might require status check)
            stripe_refund_response = processor.process_refund("stripe", stripe_payment_id, 7.0)
            print(f"Stripe Process Refund Response: {stripe_refund_response}")

        if paypal_payment_id:
            paypal_refund_response = processor.process_refund("paypal", paypal_payment_id, 10.00)
            print(f"Paypal Process Refund Response: {paypal_refund_response}")

        # Refund for an agent not used in init payment (but registered)
        if "l402" in discovery.list_agents():
             l402_refund_on_unknown_id = processor.process_refund("l402", "some_l402_id_not_from_init", 2.0)
             print(f"L402 Refund on unknown ID: {l402_refund_on_unknown_id}")


    except ImportError as e:
        print(f"Error during example: Could not import a required class. {e}")
        print("Please ensure all adapter files and payment_agent_discovery.py are in the PYTHONPATH.")
    except TypeError as e:
        print(f"Type error during example setup: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during example execution: {e}")
