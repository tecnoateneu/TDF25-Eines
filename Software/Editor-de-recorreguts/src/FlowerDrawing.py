# Creation date: 2020-04-20
# Last modified: 2020-04-20
# Creator: Robert Guzman
# Description:
#Software for reading a GCODE file and displaying it on the screen

#Import libraries
import pygame
from pygame.locals import RLEACCEL
import pandas as pd
import untangle

# Define constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 900
FIELD_WIDTH = 800 #In mm
FIELD_HEIGHT = 600 #In mm
X_SPRITE_SIZE = 54
Y_SPRITE_SIZE = 44
FPS = 30 #Frames per second
GCODE_SCALE = 7 #We scale the GCODE to fit the field, just x and y, no speed
SVG_SCALE = 1 #We scale the SVG to fit the field
REPRODUCTION_SPEED = 30 #To speed up the reproduction

scale = SCREEN_WIDTH / FIELD_WIDTH
file = "GCODETest.gcode"
path_file = "Recorregut5"
export_file = "DotTest.txt"

from pygame.locals import (
    RLEACCEL,
)
############################ INSTRUCTIONS ##########################################
# SVG files are read and stored in a list, which I call gcode_data with three different type of elements:
#  - F3400 Speed in mm/min
#  - X100 Y200 Absolute coordinates in mm
#  - W1000 Wait for 1000 ms
# This list my be animated on the screen or create a file with the format
# 100,200 Relative coordinates in mm
####################################################################################


################################# SVG ############################################

# Extract the paths from an SVG file and assign every path to the movement of a flower
# Input: file_path: path to the SVG file
# Output: flower_movements: list of lists with the movements of every flower
def read_svg_file(file_path):
    try:
        svg_data = untangle.parse(file_path)
    except FileNotFoundError:
        print("read_svg_file: SVG file not found.")

    # Get all the paths
    lines = []
    for line in svg_data.svg.g.path:
        lines.append(line['d'])
    
    # Create structure for all the flower's movements
    flower_movements = []

    # Get de dots for every line
    dots_data = []
    for line in lines:
        # Extract the characters between 'm' and 'l' for the starting point
        if ('m' in line) and ('l' in line):
            m_index = line.index('m')
            l_index = line.index('l')
            start_point = line[(m_index + 1):l_index]
        else:
            print("read_svg_file: No path found on file. It must be first object")
            return
 
        # Extract the characters between 'l' and 'l'
        dots_data = line[l_index:]
        dots_data = dots_data.split("l")
        # Transform from 74,75 to X74 Y75
        for dot in dots_data:
            dot = 'X' + dot
            dot = dot.replace(',', ' Y')

        #From relative coordinates to absolute coordinates and store in Xxxxx Yyyyy format
        x = float(start_point.split(',')[0]) * SVG_SCALE
        y = (float(svg_data.svg._attributes['height']) - float(start_point.split(',')[1])) * SVG_SCALE
        dots_data[0] = 'X' + str(x) + ' Y' + str(y)
        for i in range(1, len(dots_data)):
            x = x + float(dots_data[i].split(',')[0]) * SVG_SCALE
            y = y - float(dots_data[i].split(',')[1]) * SVG_SCALE
            dots_data[i] = 'X' + str(x) + ' Y' + str(y) 
    
        # Adddots_data to flower_movements
        flower_movements.append(dots_data)

    return flower_movements

def add_timing_data(file_path, gcode_data):
    try:
        with open(file_path, 'r') as file:
            speed_data = file.read()
    except FileNotFoundError:
        print("add_timing_data: SPEED file not found.")
        return
    
    flower = 0
    speed_data = speed_data.split("\n")

    for line in speed_data:
        if line.startswith("R"):
            flower = int(line[1:])
        else:
            if not line.startswith("#"): # It means no comment
                point = int(line.split(' ')[0])
                instruction = line.split(' ')[1]
        # Insert instruction in row point, column flower of gcode_data
            
# Analyze al the flower movements inside a list
# Input: list_points: list of lists with the movements of every flower
# Output: print on screen the number of flowers and the max and min values of F, X and Y
def points_analytics(list_points):
    if not list_points:
        print ("points_analytics: No points to analyze.")
        return

    # Print number or records
    print("Number of flowers: " + str(len(list_points)))

    # Analyze every record
    counter = 0
    for flower in list_points:
        print("--- " + "Flower " + str(counter) + ' ---')
        list_F = []
        list_X = []
        list_Y = []

        # Separation F and XY
        for record in flower:
            if record.startswith("F"):
                list_F.append(int(record[1:]))
            if record.startswith("X"):
                list_X.append(float(record.split('X')[1].split(' ')[0]))
                list_Y.append(float(record.split('Y')[1].split(' ')[0]))
             
        if list_F: print("Fmax:" + str(max(list_F)))
        if list_F: print("Fmin:" + str(min(list_F)))
        if list_X: print("Xmax:" + str(max(list_X)))
        if list_X: print("Xmin:" + str(min(list_X)))
        if list_Y: print("Ymax:" + str(max(list_Y)))
        if list_Y: print("Ymin:" + str(min(list_Y)))
        counter += 1

