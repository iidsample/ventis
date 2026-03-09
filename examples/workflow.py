# Example workflow that uses generated stubs to call finance and market agents.
# The stubs make gRPC calls to the LocalController rather than calling functions directly.

import sys
import os

# Add stubs directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "stubs"))
# Add src directory for Future import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
# Add grpc_stubs for protobuf modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "grpc_stubs"))

from finance_agent_stub import FinanceAgentStub
from market_agent_stub import MarketResearchAgentStub


def main():
    finance = FinanceAgentStub()
    market = MarketResearchAgentStub()

    # Call finance agent functions
    price = finance.get_stock_price(ticker="AAPL")
    company = finance.get_company_name(ticker="AAPL")

    print(f"Stock price: {price.value()}")
    print(f"Company name: {company.value()}")

    # Call market agent functions
    trend = market.get_market_trend(sector="tech")
    analysis = market.get_sector_analysis(sector="tech")
    competitors = market.get_competitor_list(company="Apple")

    print(f"Market trend: {trend.value()}")
    print(f"Sector analysis: {analysis.value()}")
    print(f"Competitors: {competitors.value()}")


if __name__ == "__main__":
    main()
