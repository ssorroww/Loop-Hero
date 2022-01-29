import pygame, sys, math, random, textwrap, pickle
from pygame.locals import *

BLACK = pygame.color.THECOLORS["black"]
WHITE = pygame.color.THECOLORS["white"]
RED = pygame.color.THECOLORS["red"]
GREEN = pygame.color.THECOLORS["green"]
BLUE = pygame.color.THECOLORS["blue"]
YELLOW = pygame.color.THECOLORS["yellow"]
ORANGE = pygame.color.THECOLORS["orange"]
VIOLET = pygame.color.THECOLORS["violet"]
LIGHT_CYAN = pygame.color.THECOLORS["lightcyan"]
LIGHT_GREEN = pygame.color.THECOLORS["lightgreen"]
LIGHT_BLUE = pygame.color.THECOLORS["lightblue"]
LIGHT_YELLOW = pygame.color.THECOLORS["lightyellow"]

SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480

TILE_WIDTH = 32
TILE_HEIGHT = 32

MAP_WIDTH = 640 * 2
MAP_HEIGHT = 480 * 2

TILE_MAP_WIDTH = int(MAP_WIDTH / TILE_WIDTH)
TILE_MAP_HEIGHT = int(MAP_HEIGHT / TILE_HEIGHT)

ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 4
MAX_ROOMS = 30

HEAL_AMOUNT = 4
LIGHTNING_DAMAGE = 20
LIGHTNING_RANGE = 5 * TILE_WIDTH
CONFUSE_RANGE = 8 * TILE_WIDTH
CONFUSE_NUM_TURNS = 10
FIREBALL_RADIUS = 3 * TILE_WIDTH
FIREBALL_DAMAGE = 12

LEVEL_UP_BASE = 200
LEVEL_UP_FACTOR = 150

TORCH_RADIUS = 10

MSG_X = 5
MSG_WIDTH = int(SCREEN_WIDTH / 15)
MSG_HEIGHT = 3


def main():
    pygame.init()

    global screen, font, images, gui, blank_surface, impact_image, impact_image_pos, impact
    screen = pygame.display.set_mode((640, 480), )
    pygame.display.set_caption("Loop Hero")
    font = pygame.font.SysFont('Arial', 20, bold=True)

    rogue_tiles = pygame.image.load('loop_hero.png').convert()
    tile_width = int(rogue_tiles.get_width() / 11)
    tile_height = rogue_tiles.get_height()
    blank_surface = pygame.Surface((TILE_WIDTH, TILE_HEIGHT)).convert()
    blank_surface.set_colorkey(blank_surface.get_at((0, 0)))
    impact_image = get_impact_image()
    impact_image_pos = [0, 0]
    impact = False
    images = []
    for i in range(11):
        image = rogue_tiles.subsurface(tile_width * i, 0, tile_width, tile_height).convert()
        if i not in (0, 1, 9):
            image.set_colorkey(image.get_at((0, 0)))
        images.append(image)

    main_menu()


def make_map():
    global level_map, objects, stairs

    objects = [player]

    level_map = [[Tile(True, x, y)
                  for y in range(0, MAP_HEIGHT, TILE_HEIGHT)]
                 for x in range(0, MAP_WIDTH, TILE_WIDTH)]

    rooms = []
    num_rooms = 0

    for r in range(MAX_ROOMS):
        w = random.randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = random.randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        x = random.randint(0, TILE_MAP_WIDTH - w - 1)
        y = random.randint(0, TILE_MAP_HEIGHT - h - 1)
        new_room = Rectangle(x, y, w, h)
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break
        if not failed:
            create_room(new_room)
            (new_x, new_y) = new_room.center()
            if num_rooms == 0:
                player.x = new_x * TILE_WIDTH
                player.y = new_y * TILE_HEIGHT
                level_map[new_x][new_y].entity = player
                player.tile = level_map[new_x][new_y]
                check_tile(new_x, new_y)
            else:
                (prev_x, prev_y) = rooms[num_rooms - 1].center()
                if random.randint(0, 1) == 1:
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)
            place_objects(new_room)
            rooms.append(new_room)
            num_rooms += 1
    stairs = Object(new_x * TILE_WIDTH, new_y * TILE_HEIGHT, images[9], 'stairs')
    level_map[new_x][new_y].item = stairs
    objects.append(stairs)