################################# ANIMATION ############################################

class flowers_positions:
    def __init__(self, initial_x, initial_y):
        self.x = initial_x # Actual x position
        self.y = initial_y # Actual y position
        self.xin = 0 # Initial x position in mm of the line it is in
        self.yin = 0 # Initial y position in mm of the line it is in
        self.xfin = 0 # Final x position in mm of the line it is in
        self.yfin = 0 # Final y position in mm of the line it is in
        self.a = 1 # Parameter a of the line to go to the next point
        self.b = 0 # Parameter b of the line to go to the next point
        self.t = 0 # Actual frame in the line
        self.dx = 0 # X increment for each frame
        self.nt = 1 # Number of frames to go to the next point
        self.no_vertical = True # True if the line is not vertical
        self.F = 1000 # Default speeed mm/min
        self.n = 0 # Actual instruction number
        self.end_movement = False # True if the movement has ended
        self.get_instructions = True # True if it is time to get the next instruction
        self.start_position_reached = False #True if flower has reached its start position.

    def get_next_line(self, instruction):
        self.xfin = float(instruction.split('X')[1].split(' ')[0])
        self.yfin = float(instruction.split('Y')[1].split(' ')[0])
        self.t = 1   
        if self.x != self.xfin:
            self.a = (self.yfin - self.y) / (self.xfin - self.x) #Parameter of the line to go to the next point
            self.no_vertical = True
        else:
            self.no_vertical = False
        self.b = self.y - self.a * self.x
        length = ((self.xfin - self.x)**2 + (self.yfin - self.y)**2)**0.5 #Length of the line to go to the next point
        time = (length / (self.F/60))/REPRODUCTION_SPEED #Time to go to the next point
        self.nt = time * FPS #Number of frames to go to the next point
        self.dx = (self.xfin - self.x) / self.nt #X increment each frame
        self.xin = self.x
        self.yin = self.y
    
    def set_speed(self, instruction):
        self.F = int(instruction[1:].split(" ")[0])
    
    def get_next_position(self):
        self.x = self.xin + self.t * self.dx
        if self.no_vertical:
            self.y = self.a * self.x + self.b
        else:
            self.y = self.yin + self.t * (self.yfin - self.yin) / self.nt
        self.t += 1
        if self.t > self.nt:    #Have we drawn the whole line?
            self.n += 1
            return True
        return False   
 
    def get_flower_coordinates(self):
        pixel_x = int(round((self.x * scale)-X_SPRITE_SIZE/2))
        pixel_y = int(round((FIELD_HEIGHT-self.y) * scale - Y_SPRITE_SIZE/2))
        return pixel_x, pixel_y
        

