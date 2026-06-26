import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

class Player:
    def __init__(self, name, rating):
        self.name = name
        self.rating = rating
        self.points = 0.0
        self.opponents = []
        self.colors = []
        self.has_bye = False   # track if already got bye in tournament

class Tournament:
    def __init__(self):
        self.players = []
        self.current_round = 0
        self.pairings = []

    def add_player(self, name, rating):
        self.players.append(Player(name, rating))

    def clear(self):
        self.players.clear()
        self.current_round = 0
        self.pairings.clear()

    def standings(self):
        return sorted(self.players, key=lambda p: (-p.points, -p.rating))

    def pair_first_round(self):
        sorted_players = sorted(self.players, key=lambda p: (-p.rating, p.name))
        n = len(sorted_players)
        mid = n // 2
        top = sorted_players[:mid]
        bottom = sorted_players[mid:]
        pairs = []
        # Only one bye in first round if total players odd
        if n % 2 == 1:
            bye_player = bottom.pop()
            bye_player.points += 1.0
            bye_player.has_bye = True
            pairs.append((bye_player, None))
        for i in range(len(bottom)):
            if i % 2 == 0:
                w, b = top[i], bottom[i]
            else:
                w, b = bottom[i], top[i]
            pairs.append((w, b))
        self.pairings = pairs
        return pairs

    def pair_next_round(self):
        if len(self.players) < 2:
            return []
        # 1) Check total number of players. If odd, we need exactly ONE bye.
        total_players = len(self.players)
        need_bye = (total_players % 2 == 1)
        bye_player = None
        if need_bye:
            # Choose player with lowest rating who has not yet had a bye
            candidates = [p for p in self.players if not p.has_bye]
            if not candidates:
                candidates = self.players[:]
            bye_player = min(candidates, key=lambda p: (p.rating, p.name))
            bye_player.points += 1.0
            bye_player.has_bye = True

        # 2) Remove bye_player from pairing pool if exists
        remaining = [p for p in self.players if p != bye_player]

        # 3) Group remaining players by points
        groups = {}
        for p in remaining:
            groups.setdefault(p.points, []).append(p)
        sorted_points = sorted(groups.keys(), reverse=True)

        all_pairs = []
        # We will process groups sequentially, and no more bye inside groups
        for pts in sorted_points:
            group = groups[pts]
            group.sort(key=lambda p: (-p.rating, p.name))
            n = len(group)
            # Split into top and bottom halves
            mid = n // 2
            top = group[:mid]    # higher rated
            bottom = group[mid:] # lower rated

            # Color point function
            def color_point(p):
                return sum(1 if c == 'white' else -1 for c in p.colors)

            def desired(p):
                if not p.colors:
                    return 'white'
                return 'black' if p.colors[-1] == 'white' else 'white'

            used_top = [False] * len(top)
            temp_pairs = []

            for i in range(len(bottom)):
                white_candidate = bottom[i]
                best_j = -1
                best_score = float('inf')
                best_swap = False
                for j in range(len(top)):
                    if used_top[j]:
                        continue
                    if white_candidate.name in top[j].opponents:
                        continue
                    black_candidate = top[j]
                    # Option A: white_candidate white, black_candidate black
                    cp_w = color_point(white_candidate)
                    cp_b = color_point(black_candidate)
                    scoreA = abs((cp_w + 1) + (cp_b - 1))
                    # Option B: white_candidate black, black_candidate white
                    scoreB = abs((cp_w - 1) + (cp_b + 1))
                    # Determine higher rated
                    higher = white_candidate if white_candidate.rating >= black_candidate.rating else black_candidate
                    desired_higher = desired(higher)
                    # Option A: who gets white?
                    if (higher == white_candidate and desired_higher == 'white') or (higher == black_candidate and desired_higher == 'black'):
                        scoreA -= 0.5
                    else:
                        scoreA += 0.5
                    # Option B: higher gets white if higher == black_candidate
                    if (higher == black_candidate and desired_higher == 'white') or (higher == white_candidate and desired_higher == 'black'):
                        scoreB -= 0.5
                    else:
                        scoreB += 0.5
                    if scoreA < best_score:
                        best_score = scoreA
                        best_j = j
                        best_swap = False
                    if scoreB < best_score:
                        best_score = scoreB
                        best_j = j
                        best_swap = True
                if best_j != -1:
                    black_candidate = top[best_j]
                    used_top[best_j] = True
                    if best_swap:
                        white, black = black_candidate, white_candidate
                    else:
                        white, black = white_candidate, black_candidate
                    temp_pairs.append((white, black))
            all_pairs.extend(temp_pairs)

        # If we had a bye, add it at the end (or beginning)
        if bye_player:
            all_pairs.append((bye_player, None))

        self.pairings = all_pairs
        return all_pairs

    def enter_result(self, white, black, result):
        if result == '1-0':
            white.points += 1.0
        elif result == '0-1':
            black.points += 1.0
        elif result == '1/2-1/2':
            white.points += 0.5
            black.points += 0.5
        else:
            return
        white.opponents.append(black.name)
        black.opponents.append(white.name)
        white.colors.append('white')
        black.colors.append('black')