def random_choice_index(chances):
    dice = random.randint(1, sum(chances))
    running_sum = 0
    choice = 0
    for w in chances:
        running_sum += w
        if dice <= running_sum:
            return choice
        choice += 1


def random_choice(chances_dict):
    chances = chances_dict.values()
    strings = list(chances_dict.keys())
    return strings[random_choice_index(chances)]


def from_dungeon_level(table):
    for (value, level) in reversed(table):
        if dungeon_level >= level:
            return value
    return 0


def next_level():
    global dungeon_level
    message('You take a moment to rest, and recover your strength.', VIOLET)
    player.fighter.heal(int(player.fighter.max_hp / 2))

    dungeon_level += 1
    message('After a rare moment of peace, you descend deeper into the heart of the dungeon...', RED)
    make_map()
    camera.update()
    update_gui()


def render_all():
    global active_entities
    active_entities = []
    screen.fill(BLACK)
    for y in range(camera.tile_map_y, camera.y_range):
        for x in range(camera.tile_map_x, camera.x_range):
            tile = level_map[x][y]
            if tile.visible:
                if tile.block_sight:
                    screen.blit(images[0], (tile.x - camera.x, tile.y - camera.y))
                else:
                    screen.blit(images[1], (tile.x - camera.x, tile.y - camera.y))
                    if tile.item:
                        tile.item.draw(screen)
                    if tile.entity:
                        tile.entity.draw(screen)
                        active_entities.append(tile.entity)
    if impact:
        screen.blit(impact_image, impact_image_pos)
    screen.blit(gui, (10, 456))
    if message_log:
        y = 10
        for msg in game_msgs:
            screen.blit(msg, (5, y))
            y += 24
    pygame.display.flip()
    #pygame.time.Clock().tick(30)


def create_room(room):
    global level_map
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            tile = level_map[x][y]
            tile.blocked = False
            tile.block_sight = False
            tile.room = room


def create_h_tunnel(x1, x2, y):
    global level_map
    for x in range(min(x1, x2), max(x1, x2) + 1):
        level_map[x][y].blocked = False
        level_map[x][y].block_sight = False


def create_v_tunnel(y1, y2, x):
    global level_map
    for y in range(min(y1, y2), max(y1, y2) + 1):
        level_map[x][y].blocked = False
        level_map[x][y].block_sight = False


def check_tile(x, y):
    tile = level_map[x][y]
    if not tile.explored:
        tile.explored = True
        old_x = x
        old_y = y
        for x in range(old_x - 1, old_x + 2):
            for y in range(old_y - 1, old_y + 2):
                level_map[x][y].visible = True
        if tile.room and not tile.room.explored:
            room = tile.room
            room.explored = True
            for x in range(room.x1, room.x2 + 1):
                for y in range(room.y1, room.y2 + 1):
                    level_map[x][y].visible = True


def is_blocked(x, y):
    if level_map[x][y].blocked:
        return True
    if level_map[x][y].entity:
        return True
    return False


