from typing import TypedDict, List ,Annotated
import operator

class AgentState(TypedDict):
    """
    This is the state of the agent.
    - messages: The messages of the agent.
    - current_query: The current query of the agent.
    - documents: The documents of the agent.
    - plan: The plan of the agent.
    - status: The status of the agent.
    - final_answer: The final answer of the agent.
    """
    messages: Annotated[List[dict], operator.add]
    current_query:str
    documents:List[str]
    plan:List[str]
    status:str
    final_answer:str