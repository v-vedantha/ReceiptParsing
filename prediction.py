import pandas as pd
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import re
import json
import math
from pathlib import Path

class Pantry:
    def __init__(self, ingredients, commonly_used):
        """
        Initialises a dataframe to store the 'pantry' of items as well as the list of ingredients that we use.
        """
        data_dict = {}
        for ingredient in ingredients:
            data_dict[ingredient] = [0,0.0,0.0,0.0, 0]
        self.pantry = pd.DataFrame(data_dict, index=pd.Index(ingredients, name='Ingredients'),
                  columns=pd.Index(['most_recent_date', 'most_recent_amount', 'total_amount', 'rate', 'current_amount'], name=''))
        self.relevent_ingredients = commonly_used
    
    def __init__(self, path):
        """
        Loads a dataframe from the path
        """
        try:
            self.pantry = pickle.load(path / 'pantry.pkl')
            self.relevent_ingredients = pickle.load(path / 'ingredients.pkl')
        except:
            print("Loading error")
            return None
    def save(self, path):
        """
        Saves a dataframe to the file at path
        """
        # Makes the directory if it does not exist
        try:
            os.makedirs(path, exist_ok=True)
        except:
            print('Unable to make that folder. This may mean the path to it is entered incorrectly')
        self.pantry.to_pickle(path / 'pantry.pkl')
        with open(path / 'ingredients.pkl', "wb") as f:
            pickle.dump(self.relevent_ingredients, f)
        return None
    def parse_receipt(self, path_to_receipt):
        """
        Sends the receipt into the receipt parser and returns the parsed receipt
        """
        api_instance = cloudmersive_ocr_api_client.ImageOcrApi()
        image_file = path_to_receipt # file | Image file to perform OCR on.  Common file formats such as PNG, JPEG are supported.
        
        configuration = cloudmersive_ocr_api_client.Configuration()
        api_instance.api_client.configuration.api_key = {}
        api_instance.api_client.configuration.api_key['Apikey'] = 'fancyapi'
        try:
            # Recognize a photo of a receipt, extract key business information
            api_response = api_instance.image_ocr_photo_recognize_receipt(image_file)
            return api_response
        except ApiException as e:
            print("Exception when calling ImageOcrApi->image_ocr_photo_recognize_receipt: %s\n" % e)
            return None

    def get_closest(self, ingredients, query):
        """
        Uses fuzzy comparison to find the item closes to the query.

        If no such item is found, then return None.
        """
        score = -1
        closest_match = ''
        for ingredient_ in ingredients:

            # Placeholder matching algorithm
            ingredient = re.sub('[^0-9a-zA-Z]+', ' ', ingredient_)
            current_score = fuzz.partial_ratio(ingredient, query)

            # Compare to find the highest element
            if current_score > score:
                score = current_score
                closest_match = ingredient_
                
        # If no close match is found, do not return anything
        if score < 60:
            return None
        return closest_match

    def update_amount(self):
        """
        This takes your data and for each element subtracting out the rate from its current amount
        """
        self.pantry['current_amount']-=self.pantry['rate']


    def update_rate(self, item, buy_date, alpha):
        """
        This updates the rates (round trip times) for an item in the data frame

        We are doing this using the formula from 6.02 where rtt = a*rtt + 1-a * rtt_old
        """
        
        # If the item is already relevent (meaning it has been bought before), then update its rate
        if item in self.relevent_ingredients:
            if not math.isnan(self.pantry.at[item, 'rate']):
                # If there is already a rate then do this
                self.pantry.at[item, 'rate'] = alpha*self.pantry.at[item, 'most_recent_amount']/(buy_date - self.pantry.at[item, 'most_recent_date']).days + \
                     (1-alpha)*self.pantry.at[item, 'rate']
            else:
                # If there is no rate then do this
                self.pantry.at[item, 'rate'] = self.pantry.at[item, 'most_recent_amount']/(buy_date - self.pantry.at[item, 'most_recent_date']).days

    def make_shopping_list(self):
        """
        This takes your dataframe and looks at which items are currently at 0
        or close to 0.

        Then it recommends you get that item.
        """
        return (self.pantry[self.pantry['current_amount'] < self.pantry['rate']].index).intersection(self.relevent_ingredients)
    def update_pantry_from_receipt(self, receipt_parsed):
        """
        This takes a receipt and uses fuzzy comparison to update the relevant elements in the 
        data frame.

        Additionally, we want to add some special cases for 1 off items. For example if an item
        is very negative but is not being bought then remove it from the list of things you buy
        regularly.
        """
        for item in receipt_parsed.receipt_items:
            self.add_item(item.item_description, receipt_parsed.timestamp, float(item.item_price))
    def add_item(self,ingredient, date, amount):
        """
        This adds the given item and it's date information/amount to the data frame
        
        If no such close by item is available, it will ignore the ingredient

        It also updates the rate calculations for that item.
        """
        
        # Checks if the ingredient is something we use right now
        item_in_current_purchases = self.get_closest(self.relevent_ingredients, ingredient)
        if item_in_current_purchases == None:
            item_in_current_purchases = self.get_closest(self.pantry.index, ingredient)
            if item_in_current_purchases == None:
                return None # This means the ingredient was not something we consider an ingredient
        
        # Adds the item to the pantry
        # If the item hasn't been used before then set up its amount
        if math.isnan(self.pantry.at[item_in_current_purchases, 'total_amount']):
            self.pantry.at[item_in_current_purchases, 'total_amount'] = 0
        self.update_rate(item_in_current_purchases, date, 0.2)
        
        self.pantry.at[item_in_current_purchases, 'most_recent_date'] = date
        self.pantry.at[item_in_current_purchases, 'most_recent_amount'] = amount
        self.pantry.at[item_in_current_purchases, 'current_amount'] = amount
        self.pantry.at[item_in_current_purchases, 'total_amount'] += amount
        
        self.relevent_ingredients.add(item_in_current_purchases)
        
        return 0