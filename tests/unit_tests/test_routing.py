"""Unit tests for WhatsApp routing helpers."""

from agent.routing import (
    extract_contact_name,
    extract_phone_number,
    wants_email_report,
    wants_pdf_report,
    wants_whatsapp_messaging,
)


def test_extract_phone_number():
    text = "Reply to +1 555 123 4567 on whatsapp"
    assert extract_phone_number(text) == "+15551234567"


def test_extract_contact_name():
    text = "message John Smith on whatsapp"
    assert extract_contact_name(text) == "John Smith"


def test_whatsapp_messaging_intent():
    assert wants_whatsapp_messaging("reply to whatsapp messages")
    assert wants_whatsapp_messaging("")
    assert wants_whatsapp_messaging("", state_contact_filter="Alice")
    assert not wants_whatsapp_messaging("what is the weather today")


def test_pdf_report_intent():
    assert wants_pdf_report("generate a pdf report")
    assert not wants_pdf_report("hello")


def test_email_report_intent():
    assert wants_email_report("email me the report")
    assert not wants_email_report("hello")
