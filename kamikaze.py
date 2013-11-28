import rg
import operator
from time import time
import heapq
import sys
import random
import math

class Node(object):
    def __init__(self, x, y, walkable=True):
        self.x = x
        self.y = y
        self.walkable = walkable
        self.opened = False
        self.closed = False
        self.by = None
        self.parent = None

timings = {}

class Robot:
    """
    # NOTE: This is a god damned LIE
    # robots are not actually instantiated, it only ever creates one robot, 
    # and then changes it's attributes and calls .act
    """
    # def __init__(self):
    #     self.nodemap = []

    def testact(self, game, meta=2):
        # self.__init__() #Calling __init__ because of LIES
        target = rg.CENTER_POINT

        if self.location == target:
            return self.guard()

        for loc, bot in game.get('robots').items():
            if bot.player_id != self.player_id:
                if rg.dist(loc, self.location) <= 1:
                    return self.attack(loc)

        t0 = time()
        path = astar_find_path(self.location, target)
        t = time()
        print("A Star Pathfinding took "+str((t-t0)*1000)+" milliseconds. "+str(len(path))+" steps.")

        next_step = path[1]
        
        # t0 = time()
        # path = self.nice_find_path(self.location, target, game)
        # t = time()
        # print("Best-First Pathfinding took "+str((t-t0)*1000)+" milliseconds. "+str(len(path))+" steps.")

        if len(path) > 1:

            print(next_step)
            print("#############      awesome, we got a path      ###########")
            return self.move(next_step)

        print("CRAP: No path found from "+str(self.location))
        return self.guard()

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
    def timingact(self, game, meta=2):
        ts = time()
        action = self.realact(game, meta)
        tf = time()
        ms = round((tf-ts)*1000, 4)
        turn = game['turn']
        if turn in timings:
            timings[turn] += ms
        else:
            if (turn-1) in timings:
                print("turn "+str(turn-1)+" took "+str(timings[(turn-1)])+" milliseconds")
            timings[turn] = ms
        return action

    def act(self, game, meta=2): 
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
            if len(organized) == 0:
                print('found nothing')
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

        if len(all_enemies) == 0:
            print('---$$$$$      There are no enemies remaining!      $$$$$---')

        # For now we're a hunter
        # we're going to target the weakest enemy first,
        # unless there's somebody else closer, in which case we'll go for them

        # first_enemy_location = get_first_enemy_location()
        weakest_enemy = get_weakest_enemy()
        target_enemy = weakest_enemy
        
        if len(adjacent_enemies) > 0:
            weakest_adjacent_enemy = get_weakest_adjacent_enemy()
            target_enemy = weakest_adjacent_enemy

        # def nearest_of_x_weakest_enemies(x=3):


        # STRATEGY HERE:
        # move towards the weakest enemy
        ultimate_target = target_enemy.location

        path = astar_find_path(self.location, ultimate_target)

        next_step = path[1]

        # next_step = rg.toward(self.location, ultimate_target)

        # figure out if any friendly robots are near our next step, this includes us
        adjacent_to_target_friendlies = self.get_adjacent_robots_to(next_step, game, operator.__eq__)

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
                if meta > 1:
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
                simul_attackers = 0
                for loc,bot in adjacent_to_target_friendlies.items():
                    if loc == self.location:
                        metaaction = self.attack(target_enemy.location)
                    else:
                        metabot = Robot.new(bot)
                        metaaction = metabot.act(game, meta-1)

                    if metaaction[0] == 'attack':
                        if metaaction[1] == target_enemy.location:
                            simul_attackers += 1

                if target_enemy.hp <= (rg.settings.attack_range[0]*simul_attackers):
                    potential_kills -= 1




            if potential_kills >= 1.5:
                return ['suicide']

            # should also avoid over-killing robots
            return ['attack', weakest_adjacent_enemy.location]
        elif len(adjacent_enemies) >= suicide_threshold:
            return ['suicide']

        '''
        # ###############
        # Movement Code
        conflict resolution is still buggy
            - if a and b want to go to L, and L is already occupied by c,
            c gets out, but a and b hit each other
            - if a wants to move into a space enemy b happens to as well, it does this continuously, huurting itslef
            - 
        todo:
        * dodge enemy suicides
        dodge preemtive attacks against me
        # ###############
        '''

        # if i'm a newer bot, I have priority
        def has_priority(action): 
            for loc,bot in adjacent_to_target_friendlies.items():
                if self.robot_id == bot.robot_id:
                    continue
                mbot = Robot.new(bot)
                maction = mbot.act(game, meta-1)
                if maction == action:
                    print("resolving priority, "+str(maction)+" "+str(self.robot_id)+" at "+str(self.location)+" vs "+str(bot.robot_id)+" at "+str(bot.location))
                    winrar = self.robot_id < bot.robot_id
                    if winrar == False:
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

        def is_move_possible(robot, t_pos):
            # determine if the tile is even walkable
            if not self.check_walkable(t_pos, game):
                return False
            # determine if the IS OCCUPIED and/or WILL STAY occupied

            if (t_pos in game['robots']): # is currently occupied
                bot = game['robots'][t_pos]
                if meta > 0 and bot.player_id == self.player_id:
                    # let's see if an ally will move out of the way, to let us pass
                    rbot = Robot.new(bot)
                    raction = rbot.act(game, meta-1)
                    # should be fine, but may want to test above
                    # figure out if ally will move out of the way
                    if raction[0] in ['attack', 'guard']:
                        return False

                    if raction[0] == 'suicide':
                        # return True # don't return because other reasons may prevent uis from moving
                        seomthing = True
                    elif (raction[0] == 'move'): # maybe also check if it's not moving towrds us
                        seomthing = True
                        # return True # don't return because other reasons may prevent uis from moving
                else:
                    return False

            if meta > 0:
                if not has_priority(['move', t_pos]):
                    # print("#"+str(self.robot_id)+" @ "+str(self.location)+' cannot move due to priority')
                    return False

            # if (t_pos in game['robots']) or (meta == 0 or has_priority(['move', t_pos])):
            #     if meta > 0 and t_pos in adjacent_to_target_friendlies:
            #         rbot = Robot.new(all_friendlies[t_pos])
            #         raction = rbot.act(game, meta-1)
            #         # figure out if ally will move out of the way
            #         if raction[0] == 'suicide':
            #             # return True
            #         elif raction[0] == 'move' and raction[1] not in [t_pos, robot.location]:
            #             # return True
            #     else:
            #         return False

            return True

        def try_move_to(t):
            if is_move_possible(self, t):
                return ['move', t]
            else:
                # print('considering alternatives')
                alternatives = {}
                for loc in rg.locs_around(self.location, ['invalid', 'obstacle']):
                    if loc != t and is_move_possible(self, loc):
                        alternatives[loc] = rg.dist(self.location, loc)
                if len(alternatives) > 0:
                    best_alt = sorted(alternatives.iteritems(), key=operator.itemgetter(1))[0][0]
                    return ['move', best_alt]

        m = try_move_to(next_step)
        if m:
            return m
        #if we couldn't decide to do anything else, just guard
        return self.guard()


    # interface to robot action, in case the API changes
    ############################################################
    def guard(self):
        return ['guard']

    def attack(self, loc):
        return ['attack', loc]

    def move(self, loc):
        return ['move', loc]

    ############################################################
    
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


    def check_walkable(self, loc, game):
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


    # same idea as rg.toward but, this will consider other robots as path blockers

    '''
    ##########################################################################################
    # PATHFINDING STARTS HERE
    inspired by:
    bi-directional best first search pathfinder:

    https://github.com/qiao/PathFinding.js/blob/master/src/finders/BiBreadthFirstFinder.js
    ##########################################################################################
    '''

    def generate_nodemap(self, game, board_size):
        self.nodemap = []
        # print("generated a "+str(board_size)+" square grid")
        for x in range(board_size):
            self.nodemap.append([])
            for y in range(board_size):
                self.nodemap[x].append(Node(x, y, self.check_walkable((x, y), game)))
        # return nodemap


    def get_neighbors(self, node, allow_diagonal=False, dont_cross_corners=True):
        # print('- Getting Neighbors:')
        x0 = node.x
        y0 = node.y
        neighbors = []
        for loc in rg.locs_around((x0, y0)):
            if loc != (x0, y0):
                x = loc[0]
                y = loc[1]
                # print("checking "+str(x)+", "+str(y))
                yes = self.nodemap[x][y].walkable
                # print("-- "+str(yes))
                if yes:
                    neighbors.append(self.nodemap[x][y])
        # currently the code for diagonals is unnecessary and thus missing
        # print("= got "+str(len(neighbors))+" neighbors")
        if allow_diagonal == False:
            return neighbors

    def backtrace(self, node):
        path = [(node.x, node.y)]
        while node.parent:
            node = node.parent
            path.append((node.x, node.y))

        path.reverse()
        return path

    def bi_backtrace(self, node_a, node_b):
        path_a = self.backtrace(node_a)
        path_b = self.backtrace(node_b)
        path_b.reverse()
        return operator.add(path_a, path_b)

    def nice_find_path(self, start, end, game):
        board_size = (rg.CENTER_POINT[0] * 2) + 1
        self.generate_nodemap(game, board_size)
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

        # print("----- doing pathfinding -----")
        while (len(start_open_list) > 0) and (len(end_open_list) > 0):
            # print("searching "+str(len(start_open_list)) + " plus " + str(len(end_open_list))+" nodes")

            node = start_open_list.pop(0)
            # print("    now  looking at "+str(node.x)+", "+str(node.y))
            node.closed = True
            neighbors = self.get_neighbors(node, allow_diagonal=False, dont_cross_corners=True)
            for neighbor in neighbors:
                if neighbor.closed:
                    # print("closed!!")
                    continue
                if neighbor.opened:
                    # if this node has been inspected by the,
                    # reversed search, then a path has been found
                    if neighbor.by == BY_END:
                        path = self.bi_backtrace(node, neighbor)
                        return path
                    continue
                neighbor.parent = node
                neighbor.opened = True
                neighbor.by = BY_START
                start_open_list.append(neighbor)
                # print("queued neighbor start")

            # expand end open list
            node = end_open_list.pop(0)
            # print("   also looking at "+str(node.x)+", "+str(node.y))
            node.closed = True
            neighbors = self.get_neighbors(node, allow_diagonal=False, dont_cross_corners=True)
            for neighbor in neighbors:

                if neighbor.closed:
                    # print("closed!!")
                    continue
                if neighbor.opened:
                    if neighbor.by == BY_START:
                        path = self.bi_backtrace(neighbor, node)
                        return path
                    continue
                neighbor.parent = node
                neighbor.opened = True
                neighbor.by = BY_END
                end_open_list.append(neighbor)
                # print("queued neighbor end")

            # print("left to search "+str(len(start_open_list)) + " plus " + str(len(end_open_list))+" nodes")

        return []

