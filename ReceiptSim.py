class APIResponse:
    def __init__(self, date, *receipt_items):
        self.timestamp = date
        self.receipt_items = receipt_items
class receipt_item:
    def __init__(self, description, price):
        self.item_description = description
        self.item_price = price