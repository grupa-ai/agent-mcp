import logging
from typing import Dict, List, Optional, Type

from payment_interface import PaymentInterface
# Attempt to import all defined adapters
try:
    from l402_adapter import L402Adapter
    from stripe_adapter import StripeAdapter
    from paypal_adapter import PaypalAdapter
    from coinbase_adapter import CoinbaseAdapter
    from poof_adapter import PoofAdapter
except ImportError as e:
    logging.error(f"Could not import one or more payment adapters: {e}. Some functionality may be limited.")
    # Define dummy classes for missing adapters if needed for type hinting or basic structure
    # This is optional and depends on how strictly one wants to handle missing modules at this stage
    class L402Adapter: pass
    class StripeAdapter: pass
    class PaypalAdapter: pass
    class CoinbaseAdapter: pass
    class PoofAdapter: pass


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymentAgentDiscovery:
    """
    Manages the registration and retrieval of payment agent adapters.
    """

    def __init__(self):
        """
        Initializes the PaymentAgentDiscovery with an empty store for agents.
        """
        self.agents: Dict[str, PaymentInterface] = {}

    def register_agent(self, agent_name: str, agent_instance: PaymentInterface) -> None:
        """
        Registers a payment agent instance.

        Args:
            agent_name: The name to register the agent under (e.g., "stripe", "paypal").
            agent_instance: An instance of a class implementing PaymentInterface.

        Raises:
            TypeError: If agent_instance is not an instance of PaymentInterface.
        """
        if not isinstance(agent_instance, PaymentInterface):
            raise TypeError(f"Agent instance for '{agent_name}' must implement PaymentInterface. "
                            f"Got type: {type(agent_instance).__name__}")

        if agent_name in self.agents:
            logger.warning(f"Agent '{agent_name}' is already registered. Overwriting.")

        self.agents[agent_name] = agent_instance
        logger.info(f"Payment agent '{agent_name}' registered successfully.")

    def get_agent(self, agent_name: str) -> Optional[PaymentInterface]:
        """
        Retrieves a registered payment agent by its name.

        Args:
            agent_name: The name of the agent to retrieve.

        Returns:
            The agent instance if found, otherwise None.
        """
        agent = self.agents.get(agent_name)
        if not agent:
            logger.warning(f"Payment agent '{agent_name}' not found.")
        return agent

    def list_agents(self) -> List[str]:
        """
        Lists the names of all registered payment agents.

        Returns:
            A list of strings, where each string is the name of a registered agent.
        """
        return list(self.agents.keys())

if __name__ == "__main__":
    logger.info("Starting PaymentAgentDiscovery example...")
    discovery = PaymentAgentDiscovery()

    # Mock initialization of adapters.
    # In a real application, these would be configured with actual API keys/credentials.

    # Check if adapter classes were properly imported before trying to instantiate
    adapters_available = {
        "l402": "L402Adapter" in globals(),
        "stripe": "StripeAdapter" in globals(),
        "paypal": "PaypalAdapter" in globals(),
        "coinbase": "CoinbaseAdapter" in globals(),
        "poof": "PoofAdapter" in globals(),
    }

    try:
        if adapters_available["l402"] and hasattr(L402Adapter, '__init__'):
            # L402Adapter in this project does not require args for its __init__
            try:
                l402_agent = L402Adapter()
                discovery.register_agent("l402", l402_agent)
            except Exception as e:
                logger.error(f"Failed to initialize or register L402Adapter: {e}")
        else:
            logger.warning("L402Adapter not available or not correctly defined for example.")

        if adapters_available["stripe"] and hasattr(StripeAdapter, '__init__'):
            try:
                stripe_agent = StripeAdapter(api_key="sk_mock_test_EXAMPLEKEY")
                discovery.register_agent("stripe", stripe_agent)
            except Exception as e:
                logger.error(f"Failed to initialize or register StripeAdapter: {e}")
        else:
            logger.warning("StripeAdapter not available or not correctly defined for example.")

        if adapters_available["paypal"] and hasattr(PaypalAdapter, '__init__'):
            try:
                paypal_agent = PaypalAdapter(client_id="paypal_mock_id_EXAMPLE", client_secret="paypal_mock_secret_EXAMPLE")
                discovery.register_agent("paypal", paypal_agent)
            except Exception as e:
                logger.error(f"Failed to initialize or register PaypalAdapter: {e}")
        else:
            logger.warning("PaypalAdapter not available or not correctly defined for example.")

        if adapters_available["coinbase"] and hasattr(CoinbaseAdapter, '__init__'):
            try:
                coinbase_agent = CoinbaseAdapter(api_key="coinbase_mock_key_EXAMPLE")
                discovery.register_agent("coinbase", coinbase_agent)
            except Exception as e:
                logger.error(f"Failed to initialize or register CoinbaseAdapter: {e}")
        else:
            logger.warning("CoinbaseAdapter not available or not correctly defined for example.")

        if adapters_available["poof"] and hasattr(PoofAdapter, '__init__'):
            try:
                poof_agent = PoofAdapter(api_key="poof_mock_key_EXAMPLE")
                discovery.register_agent("poof", poof_agent)
            except Exception as e:
                logger.error(f"Failed to initialize or register PoofAdapter: {e}")
        else:
            logger.warning("PoofAdapter not available or not correctly defined for example.")

        logger.info(f"Registered agents: {discovery.list_agents()}")

        retrieved_stripe_agent = discovery.get_agent("stripe")
        if retrieved_stripe_agent:
            logger.info("Retrieved Stripe agent successfully.")
            # Example of calling a method (would be a mock call)
            # logger.info(retrieved_stripe_agent.initiate_payment(10.0, "USD",
            #               {'description': 'Test payment via retrieved agent'}))

        non_existent_agent = discovery.get_agent("non_existent_agent")
        logger.info(f"Retrieving non_existent_agent: {non_existent_agent}")

        # Test re-registration (if stripe_agent was created)
        if 'stripe_agent' in locals() and stripe_agent:
            discovery.register_agent("stripe", stripe_agent) # Should log warning

        # Test type checking
        class NotAnAgent:
            pass

        not_an_agent_instance = NotAnAgent()
        try:
            discovery.register_agent("invalid_agent", not_an_agent_instance) # type: ignore
        except TypeError as e:
            logger.error(f"Error registering invalid agent: {e}")

        logger.info("PaymentAgentDiscovery example finished.")

    except ImportError as e:
        # This specific ImportError for adapters is handled at the top of the file now.
        # This catch block remains for any other unexpected ImportErrors during example execution.
        logger.error(f"Error during example: Could not import a module. {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during example execution: {e}", exc_info=True)