# kill switch
# import sys
# sys.exit(1)

'''
##########################################################################################
# PATHFINDING Continues HERE
inspired by:
a start pathfinder

https://github.com/eshira/kapal
##########################################################################################
changes: 
kapal.inf -> inf

combined all files into one

commented out imports
'''
# __init__.py
##########################################################################################
inf = 1e100
##########################################################################################

# state.py
##########################################################################################
# import kapal

class State:
    pass

class State2d(State):
    def __init__(self, x=0, y=0):
        self.y = y
        self.x = x
    def __str__(self):
        return "(" + str(self.x) + ", " + str(self.y) + ")"

class State2dAStar(State2d):
    def __init__(self, x=0, y=0, g=inf, h=0, bp=None):
        State2d.__init__(self, x, y)
        self.g = g
        self.h = h
        self.bp = bp
    
    def reset(self):
        self.g = inf

    def __cmp__(self, other):
        # TODO: allow any key function?
        # heapq library is a min heap
        self_f = self.g + self.h
        other_f = other.g + other.h
        if self_f < other_f or (self_f == other_f and self.g > other.g):
            # priority(self) > priority(other), so self < other
            return -1
        elif self_f == other_f and self.g == other.g:
            return 0
        return 1

    def __str__(self):
        s = State2d.__str__(self) + "-->"
        if self.bp is None:
            s += "None"
        else:
            s += State2d.__str__(self.bp)
        s += ": g = " + str(self.g) + "; h = " + str(self.h)
        return s