# It draws a screen with all the flowers moving according to the list of points
# Screen size is defined by SCREEN_WIDTH and SCREEN_HEIGHT
# Input: gcode_data: list of lists with the movements of every flower
def animate_gcode(gcode_data):
    if not gcode_data:
        print("animate_gcode: No points to draw.")
        return
    # Define a Flower object, our sprite
    class Flower_sprite(pygame.sprite.Sprite):
        def __init__(self, flower_number):
            super(Flower_sprite, self).__init__()
            # Image name
            image_name = "Eines/Editor-de-recorreguts/data/Sprites/Flower" + str(flower_number) + ".png"
            self.surf = pygame.image.load(image_name).convert_alpha()
            self.surf = pygame.transform.scale(self.surf, (X_SPRITE_SIZE, Y_SPRITE_SIZE)) #Scale the image
            self.surf.set_colorkey((255, 255, 255), pygame.locals.RLEACCEL)
            self.rect = self.surf.get_rect()

    # Initialize the pygame library
    pygame.init()

    # Set up the drawing window
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Temps de flors 2025")
    
    sprites = []
    for i in range(len(gcode_data)):
        sprites.append(Flower_sprite(i))

    # Text initialization
    font = pygame.font.Font('freesansbold.ttf', 15)
    
    # Run until the user asks to quit
    running = True
    pause = False

    # First, all the flowers to start position
    everybody_ready_to_start = False
    flower_to_position = -1
    flower_positioned = True

    clock = pygame.time.Clock()

    # Instantiate all Flowers
    flowers = []
    for i in range(len(gcode_data)):
        flowers.append(flowers_positions(((len(gcode_data)-i)*50)+30, 100))

    while running:

        # Did the user click the window close button?
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                pause = not pause
                
        if not pause:
            if not everybody_ready_to_start: # We position all flowers to start
                if flower_positioned: # We get position of next flower to position
                    flower_to_position += 1
                    if flower_to_position >= len(gcode_data):
                        everybody_ready_to_start = True
                    else:
                        if gcode_data[flower_to_position][flowers[flower_to_position].n].startswith("F"):   #Speed instruction
                            flowers[flower_to_position].set_speed(gcode_data[flower_to_position][flowers[flower_to_position].n])
                            flowers[flower_to_position].n += 1
                        if gcode_data[flower_to_position][flowers[flower_to_position].n].startswith("X"):   #Movement instruction
                            flowers[flower_to_position].get_next_line(gcode_data[flower_to_position][flowers[flower_to_position].n])
            
                if flower_to_position < len(gcode_data):
                    # We move flower to its initial position
                    flower_positioned = flowers[flower_to_position].get_next_position()

            else: # Update the position of every flower acording to gcode
                for i in range(len(gcode_data)):
                    if not flowers[i].end_movement:
                        if flowers[i].get_instructions: #Get the next instruction            
                            if gcode_data[i][flowers[i].n].startswith("F"):   #Speed instruction
                                flowers[i].set_speed(gcode_data[i][flowers[i].n])
                                flowers[i].n += 1
                
                            if gcode_data[i][flowers[i].n].startswith("X"):   #Movement instruction
                                flowers[i].get_next_line(gcode_data[i][flowers[i].n])
                                flowers[i].get_instructions = False
        
                        flowers[i].get_instructions = flowers[i].get_next_position()
                        if flowers[i].n >= len(gcode_data[i]):
                            flowers[i].end_movement = True
            
            # Update the display
            screen.fill((0, 0, 0))  # Fill the background black
            pygame.draw.rect(screen, (255,255,255), pygame.Rect(0, 0, FIELD_WIDTH * scale, FIELD_HEIGHT * scale)) #Draw the field in white
        
            for i in range(len(gcode_data)): # Update sprites on the screen
                screen.blit(sprites[i].surf, flowers[i].get_flower_coordinates())

            text1 = font.render('F: ', True, (0, 0, 0), (255, 255, 255)) # Titles for text
            text2 = font.render('X: ', True, (0, 0, 0), (255, 255, 255))
            text3 = font.render('Y: ', True, (0, 0, 0), (255, 255, 255))
            screen.blit(text1, (10, 10))
            screen.blit(text2, (10, 35))
            screen.blit(text3, (10, 60))
            for i in range(len(gcode_data)): # Update text for every flower
                text1 = font.render(str(flowers[i].F), True, (0, 0, 0), (255, 255, 255))
                text2 = font.render(str(round(flowers[i].xfin, 2)), True, (0, 0, 0), (255, 255, 255))
                text3 = font.render(str(round(flowers[i].yfin, 2)), True, (0, 0, 0), (255, 255, 255))
                screen.blit(text1, (27 + (i*50), 10))
                screen.blit(text2, (27 + (i*50), 35))
                screen.blit(text3, (27 + (i*50), 60))

            pygame.display.flip()
            clock.tick(FPS)
             
    # Done! Time to quit.
    pygame.quit()

def export_gcode(gcode_data):
    if not gcode_data:
        print("export_gcode: No points to export.")
        return
    
    data_file = []

    first_coordinates_found = False
    for line in gcode_data:
        if line.startswith("F"):
            F = int(line[1:].split(" ")[0])
        if line.startswith("X"):
            if not first_coordinates_found:
                x = float(line.split('X')[1].split(' ')[0])
                y = float(line.split('Y')[1].split(' ')[0])
                first_coordinates_found = True
            else:
                dx = float(line.split('X')[1].split(' ')[0]) - x
                dy = float(line.split('Y')[1].split(' ')[0]) - y
                x = float(line.split('X')[1].split(' ')[0])
                y = float(line.split('Y')[1].split(' ')[0])
                data_file.append(str(dx) + "," + str(dy))

    #Create a file with the same name and add _export
    try:
        with open(export_file, 'w') as file:
            for line in data_file:
                file.write(line + "\n")
    except FileNotFoundError:
        print("export_gcode: Error creating file.")

#Main function
def main():
    #dots_gcode = read_gcode_file("gcode/"+file)
    dots_svg = read_svg_file("Eines/Editor-de-recorreguts/data/Coreografies/" + path_file + ".svg")
    points_analytics(dots_svg)
    add_timing_data("Eines/Editor-de-recorreguts/data/Coreografies/" + path_file + ".spd", dots_svg)
    animate_gcode(dots_svg)
    export_gcode(dots_svg)


if __name__ == "__main__":
    main()

