from src.nonprofit_magic_link import DonorReceipt, receipt_message


def test_positive_donation_gets_a_named_campaign_receipt():
    receipt = DonorReceipt("Maya", 75, "Winter food fund")

    assert receipt_message(receipt) == "Thank you, Maya: $75 for Winter food fund."


def test_zero_donation_stays_pending():
    assert receipt_message(DonorReceipt("Maya", 0, "Winter food fund")) == "Donation receipt pending"