def place_objects(room):
    max_monsters = from_dungeon_level([[2, 1], [3, 4], [5, 6]])
    monster_chances = {}
    monster_chances['orc'] = 80
    monster_chances['troll'] = from_dungeon_level([[15, 3], [30, 5], [60, 7]])
    max_items = from_dungeon_level([[1, 1], [2, 4]])
    item_chances = {}
    item_chances['heal'] = 35
    item_chances['lightning'] = from_dungeon_level([[25, 4]])
    item_chances['fireball'] = from_dungeon_level([[25, 6]])
    item_chances['confuse'] = from_dungeon_level([[10, 2]])
    item_chances['sword'] = from_dungeon_level([[5, 4]])
    item_chances['shield'] = from_dungeon_level([[15, 8]])
    num_monsters = random.randint(0, max_monsters)

    for i in range(num_monsters):
        x = random.randint(room.x1 + 1, room.x2 - 1)
        y = random.randint(room.y1 + 1, room.y2 - 1)
        if not is_blocked(x, y):
            choice = random_choice(monster_chances)
            if choice == 'orc':
                fighter_component = Fighter(hp=20, defense=0, power=4, exp=35, death_function=monster_death)
                ai_component = BasicMonster()
                monster = Object(x * TILE_WIDTH, y * TILE_HEIGHT, images[3], 'orc', blocks=True,
                                 fighter=fighter_component, ai=ai_component)
            elif choice == 'troll':
                fighter_component = Fighter(hp=30, defense=2, power=8, exp=100, death_function=monster_death)
                ai_component = BasicMonster()
                monster = Object(x * TILE_WIDTH, y * TILE_HEIGHT, images[4], 'troll', blocks=True,
                                 fighter=fighter_component, ai=ai_component)

            objects.append(monster)
            level_map[x][y].entity = monster
            monster.tile = level_map[x][y]
    num_items = random.randint(0, max_items)

    for i in range(num_items):
        x = random.randint(room.x1 + 1, room.x2 - 1)
        y = random.randint(room.y1 + 1, room.y2 - 1)
        if not is_blocked(x, y):
            choice = random_choice(item_chances)
            if choice == 'heal':
                item_component = Item(use_function=cast_heal)
                item = Object(x * TILE_WIDTH, y * TILE_HEIGHT, images[6],
                              'healing potion', item=item_component)
            elif choice == 'lightning':
                item_component = Item(use_function=cast_lightning)
                item = Object(x * TILE_WIDTH, y * TILE_HEIGHT, images[5],
                              'scroll of lightning bolt', item=item_component)
            elif choice == 'fireball':
                item_component = Item(use_function=cast_fireball)
                item = Object(x * TILE_WIDTH, y * TILE_HEIGHT, images[5],
                              'scroll of fireball', item=item_component)
            elif choice == 'confuse':
                item_component = Item(use_function=cast_confuse)
                item = Object(x * TILE_WIDTH, y * TILE_HEIGHT, images[5],
                              'scroll of confusion', item=item_component)
            elif choice == 'sword':
                equipment_component = Equipment(slot='right hand', power_bonus=3)
                item = Object(x * TILE_WIDTH, y * TILE_HEIGHT, images[7],
                              'sword', equipment=equipment_component)
            elif choice == 'shield':
                equipment_component = Equipment(slot='left hand', defense_bonus=1)
                item = Object(x * TILE_WIDTH, y * TILE_HEIGHT, images[8],
                              'shield', equipment=equipment_component)
            objects.append(item)
            level_map[x][y].item = item
            item.send_to_back()


def player_move_or_attack(dx, dy):
    global player_action
    target = None
    x = int((player.x + dx) / TILE_WIDTH)
    y = int((player.y + dy) / TILE_HEIGHT)
    if not is_blocked(x, y):
        player.x += dx
        player.y += dy
        player.tile.entity = None
        level_map[x][y].entity = player
        player.tile = level_map[x][y]
        check_tile(x, y)
        camera.update()
    elif level_map[x][y].entity:
        target = level_map[x][y].entity
        player.fighter.attack(target)
    player_action = 'taked-turn'


def player_death(player):
    global game_state
    message('You died!', RED)
    game_state = 'dead'
    player.image = images[10]
    player.image_index = 10
    player.tile.entity = None
    player.tile.item = player


def monster_death(monster):
    message('The ' + monster.name + ' is dead! You gain ' + str(monster.fighter.exp) + ' experience points.', ORANGE)
    monster.image = images[10]
    monster.image_index = 10
    monster.tile.entity = None
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'remains of ' + monster.name
    monster.send_to_back()
    monster.item = Item()
    monster.item.owner = monster
    if not monster.tile.item:
        monster.tile.item = monster


def closest_monster(max_range):
    closest_enemy = None
    closest_dist = max_range + 1

    for obj in active_entities:
        if obj.fighter and obj != player and obj.tile.visible:
            dist = player.distance_to(obj)
            if dist < closest_dist:
                closest_enemy = obj
                closest_dist
    return closest_enemy


def target_tile(max_range=None):
    global message_log
    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    message_log = False
                    return (None, None)
            if event.type == MOUSEBUTTONDOWN:
                if event.button == 3:
                    message_log = False
                    return (None, None)
                if event.button == 1:
                    mouse_x, mouse_y = event.pos
                    mouse_x += camera.x
                    mouse_y += camera.y
                    x = int(mouse_x / TILE_WIDTH)
                    y = int(mouse_y / TILE_HEIGHT)
                    if (level_map[x][y].visible and
                            (max_range is None or player.distance(mouse_x, mouse_y) <= max_range)):
                        return (mouse_x, mouse_y)
        render_all()


