import rg
import operator

class Robot:
    def act(self, game): 
        adjacent_robots = self.get_adjacent_robots(game)
        adjacent_friendlies = self.get_adjacent_robots(game, operator.__eq__)
        adjacent_enemies = self.get_adjacent_robots(game, operator.__ne__)

        all_enemies = self.get_all_robots(game, operator.__ne__)
        def get_weakest_enemy_location():
            tgt = (0, 0)
            min_hp = 1000
            for loc,bot in all_enemies.items():
                if bot.hp < min_hp:
                    tgt = loc
                    min_hp = bot.hp
            return tgt

        def get_first_enemy_location():
            min_bot_id = 1000000
            l = (9, 9)
            for loc,bot in all_enemies.items():
                if bot['player_id'] < min_bot_id:
                    min_bot_id = bot['player_id']
                    l = bot.location
            # return list(all_enemies.keys())[offset]
            return l

        def get_weakest_adjacent_enemy_location():
            l = (9, 9)
            lowest_hp = 10000
            for loc,bot in adjacent_enemies.items():
                if bot.hp < lowest_hp:
                    lowest_hp = bot.hp
                    l = bot.location
            # return list(all_enemies.keys())[offset]
            return l

        first_enemy_location = get_first_enemy_location()
        weakest_enemy_location = get_weakest_enemy_location()
        weakest_adjacent_enemy = get_weakest_adjacent_enemy_location()

        # if there are enemies around, attack them
        if len(adjacent_enemies) >= 1 and len(adjacent_enemies) < 3:
            if self.hp < 10:
                return ['suicide']
            return ['attack', weakest_adjacent_enemy]
        elif len(adjacent_enemies) >= 3:
            return ['suicide']
            
        # move toward the center, if moving there would not put you in range of 2 robots
        target_pos = rg.toward(self.location, weakest_enemy_location)

        # figure out if any friendly robots would also want to move to our target
        adjacent_to_target_friendlies = self.get_adjacent_robots_to(target_pos, game, operator.__eq__)
        def has_priority():
            for loc,bot in adjacent_to_target_friendlies.items():
                their_target_pos = rg.toward(loc, weakest_enemy_location)
                # check if bots will collide
                if their_target_pos == target_pos:
                    # if i'm more bottom or more to the right, i'll take priority
                    if self.location[0] < loc[0] or self.location[1] < loc[1]:
                        #don't move then, do something else
                        return False
            return True

        if self.location != target_pos and has_priority():
            if 'obstacle' not in rg.loc_types(target_pos):
                adjacent_to_target_enemies = self.get_adjacent_robots_to(target_pos, game, operator.__ne__)
                # if len(adjacent_to_target_enemies) <= 1 or len(adjacent_to_target_enemies) >= 3:
                return ['move', target_pos]
        
        # if self.location == rg.CENTER_POINT
            # return ['move', rg.toward(self.location, all_enemies[0].location)]
        # if we're in the center, stay put
        # if self.location == rg.CENTER_POINT:
            # return self.guard()
        
        #if we couldn't decide to do anything else, just guard
        return self.guard()
    
    def toward(curr, dest):
        if curr == dest:
            return curr

        x0, y0 = curr
        x, y = dest
        x_diff, y_diff = x - x0, y - y0

        if abs(x_diff) < abs(y_diff):
            return (x0, y0 + y_diff / abs(y_diff))
        elif abs(x_diff) == abs(y_diff):
            # BROKEN FIX
            return (0, 0)
        else:
            return (x0 + x_diff / abs(x_diff), y0)

    def guard(self):
        return ['guard']
    
    def get_all_robots(self, game, player_comparator=None):
        def generate():
            for loc,bot in game.get('robots').items():
                if player_comparator == None or player_comparator(self.player_id, bot.player_id):
                    yield (loc, bot)

        return dict(generate())

    def get_adjacent_robots_to(self, some_location, game, player_comparator=None):
 
        def generate():
            for loc,bot in game.get('robots').items():
                if rg.wdist(loc, some_location) <= 1:
                    if player_comparator == None or player_comparator(self.player_id, bot.player_id):
                        yield (loc, bot)
 
        return dict(generate())
            
    def get_adjacent_robots(self, game, player_comparator=None):
        return self.get_adjacent_robots_to(self.location, game, player_comparator)
