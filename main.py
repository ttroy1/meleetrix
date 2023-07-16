# Thomas Troy, 2023
# Using websockets, retrieve information from slp-realtime and display on matrix

# -----------------------------------------------------------------------------
import os
import time
import sys
import websockets
import threading
import asyncio
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
from PIL import Image
from PIL import ImageDraw, ImageFont
import numpy as np
# Base matrix instance from rpi-rgb-led-matrix library
from samplebase import SampleBase
import json
import traceback
from PIL import BdfFontFile
from datetime import datetime

# -----------------------------------------------------------------------------
# Square class (for example)
class Meleetrix(SampleBase):
    # Establish baseline attributes in initiation of class object
    def __init__(self, *args, **kwargs):
        super(Meleetrix, self).__init__(*args, **kwargs)
        
        # Create draw objects
        self.image = Image.new("RGB", (64, 64))
        self.draw = ImageDraw.Draw(self.image)
        self.background = Image.new("RGB", (64, 64))
        self.background_draw = ImageDraw.Draw(self.background)
        
        # Load configuration JSON, apply to requisite fields
        self.config = json.load(open('config.json'))
        # Display borders toggle; load chosen border color
        self.borders_active = self.config['colors']['borders_active']
        self.borders_rgb = tuple(self.config['colors']['borders_rgb'])
        # Four player grid view toggle
        self.grid_view = self.config['grid_view_4p']
        # General background color toggle
        self.backgrounds_active = self.config['colors']['backgrounds_active']
        # Toggles for disabling/enabling colors for characters
        self.custom_backgrounds_active = self.config['colors']['custom_backgrounds_active']
        self.custom_foregrounds_active = self.config['colors']['custom_foregrounds_active']
        # Load custom character/color specific RGB pairings
        self.custom_char_bgs = self.config['colors']['custom_char_bgs']
        self.custom_char_fgs = self.config['colors']['custom_char_fgs']

        # Player Stock Counts
        self.p1_stocks = 4
        self.p2_stocks = 4
        self.p3_stocks = 4
        self.p4_stocks = 4
        
        # Player Percentages
        self.p1_perc = "0%"
        self.p2_perc = "0%"
        self.p3_perc = "0%"
        self.p4_perc = "0%"
        
        # Game Start - Player Count (also serves as flag for icon import)
        self.player_count = 0
        self.active_indexes = []
        
        # Splash screen and game active flags
        self.seen_splash = False
        self.game_active = False
        
        # Icon Paths
        self.p1_icon_path = ""
        self.p2_icon_path = ""
        self.p3_icon_path = ""
        self.p4_icon_path = ""
        
        # Current stage
        self.stage = ""
        self.stage_x_loc = 5

        # Game End Specific Info
        self.postgame = False
        self.winner_index = None
        self.gameEnd_method = None
        
        # Font objects
        self.stage_font = ImageFont.load("./assets/fonts/4x6.pil")
        self.wait_font = ImageFont.load("./assets/fonts/5x7.pil")
        self.grid_font = ImageFont.load("./assets/fonts/6x10.pil")
        self.font = ImageFont.load("./assets/fonts/7x13.pil")
        self.winner_font = ImageFont.load("./assets/fonts/7x13B.pil")

    # if_valid: 
    def if_valid(self, path):
        if os.path.exists(path):
            return Image.open(path)
        else:
            print("Failed to open image! Provided path:", path)
            return Image.open("./assets/icons/mario-default.png")

    # create_icon_path: Create character icon path
    # Arguments:
    #   char_color: The name of the active color
    #   char_name: The name of the active character
    # Returns:
    #   filepath: String with filepath to corresponding icon
    def create_icon_path(self, char_color, char_name):
        # Accounting for case sensitivty to be safe
        name_lower = char_name.lower()
        color_lower = char_color.lower()
        # Smushed filepath to return
        filepath = "./assets/icons/" + name_lower + "-" + color_lower + ".png"
        return filepath

    # get_colors: RGB color determination
    # Arguments:
    #   char_color: The name of the active color
    #   char_name: The name of the active character
    def get_colors(self, char_color, char_name):

        # Recreate naming convention to determine if there are custom assignments
        color_pairing = char_name.lower() + "-" + char_color.lower()
        
        # First, check if the character/skin specific foreground color
        if self.custom_foregrounds_active == True and color_pairing in self.custom_char_fgs.keys():
            ret_colors = [tuple(self.custom_char_fgs[color_pairing])]
        else:
            ret_colors = [(255,255,0)]

        # Check if backgrounds have been disabled in general, or if the char is using a default color
        if self.backgrounds_active == False or char_color in ['Default', 'Black']:
            ret_colors.append((0, 0, 0))
        # Then, check if the active character has a custom background color
        elif self.custom_backgrounds_active == True and color_pairing in self.custom_char_bgs.keys():
            ret_colors.append(tuple(self.custom_char_bgs[color_pairing]))
        # Otherwise, check for the remaining generic colors
        elif char_color == 'Red':
            ret_colors.append((102, 0, 0))
        elif char_color == 'Blue':
            ret_colors.append((102, 102, 255))
        elif char_color == 'Green':
            ret_colors.append((0, 153, 56))
        elif char_color == 'White':
            ret_colors.append((130, 130, 130))
        elif char_color == 'Yellow':
            ret_colors.append((117, 106, 45))
        elif char_color == 'Purple':
            ret_colors.append((37, 12, 46))
        # Pikachu-specific
        elif char_color == "Party Hat":
            ret_colors.append((102, 102, 255))
        # Pikachu-specific
        elif char_color == "Cowboy Hat":
            ret_colors.append((0, 153, 56))
        # Puff-specific
        elif char_color == "Crown":
            ret_colors.append((252, 186, 3))
        # Puff-specific
        elif char_color == "Headband":
            ret_colors.append((7, 125, 94))
            
        return ret_colors

    # perc_loc_determ: Determine the x-axis location of the percentage
    # Arguments:
    #   curr_percent (String): The current percent in string format
    # Returns:
    #   An integer representing the location on the x axis to place text
    def perc_loc_determ(self, curr_percent):

        # Length is one ("-")
        if len(curr_percent) == 1:
            return 40
        # Length is two (e.g. 0%)
        elif len(curr_percent) == 2:
            return 37
        # Length is three (e.g. 10%)
        elif len(curr_percent) == 3:
            return 34
        # Length is four (e.g. 100%)
        elif len(curr_percent) == 4:
            return 30
    
    # Clear the matrix through creating a black rectangle
    def Clear_Image(self):
        self.draw.rectangle((0, 0, 63, 63), fill=(0, 0, 0), outline=(0, 0, 0))

    # create_background
    def create_background(self):
        
        # Reset background values
        self.background = Image.new("RGB", (64, 64))
        self.background_draw = ImageDraw.Draw(self.background)
        
        # ---------------------------------------------------------------------
        # Drawing indexes based on no. of players
        if self.player_count == 2:

            # First, check if borders are active
            if self.borders_active == True:
                self.background_draw.rectangle((0, 0, 63, 50), fill=(0, 0, 0, 0), outline=self.borders_rgb)
                self.background_draw.rectangle((0, 0, 63, 25), fill=(0, 0, 0, 0), outline=self.borders_rgb)

            # Iterate over active indexes
            for idx, player in enumerate(self.active_indexes):
                if player == 0:
                    icon = self.p1_image.convert("RGB")
                    rect_color = self.p1_bg_color

                elif player == 1:
                    icon = self.p2_image.convert("RGB")
                    rect_color = self.p2_bg_color

                elif player == 2:
                    icon = self.p3_image.convert("RGB")
                    rect_color = self.p3_bg_color

                elif player == 3:
                    icon = self.p4_image.convert("RGB")
                    rect_color = self.p4_bg_color

                # Iterating over list of indexes, and assigning locations based on which player listed first
                if idx == 0:
                    # Background Rectangle
                    self.background_draw.rectangle((25, 1, 62, 24), fill=rect_color, outline=rect_color)
                    # Character Image
                    Image.Image.paste(self.background, icon, (1, 1))

                elif idx == 1:
                    # Background Rectangle
                    self.background_draw.rectangle((25, 26, 62, 49), fill=rect_color, outline=rect_color)
                    # Character Image
                    Image.Image.paste(self.background, icon, (1, 26))

            # Finally, adding stage name
            self.background_draw.text((self.stage_x_loc, 54), self.stage, font=self.stage_font, fill=(255, 255, 255, 255))

        
        # Drawing indexes based on no. of players
        elif self.player_count == 3:
            # New image size for player icons is 17
            newsize = (16, 16)

            # First, check if borders are active
            if self.borders_active == True:
                self.background_draw.rectangle((0, 0, 63, 51), fill=(0, 0, 0, 0), outline=self.borders_rgb)
                self.background_draw.rectangle((0, 0, 63, 34), fill=(0, 0, 0, 0), outline=self.borders_rgb)
                self.background_draw.rectangle((0, 0, 63, 17), fill=(0, 0, 0, 0), outline=self.borders_rgb)

            # Iterate over active indexes
            for idx, player in enumerate(self.active_indexes):
                if player == 0:
                    icon = self.p1_image.convert("RGB").resize(newsize)
                    rect_color = self.p1_bg_color

                elif player == 1:
                    icon = self.p2_image.convert("RGB").resize(newsize)
                    rect_color = self.p2_bg_color

                elif player == 2:
                    icon = self.p3_image.convert("RGB").resize(newsize)
                    rect_color = self.p3_bg_color

                elif player == 3:
                    icon = self.p4_image.convert("RGB").resize(newsize)
                    rect_color = self.p4_bg_color

                # Iterating over list of indexes, and assigning locations based on which player listed first
                if idx == 0:
                    # Background Rectangle
                    self.background_draw.rectangle((25, 1, 62, 16), fill=rect_color, outline=rect_color)
                    # Character Image
                    Image.Image.paste(self.background, icon, (1, 1))

                elif idx == 1:
                    # Background Rectangle
                    self.background_draw.rectangle((25, 18, 62, 33), fill=rect_color, outline=rect_color)
                    # Character Image
                    Image.Image.paste(self.background, icon, (1, 18))
                
                elif idx == 2:
                    # Background Rectangle
                    self.background_draw.rectangle((25, 35, 62, 50), fill=rect_color, outline=rect_color)
                    # Character Image
                    Image.Image.paste(self.background, icon, (1, 35))
            
            # Finally, adding stage name
            self.background_draw.text((self.stage_x_loc, 55), self.stage, font=self.stage_font, fill=(255, 255, 255, 255))
        
        # Four player background, bar view
        elif self.player_count == 4 and self.grid_view == False:
            # New image size for player icons is 13
            newsize = (13, 13)

            # First, check if borders are active
            if self.borders_active == True:
                self.background_draw.rectangle((0, 0, 63, 56), fill=(0, 0, 0, 0), outline=self.borders_rgb)
                self.background_draw.rectangle((0, 0, 63, 42), fill=(0, 0, 0, 0), outline=self.borders_rgb)
                self.background_draw.rectangle((0, 0, 63, 28), fill=(0, 0, 0, 0), outline=self.borders_rgb)
                self.background_draw.rectangle((0, 0, 63, 14), fill=(0, 0, 0, 0), outline=self.borders_rgb)

            # Iterate over active indexes
            for idx, player in enumerate(self.active_indexes):
                if player == 0:
                    icon = self.p1_image.convert("RGB").resize(newsize)
                    rect_color = self.p1_bg_color

                elif player == 1:
                    icon = self.p2_image.convert("RGB").resize(newsize)
                    rect_color = self.p2_bg_color

                elif player == 2:
                    icon = self.p3_image.convert("RGB").resize(newsize)
                    rect_color = self.p3_bg_color

                elif player == 3:
                    icon = self.p4_image.convert("RGB").resize(newsize)
                    rect_color = self.p4_bg_color

                # Iterating over list of indexes, and assigning locations based on which player listed first
                if idx == 0:
                    # Background Rectangle
                    self.background_draw.rectangle((14, 1, 62, 13), fill=rect_color, outline=rect_color)
                    # Character Image
                    Image.Image.paste(self.background, icon, (1, 1))

                elif idx == 1:
                    # Background Rectangle
                    self.background_draw.rectangle((14, 15, 62, 27), fill=rect_color, outline=rect_color)
                    # Character Image
                    Image.Image.paste(self.background, icon, (1, 15))
                
                elif idx == 2:
                    # Background Rectangle
                    self.background_draw.rectangle((14, 29, 62, 41), fill=rect_color, outline=rect_color)
                    # Character Image
                    Image.Image.paste(self.background, icon, (1, 29))
                
                elif idx == 3:
                    # Background Rectangle
                    self.background_draw.rectangle((14, 43, 62, 55), fill=rect_color, outline=rect_color)
                    # Character Image
                    Image.Image.paste(self.background, icon, (1, 43))
            
            # Finally, adding stage name
            self.background_draw.text((self.stage_x_loc, 58), self.stage, font=self.stage_font, fill=(255, 255, 255, 255))

        # Four player background, grid view
        elif self.player_count == 4 and self.grid_view == True:
            # New image size for player icons is 14
            newsize = (14, 14)
            # Iterate over active indexes
            for idx, player in enumerate(self.active_indexes):
                if player == 0:
                    icon = self.p1_image.convert("RGB").resize(newsize)
                    rect_color = self.p1_bg_color

                elif player == 1:
                    icon = self.p2_image.convert("RGB").resize(newsize)
                    rect_color = self.p2_bg_color

                elif player == 2:
                    icon = self.p3_image.convert("RGB").resize(newsize)
                    rect_color = self.p3_bg_color

                elif player == 3:
                    icon = self.p4_image.convert("RGB").resize(newsize)
                    rect_color = self.p4_bg_color
            
                # Iterating over list of indexes, and assigning locations based on which player listed first
                if idx == 0:
                    # Background Rectangles
                    self.background_draw.rectangle((1, 1, 31, 26), fill=(0,0,0), outline=self.p1_bg_color)
                    self.background_draw.rectangle((16, 1, 31, 15), fill=self.p1_bg_color, outline=self.p1_bg_color)
                    # Character Image
                    Image.Image.paste(self.background, icon, (2, 2))

                elif idx == 1:
                    # Background Rectangles
                    self.background_draw.rectangle((32, 1, 62, 26), fill=(0,0,0), outline=self.p2_bg_color)
                    self.background_draw.rectangle((47, 1, 62, 15), fill=self.p2_bg_color, outline=self.p2_bg_color)
                    # Character Image
                    Image.Image.paste(self.background, icon, (33, 2))
                
                elif idx == 2:
                    # Background Rectangles
                    self.background_draw.rectangle((1, 28, 31, 53), fill=(0,0,0), outline=self.p3_bg_color)
                    self.background_draw.rectangle((16, 28, 31, 42), fill=self.p3_bg_color, outline=self.p3_bg_color)
                    # Character Image
                    Image.Image.paste(self.background, icon, (2, 29))

                elif idx == 3:
                    # Background Rectangles
                    self.background_draw.rectangle((32, 28, 62, 53), fill=(0,0,0), outline=self.p4_bg_color)
                    self.background_draw.rectangle((47, 28, 62, 42), fill=self.p4_bg_color, outline=self.p4_bg_color)
                    # Character Image
                    Image.Image.paste(self.background, icon, (33, 29))
                
            # Finally, adding stage name
            self.background_draw.text((self.stage_x_loc, 56), self.stage, font=self.stage_font, fill=(255, 255, 255, 255))

    # draw_in_game
    def draw_in_game(self):

        # Reset the active image to the current background image
        self.image = self.background.copy()
        self.draw = ImageDraw.Draw(self.image)
        

        # Add default variables for active players
        if 0 in self.active_indexes:
            p1_stocks = self.p1_stocks
            p1_empty = self.p1_bg_color
            p1_percent = str(self.p1_perc)
            p1_perc_loc = self.perc_loc_determ(p1_percent)
            foreground_rgb = self.p1_fg_color

            # Player 1 Stock Icons
            p1_stockOne_fill = foreground_rgb
            p1_stockTwo_fill = foreground_rgb
            p1_stockThree_fill = foreground_rgb
            p1_stockFour_fill = foreground_rgb
            # Determine which stocks should be displayed as empty for all players
            # Player 1 - Display as Empty
            if p1_stocks < 4:
                p1_stockFour_fill = p1_empty
            if p1_stocks < 3:
                p1_stockThree_fill = p1_empty
            if p1_stocks < 2:
                p1_stockTwo_fill = p1_empty
            if p1_stocks < 1:
                p1_stockOne_fill = p1_empty
        
        # Add default variables for active players
        if 1 in self.active_indexes:
            p2_stocks = self.p2_stocks
            p2_empty = self.p2_bg_color
            p2_percent = str(self.p2_perc)
            p2_perc_loc = self.perc_loc_determ(p2_percent)
            foreground_rgb = self.p2_fg_color

            # Player 1 Stock Icons
            p2_stockOne_fill = foreground_rgb
            p2_stockTwo_fill = foreground_rgb
            p2_stockThree_fill = foreground_rgb
            p2_stockFour_fill = foreground_rgb
            # Determine which stocks should be displayed as empty for all players
            # Player 1 - Display as Empty
            if p2_stocks < 4:
                p2_stockFour_fill = p2_empty
            if p2_stocks < 3:
                p2_stockThree_fill = p2_empty
            if p2_stocks < 2:
                p2_stockTwo_fill = p2_empty
            if p2_stocks < 1:
                p2_stockOne_fill = p2_empty
        
        # Add default variables for active players
        if 2 in self.active_indexes:
            p3_stocks = self.p3_stocks
            p3_empty = self.p3_bg_color
            p3_percent = str(self.p3_perc)
            p3_perc_loc = self.perc_loc_determ(p3_percent)
            foreground_rgb = self.p3_fg_color

            # Player 1 Stock Icons
            p3_stockOne_fill = foreground_rgb
            p3_stockTwo_fill = foreground_rgb
            p3_stockThree_fill = foreground_rgb
            p3_stockFour_fill = foreground_rgb
            # Determine which stocks should be displayed as empty for all players
            # Player 1 - Display as Empty
            if p3_stocks < 4:
                p3_stockFour_fill = p3_empty
            if p3_stocks < 3:
                p3_stockThree_fill = p3_empty
            if p3_stocks < 2:
                p3_stockTwo_fill = p3_empty
            if p3_stocks < 1:
                p3_stockOne_fill = p3_empty
        
        # Add default variables for active players
        if 3 in self.active_indexes:
            p4_stocks = self.p4_stocks
            p4_empty = self.p4_bg_color
            p4_percent = str(self.p4_perc)
            p4_perc_loc = self.perc_loc_determ(p4_percent)
            foreground_rgb = self.p4_fg_color

            # Player 1 Stock Icons
            p4_stockOne_fill = foreground_rgb
            p4_stockTwo_fill = foreground_rgb
            p4_stockThree_fill = foreground_rgb
            p4_stockFour_fill = foreground_rgb
            # Determine which stocks should be displayed as empty for all players
            # Player 1 - Display as Empty
            if p4_stocks < 4:
                p4_stockFour_fill = p4_empty
            if p4_stocks < 3:
                p4_stockThree_fill = p4_empty
            if p4_stocks < 2:
                p4_stockTwo_fill = p4_empty
            if p4_stocks < 1:
                p4_stockOne_fill = p4_empty

        # ---------------------------------------------------------------------
        # Drawing indexes based on no. of players
        if self.player_count == 2:
            # Iterate over active indexes
            for idx, player in enumerate(self.active_indexes):
                if player == 0:
                    stockOne_fill = p1_stockOne_fill
                    stockTwo_fill = p1_stockTwo_fill
                    stockThree_fill = p1_stockThree_fill
                    stockFour_fill = p1_stockFour_fill
                    foreground_rgb = self.p1_fg_color
                    # Percentage Info
                    percentage = p1_percent
                    perc_loc = p1_perc_loc

                elif player == 1:
                    stockOne_fill = p2_stockOne_fill
                    stockTwo_fill = p2_stockTwo_fill
                    stockThree_fill = p2_stockThree_fill
                    stockFour_fill = p2_stockFour_fill
                    foreground_rgb = self.p2_fg_color
                    # Percentage Info
                    percentage = p2_percent
                    perc_loc = p2_perc_loc

                elif player == 2:
                    stockOne_fill = p3_stockOne_fill
                    stockTwo_fill = p3_stockTwo_fill
                    stockThree_fill = p3_stockThree_fill
                    stockFour_fill = p3_stockFour_fill
                    foreground_rgb = self.p3_fg_color
                    # Percentage Info
                    percentage = p3_percent
                    perc_loc = p3_perc_loc

                elif player == 3:
                    stockOne_fill = p4_stockOne_fill
                    stockTwo_fill = p4_stockTwo_fill
                    stockThree_fill = p4_stockThree_fill
                    stockFour_fill = p4_stockFour_fill
                    foreground_rgb = self.p4_fg_color
                    # Percentage Info
                    percentage = p4_percent
                    perc_loc = p4_perc_loc

                # Iterating over list of indexes, and assigning locations based on which player listed first
                if idx == 0:
                    # First Player Stock Icons
                    self.draw.rectangle((33, 18, 36, 21), fill=stockOne_fill, outline=foreground_rgb)
                    self.draw.rectangle((39, 18, 42, 21), fill=stockTwo_fill, outline=foreground_rgb)
                    self.draw.rectangle((45, 18, 48, 21), fill=stockThree_fill, outline=foreground_rgb)
                    self.draw.rectangle((51, 18, 54, 21), fill=stockFour_fill, outline=foreground_rgb)

                    # Percentage Text
                    self.draw.text((perc_loc, 3), percentage, font=self.font, fill=foreground_rgb)

                elif idx == 1:
                    # Second Player Stock Icons
                    self.draw.rectangle((33, 43, 36, 46), fill=stockOne_fill, outline=foreground_rgb)
                    self.draw.rectangle((39, 43, 42, 46), fill=stockTwo_fill, outline=foreground_rgb)
                    self.draw.rectangle((45, 43, 48, 46), fill=stockThree_fill, outline=foreground_rgb)
                    self.draw.rectangle((51, 43, 54, 46), fill=stockFour_fill, outline=foreground_rgb)

                    # Percentage Text
                    self.draw.text((perc_loc, 28), percentage, font=self.font, fill=foreground_rgb)
        
        # ---------------------------------------------------------------------
        # Drawing indexes based on no. of players
        elif self.player_count == 3:
            # Iterate over active indexes
            for idx, player in enumerate(self.active_indexes):
                if player == 0:
                    stockOne_fill = p1_stockOne_fill
                    stockTwo_fill = p1_stockTwo_fill
                    stockThree_fill = p1_stockThree_fill
                    stockFour_fill = p1_stockFour_fill
                    foreground_rgb = self.p1_fg_color
                    # Percentage Info
                    percentage = p1_percent
                    perc_loc = p1_perc_loc


                elif player == 1:
                    stockOne_fill = p2_stockOne_fill
                    stockTwo_fill = p2_stockTwo_fill
                    stockThree_fill = p2_stockThree_fill
                    stockFour_fill = p2_stockFour_fill
                    foreground_rgb = self.p2_fg_color
                    # Percentage Info
                    percentage = p2_percent
                    perc_loc = p2_perc_loc


                elif player == 2:
                    stockOne_fill = p3_stockOne_fill
                    stockTwo_fill = p3_stockTwo_fill
                    stockThree_fill = p3_stockThree_fill
                    stockFour_fill = p3_stockFour_fill
                    foreground_rgb = self.p3_fg_color
                    # Percentage Info
                    percentage = p3_percent
                    perc_loc = p3_perc_loc


                elif player == 3:
                    stockOne_fill = p4_stockOne_fill
                    stockTwo_fill = p4_stockTwo_fill
                    stockThree_fill = p4_stockThree_fill
                    stockFour_fill = p4_stockFour_fill
                    # Percentage Info
                    percentage = p4_percent
                    perc_loc = p4_perc_loc


                # Iterating over list of indexes, and assigning locations based on which player listed first
                if idx == 0:
                    # Background Rectangle
                    self.draw.rectangle((18, 1, 62, 16), fill=self.p1_bg_color, outline=self.p1_bg_color)
                    # First Player Stock Icons
                    self.draw.rectangle((32, 12, 34, 14), fill=stockOne_fill, outline=foreground_rgb)
                    self.draw.rectangle((37, 12, 39, 14), fill=stockTwo_fill, outline=foreground_rgb)
                    self.draw.rectangle((42, 12, 44, 14), fill=stockThree_fill, outline=foreground_rgb)
                    self.draw.rectangle((47, 12, 49, 14), fill=stockFour_fill, outline=foreground_rgb)

                    # Percentage Text
                    self.draw.text((perc_loc, 3), percentage, font=self.wait_font, fill=foreground_rgb)

                elif idx == 1:
                    # Background Rectangle
                    self.draw.rectangle((18, 18, 62, 33), fill=self.p2_bg_color, outline=self.p2_bg_color)
                    # Second Player Stock Icons
                    self.draw.rectangle((32, 29, 34, 31), fill=stockOne_fill, outline=foreground_rgb)
                    self.draw.rectangle((37, 29, 39, 31), fill=stockTwo_fill, outline=foreground_rgb)
                    self.draw.rectangle((42, 29, 44, 31), fill=stockThree_fill, outline=foreground_rgb)
                    self.draw.rectangle((47, 29, 49, 31), fill=stockFour_fill, outline=foreground_rgb)

                    # Percentage Text
                    self.draw.text((perc_loc, 20), percentage, font=self.wait_font, fill=foreground_rgb)
                
                elif idx == 2:
                    # Background Rectangle
                    self.draw.rectangle((18, 35, 62, 50), fill=self.p3_bg_color, outline=self.p3_bg_color)
                    # Third Player Stock Icons
                    self.draw.rectangle((32, 46, 34, 48), fill=stockOne_fill, outline=foreground_rgb)
                    self.draw.rectangle((37, 46, 39, 48), fill=stockTwo_fill, outline=foreground_rgb)
                    self.draw.rectangle((42, 46, 44, 48), fill=stockThree_fill, outline=foreground_rgb)
                    self.draw.rectangle((47, 46, 49, 48), fill=stockFour_fill, outline=foreground_rgb)

                    # Percentage Text
                    self.draw.text((perc_loc, 37), percentage, font=self.wait_font, fill=foreground_rgb)
        
        # ---------------------------------------------------------------------
        # Drawing indexes based on no. of players
        elif self.player_count == 4 and self.grid_view == False:
            # Iterate over active indexes
            for idx, player in enumerate(self.active_indexes):
                if player == 0:
                    stockOne_fill = p1_stockOne_fill
                    stockTwo_fill = p1_stockTwo_fill
                    stockThree_fill = p1_stockThree_fill
                    stockFour_fill = p1_stockFour_fill
                    foreground_rgb = self.p1_fg_color
                    # Percentage Info
                    percentage = p1_percent
                    perc_loc = p1_perc_loc

                elif player == 1:
                    stockOne_fill = p2_stockOne_fill
                    stockTwo_fill = p2_stockTwo_fill
                    stockThree_fill = p2_stockThree_fill
                    stockFour_fill = p2_stockFour_fill
                    foreground_rgb = self.p2_fg_color
                    # Percentage Info
                    percentage = p2_percent
                    perc_loc = p2_perc_loc

                elif player == 2:
                    stockOne_fill = p3_stockOne_fill
                    stockTwo_fill = p3_stockTwo_fill
                    stockThree_fill = p3_stockThree_fill
                    stockFour_fill = p3_stockFour_fill
                    foreground_rgb = self.p3_fg_color
                    # Percentage Info
                    percentage = p3_percent
                    perc_loc = p3_perc_loc

                elif player == 3:
                    stockOne_fill = p4_stockOne_fill
                    stockTwo_fill = p4_stockTwo_fill
                    stockThree_fill = p4_stockThree_fill
                    stockFour_fill = p4_stockFour_fill
                    foreground_rgb = self.p4_fg_color
                    # Percentage Info
                    percentage = p4_percent
                    perc_loc = p4_perc_loc

                # Iterating over list of indexes, and assigning locations based on which player listed first
                if idx == 0:
                    # First Player Stock Icons
                    self.draw.rectangle((16, 3, 19, 6), fill=stockOne_fill, outline=foreground_rgb)
                    self.draw.rectangle((21, 3, 24, 6), fill=stockTwo_fill, outline=foreground_rgb)
                    self.draw.rectangle((16, 8, 19, 11), fill=stockThree_fill, outline=foreground_rgb)
                    self.draw.rectangle((21, 8, 24, 11), fill=stockFour_fill, outline=foreground_rgb)
                    # Percentage Text
                    self.draw.text((perc_loc, 1), percentage, font=self.font, fill=foreground_rgb)

                elif idx == 1:
                    # Second Player Stock Icons
                    self.draw.rectangle((16, 17, 19, 20), fill=stockOne_fill, outline=foreground_rgb)
                    self.draw.rectangle((21, 17, 24, 20), fill=stockTwo_fill, outline=foreground_rgb)
                    self.draw.rectangle((16, 22, 19, 25), fill=stockThree_fill, outline=foreground_rgb)
                    self.draw.rectangle((21, 22, 24, 25), fill=stockFour_fill, outline=foreground_rgb)
                    # Percentage Text
                    self.draw.text((perc_loc, 15), percentage, font=self.font, fill=foreground_rgb)                    
                elif idx == 2:
                    # Third Player Stock Icons
                    self.draw.rectangle((16, 31, 19, 34), fill=stockOne_fill, outline=foreground_rgb)
                    self.draw.rectangle((21, 31, 24, 34), fill=stockTwo_fill, outline=foreground_rgb)
                    self.draw.rectangle((16, 36, 19, 39), fill=stockThree_fill, outline=foreground_rgb)
                    self.draw.rectangle((21, 36, 24, 39), fill=stockFour_fill, outline=foreground_rgb)
                    # Percentage Text
                    self.draw.text((perc_loc, 29), percentage, font=self.font, fill=foreground_rgb)

                elif idx == 3:
                    # Fourth Player Stock Icons
                    self.draw.rectangle((16, 45, 19, 48), fill=stockOne_fill, outline=foreground_rgb)
                    self.draw.rectangle((21, 45, 24, 48), fill=stockTwo_fill, outline=foreground_rgb)
                    self.draw.rectangle((16, 50, 19, 53), fill=stockThree_fill, outline=foreground_rgb)
                    self.draw.rectangle((21, 50, 24, 53), fill=stockFour_fill, outline=foreground_rgb)
                    # Percentage Text
                    self.draw.text((perc_loc, 43), percentage, font=self.font, fill=foreground_rgb)
                
        # -------------------------------------------------------------
        # Grid View
        # Drawing indexes based on no. of players
        elif self.player_count == 4 and self.grid_view == True:
            # Iterate over active indexes
            for idx, player in enumerate(self.active_indexes):
                if player == 0:
                    stockOne_fill = p1_stockOne_fill
                    stockTwo_fill = p1_stockTwo_fill
                    stockThree_fill = p1_stockThree_fill
                    stockFour_fill = p1_stockFour_fill
                    foreground_rgb = self.p1_fg_color
                    # Percentage Info
                    percentage = p1_percent
                    perc_loc = p1_perc_loc-25

                elif player == 1:
                    stockOne_fill = p2_stockOne_fill
                    stockTwo_fill = p2_stockTwo_fill
                    stockThree_fill = p2_stockThree_fill
                    stockFour_fill = p2_stockFour_fill
                    foreground_rgb = self.p2_fg_color
                    # Percentage Info
                    percentage = p2_percent
                    perc_loc = p2_perc_loc+6

                elif player == 2:
                    stockOne_fill = p3_stockOne_fill
                    stockTwo_fill = p3_stockTwo_fill
                    stockThree_fill = p3_stockThree_fill
                    stockFour_fill = p3_stockFour_fill
                    foreground_rgb = self.p3_fg_color
                    # Percentage Info
                    percentage = p3_percent
                    perc_loc = p3_perc_loc-25

                elif player == 3:
                    stockOne_fill = p4_stockOne_fill
                    stockTwo_fill = p4_stockTwo_fill
                    stockThree_fill = p4_stockThree_fill
                    stockFour_fill = p4_stockFour_fill
                    foreground_rgb = self.p4_fg_color
                    # Percentage Info
                    percentage = p4_percent
                    perc_loc = p4_perc_loc+6
                
                if idx == 0:
                    # First Player Stock Icons
                    self.draw.rectangle((19, 4, 22, 7), fill=stockOne_fill, outline=foreground_rgb)
                    self.draw.rectangle((25, 4, 28, 7), fill=stockTwo_fill, outline=foreground_rgb)
                    self.draw.rectangle((19, 10, 22, 13), fill=stockThree_fill, outline=foreground_rgb)
                    self.draw.rectangle((25, 10, 28, 13), fill=stockFour_fill, outline=foreground_rgb)
                    # Percentage Text
                    self.draw.text((perc_loc, 16), percentage, font=self.grid_font, fill=foreground_rgb)

                elif idx == 1:
                    # Second Player Stock Icons
                    self.draw.rectangle((50, 4, 53, 7), fill=stockOne_fill, outline=foreground_rgb)
                    self.draw.rectangle((56, 4, 59, 7), fill=stockTwo_fill, outline=foreground_rgb)
                    self.draw.rectangle((50, 10, 53, 13), fill=stockThree_fill, outline=foreground_rgb)
                    self.draw.rectangle((56, 10, 59, 13), fill=stockFour_fill, outline=foreground_rgb)
                    # Percentage Text
                    self.draw.text((perc_loc, 16), percentage, font=self.grid_font, fill=foreground_rgb)
                                        
                elif idx == 2:
                    # Third Player Stock Icons
                    self.draw.rectangle((19, 31, 22, 34), fill=stockOne_fill, outline=foreground_rgb)
                    self.draw.rectangle((25, 31, 28, 34), fill=stockTwo_fill, outline=foreground_rgb)
                    self.draw.rectangle((19, 37, 22, 40), fill=stockThree_fill, outline=foreground_rgb)
                    self.draw.rectangle((25, 37, 28, 40), fill=stockFour_fill, outline=foreground_rgb)
                    # Percentage Text
                    self.draw.text((perc_loc, 43), percentage, font=self.grid_font, fill=foreground_rgb)
                
                elif idx == 3:
                    # Fourth Player Stock Icons
                    self.draw.rectangle((50, 31, 53, 34), fill=stockOne_fill, outline=foreground_rgb)
                    self.draw.rectangle((56, 31, 59, 34), fill=stockTwo_fill, outline=foreground_rgb)
                    self.draw.rectangle((50, 37, 53, 40), fill=stockThree_fill, outline=foreground_rgb)
                    self.draw.rectangle((56, 37, 59, 40), fill=stockFour_fill, outline=foreground_rgb)
                    # Percentage Text
                    self.draw.text((perc_loc, 43), percentage, font=self.grid_font, fill=foreground_rgb)

    # stagename_checker
    def stagename_checker(self, curr_stage):    
        
        # stagename_checker: Determine if the string of a stage name should be shortened
        # Arguments:
        #   curr_stage (String): The name of the stage
        if curr_stage == "Mushroom Kingdom":
            curr_stage = "Mushroom King."
            self.stage = curr_stage
        elif curr_stage == "Mushroom Kingdom II":
            curr_stage = "Mushroom K. II"
            self.stage = curr_stage
        elif curr_stage == "Final Destination":
            curr_stage = "Final Dest."
            self.stage = curr_stage
        elif curr_stage == "Fountain of Dreams":
            curr_stage = "Fountain of Dr."
            self.stage = curr_stage
        elif curr_stage == "Princess Peach's Castle":
            curr_stage = "Peach's Castle"
            self.stage = curr_stage

        # Return curr_stage whether changes were made or not
        return curr_stage

    # perc_loc_determ: Determine the x-axis location of the percentage
    # Arguments:
    #   curr_stage (String): The current stage's name
    # Returns:
    #   An integer representing the location on the x axis to place text
    def stage_loc_determ(self, curr_stage):

        # Send the name to the checker to preprocess
        curr_stage = self.stagename_checker(curr_stage)
        # Length is two (e.g. 0%)
        if len(curr_stage) <= 15:
            # Total pixels used by the stage name
            str_chars = 4 * len(curr_stage)
            # Pixel usage relative to total width of display
            # and remaining pixels on each side, minus 1 for index
            indv_buffer = (64 - str_chars)/2
            # Return the buffer value
            return indv_buffer

        # Otherwise, use 1 as the safest option
        else:
            return 0

    # Waiting for game state
    def state_waiting(self, offscreen_canvas):
        # Create needed strings and variables
        wait_str = "Waiting"
        forgame_str = "for game"
        waiting_x = 14
        waiting_y = 23
        forgame_x = 5
        forgame_y = 31
        ellipsis_arr = ["", ".", "..", "..."]

        # Clear matrix (needed if coming from postgame screen)
        self.Clear_Image()
        
        # Update the ellipsis str based on the current value 
        for waitloop in range(0,4):
            
            # Clear matrix, update elipsis_str based on loop
            self.Clear_Image()
            ellipsis_str = ellipsis_arr[waitloop]

            # Drawing the text graphics, updating matrix, wait, clear
            self.draw.text((waiting_x, waiting_y), wait_str, font=self.wait_font, fill=(255, 255, 255, 255))
            self.draw.text((forgame_x, forgame_y), forgame_str + ellipsis_str, font=self.wait_font, fill=(255, 255, 255, 255))
            
            # Set matrix screen to updated waiting image
            offscreen_canvas.SetImage(self.image, 0, 0)
            self.matrix.SwapOnVSync(offscreen_canvas)

            time.sleep(.5)

    # At start of game
    def state_start_game(self):
        # Set the game_active flag to True
        self.game_active = True
        # If a game was active on boot, don't need to show the splash screen
        self.seen_splash = True
        # Create background image that contains static info
        self.create_background()
        
    
    # While in game (two-player match)
    def state_game_active(self, offscreen_canvas):

        # Draw player stocks and other shapes
        self.draw_in_game()

        # Draw PIL image to offscreen_canvas (stocks and background rects.)
        offscreen_canvas.SetImage(self.image, 0, 0)

        # Draw to offscreen canvas, wait for short period
        offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas )
        time.sleep(.05)

    def state_splash(self, offscreen_canvas):
        # Load shine.png (splash screen) 
        shine_png = Image.open("./assets/splash/shine.png").convert('RGB')
        
        # Start small, get bigger
        for size in range(1, 31):
            
            # Clear matrix, resize shine image for the current loop
            resized_shine = shine_png.resize((size, int(size*1.2)))
            self.matrix.Clear()

            # Set image directly to matrix canvas and sleep
            self.matrix.SetImage(resized_shine, (32-int(size/2)), (22-int(size/2)))
            time.sleep(0.012)

        # Gradually make text brighter
        for x in range(0,25):
            # Val used to minimize number of refreshes
            val = x*10

            Image.Image.paste(self.image, resized_shine, ((32-int(size/2)), (22-int(size/2))))
            self.draw.text((6, 50), "Meleetrix 1.0", font=self.stage_font, fill=(val, val, val, val))
            
            offscreen_canvas.SetImage(self.image, 0, 0)
            self.matrix.SwapOnVSync(offscreen_canvas) 
            time.sleep(.1)
            
        
        time.sleep(0)

        # Clear matrix
        self.Clear_Image()

        # Set splash to true
        self.seen_splash = True
        
        return offscreen_canvas

    # state_postgame
    def state_postgame(self, offscreen_canvas):

        # Clear canvas, reset main image
        offscreen_canvas.Clear()
        self.image = Image.new("RGB", (64, 64))
        self.draw = ImageDraw.Draw(self.image)

        # Determine winner based on winner index
        if self.is_teams == False:
            if self.winner_index == 0:
                winning_char = self.p1_character
                winning_icon = self.p1_image.convert("RGB")
            elif self.winner_index == 1:
                winning_char = self.p2_character
                winning_icon = self.p2_image.convert("RGB")
            elif self.winner_index == 2:
                winning_char = self.p3_character
                winning_icon = self.p3_image.convert("RGB")
            elif self.winner_index == 3:
                winning_char = self.p4_character
                winning_icon = self.p4_image.convert("RGB")

            # Indicate the winning player's port in str
            char_str = winning_char + " (P" + str(self.winner_index+1) + ")"
            # Draw winning player's icon
            Image.Image.paste(self.image, winning_icon, (19, 7))

        # If Teams, determine the winning team's color
        else:
            # List of player index colors to pull
            if self.winner_index == 0:
                color_str = self.p1_color
            elif self.winner_index == 1:
                color_str = self.p2_color
            elif self.winner_index == 2:
                color_str = self.p3_color
            elif self.winner_index == 3:
                color_str = self.p4_color
            
            # Determine color to show based on color
            # Can't use char-color rgb because it's customizable
            if color_str == 'Red':
                winner_rgb = (102, 0, 0)
            elif color_str == 'Blue':
                winner_rgb = (102, 102, 255)
            elif color_str == 'Green':
                winner_rgb = (0, 153, 56)

            # Assign char_str
            char_str = color_str + " Team"

            # Draw colored square in place of player icon
            self.draw.rectangle((19, 7, 42, 30), fill=winner_rgb, outline=winner_rgb)
            
        # Check winner string, draw to canvas
        char_str_x = self.stage_loc_determ(char_str)
        self.draw.text((char_str_x, 47), char_str, font=self.stage_font, fill=(255, 255, 255, 255))

        # Draw 'Winner!' to canvas
        self.draw.text((9, 32), "Winner!", font=self.winner_font, fill=(255, 255, 255, 255))
        
        # Update offscreen_canvas/matrix
        offscreen_canvas.SetImage(self.image, 0, 0)
        self.matrix.SwapOnVSync(offscreen_canvas)
        time.sleep(10)
        
        # Once function is complete reset postgame value and exit
        offscreen_canvas.Clear()
        self.postgame = False
        self.game_active = False
        self.player_count = 0
    
    # -------------------------------------------------------------------------
    # Main function - where the sausage is made
    def run(self):

        # Offscreen canvas        
        offscreen_canvas = self.matrix.CreateFrameCanvas()

        # Infinite while loop whose variables and states will be updated
        # as new information is received from the web socket
        while True:
            try:
                # Active Game 
                if self.game_active == True:
                    self.state_game_active(offscreen_canvas)

                # Postgame
                elif self.postgame == True:
                    self.state_postgame(offscreen_canvas)
        
                # Initiate Game Data
                elif self.player_count != 0 and self.game_active == False:
                    self.state_start_game()
                
                # Splash Screen (Launch)
                elif self.seen_splash == False:
                    offscreen_canvas = self.state_splash(offscreen_canvas)

                # Waiting for Game
                elif self.seen_splash == True and self.game_active == False:
                    self.state_waiting(offscreen_canvas)
                
            
            except Exception as e:
                traceback.print_exc()
                exit()