def target_monster(max_range=None):
    while True:
        (x, y) = target_tile(max_range)
        if x is None:
            return None
        x = int(x / TILE_WIDTH)
        y = int(y / TILE_HEIGHT)
        tile = level_map[x][y]
        for obj in active_entities:
            if obj.x == tile.x and obj.y == tile.y and obj.fighter and obj != player:
                return obj


def cast_heal():
    if player.fighter.hp == player.fighter.max_hp:
        message('You are already at full health.', RED)
        return 'cancelled'
    message('Your wounds start to feel better!', VIOLET)
    player.fighter.heal(HEAL_AMOUNT)


def cast_lightning():
    monster = closest_monster(LIGHTNING_RANGE)
    if monster is None:
        message('No enemy is close enough to strike.', RED)
        return 'cancelled'

    message('A lighting bolt strikes the ' + monster.name + ' with a loud thunder! The damage is '
            + str(LIGHTNING_DAMAGE) + ' hit points.', LIGHT_BLUE)
    monster.fighter.take_damage(LIGHTNING_DAMAGE)


def cast_fireball():
    message('Left-click a target tile for the fireball, or right-click to cancel.', LIGHT_CYAN)
    (x, y) = target_tile()
    if x is None: return 'cancelled'
    message('The fireball explodes, burning everything within ' + str(int(FIREBALL_RADIUS / TILE_WIDTH)) + ' tiles!',
            ORANGE)

    for obj in active_entities:
        if obj.distance(x, y) <= FIREBALL_RADIUS and obj.fighter:
            message('The ' + obj.name + ' gets burned for ' + str(FIREBALL_DAMAGE) + ' hit points.', ORANGE)
            obj.fighter.take_damage(FIREBALL_DAMAGE)


def cast_confuse():
    message('Left-click an enemy to confuse it, or right-click to cancel.', LIGHT_CYAN)
    monster = target_monster(CONFUSE_RANGE)
    if monster is None: return 'cancelled'

    old_ai = monster.ai
    monster.ai = ConfusedMonster(old_ai)
    monster.ai.owner = monster
    message('The eyes of the ' + monster.name + ' look vacant, as he starts to stumble around!', LIGHT_GREEN)


def message(new_msg, color=WHITE):
    global game_msgs, message_log, game_msgs_data
    if not message_log:
        game_msgs = []
        game_msgs_data = []
    message_log = True
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

    for line in new_msg_lines:
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]
            del game_msgs_data[0]
        msg = font.render(line, True, color)
        game_msgs.append(msg)
        game_msgs_data.append((line, color))

    render_all()
    wait_time = 0
    while wait_time < 10:
        wait_time += 1


def entity_flash(entity):
    global impact
    impact = True
    impact_image_pos[0] = entity.x - camera.x
    impact_image_pos[1] = entity.y - camera.y
    render_all()
    impact = False
    wait_time = 0
    while wait_time < 5:
        wait_time += 1
    flash = 3
    flash_time = 2
    if entity.fighter.hp <= 0:
        flash_time = 4
    entity_old_image = entity.image
    while flash_time > 1:
        if flash:
            entity.image = blank_surface
        render_all()
        if not flash:
            flash = 6
        flash -= 1
        if flash < 1:
            flash = False
            flash_time -= 1
            entity.image = entity_old_image
            if flash_time < 1:
                flash_time = 0
                flash = False
                entity.image = entity_old_image


def get_impact_image():
    color = (230, 230, 230)
    impact_image = pygame.Surface((TILE_WIDTH, TILE_WIDTH)).convert()
    impact_image.set_colorkey(impact_image.get_at((0, 0)))
    image = pygame.Surface((int(TILE_WIDTH / 2), int(TILE_HEIGHT / 3))).convert()
    top = 0
    left = 0
    bottom = image.get_width() - 1
    right = image.get_height() - 1
    center_x = int(image.get_width() / 2) - 1
    center_y = int(image.get_height() / 2) - 1
    pygame.draw.line(image, color, (top, left), (bottom, right), 2)
    x = int((impact_image.get_width() - image.get_width()) / 2)
    y = int((impact_image.get_height() - image.get_height()) / 2)
    impact_image.blit(image, (x, y))
    return impact_image


