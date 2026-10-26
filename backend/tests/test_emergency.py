import pytest
from backend.app.chatbot.graph.nodes.emergency_detector import emergency_detector_node
from backend.app.chatbot.graph.state import ChatbotState


def test_emergency_chest_pain():
    state: ChatbotState = {"sanitized_query": "I am having sudden crushing chest pain and sweating"}
    res = emergency_detector_node(state)
    assert res["is_emergency"] is True
    assert "911" in res["emergency_response"]
    assert "MEDICAL EMERGENCY DETECTED" in res["emergency_response"]


def test_emergency_difficulty_breathing():
    state: ChatbotState = {"sanitized_query": "Help me I can't breathe and my lips are turning blue"}
    res = emergency_detector_node(state)
    assert res["is_emergency"] is True
    assert "911" in res["emergency_response"]


def test_emergency_stroke_symptoms():
    state: ChatbotState = {"sanitized_query": "My mother has sudden facial droop and slurred speech"}
    res = emergency_detector_node(state)
    assert res["is_emergency"] is True
    assert "Emergency Room" in res["emergency_response"]


def test_emergency_suicide_crisis():
    state: ChatbotState = {"sanitized_query": "I want to end my life, please help"}
    res = emergency_detector_node(state)
    assert res["is_emergency"] is True
    assert "988" in res["emergency_response"]
    assert "Lifeline" in res["emergency_response"]


def test_non_emergency_routine_question():
    state: ChatbotState = {"sanitized_query": "How do I book a routine dental or cardiology checkup?"}
    res = emergency_detector_node(state)
    assert res["is_emergency"] is False
    assert res.get("emergency_response") is None