# ----- GUI (ඉහත කේතයේ GUI කොටස මෙලෙසම පවතී) -----
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Swiss Chess - Fixed Bye (One per round)")
        self.root.geometry("850x600")
        self.tournament = Tournament()
        self.build_ui()

    def build_ui(self):
        f1 = ttk.LabelFrame(self.root, text="Add Player")
        f1.pack(fill="x", padx=10, pady=5)
        ttk.Label(f1, text="Name:").grid(row=0, column=0)
        self.name_entry = ttk.Entry(f1, width=20)
        self.name_entry.grid(row=0, column=1)
        ttk.Label(f1, text="Rating:").grid(row=0, column=2)
        self.rating_entry = ttk.Entry(f1, width=10)
        self.rating_entry.grid(row=0, column=3)
        ttk.Button(f1, text="Add Player", command=self.add_player).grid(row=0, column=4, padx=5)
        ttk.Button(f1, text="New Tournament", command=self.new_tournament).grid(row=0, column=5)

        f2 = ttk.LabelFrame(self.root, text="Players")
        f2.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree = ttk.Treeview(f2, columns=("Name","Rating","Points"), show="headings")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Rating", text="Rating")
        self.tree.heading("Points", text="Points")
        self.tree.pack(fill="both", expand=True)

        f3 = ttk.Frame(self.root)
        f3.pack(fill="x", padx=10, pady=5)
        ttk.Button(f3, text="Round 1", command=self.round1).pack(side="left", padx=5)
        ttk.Button(f3, text="Next Round", command=self.next_round).pack(side="left", padx=5)
        ttk.Button(f3, text="Enter Results", command=self.enter_results).pack(side="left", padx=5)
        self.round_label = ttk.Label(f3, text="Round: 0", font=("Arial",10,"bold"))
        self.round_label.pack(side="left", padx=20)

        f4 = ttk.LabelFrame(self.root, text="Pairings")
        f4.pack(fill="both", expand=True, padx=10, pady=5)
        self.pair_text = tk.Text(f4, height=10, wrap="word")
        self.pair_text.pack(fill="both", expand=True)

        self.update_table()

    def add_player(self):
        name = self.name_entry.get().strip()
        rat_str = self.rating_entry.get().strip()
        if not name:
            return
        try:
            rat = int(rat_str) if rat_str else 1200
        except:
            rat = 1200
        self.tournament.add_player(name, rat)
        self.name_entry.delete(0, tk.END)
        self.rating_entry.delete(0, tk.END)
        self.update_table()

    def update_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for p in self.tournament.standings():
            self.tree.insert("", tk.END, values=(p.name, p.rating, p.points))

    def round1(self):
        if len(self.tournament.players) < 2:
            messagebox.showerror("Error", "Need at least 2 players")
            return
        self.tournament.current_round = 1
        pairs = self.tournament.pair_first_round()
        self.show_pairings(pairs)
        self.round_label.config(text=f"Round: {self.tournament.current_round}")

    def next_round(self):
        if self.tournament.current_round == 0:
            messagebox.showerror("Error", "First round not paired")
            return
        self.tournament.current_round += 1
        pairs = self.tournament.pair_next_round()
        self.show_pairings(pairs)
        self.round_label.config(text=f"Round: {self.tournament.current_round}")

    def show_pairings(self, pairs):
        self.pair_text.delete(1.0, tk.END)
        if not pairs:
            self.pair_text.insert(tk.END, "No pairings.")
            return
        for i, (w, b) in enumerate(pairs, 1):
            if b is None:
                self.pair_text.insert(tk.END, f"Board {i}: {w.name} (bye +1pt)\n")
            else:
                self.pair_text.insert(tk.END, f"Board {i}: {w.name} (white) vs {b.name} (black)\n")
        self.pair_text.insert(tk.END, "\nClick 'Enter Results' after matches.")

    def enter_results(self):
        if not self.tournament.pairings:
            messagebox.showinfo("Info", "No pairings")
            return
        for w, b in self.tournament.pairings:
            if b is None:
                continue
            res = simpledialog.askstring("Result", f"{w.name} (white) vs {b.name} (black)\n1-0, 0-1, 1/2-1/2")
            if res not in ['1-0','0-1','1/2-1/2']:
                continue
            self.tournament.enter_result(w, b, res)
        self.update_table()
        self.tournament.pairings = []
        self.pair_text.delete(1.0, tk.END)
        self.pair_text.insert(tk.END, "Results recorded. Click 'Next Round'.")
        messagebox.showinfo("Done", "Results saved")

    def new_tournament(self):
        if messagebox.askyesno("New Tournament", "Clear all data?"):
            self.tournament.clear()
            self.update_table()
            self.pair_text.delete(1.0, tk.END)
            self.round_label.config(text="Round: 0")
            self.pair_text.insert(tk.END, "New tournament. Add players and press 'Round 1'.")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()