def menu(header, options):
    if len(options) > 26: raise ValueError('Cannot have a menu with more than 26 options.')
    screen.fill(BLACK)
    header = font.render(header, True, YELLOW)
    screen.blit(header, (0, 0))
    y = header.get_height() + 5
    letter_index = ord('a')
    for option_text in options:
        text = font.render('(' + chr(letter_index) + ') ' + option_text, True, WHITE)
        screen.blit(text, (0, y))
        y += text.get_height()
        letter_index += 1
    pygame.display.flip()
    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                else:
                    if event.unicode != '':
                        index = ord(event.unicode) - ord('a')
                        if index >= 0 and index < len(options):
                            return index
                        else:
                            return None


def inventory_menu(header):
    if len(inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = []
        for item in inventory:
            text = item.name
            if item.equipment and item.equipment.is_equipped:
                text = text + ' (on ' + item.equipment.slot + ')'
            options.append(text)

    index = menu(header, options)

    if index is None or len(inventory) == 0:
        return None
    return inventory[index].item


def update_gui():
    global gui
    gui = font.render(
        'HP: ' + str(player.fighter.hp) + '/' + str(player.fighter.max_hp) + ' ' * 60 + ' Dungeon level ' + str(
            dungeon_level), True, YELLOW)


def get_names_under_mouse(mouse_x, mouse_y):
    x = int((mouse_x + camera.x) / TILE_WIDTH)
    y = int((mouse_y + camera.y) / TILE_HEIGHT)
    tile = level_map[x][y]
    if tile.visible:
        if not (tile.item or tile.entity):
            message("There is nothing there")
        else:
            names = []
            if tile.item:
                names.append(tile.item.name)
            if tile.entity:
                names.append(tile.entity.name)
            if tile.item and tile.entity:
                names = ' and '.join(names)
                message("There is " + names + " there")
            else:
                message("There is " + names[0] + " there")
    else:
        message("You can't see that spot")


def check_level_up():
    level_up_exp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
    if player.fighter.exp >= level_up_exp:
        player.level += 1
        player.fighter.exp -= level_up_exp
        message('Your battle skills grow stronger! You reached level ' + str(player.level) + '!', YELLOW)

        choice = None
        while choice == None:
            choice = menu('Level up! Choose a stat to raise:',
                          ['Constitution (+20 HP, from ' + str(player.fighter.max_hp) + ')',
                           'Strength (+1 attack, from ' + str(player.fighter.power) + ')',
                           'Agility (+1 defense, from ' + str(player.fighter.defense) + ')'])

        if choice == 0:
            player.fighter.max_hp += 20
            player.fighter.hp += 20
        elif choice == 1:
            player.fighter.power += 1
        elif choice == 2:
            player.fighter.defense += 1
        update_gui()


def get_equipped_in_slot(slot):
    for obj in inventory:
        if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
            return obj.equipment
    return None


def get_all_equipped(obj):
    if obj == player:
        equipped_list = []
        for item in inventory:
            if item.equipment and item.equipment.is_equipped:
                equipped_list.append(item.equipment)
        return equipped_list
    else:
        return []


def new_game():
    global player, camera, game_state, player_action, active_entities
    global gui, game_msgs, game_msgs_data, message_log, inventory, dungeon_level

    fighter_component = Fighter(hp=30, defense=2, power=5, exp=0, death_function=player_death)
    player = Object(TILE_WIDTH * 10, TILE_HEIGHT * 7, images[2], "player",
                    blocks=True, fighter=fighter_component)

    player.level = 1
    dungeon_level = 1
    make_map()
    camera = Camera(player)

    game_state = 'playing'
    player_action = 'didnt-take-turn'
    inventory = []
    active_entities = []

    update_gui()
    game_msgs = []
    game_msgs_data = []
    message_log = True
    message('Welcome stranger!', RED)

    equipment_component = Equipment(slot='right hand', power_bonus=2)
    obj = Object(0, 0, images[10], 'dagger', equipment=equipment_component)
    inventory.append(obj)
    equipment_component.equip()


def msgbox(text):
    menu(text, [])


def play_game():
    global player_action, message_log

    player_move = False
    pygame.key.set_repeat(400, 30)

    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

            if game_state == 'playing':
                if event.type == KEYUP:
                    if event.key == K_ESCAPE:
                        return
                    message_log = False
                    if event.key == K_UP:
                        player_move_or_attack(0, -TILE_HEIGHT)
                    elif event.key == K_DOWN:
                        player_move_or_attack(0, TILE_HEIGHT)
                    if event.key == K_LEFT:
                        player_move_or_attack(-TILE_WIDTH, 0)
                    elif event.key == K_RIGHT:
                        player_move_or_attack(TILE_WIDTH, 0)
                    if event.key == K_g:
                        if player.tile.item and player.tile.item.item:
                            player.tile.item.item.pick_up()
                            player.tile.item = None
                    if event.key == K_i:
                        chosen_item = inventory_menu("Press the key next to an item to use it, or any other to cancel.")
                        if chosen_item is not None:
                            chosen_item.use()
                            update_gui()
                    if event.key == K_d:
                        if player.tile.item:
                            message("There's already something here")
                        else:
                            chosen_item = inventory_menu(
                                'Press the key next to an item to drop iy, or any other to cancel.')
                            if chosen_item is not None:
                                chosen_item.drop()
                    if event.key == K_c:
                        level_up_exp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
                        menu('Character Information',
                             ['Level: ' + str(player.level), 'Experience: ' + str(player.fighter.exp),
                              'Experience to level up: ' + str(level_up_exp),
                              'Maximum HP: ' + str(player.fighter.max_hp),
                              'Attack: ' + str(player.fighter.power), 'Defense: ' + str(player.fighter.defense)])
                    if event.key in (K_LESS, K_PERIOD) or event.unicode == '>':
                        if stairs.x == player.x and stairs.y == player.y:
                            next_level()
                if event.type == MOUSEBUTTONDOWN:
                    if event.button == 1:
                        player_move = True
                        message_log = False
                    elif event.button == 3:
                        mouse_x, mouse_y = event.pos
                        get_names_under_mouse(mouse_x, mouse_y)
                if event.type == MOUSEBUTTONUP:
                    if event.button == 1:
                        player_move = False

        if player_move and game_state == 'playing':
            pos = pygame.mouse.get_pos()
            x = int((pos[0] + camera.x) / TILE_WIDTH)
            y = int((pos[1] + camera.y) / TILE_HEIGHT)
            tile = level_map[x][y]
            if tile != player.tile:
                dx = tile.x - player.x
                dy = tile.y - player.y
                distance = math.sqrt(dx ** 2 + dy ** 2)
                dx = int(round(dx / distance)) * TILE_WIDTH
                dy = int(round(dy / distance)) * TILE_HEIGHT
                player_move_or_attack(dx, dy)

        if game_state == 'playing' and player_action != 'didnt-take-turn':
            for entity in active_entities:
                if entity.ai:
                    entity.ai.take_turn()
            player_action = 'didnt-take-turn'

        render_all()


def main_menu():
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont('Arial', 45, bold=True)
    game_title = title_font.render("Loop Hero", True,  LIGHT_CYAN)
    game_title_pos = (int((SCREEN_WIDTH - game_title.get_width()) / 2), 150)
    cursor_img = pygame.Surface((16, 16)).convert()
    cursor_img.set_colorkey(cursor_img.get_at((0, 0)))
    pygame.draw.polygon(cursor_img, GREEN, [(0, 0), (16, 8), (0, 16)], 0)
    cursor_img_pos = [195, 254]
    menu_choices = ['Play a game', 'Quit']
    for i in range(len(menu_choices)):
        menu_choices[i] = font.render(menu_choices[i], True, YELLOW)
    choice = 0
    choices_length = len(menu_choices) - 1
    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    return

                if event.key == K_UP:
                    cursor_img_pos[1] -= 24
                    choice -= 1
                    if choice < 0:
                        choice = choices_length
                        cursor_img_pos[1] = 278
                elif event.key == K_DOWN:
                    cursor_img_pos[1] += 24
                    choice += 1
                    if choice > choices_length:
                        choice = 0
                        cursor_img_pos[1] = 254
                if event.key == K_RETURN:
                    if choice == 0:
                        new_game()
                        play_game()
                    elif choice == 1:
                        return

        screen.fill(BLACK)
        y = 250
        for menu_choice in menu_choices:
            screen.blit(menu_choice, (230, y))
            y += 24
        screen.blit(game_title, game_title_pos)
        screen.blit(cursor_img, cursor_img_pos)
        pygame.display.flip()


class Object:
    def __init__(self, x, y, image, name, blocks=False, fighter=None, ai=None, item=None, equipment=None):
        self.x = x
        self.y = y
        self.image = image
        self.image_index = images.index(image)
        self.name = name
        self.blocks = blocks
        self.tile = None
        self.fighter = fighter
        if self.fighter:
            self.fighter.owner = self
        self.ai = ai
        if self.ai:
            self.ai.owner = self
        self.item = item
        if self.item:
            self.item.owner = self
        self.equipment = equipment
        if self.equipment:
            self.equipment.owner = self
            self.item = Item()
            self.item.owner = self

    def move(self, dx, dy):
        x = int((self.x + dx) / TILE_WIDTH)
        y = int((self.y + dy) / TILE_HEIGHT)
        if not is_blocked(x, y):
            self.x += dx
            self.y += dy
            self.tile.entity = None
            level_map[x][y].entity = self
            self.tile = level_map[x][y]

    def move_towards(self, target_x, target_y):
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
        dx = int(round(dx / distance)) * TILE_WIDTH
        dy = int(round(dy / distance)) * TILE_HEIGHT
        self.move(dx, dy)

    def distance_to(self, other):
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def distance(self, x, y):
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    def send_to_back(self):
        global objects
        objects.remove(self)
        objects.insert(0, self)

    def draw(self, surface):
        surface.blit(self.image, (self.x - camera.x, self.y - camera.y))


class Fighter:
    def __init__(self, hp, defense, power, exp, death_function=None):
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power
        self.exp = exp
        self.death_function = death_function

    def attack(self, target):
        damage = self.power - target.fighter.defense

        if damage > 0:
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.')
            target.fighter.take_damage(damage)
        else:
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!')

    def take_damage(self, damage):
        if damage > 0:
            self.hp -= damage
            entity_flash(self.owner)
            if self.owner == player:
                update_gui()
            if self.hp <= 0:
                self.hp = 0
                update_gui()
                function = self.death_function
                if function is not None:
                    function(self.owner)
                if self.owner != player:
                    player.fighter.exp += self.exp
                    check_level_up()

    def heal(self, amount):
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp


class Rectangle:
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h
        self.explored = False

    def center(self):
        center_x = int((self.x1 + self.x2) / 2)
        center_y = int((self.y1 + self.y2) / 2)
        return (center_x, center_y)

    def intersect(self, other):
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)


