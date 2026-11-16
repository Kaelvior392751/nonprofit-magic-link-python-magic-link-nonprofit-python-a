from src.nonprofit_magic_link import DonorReceipt, receipt_message


if __name__ == "__main__":
    receipt = DonorReceipt("Maya", 75, "Winter food fund")
    print(receipt_message(receipt))