##########################################################################################


# world.py
##########################################################################################
# from state import *

class World:
    """
    World is the base class for all other world types.
    This class shows the primitive functions that all other worlds
    should implement.

    An algorithm may assume that all the functions defined here are
    implemented for any world.
    """
    def succ(self, s):
        """
        Returns the successors of state s.
        """
        pass
    def pred(self, s):
        """
        Returns the predecessors of state s.
        """
        pass
    def c(self, s1, s2):
        """
        Returns the cost of moving from s1 to s2.
        """
        pass
    def h(self, s1, s2):
        """
        Returns the heuristic cost of s1 to s2.
        """
        pass
    def change_c(self, s1, s2, c):
        """
        Change the cost of moving from s1 to s2.
        """
        pass
    def reset(self):
        """
        An algorithm may reset the world. That is, the world
        forgets all previous knowledge and starts planning
        'from scratch'.
        """
        pass

class World2d(World):
    """
    World2d is a tile-based 2-d world representation.
    """

    def __init__(self, costs=None, state_type=State2d, diags=False, diags_mult=1.42):
        self.states = []
        self.costs = costs
        self.diags = diags
        self.diags_mult = diags_mult

        for r in range(len(costs)):
            world_l = []
            self.states.append(world_l)
            for c in range(len(costs[r])):
                world_l.append(state_type(r, c))

    def succ(self, s):
        # order: [1][2][3]        [ ][1][ ]
        #        [4][ ][5]   or   [2][ ][3]
        #        [6][7][8]        [ ][4][ ]

        succs = []
        for i in range(-1, 2):
            x = s.x + i
            for j in range(-1, 2):
                y = s.y + j 
                if not self.in_bounds(x, y):    # out of bounds
                    continue
                if x == s.x and y == s.y:   # self cannot have self as neigh
                    continue
                cost = self.costs[x][y]
                edge_count = abs(i) + abs(j)
                if edge_count == 2 and not self.diags:
                    continue    # ignore diags if requested
                elif edge_count == 2:
                    cost *= self.diags_mult     # diags allowed, so mult cost
                succs.append((self.states[x][y], cost))
        return succs

    def pred(self, s):
        return self.succ(s)

    def c(self, s1, s2):
        return costs[s2.x][s2.y]

    def h(self, s1, s2):
        # if self.diags:
        dy = abs(s2.y - s1.y)
        dx = abs(s2.x - s1.x)
        return math.sqrt(dx**2 + dy**2)
        # else:
        #     return abs(s2.y-s1.y) + abs(s2.x-s1.x)

    def change_c(self, s1, s2, c):
        if not self.in_bounds(s2.x, s2.y):
            return False
        self.costs[s2.x][s2.y] = c
        return True

    def reset(self):
        for r in self.states:
            for c in r:
                c.reset()

    def state(self, x, y):
        return self.states[x][y]

    def in_bounds(self, x, y):
        size_x, size_y = self.size()
        return y >= 0 and y < size_y and x >= 0 and x < size_x

    def size(self, col = 0):
        return (len(self.states), len(self.states[col]))

    def __str__(self):
        s = "World2d\n"
        s += "x size: " + str(len(self.states)) + "\n"
        s += "y size: " + str(len(self.states[0])) + "\n"
        return s
