# Example of a simple finance agent

class FinanceAgent(object):
    def __init__(self):
        self.tools = [self.get_stock_price, self.get_company_name]

    def get_stock_price(self, ticker: str) -> float:
        """Get the stock price for a given ticker."""
        return 100.0

    def get_company_name(self, ticker: str) -> str:
        """Get the company name for a given ticker."""
        return "Apple"

    def run(self, query: str) -> str:
        return_val = self.get_stock_price(self.get_company_name(query)) + self.get_company_name(query)
        return return_val

if __name__ == "__main__":
    agent = FinanceAgent()
    print(agent.run("What is the stock price of Apple?"))