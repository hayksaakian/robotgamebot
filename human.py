import ast
import rg

char_map = {
    "invalid":None,
    "normal":" ",
    "spawn":"+",
    "obstacle":"-",
    "enemy":"E",
    "ally":"A",
    "self":"S",
    "directions":{
        "up":"^",
        "down":"v",
        "left":"<",
        "right":">",
        "w":"^",
        "s":"v",
        "a":"<",
        "d":">"
    },
    "actions":{
        "attack":"Q",
        "move":"M",
        "suicide":"X",
        "guard":"#"
    }
}
loc_type_priority = [
    "invalid",
    "obstacle",
    "spawn",
    "normal"
]

possible_actions = [
    "guard",
    "suicide",
    "attack",
    "move"
]
actions_requiring_location = [
    "attack",
    "move"
]
action_synonyms = {
    "attack" : ["a", "atk", "attack", "q"],
    "guard" : ["g", "grd", "guard", "defend"],
    "move" : ["m", "go", "goto", "mv", "move", "e"],
    "suicide" : ["s", "die", "suicide"]
}
back_indicators = [
    "back",
    "cancel",
    "no",
    "action",
    "exit",
    "undo"
]
directions = {
    "left":(-1, 0),
    "right":(1, 0),
    "up":(0, -1),
    "down":(0, 1),
    "a":(-1, 0),
    "d":(1, 0),
    "w":(0, -1),
    "s":(0, 1)
}
def first_direction_by_value(v):
    for k, val in directions.items():
        if val == v:
            return k

quick_actions = ["qa", "qs", "qd", "qw", "ea", "es", "ed", "ew"]
action_cache = {}
# action_cache[(turn, robot_location)] = action

global turn
turn = None
class Robot:

    def act(self, game):
        global turn
        if turn != game['turn']:
            print("     ~~~~~     NEW TURN     ~~~~~     ")
            turn = game['turn']
        print("     ~~~~~     TURN "+str(turn)+"/100     ~~~~~     ")


        self.print_board(game)
        action = self.prompt_human(game)
        print(str(self.location)+" will try to "+str(action))
        action_cache[(game['turn'], self.location)] = action
        return action

    def prompt_human(self, game):
        action = None
        location = None
        while(action not in possible_actions):
            print(str(self.location)+" ("+str(self.hp)+"/50hp) What will this Robot do?")
            action = raw_input()
            if action in quick_actions:
                qa = self.quick_action(action)
                action = qa[0]
                location = qa[1]
                # print(qa)
            else:
                action = self.parse_action(action)

        if action in actions_requiring_location:
            while(self.validate_action([action, location], game) == False):
                print("Where should this Robot "+action+"?")
                rloc = raw_input()
                if rloc in back_indicators:
                    break

                if rloc in directions:
                    location = self.add_tuples(directions[rloc], self.location)
                else:
                    location = ast.literal_eval(rloc)
            if location == None:
                return self.prompt_human(game)
            else:
                return [action, location]
        else:
            return [action]

    def subtract_tuples(self, a, b):
        return (a[0]-b[0], a[1]-b[1])

    def add_tuples(self, a, b):
        return (a[0]+b[0], a[1]+b[1])
        
    def validate_action(self, formatted_action, game):
        if len(formatted_action) > 1:
            if formatted_action[1] == None:
                return False
            if formatted_action[0] == "move":
                return formatted_action[1] in rg.locs_around(self.location)
        return True #placeholder

    def parse_action(self, action):
        for a in action_synonyms:
            if action in action_synonyms[a]:
                action = a
                break
        return action

    def quick_action(self, action):
        parts = list(action) #str.split by characters
        result_action = [self.parse_action(parts.pop(0))]
        if len(parts) > 0:
            result_action.append(self.add_tuples(directions[parts.pop(0)], self.location))
        return result_action

    def print_board(self, game):
        board_size = (rg.CENTER_POINT[0] * 2) + 1
        space_w = 4
        space_h = 2
        rows = map(lambda i: [], range(board_size))

        def nice_number(n):
            return " "+(str(n) if n >=  10 else " "+str(n))
        def draw(l):
            if l == self.location:
                k = "self"
            elif l in game['robots']:
                k = "ally" if game['robots'][l].player_id == self.player_id else "enemy"
            else:
                loc_types = sorted(rg.loc_types(l), key=lambda t:loc_type_priority.index(t))
                k = loc_types[0]

            if k in char_map:
                k = char_map[k]
            return k    

        for y in range(board_size):
            for x in range(board_size):
                l = (x, y)
                cell = []
                # example:
                # SSSS # currently selected robot
                # 39hp
                # AAQ> # ally attacking right
                # 20hp
                for h in range(space_h):
                    r = []
                    for w in range(space_w):
                        if l in game['robots']:
                            if (w >= 2 and w <= 3) and h == 0:
                                if w == 2 and (game['turn'], l) in action_cache:
                                    act = action_cache[(game['turn'], l)]
                                    a = char_map['actions'][act[0]]
                                    d = a
                                    if len(act)>1:
                                        delta = self.subtract_tuples(act[1], l)
                                        d_name = first_direction_by_value(delta)
                                        d = char_map['directions'][d_name]
                                    r.append(a)
                                    r.append(d)
                                else:
                                    r.append(draw(l))
                            elif (w >= 0 and w <= 3) and h == 1:
                                if w == 0:
                                    r = list(nice_number(game['robots'][l]['hp']).strip()+"hp")
                            else:# w == 0 and h == 0:
                                r.append(draw(l))
                        else:# we don't have stats to show if there's no robot
                            r.append(draw(l))

                    cell.append(r)
                rows[y].append(cell)


        space_w = 4
        space_h = 2
        # SSSS
        # 39hp

        dbl_rows = []
        # NOTE this takes advantage of how python divides integers
        # so don't use algebra to remove any division when refactoring
        # eg: 2/4 == 0
        for ri in range(len(rows)*space_h):
            ysci = ri/space_h
            r = rows[ysci] # and r is a list of cells
            nr = []
            num = nice_number(ysci) if ri % space_h == 0 else "   "
            nr.append(num+" ")
            for ci in range(len(r)*space_w):
                xsci = ci/space_w
                x_in_cell = ci - (xsci * space_w)
                y_in_cell = ri - (ysci * space_h)
                cell_c = r[xsci][y_in_cell][x_in_cell]
                nr.append(cell_c)

                # for tj in range(space_w):
                # nr.append(c)

            dbl_rows.append(nr)

        strlist = map(lambda z: " ", range(space_w))+map(nice_number, range(board_size))
        dbl_rows.insert(0, strlist)

        for r in range(len(dbl_rows)):
            sr = nice_number(r)
            print "".join(dbl_rows[r])