class Item:
    def __init__(self, use_function=None):
        self.use_function = use_function

    def pick_up(self):
        if len(inventory) >= 26:
            message('Your inventory is full, cannot pick up ' + self.owner.name + '.', VIOLET)
        else:
            inventory.append(self.owner)
            objects.remove(self.owner)
            message('You picked up a ' + self.owner.name + '!', BLUE)

            equipment = self.owner.equipment
            if equipment and get_equipped_in_slot(equipment.slot) is None:
                equipment.equip()

    def drop(self):
        if self.owner.equipment:
            self.owner.equipment.dequip()

        objects.append(self.owner)
        inventory.remove(self.owner)
        self.owner.x = player.x
        self.owner.y = player.y
        player.tile.item = self.owner
        message('You dropped a ' + self.owner.name + '.', YELLOW)

    def use(self):
        if self.owner.equipment:
            self.owner.equipment.toggle_equip()
            return

        if self.use_function is None:
            message('The ' + self.owner.name + ' cannot be used.')
        else:
            if self.use_function() != 'cancelled':
                inventory.remove(self.owner)


class Equipment:
    def __init__(self, slot, power_bonus=0, defense_bonus=0, max_hp_bonus=0):
        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus
        self.max_hp_bonus = max_hp_bonus

        self.slot = slot
        self.is_equipped = False

    def toggle_equip(self):
        if self.is_equipped:
            self.dequip()
        else:
            self.equip()

    def equip(self):
        old_equipment = get_equipped_in_slot(self.slot)
        if old_equipment is not None:
            old_equipment.dequip()

        self.is_equipped = True
        player.fighter.power += self.power_bonus
        player.fighter.defense += self.defense_bonus
        player.fighter.max_hp += self.max_hp_bonus
        message('Equipped ' + self.owner.name + ' on ' + self.slot + '.', ORANGE)

    def dequip(self):
        if not self.is_equipped: return
        self.is_equipped = False
        player.fighter.power -= self.power_bonus
        player.fighter.defense -= self.defense_bonus
        player.fighter.max_hp -= self.max_hp_bonus
        if player.fighter.hp > player.fighter.max_hp:
            player.fighter.hp = player.fighter.max_hp
        message('Dequipped ' + self.owner.name + ' from ' + self.slot + '.', LIGHT_YELLOW)


