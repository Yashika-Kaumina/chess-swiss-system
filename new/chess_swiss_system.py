class Player:
    def __init__(self, name, rating=1200):
        self.name = name
        self.rating = rating
        self.points = 0.0
        self.opponents = []      # list of opponent names
        self.colors = []          # list of colors played
    
    def add_result(self, opponent_name, result, color):
        self.points += result
        self.opponents.append(opponent_name)
        self.colors.append(color)
    
    def __repr__(self):
        return f"{self.name} (pts:{self.points}, rating:{self.rating})"


class Tournament:
    def __init__(self, name):
        self.name = name
        self.players = []
        self.current_round_pairs = []
    
    def add_player(self, name, rating=1200):
        self.players.append(Player(name, rating))
    
    def get_standings(self):
        return sorted(self.players, key=lambda p: (-p.points, -p.rating))
    
    def pair_round(self):
        players = self.get_standings()
        used = set()
        pairs = []
        
        for i in range(len(players)):
            if players[i].name in used:
                continue
            white = players[i]
            best_opp = None
            best_diff = float('inf')
            for j in range(i+1, len(players)):
                black_candidate = players[j]
                if black_candidate.name in used:
                    continue
                if black_candidate.name in white.opponents:
                    continue
                diff = abs(white.points - black_candidate.points)
                if diff < best_diff:
                    best_diff = diff
                    best_opp = black_candidate
            
            if best_opp:
                pairs.append((white, best_opp))
                used.add(white.name)
                used.add(best_opp.name)
            else:
                # bye: give 1 point? Not implemented here
                used.add(white.name)
        
        self.current_round_pairs = pairs
        return pairs
    
    def enter_result(self, white_name, black_name, result):
        white = None
        black = None
        for p in self.players:
            if p.name == white_name:
                white = p
            if p.name == black_name:
                black = p
        if white is None or black is None:
            raise ValueError("Player not found")
        
        if result == '1-0':
            white.add_result(black_name, 1.0, 'white')
            black.add_result(white_name, 0.0, 'black')
        elif result == '0-1':
            white.add_result(black_name, 0.0, 'white')
            black.add_result(white_name, 1.0, 'black')
        elif result == '1/2-1/2':
            white.add_result(black_name, 0.5, 'white')
            black.add_result(white_name, 0.5, 'black')
        else:
            raise ValueError("Invalid result. Use '1-0', '0-1', or '1/2-1/2'")


# Test the system
if __name__ == "__main__":
    t = Tournament("Demo Swiss")
    t.add_player("Alice", 1500)
    t.add_player("Bob", 1400)
    t.add_player("Charlie", 1300)
    t.add_player("Diana", 1600)
    
    # Round 1
    print("=== Round 1 ===")
    pairs = t.pair_round()
    for white, black in pairs:
        print(f"{white.name} (white) vs {black.name} (black)")
        # Simulate results: white wins
        t.enter_result(white.name, black.name, '1-0')
    
    print("Standings after round 1:")
    for p in t.get_standings():
        print(f"{p.name}: {p.points} pts")
    
    # Round 2
    print("\n=== Round 2 ===")
    pairs = t.pair_round()
    for white, black in pairs:
        print(f"{white.name} (white) vs {black.name} (black)")
        # Simulate results: black wins
        t.enter_result(white.name, black.name, '0-1')
    
    print("Standings after round 2:")
    for p in t.get_standings():
        print(f"{p.name}: {p.points} pts")