##########################################################################################


# algo.py
##########################################################################################
# import heapq
# from state import *
# from world import *
import sys
class Algo:
    """
    A base class for algorithms.

    All algorithms should inherit Algo and should overwrite Algo.plan.
    """
    def __init__(self, world, start, goal):
        self.world = world
        self.start = start
        self.goal = goal
    def plan(self):
        pass

class AStar(Algo):
    """
    A* algorithm.

    A* makes a couple of assumptions:
        - non-negative edge weights
        - heuristics function is consistent (and thus admissible)
            - http://en.wikipedia.org/wiki/Consistent_heuristic
    """

    def __init__(self, world, start=None, goal=None, backwards=True):
        Algo.__init__(self, world, start, goal)
        self.backwards = backwards
        self.open = []

    def plan(self):
        """
        Plans and returns the optimal path, from start to goal.
        """
        return list(self.__plan_gen())

    def __plan_gen(self):
        """
        Plans the optimal path via a generator.

        A generator that yields states as it is popped off
        the open list, which is the optimal path in A* assuming
        all assumptions regarding heuristics are held.

        The user should not call AStar.__plan_gen. Call
        AStar.plan instead. This is a generator for the sake of
        easy debugging; it is usually unsafe to use the yielded
        states as the path.
        """
        self.world.reset()      # forget previous search's g-vals
        goal = self.goal
        succ = self.world.succ  # successor function

        if self.backwards:
            self.goal.g = 0
            self.open = [self.goal]
            goal = self.start
            succ = self.world.pred  # flip map edges
        else:
            self.start.g = 0
            self.open = [self.start]

        # A*
        s = None
        while s is not goal and len(self.open) > 0:
            s = heapq.heappop(self.open)
            for n, cost in succ(s):
                if n.g > s.g + cost:
                    # s improves n
                    n.g = s.g + cost
                    n.h = self.h(n, goal)
                    n.bp = s
                    heapq.heappush(self.open, n)
            yield s

    def path(self):
        """
        Returns the path from goal to the first state with bp = None.

        This method assumes that 
        """
        p = []
        s = self.goal
        if self.backwards:
            s = self.start
        while s is not None:
            p.append(s)
            if s is not None:
                s = s.bp
        return p
        
    def h(self, s1, s2, h_func=None):
        """
        Returns the heuristic value between s1 and s2.

        Uses h_func, a user-defined heuristic function, if
        h_func is passed in.
        """
        if h_func is None:
            return self.world.h(s1, s2)
        else:
            return h_func(s1, s2)

