import asyncio
from browser_use import Agent
from browser_use.llm import ChatOpenAI

async def test_simple():
    print("Testing browser-use...")
    
    agent = Agent(
        task="Go to https://www.google.com and tell me what you see",
        llm=ChatOpenAI(model="gpt-4o-mini"),
    )
    
    result = await agent.run()
    print("=== RESULT ===")
    print(result)
    print("=== END ===")

if __name__ == "__main__":
    asyncio.run(test_simple()) 