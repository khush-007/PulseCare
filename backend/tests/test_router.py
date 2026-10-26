import pytest
from backend.app.chatbot.graph.nodes.router import router_node
from backend.app.chatbot.graph.state import ChatbotState


def test_route_doctor_lookup():
    state: ChatbotState = {"standalone_query": "Is there a cardiologist available on Monday?"}
    res = router_node(state)
    assert "doctor_service_lookup" in res["routes"]


def test_route_personal_data():
    state: ChatbotState = {"standalone_query": "When is my appointment scheduled?"}
    res = router_node(state)
    assert "personal_data" in res["routes"]


def test_route_medicine_info():
    state: ChatbotState = {"standalone_query": "What are the common side effects of Lisinopril?"}
    res = router_node(state)
    assert "medicine_info" in res["routes"]


def test_route_triage_handoff():
    state: ChatbotState = {"standalone_query": "I have a fever and my head hurts, can you triage me?"}
    res = router_node(state)
    assert "triage_handoff" in res["routes"]


def test_route_website_help():
    state: ChatbotState = {"standalone_query": "What is the appointment cancellation policy?"}
    res = router_node(state)
    assert "website_help" in res["routes"]


def test_route_direct_llm():
    state: ChatbotState = {"standalone_query": "Hello there! Good morning."}
    res = router_node(state)
    assert "direct_llm" in res["routes"]


def test_route_out_of_scope():
    state: ChatbotState = {"standalone_query": "Who is going to win the football match tonight?"}
    res = router_node(state)
    assert "out_of_scope" in res["routes"]


def test_multi_route_query():
    state: ChatbotState = {
        "standalone_query": "Is Dr. Sarah Smith available tomorrow and what are the side effects of Metformin?"
    }
    res = router_node(state)
    assert "doctor_service_lookup" in res["routes"]
    assert "medicine_info" in res["routes"]
