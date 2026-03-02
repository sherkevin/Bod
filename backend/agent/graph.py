
import os
import json
from typing import TypedDict, Annotated, List, Optional, Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from backend.ai_service import API_KEY, BASE_URL, MODEL_NAME

# Define State
class AgentState(TypedDict):
    messages: List[BaseMessage]
    transcript: str
    intent: Optional[str]
    extracted_data: Optional[dict]
    final_response: Optional[str]

# Initialize LLM
llm = ChatOpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    model=MODEL_NAME,
    temperature=0.7
)

# Nodes

def intent_classifier(state: AgentState):
    """
    Classify the user's intent: LOG_WORKOUT, CHIT_CHAT, or QUERY.
    """
    transcript = state["transcript"]
    
    system_prompt = """You are a fitness assistant router. Classify the user input into one of these categories:
    - LOG_WORKOUT: User is reporting an exercise set (e.g., "Bench press 100kg", "I did 5 reps").
    - CHIT_CHAT: Greetings or casual conversation (e.g., "Hello", "I'm tired").
    - QUERY: User is asking a question about fitness (e.g., "How to squat?").
    
    Return ONLY the category name."""
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=transcript)
    ])
    
    intent = response.content.strip().upper()
    if intent not in ["LOG_WORKOUT", "CHIT_CHAT", "QUERY"]:
        intent = "CHIT_CHAT" # Default fallback
        
    return {"intent": intent}

def workout_extractor(state: AgentState):
    """
    Extract workout data from the transcript.
    """
    transcript = state["transcript"]
    
    system_prompt = """Extract workout data from the user input. Return a JSON object with these keys:
    - exercise: str (name of exercise)
    - weight: number (kg)
    - sets: number (default 1)
    - reps: number
    
    If any field is missing, try to infer or set to null.
    Return ONLY JSON, no markdown."""
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=transcript)
    ])
    
    content = response.content.strip()
    # Clean code blocks
    if content.startswith("```json"):
        content = content[7:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    
    try:
        data = json.loads(content)
    except:
        data = {"exercise": None, "weight": None, "sets": None, "reps": None}
        
    return {"extracted_data": data}

def response_generator(state: AgentState):
    """
    Generate a response based on the intent and data.
    """
    intent = state["intent"]
    data = state.get("extracted_data")
    transcript = state["transcript"]
    
    if intent == "LOG_WORKOUT" and data:
        # Check if data is valid
        if data.get("exercise"):
            prompt = f"User logged: {data}. Give a short, encouraging confirmation. Keep it under 20 words."
        else:
            prompt = "User tried to log a workout but I couldn't understand the exercise details. Ask them to repeat with exercise name, weight, and reps."
    elif intent == "QUERY":
        prompt = f"User asked: {transcript}. Answer the question briefly as a fitness coach."
    else: # CHIT_CHAT
        prompt = f"User said: {transcript}. Reply naturally as a fitness coach."
        
    response = llm.invoke([
        SystemMessage(content="You are an encouraging AI fitness coach."),
        HumanMessage(content=prompt)
    ])
    
    return {"final_response": response.content}

from langgraph.checkpoint.memory import MemorySaver

# Graph Construction

workflow = StateGraph(AgentState)
checkpointer = MemorySaver()

workflow.add_node("classifier", intent_classifier)
workflow.add_node("extractor", workout_extractor)
workflow.add_node("generator", response_generator)

workflow.set_entry_point("classifier")

def route_intent(state: AgentState):
    intent = state["intent"]
    if intent == "LOG_WORKOUT":
        return "extractor"
    else:
        return "generator"

workflow.add_conditional_edges(
    "classifier",
    route_intent,
    {
        "extractor": "extractor",
        "generator": "generator"
    }
)

workflow.add_edge("extractor", "generator")
workflow.add_edge("generator", END)

app_graph = workflow.compile(checkpointer=checkpointer)

async def run_agent(transcript: str, thread_id: str = "default") -> dict:
    """
    Run the agent on the transcript and return result compatible with existing API.
    """
    initial_state = {
        "messages": [HumanMessage(content=transcript)], # Append new message
        "transcript": transcript,
        "intent": None,
        "extracted_data": None,
        "final_response": None
    }
    
    config = {"configurable": {"thread_id": thread_id}}
    
    result = await app_graph.ainvoke(initial_state, config=config)
    
    # Map to legacy format for frontend compatibility
    extracted = result.get("extracted_data") or {}
    
    return {
        "exercise": extracted.get("exercise"),
        "weight": extracted.get("weight"),
        "sets": extracted.get("sets"),
        "reps": extracted.get("reps"),
        "feedback": result.get("final_response")
    }