class Dijkstra(AStar):
    """
    Classic Dijkstra search.

    Assumptions:
        - non-negative edge weights
    """
    def h(self, s1, s2, h_func=None):
        return 0

def rand_cost_map(x_size=1, y_size=1,  min_val=1, max_val=inf,
        flip=False, flip_chance=.1):
    """
    Returns a 2d cost matrix with random values.

    Args:
        y_size - width
        x_size - height
        min_val - minimum random value
        max_val - maximum random value
        flip - if True, then the value in each cell is either min_val
               or max_val;
               if False, then min_val <= value of cell <= max_val
        flip_chance - chance of getting a max_val (only if flip=True)
    """
    grid = []
    for i in range(x_size):
        row = []
        for j in range(y_size):
            if flip:
                if random.random() < flip_chance:
                    row.append(max_val) 
                else:
                    row.append(min_val)
            else:
                row.append(random.randint(min_val, max_val))
        grid.append(row)
    return grid


def check_walkable(loc, game=None):
    if not set(rg.loc_types(loc)).isdisjoint(set(['invalid', 'obstacle'])):
        return False
    if game and game['robots'][loc]:
        return False
    return True

def draw_map(dimensions=(10, 10), min_val=1, max_val=inf, game=None):
    x_size, y_size = dimensions
    grid = []
    for i in range(x_size):
        row = []
        for j in range(y_size):
            val = 1
            if check_walkable((i, j), game):
                row.append(min_val)
            else:
                row.append(max_val)
        grid.append(row)
    return grid

def astar_find_path(start=(3, 9), end=(9, 9), game=None):
    start_time = time()

    n = (rg.CENTER_POINT[0] * 2) + 1
    c = draw_map((n, n), 1, inf, game)
    w = World2d(c, state_type = State2dAStar)

    astar = AStar(w, w.state(end[0], end[1]), w.state(start[0], start[1]))
    path = astar.plan()

    total_time = time() - start_time

    dumbpath = map(lambda p: (p.x, p.y), path)
    # print("A Star Pathfinding took "+str((total_time)*1000)+" milliseconds. "+str(len(dumbpath))+" steps.")
    return dumbpath



##########################################################################################