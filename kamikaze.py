import rg
import operator

class Node:
    opened = None
    closed = None
    by = None
    parent = None

    def __init__(self, x, y, walkable=True):
        self.x = x
        self.y = y
        self.walkable = walkable

class Robot:

    def __init__(self):
        self.nodemap = []

    @staticmethod
    def new(robot_dict={}):
        bot = Robot()
        bot.location = robot_dict.location
        bot.hp = robot_dict.hp
        bot.player_id = robot_dict.player_id
        bot.robot_id = robot_dict.robot_id
        return bot

    # act should take meta level as an argument
    # meta=0 means don't consider what other bots might do
    # meta=1 means consider what other bots might do,
        # but not what they'll do as a consequence of you thinking about whay they'll do
    # meta=2 is next level meta
    def act(self, game):
        board_size = (rg.CENTER_POINT[0] * 2) + 1
        # print("board is "+str(board_size)+" large")
        self.generate_nodemap(game, board_size)

        path = self.nice_find_path(self.location, rg.CENTER_POINT, game)

        # print(str(len(path))+" long path!!!")

        print(path)
        if len(path) == 0:
            print("no path found!!! from "+str(self.location))
            import sys
            sys.exit(1)
            return ['guard']
        else:
            print("#############      awesome, we got a path      ###########")
            target = tuple(path[1])
            print(target)
            # import sys
            # sys.exit(1)
            return ['move', target]


    def goodact(self, game, meta=1): 
        adjacent_robots = self.get_adjacent_robots(game)
        adjacent_friendlies = self.get_adjacent_robots(game, operator.__eq__)
        adjacent_enemies = self.get_adjacent_robots(game, operator.__ne__)

        all_enemies = self.get_all_robots(game, operator.__ne__)
        all_friendlies = self.get_all_robots(game, operator.__eq__)

        # "The value of the key parameter should be a function that takes 
        # a single argument and returns a key to use for sorting purposes."
        def query(bot_dict, sorting_function, offset=0):
            organized = sorted(bot_dict.items(), key=sorting_function)
            # returns a list of tuples, [(key, value),... ]
            return organized

        def get_weakest_enemy(offset=0):
            return query(all_enemies, lambda t: t[1].hp)[offset][1]

        def get_weakest_adjacent_enemy(offset=0):
            return query(adjacent_enemies, lambda t: t[1].hp)[offset][1]

        # 1) get out of a spawn if it's going to kill you
        first_turn = 0 # not sure if turn 1 or turn 0 is the first turn
        if game['turn'] % 10 == first_turn:
            if 'spawn' in rg.loc_types(self.location):
                for loc in rg.locs_around(self.location, ['invalid', 'spawn', 'obstacle']):
                    # the first good place!
                    if loc not in game['robots'].keys():
                        return ['move', loc]
                    a_robot = game['robots'][loc]
                    if meta > 0 and a_robot.player_id == self.player_id:
                        rbot = Robot.new(a_robot)
                        raction = rbot.act(game, meta-1)
                        if raction in ['move']:
                            return ['move', loc]

        # For now we're a hunter
        # we're going to target the weakest enemy first,
        # unless there's somebody else closer, in which case we'll go for them

        # first_enemy_location = get_first_enemy_location()
        weakest_enemy = get_weakest_enemy()
        target_enemy = weakest_enemy
        
        if len(adjacent_enemies) > 0:
            weakest_adjacent_enemy = get_weakest_adjacent_enemy()
            target_enemy = weakest_adjacent_enemy

        # STRATEGY HERE:
        # move towards the weakest enemy
        ultimate_target = target_enemy.location

        target_pos = rg.toward(self.location, ultimate_target)

        # figure out if any friendly robots would also want to move to our target
        adjacent_to_target_friendlies = self.get_adjacent_robots_to(target_pos, game, operator.__eq__)

        '''
        # ###############
        # Offensive Code
        todo:
        fix: sometimes it just suicides even though no one is around to hit
        # ###############
        '''

        # if there are enemies around, attack them
        # also consider suiciding when it will guarantee a kill, meaning enemy < 15 hp
        suicide_threshold = 3 # 3 is better than 4 with 83% confidence, 7-42, 10-34 vs 3-43, 7-38
        # 4 is [55, 30, 15] against 3

        def has_suicide_priority():
            adjacent_allies_to_target_enemy = self.get_adjacent_robots(game, operator.__eq__)
            weakest_allies_next_to_adjacent_target_enemy = query(adjacent_allies_to_target_enemy, lambda t: t[1].hp)
            return self.location == weakest_allies_next_to_adjacent_target_enemy[0][0]

        if len(adjacent_enemies) > 0 and len(adjacent_enemies) < suicide_threshold:
            # following line is better by 102-20-17 over just self.hp < 10
            # inspired by peterm's stupid 2.6 bot
            # assuming all adjacent enemies attacked me, if I would die
            # i should instead suicide
            if self.hp < (rg.settings.attack_range[1]*len(adjacent_enemies)):
                return ['suicide']
            # IDEA: if i could kill the enemy with 1 suicide instead of two attacks
            # NOTE: if multiple allies are going for this target, i'll actually lose too many bots
            # bad idea, 0-20 against self
            # if weakest_adjacent_enemy.hp < 15 and weakest_adjacent_enemy.hp > 8 and has_suicide_priority():
                # return ['suicide']

            # if you could kill 2+ bots by suidiciding, do it
            potential_kills = 0
            for loc,bot in adjacent_enemies.items():
                if bot.hp <= rg.settings.suicide_damage:
                    potential_kills += 1
                if meta > 0:
                    # consider likelihood of enemy running away, 
                    # we'll assume the other guy is smart if he's winning
                    smart = len(all_enemies) > len(all_friendlies)
                    if smart:
                        # determine if he can run away
                        places_to_run = set(rg.locs_around(loc, ['invalid', 'obstacle'])) - set(rg.locs_around(self.location))
                        places_to_run = filter(lambda x: x not in rg.locs_around(self.location), rg.locs_around(loc, ['invalid', 'obstacle']))
                        # assume he WILL run away if he can
                        # if he's super smart, assume his robot allies
                        # will move out of the way for him
                        if len(places_to_run) > 0:
                            potential_kills -= 1

            # this is meta level 1
            if meta > 0:
                # subtract potential kills if allied bots would 
                # kill the target with normal attacks anyway
                for loc,bot in adjacent_to_target_friendlies.items():
                    metabot = Robot.new(bot)
                    metaaction = metabot.act(game, meta-1)
                    if metaaction[0] == 'attack':
                        if metaaction[1] == target_enemy.location:
                            if target_enemy.hp <= (rg.settings.attack_range[0]*2):
                                potential_kills -= 1

            if potential_kills >= 1.5:
                return ['suicide']

            # should also avoid over-killing robots
            return ['attack', weakest_adjacent_enemy.location]
        elif len(adjacent_enemies) >= suicide_threshold:
            return ['suicide']
            
        # this function breaks on the server, 
        # so it's temporarily not being used
        # as the has_priority function
        def has_priority(action): # if i'm a newer bot, I have priority
            for loc,bot in adjacent_to_target_friendlies.items():
                mbot = Robot.new(bot)
                maction = mbot.act(game, meta-1)
                if maction == action:
                    # self.robot_id is bugged out right now
                    self_robot_id = game['robots'][self.location].robot_id
                    print("resolving priority, self: "),
                    print(self_robot_id),
                    print("vs"),
                    print(bot.robot_id)
                    print(self_robot_id > bot.robot_id)
                    if self_robot_id > bot.robot_id: # larger id means older robot
                        return False
            return True

        def byloc_has_priority(action): # if i'm more bottom or more to the right, i'll take priority
            for loc,bot in adjacent_to_target_friendlies.items():
                mbot = Robot.new(bot)
                maction = mbot.act(game, meta-1)
                if maction == action:
                    if self.location[0] < loc[0] or self.location[1] < loc[1]:
                        #don't move then, do something else
                        return False
            return True

        '''
        # ###############
        # Movement Code
        todo:
        dodge enemy suicides
        dodge preemtive attacks against me
        priority is not actually resolving conflicted moves for some reason
        if i'm moving towards X, he will preemptively attack the spot i will occupy
        # ###############
        '''
        def is_move_possible(robot, t_pos):
            # determine if the tile is even walkable
            if True in [(robot.location == t_pos), ('obstacle' in rg.loc_types(t_pos)), ('invalid' in rg.loc_types(t_pos))]:
                return False
            # determine if the IS OCCUPIED and/or WILL STAY occupied
            if (meta == 0 or has_priority(['move', t_pos])) and t_pos in game['robots']:
                if meta > 0 and t_pos in all_friendlies:
                    rbot = Robot.new(all_friendlies[t_pos])
                    raction = rbot.act(game, meta-1)
                    # figure out if ally will move out of the way
                    if raction[0] == 'suicide':
                        return True
                    elif raction[0] == 'move' and raction[1] not in [t_pos, robot.location]:
                        return True
                return False
            return True


        if is_move_possible(self, target_pos):
            return ['move', target_pos]
        else:
            alternatives = {}
            for loc in rg.locs_around(self.location, ['invalid', 'obstacle']):
                if loc != target_pos and is_move_possible(self, loc):
                    alternatives[loc] = rg.wdist(self.location, loc)
            if len(alternatives) > 0:
                best_alt = sorted(alternatives.iteritems(), key=operator.itemgetter(1))[0][0]
                return ['move', best_alt]
        
        #if we couldn't decide to do anything else, just guard
        return self.guard()

    # same idea as rg.toward but, this will consider other robots as path blockers

    '''
    ##########################################################################################
    # PATHFINDING STARTS HERE
    inspired by:
    https://github.com/qiao/PathFinding.js/blob/master/src/finders/BiBreadthFirstFinder.js
    ##########################################################################################
    '''

    # bi-directional best first search pathfinder
    @staticmethod
    def check_walkable(loc, game):
        # if True in [(loc in game['robots']), ('obstacle' in rg.loc_types(loc)), ('invalid' in rg.loc_types(loc))]:
        if True in [('obstacle' in rg.loc_types(loc)), ('invalid' in rg.loc_types(loc))]:
            return False
        # if it's a spawning turn
        # if 'spawn' in rg.loc_types(loc) and game['turn'] % 10 == 1:
        #     return False
        return True

    # def check_walkable(self, loc, game):
    #     if True in [('obstacle' in rg.loc_types(loc)), ('invalid' in rg.loc_types(loc))]:
    #         return False
    #     # if it's a spawning turn
    #     if 'spawn' in rg.loc_types(loc) and game['turn'] % 10 == 0:
    #         return False

    def generate_nodemap(self, game, board_size):
        # nodemap = []
        # print("generated a "+str(board_size)+" square grid")
        for x in range(board_size):
            self.nodemap.append([])
            for y in range(board_size):
                self.nodemap[x].append(Node(x, y, Robot.check_walkable((x, y), game)))
        # return nodemap


    @staticmethod 
    def get_neighbors(node, grid, allow_diagonal=False, dont_cross_corners=True):
        x0 = node.x
        y0 = node.y
        neighbors = []
        for loc in rg.locs_around((x0, y0)):
            if loc != (x0, y0):
                x = loc[0]
                y = loc[1]
                # print("checking "+str(x)+", "+str(y))
                yes = grid[x][y].walkable
                # print("-- "+str(yes))
                if yes:
                    neighbors.append(grid[x][y])
        # currently the code for diagonals is unnecessary and thus missing
        # print("      getting "+str(len(neighbors))+" neighbors")
        if allow_diagonal == False:
            return neighbors

    @staticmethod
    def backtrace(node):
        path = [[node.x, node.y]]
        while node.parent:
            node = node.parent
            path.append([node.x, node.y])

        path.reverse()
        return path

    @staticmethod
    def bi_backtrace(node_a, node_b):
        path_a = Robot.backtrace(node_a)
        path_b = Robot.backtrace(node_b)
        path_b.reverse()
        return operator.add(path_a, path_b)

    def nice_find_path(self, start, end, game):
        path = self.find_path(start[0], start[1], end[0], end[1], game)
        return path

    def find_path(self, startX, startY, endX, endY, game):
        BY_START = 0
        BY_END = 1
        start_node = self.nodemap[startX][startY]
        end_node = self.nodemap[endX][endY]
        start_open_list = [start_node]
        end_open_list = [end_node]

        start_node.opened = True
        start_node.by = BY_START

        start_node.opened = True
        start_node.by = BY_START
        while (len(start_open_list) > 0) and (len(end_open_list) > 0):
            # print("----------")
            # print("searching "+str(len(start_open_list)) + " plus " + str(len(end_open_list))+" nodes")

            node = start_open_list.pop(0)
            # print("    now  looking at "+str(node.x)+", "+str(node.y))
            node.closed = True
            neighbors = Robot.get_neighbors(node, self.nodemap, allow_diagonal=False, dont_cross_corners=True)
            for neighbor in neighbors:
                if neighbor.closed:
                    continue
                if neighbor.opened:
                    # if this node has been inspected by the,
                    # reversed search, then a path has been found
                    if neighbor.by == BY_END:
                        path = Robot.bi_backtrace(node, neighbor)
                        return path
                    continue
                neighbor.parent = node
                neighbor.opened = True
                neighbor.by = BY_START
                start_open_list.append(neighbor)

            # expand end open list
            node = end_open_list.pop(0)
            # print("   also looking at "+str(node.x)+", "+str(node.y))
            node.closed = True
            neighbors = Robot.get_neighbors(node, self.nodemap, allow_diagonal=False, dont_cross_corners=True)
            for neighbor in neighbors:
                if neighbor.closed:
                    continue
                if neighbor.opened:
                    if neighbor.by == BY_START:
                        path = Robot.bi_backtrace(neighbor, node)
                        return path
                    continue
                neighbor.parent = node
                neighbor.opened = True
                neighbor.by = BY_END
                end_open_list.append(neighbor)

        return []


    # @staticmethod
    # def make_path(curr, dest, game):
    #     next_step = Robot.toward(curr, dest, game)
    #     path = []
    #     if next_step == dest:

    # @staticmethod
    # def toward(curr, dest, game):

    #     if curr == dest:
    #         return curr

    #     x0, y0 = curr
    #     x, y = dest
    #     x_diff, y_diff = x - x0, y - y0

    #     next_step = (0, 0)
    #     def h_move():
    #         return (x0 + x_diff / abs(x_diff), y0)

    #     def v_move():
    #         return  (x0, y0 + y_diff / abs(y_diff))

    #     if abs(x_diff) < abs(y_diff):
    #         next_step = v_move()
    #     else abs(x_diff) > abs(y_diff):
    #         next_step = h_move()
    #     # elif abs(x_diff) == abs(y_diff):
    #     #     if x0 > y0:
    #     #         if 
    #     #         next_step = 

    #     # if x_diff <= 1 and y_diff <= 1:
    #     return next_step

    def guard(self):
        return ['guard']
    
    def get_all_robots(self, game, player_comparator=None, exclusive=False):
        def generate():
            for loc,bot in game.get('robots').items():
                if loc != self.location or exclusive == False:
                    if player_comparator == None or player_comparator(self.player_id, bot.player_id):
                        yield (loc, bot)

        return dict(generate())

    # NOTE: Excludes the location in question!
    def get_adjacent_robots_to(self, some_location, game, player_comparator=None, exclusive=True):
        def generate():
            for loc,bot in game.get('robots').items():
                if loc != some_location or exclusive == False:
                    if rg.wdist(loc, some_location) <= 1:
                        if player_comparator == None or player_comparator(self.player_id, bot.player_id):
                            yield (loc, bot)
     
        return dict(generate())
            
    def get_adjacent_robots(self, game, player_comparator=None):
        return self.get_adjacent_robots_to(self.location, game, player_comparator)