# -----------------------------------------------------------------------------
# Create a global simple square object
game_obj = Meleetrix()

# -----------------------------------------------------------------------------
# Functions for handling connection to local websocket
class WebsocketConn():
    # Coroutine; called when new connections are made with web socket
    async def handle_connection(websocket, path):
        # This function will be called whenever a new connection is made
        # with the WebSocket server.
        print("Python-based socket now awaiting input!")
        while True:
            try:
                message = await websocket.recv()
                print(message)
                # Convert to JSON
                message = json.loads(message)
                # After extracting components, check the type of message
                message_type = message['messageType']
                
                # Percent Change Update Message
                if message_type == "playerPercent":
                    # Check the player index (scale: 0-3)
                    if message['playerIndex'] == 0:
                        game_obj.p1_perc = str(int(message['percent'])) + "%"
                    elif message['playerIndex'] == 1:
                        game_obj.p2_perc = str(int(message['percent'])) + "%"
                    elif message['playerIndex'] == 2:
                        game_obj.p3_perc = str(int(message['percent'])) + "%"
                    elif message['playerIndex'] == 3:
                        game_obj.p4_perc = str(int(message['percent'])) + "%"
                
                # Stock Count Change Update
                if message_type == "countChange":
                    stock_ct = message['stocksRemaining']

                    # First, check the player index
                    if message['playerIndex'] == 0:
                        game_obj.p1_stocks = stock_ct
                        # If the number of stocks remaining is 0, update the percent
                        if stock_ct == 0:
                            game_obj.p1_perc = "-"

                    elif message['playerIndex'] == 1:
                        game_obj.p2_stocks = stock_ct
                        # If the number of stocks remaining is 0, update the percent
                        if stock_ct == 0:
                            game_obj.p2_perc = "-"

                    elif message['playerIndex'] == 2:
                        game_obj.p3_stocks = stock_ct
                        # If the number of stocks remaining is 0, update the percent
                        if stock_ct == 0:
                            game_obj.p3_perc = "-"

                    elif message['playerIndex'] == 3:
                        game_obj.p4_stocks = stock_ct
                        # If the number of stocks remaining is 0, update the percent
                        if stock_ct == 0:
                            game_obj.p4_perc = "-"
                
                # Game End Update Message
                elif message_type == "gameEnd":
                    game_obj.gameEnd_method = message['gameEndMethod']
                    game_obj.winner_index = message['winnerPlayerIndex']
                    game_obj.game_active = False
                    game_obj.postgame = True
                        
                # Game Start Update Message
                elif message_type == "gameStart":
                    # Reset active index list
                    game_obj.active_indexes = []
                    # Set the number of players in the game overall
                    game_obj.player_count = len(message['players'])
                    # Set the current stage name
                    game_obj.stage = message['stageInfo']['name']
                    # Set the x-axis location to place the stage name;
                    # also assigns modified stage names for longer names
                    game_obj.stage_x_loc = game_obj.stage_loc_determ(game_obj.stage)
                    # If game is Teams or not - needed for winning screen
                    game_obj.is_teams = message['isTeams']
                    # Iterate over each player in the game, determining the
                    # character and color of each.
                    for player in message['players']:
                        # Retrieve playerIndex and names
                        index = player["playerIndex"]
                        nametag = player["nametag"]
                        display_name = player["displayName"]

                        # Add the active index to the list of stored active indexes
                        game_obj.active_indexes.append(index)

                        # Create local variables for character color and name
                        char_color = player["CharacterColorName"]

                        # Use shortname if available - otherwise, use name
                        if "shortName" in player["characterInfo"]:
                            char_name = player["characterInfo"]["shortName"]
                        else:
                            char_name = player["characterInfo"]["name"]

                        # Call function to return character color RGB value
                        returned_colors = game_obj.get_colors(char_color, char_name)
                        fg_color = returned_colors[0]
                        bg_color = returned_colors[1]

                        # Run function to determine correct icon based on extracted info
                        char_icon = game_obj.create_icon_path(char_color, char_name)

                        # Player 1
                        if index == 0:
                            game_obj.p1_color = char_color
                            game_obj.p1_bg_color = bg_color
                            game_obj.p1_fg_color = fg_color
                            game_obj.p1_character = char_name
                            game_obj.p1_icon_path = char_icon
                            game_obj.p1_nametag = nametag
                            game_obj.p1_display_name = display_name
                            game_obj.p1_image = game_obj.if_valid(char_icon)

                        # Player 2
                        elif index == 1:
                            game_obj.p2_color = char_color
                            game_obj.p2_bg_color = bg_color
                            game_obj.p2_fg_color = fg_color
                            game_obj.p2_character = char_name
                            game_obj.p2_icon_path = char_icon
                            game_obj.p2_nametag = nametag
                            game_obj.p2_display_name = display_name
                            game_obj.p2_image = game_obj.if_valid(char_icon)

                        # Player 3
                        elif index == 2:
                            game_obj.p3_color = char_color
                            game_obj.p3_bg_color = bg_color
                            game_obj.p3_fg_color = fg_color
                            game_obj.p3_character = char_name
                            game_obj.p3_icon_path = char_icon
                            game_obj.p3_nametag = nametag
                            game_obj.p3_display_name = display_name
                            game_obj.p3_image = game_obj.if_valid(char_icon)

                        # Player 4
                        elif index == 3:
                            game_obj.p4_color = char_color
                            game_obj.p4_bg_color = bg_color
                            game_obj.p4_fg_color = fg_color
                            game_obj.p4_character = char_name
                            game_obj.p4_icon_path = char_icon
                            game_obj.p4_nametag = nametag
                            game_obj.p4_display_name = display_name
                            game_obj.p4_image = game_obj.if_valid(char_icon)

            except Exception as e:
                print("exception : ", e)
                exit()

    # Create server, listen for incoming connections
    def start_server():
        asyncio.set_event_loop(asyncio.new_event_loop())
        asyncio.get_event_loop().run_until_complete(websockets.serve(WebsocketConn.handle_connection, 'localhost', 8081))
        asyncio.get_event_loop().run_forever()

# Create a simple square instance, and run it
def draw_to_matrix():
     if (not game_obj.process()):
        game_obj.print_help()

# -----------------------------------------------------------------------------
# Main function
if __name__ == "__main__":
    print("Starting web socket and matrix!")
    t1 = threading.Thread(target=WebsocketConn.start_server)
    t2 = threading.Thread(target=draw_to_matrix)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

