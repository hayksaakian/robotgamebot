import rg
import operator

class Robot:
    def act(self, game):        
        adjacent_robots = self.get_adjacent_robots(game)
        adjacent_friendlies = self.get_adjacent_robots(game, operator.__eq__)
        adjacent_enemies = self.get_adjacent_robots(game, operator.__ne__)
        
        # if there are enemies around, attack them
        if len(adjacent_enemies) > 0 and len(adjacent_enemies) < 3:
            return ['attack', list(adjacent_enemies.keys())[0]]
        elif len(adjacent_enemies) >= 4:
            return ['suicide']
            
        # move toward the center, if moving there would not put you in range of 2 robots
        target_pos = rg.toward(self.location, rg.CENTER_POINT)
        if 'obstacle' not in rg.loc_types(target_pos):
            adjacent_to_target_enemies = self.get_adjacent_robots_to(target_pos, game, operator.__ne__)
            if len(adjacent_to_target_enemies) < 2:
            	return ['move', target_pos]
        
        # if we're in the center, stay put
        if self.location == rg.CENTER_POINT:
            return self.guard()
        
        return self.guard()
    
    def guard():
        return ['guard']
    
    
    def get_adjacent_robots_to(self, some_location, game, player_comparator=None):
 
        def generate():
            for loc,bot in game.get('robots').items():
                if rg.wdist(loc, some_location) <= 1:
                    if player_comparator == None or player_comparator(self.player_id, bot.player_id):
                        yield (loc, bot)
 
        return dict(generate())
            
    def get_adjacent_robots(self, game, player_comparator=None):
        return self.get_adjacent_robots_to(self.location, game, player_comparator)
    
    #deprecated function
    def robots_adjacent_to(position, game, of_player_id=None, player_comparator="=="):
        comparator_map = {}
        comparator_map["=="] = lambda a, b: a == b
        comparator_map["!="] = lambda a, b: a != b
        adjacent_robots = {}
        comp_func = comparator_map[player_comparator]
        for loc, bot in game.get('robots').items():
            if rg.wdist(loc, position) <= 1:
                if of_player_id == None or comp_func(of_player_id, bot.player_id):
                    adjacent_robots[loc] = bot
        return adjacent_robots
    
    
