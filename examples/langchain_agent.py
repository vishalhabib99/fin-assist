"""LangChain: fin-assist as the last step of the chain.

    pip install langchain-core            # plus a model package, e.g. langchain-ollama
    python examples/langchain_agent.py    # runs on a fake model with no setup

Swap FakeListChatModel for ChatOllama, ChatOpenAI or ChatAnthropic; the gate line stays the same.
"""
from __future__ import annotations

from langchain_core.language_models import FakeListChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from fin_assist.gate import gate

prompt = ChatPromptTemplate.from_messages([
    ("system", "Answer general questions about US retirement accounts. Education only, three sentences."),
    ("human", "{question}"),
])
model = FakeListChatModel(responses=[
    "For 2026 the IRA contribution limit is $7,000, or $8,000 if you're 50 or older.",
])


def fin_assist_gate(inputs: dict) -> str:
    verdict = gate(inputs["question"], inputs["draft"], year=2026)
    return verdict.text


chain = {"question": lambda x: x["question"], "draft": prompt | model | StrOutputParser()} | RunnableLambda(fin_assist_gate)

if __name__ == "__main__":
    print(chain.invoke({"question": "What's the IRA limit this year?"}))
