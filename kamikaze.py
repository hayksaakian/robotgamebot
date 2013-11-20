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
        elif len(adjacent_enemies) >= 3:
            return ['suicide']
            
        # move toward the center, if moving there would not put you in range of 2 robots
        target_pos = rg.toward(self.location, rg.CENTER_POINT)
        if 'obstacle' not in rg.loc_types(target_pos):
            adjacent_to_target_enemies = self.get_adjacent_robots_to(target_pos, game, operator.__ne__)
            if self.location != target_pos:
                if len(adjacent_to_target_enemies) <= 1 or len(adjacent_to_target_enemies) >= 3:
                    return ['move', target_pos]
        
        # if we're in the center, stay put
        if self.location == rg.CENTER_POINT:
            return self.guard()
        
        #if we couldn't decide to do anything else, just guard
        return self.guard()
    
    def guard(self):
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
