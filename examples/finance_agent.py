import sys
import os
import inspect

# Add stubs dir to path so we can import VllmAgentStub
# Only needed when running directly without the ventis package installed globally
stubs_dir = os.path.join(os.path.dirname(__file__), "..", "stubs")
if os.path.isdir(stubs_dir) and stubs_dir not in sys.path:
    sys.path.insert(0, stubs_dir)

try:
    from vllm_agent_stub import VllmAgentStub
except ImportError:
    VllmAgentStub = None

# Example of a simple finance agent
class FinanceAgent(object):
    def __init__(self):
        self.tools = [self.get_stock_price, self.get_company_name]
        self.vllm = VllmAgentStub() if VllmAgentStub else None

    def get_stock_price(self, ticker: str) -> float:
        """Get the stock price for a given ticker."""
        return 100.0

    def get_company_name(self, ticker: str) -> str:
        """Get the company name for a given ticker."""
        return "Apple"

    def run(self, query: str) -> str:
        company = self.get_company_name(query)
        price = self.get_stock_price(company)
        
        prompt = f"The user asked: '{query}'. The company is {company} and the stock price is ${price}. Please write a short, professional response."
        
        if self.vllm:
            # Call the VLLM agent remotely and wait for the result
            # .value() blocks until the future completes via Redis
            response = self.vllm.generate(prompt).value()
            return response
        else:
            return f"Stock price of {company} is {price}."

if __name__ == "__main__":
    agent = FinanceAgent()
    print(agent.run("What is the stock price of Apple?"))