import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

class Player:
    def __init__(self, name, rating):
        self.name = name
        self.rating = rating
        self.points = 0.0
        self.opponents = []
        self.colors = []

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
        if n % 2 == 1:
            bye = bottom.pop()
            bye.points += 1.0
            pairs.append((bye, None))
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
        # Group by points
        groups = {}
        for p in self.players:
            groups.setdefault(p.points, []).append(p)
        sorted_points = sorted(groups.keys(), reverse=True)
        all_pairs = []
        # We will process each point group
        # No carry-over between groups (standard Swiss uses floating, but for simplicity and to control bye, we reset)
        for pts in sorted_points:
            group = groups[pts]
            # Sort by rating DESCENDING (highest first) for pairing
            group.sort(key=lambda p: (-p.rating, p.name))
            n = len(group)
            # If odd number of players in this group, the LOWEST rated gets a bye
            if n % 2 == 1:
                # The last player in descending order is the lowest rated
                bye_player = group[-1]
                bye_player.points += 1.0
                all_pairs.append((bye_player, None))
                # Remove bye player from group
                group.remove(bye_player)
                n -= 1
            # Now n is even
            mid = n // 2
            top = group[:mid]
            bottom = group[mid:]
            # Pair top vs bottom avoiding previous opponents
            used_bottom = [False] * len(bottom)
            for i in range(len(top)):
                white_candidate = top[i]
                chosen = -1
                for j in range(len(bottom)):
                    if not used_bottom[j] and white_candidate.name not in bottom[j].opponents:
                        chosen = j
                        break
                if chosen == -1:
                    for j in range(len(bottom)):
                        if not used_bottom[j]:
                            chosen = j
                            break
                if chosen != -1:
                    black_candidate = bottom[chosen]
                    used_bottom[chosen] = True
                    # Determine higher player (by rating, then points)
                    def higher(p1, p2):
                        if p1.rating != p2.rating:
                            return p1 if p1.rating > p2.rating else p2
                        return p1 if p1.points > p2.points else p2
                    top_player = higher(white_candidate, black_candidate)
                    def desired(p):
                        if not p.colors:
                            return 'white'
                        return 'black' if p.colors[-1] == 'white' else 'white'
                    if desired(top_player) == 'white':
                        white, black = top_player, (black_candidate if top_player == white_candidate else white_candidate)
                    else:
                        white, black = (black_candidate if top_player == white_candidate else white_candidate), top_player
                    all_pairs.append((white, black))
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

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Swiss Chess - Fixed Bye (Lowest Rated)")
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