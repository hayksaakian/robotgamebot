import ast
import rg

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
back_indicators = [
    "back",
    "cancel",
    "no",
    "action",
    "exit",
    "undo"
]
char_map = {
    "invalid":None,
    "normal":" ",
    "spawn":"+",
    "obstacle":"-",
    "enemy":"E",
    "ally":"A",
    "self":"@"
}
loc_type_priority = [
    "invalid",
    "obstacle",
    "spawn",
    "normal"
]
directions = {
    "left":(-1, 0),
    "right":(1, 0),
    "down":(0, -1),
    "up":(0, 1),
    "a":(-1, 0),
    "d":(1, 0),
    "s":(0, -1),
    "w":(0, 1)
}
class Robot:
    def act(self, game):
        self.print_board(game)
        action = self.prompt_human(game)
        print(str(self.location)+" will try to "+str(action))
        return action

    def prompt_human(self, game):
        action = None
        while(action not in possible_actions):
            print(str(self.location)+" ("+str(self.hp)+"/50hp) What will this Robot do?")
            action = raw_input()

        if action in actions_requiring_location:
            location = None
            while(self.validate_action([action, location], game) == False):
                print("Where should this Robot "+action+"?")
                rloc = raw_input()
                if rloc in directions:
                    location = (directions[rloc][0] + self.position[0], directions[rloc][1]+self.position[1])
                else:
                    location = ast.literal_eval(rloc)

            return [action, location]
        else:
            return [action]
        
    def validate_action(self, formatted_action, game):
        if len(formatted_action) > 1:
            if formatted_action[1] == None:
                return False
            if formatted_action[0] == "move":
                return formatted_action[1] in rg.locs_around(self.location)
        return True #placeholder

    def print_board(self, game):
        board_size = (rg.CENTER_POINT[0] * 2) + 1
        rows = map(lambda i: [], range(board_size))
        for y in range(len(rows)):

            def draw(k):
                if k in char_map:
                    k = char_map[k]
                rows[y].append(k)
            for x in range(board_size):
                l = (x, y)
                if l == self.location:
                    draw("self")
                elif l in game['robots']:
                    draw("ally") if game['robots'][l].player_id == self.player_id else draw("enemy")
                else:
                    loc_types = sorted(rg.loc_types(l), key=lambda t:loc_type_priority.index(t))
                    draw(loc_types[0])

        def nice_number(n):
            return str(n) if n >=  10 else " "+str(n)

        dbl_rows = []
        for r in rows:
            nr = []
            ci = nice_number(len(dbl_rows)/2)
            nr.append(ci)
            for c in r:
                nr.append(c)
                nr.append(c)
            dbl_rows.append(nr)
            dbl_rows.append(nr)


        strlist = [" ", " "]+map(nice_number, range(board_size))
        dbl_rows.insert(0, strlist)

        for r in range(len(dbl_rows)):
            sr = nice_number(r)
            print "".join(dbl_rows[r])