class BasicMonster:
    def take_turn(self):
        monster = self.owner
        if monster.tile.visible:
            distance = monster.distance_to(player)
            if distance < 128:
                if distance >= 64:
                    monster.move_towards(player.x, player.y)
                elif player.fighter.hp > 0:
                    monster.fighter.attack(player)


class ConfusedMonster:
    def __init__(self, old_ai, num_turns=CONFUSE_NUM_TURNS):
        self.old_ai = old_ai
        self.num_turns = num_turns

    def take_turn(self):
        if self.num_turns > 0:
            dx = random.randint(-1, 1) * TILE_WIDTH
            dy = random.randint(-1, 1) * TILE_HEIGHT
            self.owner.move(dx, dy)
            self.num_turns -= 1

        else:
            self.owner.ai = self.old_ai
            message('The ' + self.owner.name + ' is no longer confused!', LIGHT_YELLOW)


class Tile:
    def __init__(self, blocked, x, y, block_sight=None):
        self.blocked = blocked

        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight
        self.x = x
        self.y = y
        self.visible = False
        self.explored = False
        self.room = None
        self.entity = None
        self.item = None


class Camera:
    def __init__(self, target):
        self.target = target
        self.width = SCREEN_WIDTH
        self.height = SCREEN_HEIGHT + TILE_HEIGHT
        self.x = self.target.x - int(self.width / 2)
        self.y = self.target.y - int(self.height / 2)
        self.center_x = self.x + int(self.width / 2)
        self.center_y = self.y + int(self.height / 2)
        self.right = self.x + self.width
        self.bottom = self.y + self.height
        self.tile_map_x = int(self.x / TILE_WIDTH)
        self.tile_map_y = int(self.y / TILE_HEIGHT)
        self.tile_map_width = int(self.width / TILE_WIDTH)
        self.tile_map_height = int(self.height / TILE_HEIGHT)
        self.x_range = self.tile_map_x + self.tile_map_width
        self.y_range = self.tile_map_y + self.tile_map_height
        self.fix_position()

    def update(self):
        if self.target.x != self.center_x:
            x_move = self.target.x - self.center_x
            self.x += x_move
            self.center_x += x_move
            self.right += x_move
            self.tile_map_x = int(self.x / TILE_WIDTH)
            self.x_range = self.tile_map_x + self.tile_map_width
        if self.target.y != self.center_y:
            y_move = self.target.y - self.center_y
            self.y += y_move
            self.center_y += y_move
            self.bottom += y_move
            self.tile_map_y = int(self.y / TILE_HEIGHT)
            self.y_range = self.tile_map_y + self.tile_map_height
        self.fix_position()

    def fix_position(self):
        if self.x < 0:
            self.x = 0
            self.center_x = self.x + int(self.width / 2)
            self.right = self.x + self.width
            self.tile_map_x = int(self.x / TILE_WIDTH)
            self.x_range = self.tile_map_x + self.tile_map_width
        elif self.right > MAP_WIDTH:
            self.right = MAP_WIDTH
            self.x = self.right - self.width
            self.center_x = self.x + int(self.width / 2)
            self.tile_map_x = int(self.x / TILE_WIDTH)
            self.x_range = self.tile_map_x + self.tile_map_width
        if self.y < 0:
            self.y = 0
            self.center_y = self.y + int(self.height / 2)
            self.bottom = self.y + self.height
            self.tile_map_y = int(self.y / TILE_HEIGHT)
            self.y_range = self.tile_map_y + self.tile_map_height
        elif self.bottom > MAP_HEIGHT:
            self.bottom = MAP_HEIGHT
            self.y = self.bottom - self.height
            self.center_y = self.y + int(self.height / 2)
            self.tile_map_y = int(self.y / TILE_HEIGHT)
            self.y_range = self.tile_map_y + self.tile_map_height



if __name__ == "__main__":
    main()
