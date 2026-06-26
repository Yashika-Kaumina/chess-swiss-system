import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv

class Player:
    def __init__(self, name, rating):
        self.name = name
        self.rating = rating
        self.points = 0.0
        self.opponents = []
        self.colors = []
        self.has_bye = False

class Tournament:
    def __init__(self):
        self.players = []
        self.current_round = 0
        self.pairings = []      # list of (white, black) for current round
        self.results = []       # list of results for current round (parallel to pairings)

    def add_player(self, name, rating):
        self.players.append(Player(name, rating))

    def clear(self):
        self.players.clear()
        self.current_round = 0
        self.pairings.clear()
        self.results.clear()

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
            bye.has_bye = True
            pairs.append((bye, None))
        for i in range(len(bottom)):
            if i % 2 == 0:
                w, b = top[i], bottom[i]
            else:
                w, b = bottom[i], top[i]
            pairs.append((w, b))
        self.pairings = pairs
        self.results = [None] * len(pairs)
        return pairs

    # Priority-based pairing for rounds >=2 (same as last version)
    def pair_next_round(self):
        if len(self.players) < 2:
            return []
        total_players = len(self.players)
        need_bye = (total_players % 2 == 1)
        bye_player = None
        if need_bye:
            candidates = [p for p in self.players if not p.has_bye]
            if not candidates:
                candidates = self.players[:]
            bye_player = min(candidates, key=lambda p: (p.rating, p.name))
            bye_player.points += 1.0
            bye_player.has_bye = True

        remaining = [p for p in self.players if p != bye_player]
        groups = {}
        for p in remaining:
            groups.setdefault(p.points, []).append(p)
        sorted_points = sorted(groups.keys(), reverse=True)

        def color_point(p):
            return sum(1 if c == 'white' else -1 for c in p.colors)

        all_pairs = []
        for pts in sorted_points:
            group = groups[pts][:]
            unpaired = group[:]
            group_pairs = []
            while len(unpaired) >= 2:
                unpaired.sort(key=lambda p: (-p.rating, p.name))
                first = unpaired[0]
                best_opp = None
                best_score = -1e9
                for i in range(1, len(unpaired)):
                    opp = unpaired[i]
                    score = 0
                    if opp.name in first.opponents:
                        score = -10000
                    else:
                        cp1 = color_point(first)
                        cp2 = color_point(opp)
                        total_cp = cp1 + cp2
                        color_balance_score = -abs(total_cp)
                        score += color_balance_score * 10
                        rating_diff = abs(first.rating - opp.rating)
                        score -= rating_diff / 100.0
                    if score > best_score:
                        best_score = score
                        best_opp = opp
                if best_opp is None:
                    best_opp = unpaired[1]
                unpaired.remove(first)
                unpaired.remove(best_opp)
                def desired(p):
                    if not p.colors:
                        return 'white'
                    return 'black' if p.colors[-1] == 'white' else 'white'
                higher = first if first.rating >= best_opp.rating else best_opp
                if desired(higher) == 'white':
                    white, black = higher, (best_opp if higher == first else first)
                else:
                    white, black = (best_opp if higher == first else first), higher
                group_pairs.append((white, black))
            all_pairs.extend(group_pairs)
        if bye_player:
            all_pairs.append((bye_player, None))
        self.pairings = all_pairs
        self.results = [None] * len(all_pairs)
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
        self.root.title("Chess Swiss - 3 Buttons for Results")
        self.root.geometry("950x700")
        self.tournament = Tournament()
        self.current_selection = None
        self.build_ui()

    def build_ui(self):
        # Top frame: add player and import
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(top_frame, text="Name:").grid(row=0, column=0)
        self.name_entry = ttk.Entry(top_frame, width=20)
        self.name_entry.grid(row=0, column=1)
        ttk.Label(top_frame, text="Rating:").grid(row=0, column=2)
        self.rating_entry = ttk.Entry(top_frame, width=10)
        self.rating_entry.grid(row=0, column=3)
        ttk.Button(top_frame, text="Add Player", command=self.add_player).grid(row=0, column=4, padx=5)
        ttk.Button(top_frame, text="Import CSV", command=self.import_csv).grid(row=0, column=5, padx=5)
        ttk.Button(top_frame, text="New Tournament", command=self.new_tournament).grid(row=0, column=6, padx=5)

        # Player list frame
        f2 = ttk.LabelFrame(self.root, text="Players")
        f2.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree = ttk.Treeview(f2, columns=("Name","Rating","Points"), show="headings")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Rating", text="Rating")
        self.tree.heading("Points", text="Points")
        self.tree.pack(fill="both", expand=True)

        # Round control buttons
        f3 = ttk.Frame(self.root)
        f3.pack(fill="x", padx=10, pady=5)
        ttk.Button(f3, text="Round 1", command=self.round1).pack(side="left", padx=5)
        ttk.Button(f3, text="Next Round", command=self.next_round).pack(side="left", padx=5)
        self.round_label = ttk.Label(f3, text="Round: 0", font=("Arial",10,"bold"))
        self.round_label.pack(side="left", padx=20)

        # Pairings display with selectable rows
        f4 = ttk.LabelFrame(self.root, text="Current Round Pairings (Select a board)")
        f4.pack(fill="both", expand=True, padx=10, pady=5)
        self.pair_tree = ttk.Treeview(f4, columns=("Board","White","Black","Result"), show="headings")
        self.pair_tree.heading("Board", text="Board")
        self.pair_tree.heading("White", text="White")
        self.pair_tree.heading("Black", text="Black")
        self.pair_tree.heading("Result", text="Result")
        self.pair_tree.pack(fill="both", expand=True)
        self.pair_tree.bind("<<TreeviewSelect>>", self.on_pair_select)

        # Three result buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="White Wins (1-0)", command=self.white_wins, width=15).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Black Wins (0-1)", command=self.black_wins, width=15).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Draw (½-½)", command=self.draw, width=15).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear All Results", command=self.clear_results, width=15).pack(side="left", padx=20)

        self.update_player_table()

    def add_player(self):
        name = self.name_entry.get().strip()
        rat_str = self.rating_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required")
            return
        try:
            rat = int(rat_str) if rat_str else 1200
        except:
            messagebox.showerror("Error", "Rating must be integer")
            return
        self.tournament.add_player(name, rat)
        self.name_entry.delete(0, tk.END)
        self.rating_entry.delete(0, tk.END)
        self.update_player_table()

    def import_csv(self):
        filename = filedialog.askopenfilename(title="Select CSV file", filetypes=[("CSV files", "*.csv")])
        if not filename:
            return
        try:
            with open(filename, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                rows = list(reader)
            if not rows:
                messagebox.showerror("Error", "File empty")
                return
            first = rows[0]
            if len(first) >= 2 and (('name' in first[0].lower()) or ('rating' in first[1].lower())):
                rows = rows[1:]
            count = 0
            for row in rows:
                if len(row) < 2:
                    continue
                name = row[0].strip()
                try:
                    rating = int(float(row[1].strip()))
                except:
                    rating = 1200
                if name:
                    self.tournament.add_player(name, rating)
                    count += 1
            self.update_player_table()
            messagebox.showinfo("Success", f"Imported {count} players")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_player_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for p in self.tournament.standings():
            self.tree.insert("", tk.END, values=(p.name, p.rating, p.points))

    def update_pairings_display(self):
        for row in self.pair_tree.get_children():
            self.pair_tree.delete(row)
        if not self.tournament.pairings:
            return
        for i, (w, b) in enumerate(self.tournament.pairings, 1):
            if b is None:
                result_str = "Bye" if self.tournament.results[i-1] is None else "Bye (done)"
                self.pair_tree.insert("", tk.END, values=(i, w.name, "bye", result_str))
            else:
                res_str = self.tournament.results[i-1] if self.tournament.results[i-1] else "Not played"
                self.pair_tree.insert("", tk.END, values=(i, w.name, b.name, res_str))
        # Auto-select first row if any
        if self.pair_tree.get_children():
            self.pair_tree.selection_set(self.pair_tree.get_children()[0])

    def on_pair_select(self, event):
        sel = self.pair_tree.selection()
        if sel:
            self.current_selection = sel[0]
        else:
            self.current_selection = None

    def get_selected_board_index(self):
        if not self.current_selection:
            messagebox.showinfo("Info", "Please select a board first")
            return -1
        item = self.current_selection
        values = self.pair_tree.item(item, "values")
        if not values:
            return -1
        board_num = int(values[0])
        return board_num - 1

    def record_result(self, result_code):
        idx = self.get_selected_board_index()
        if idx < 0 or idx >= len(self.tournament.pairings):
            return
        white, black = self.tournament.pairings[idx]
        if black is None:
            messagebox.showinfo("Info", "Bye already given 1 point")
            return
        if self.tournament.results[idx] is not None:
            if not messagebox.askyesno("Overwrite", f"Result already set to {self.tournament.results[idx]}. Overwrite?"):
                return
        # Apply result
        self.tournament.enter_result(white, black, result_code)
        self.tournament.results[idx] = result_code
        self.update_pairings_display()
        self.update_player_table()
        # Check if all results entered?
        all_done = all(r is not None for r in self.tournament.results if self.tournament.pairings[i][1] is not None for i,r in enumerate(self.tournament.results))
        if all_done:
            messagebox.showinfo("Round Complete", "All results recorded. You can now proceed to Next Round.")

    def white_wins(self):
        self.record_result('1-0')
    def black_wins(self):
        self.record_result('0-1')
    def draw(self):
        self.record_result('1/2-1/2')

    def clear_results(self):
        if not self.tournament.pairings:
            return
        if messagebox.askyesno("Clear", "Clear all results for this round?"):
            # Remove points from players
            for idx, (w, b) in enumerate(self.tournament.pairings):
                if b is None:
                    continue
                old_res = self.tournament.results[idx]
                if old_res:
                    # subtract points
                    if old_res == '1-0':
                        w.points -= 1.0
                    elif old_res == '0-1':
                        b.points -= 1.0
                    elif old_res == '1/2-1/2':
                        w.points -= 0.5
                        b.points -= 0.5
                    # remove opponents and colors
                    w.opponents.pop()
                    b.opponents.pop()
                    w.colors.pop()
                    b.colors.pop()
                    self.tournament.results[idx] = None
            self.update_player_table()
            self.update_pairings_display()
            messagebox.showinfo("Done", "Results cleared. You can re-enter results.")

    def round1(self):
        if len(self.tournament.players) < 2:
            messagebox.showerror("Error", "Need at least 2 players")
            return
        self.tournament.current_round = 1
        self.tournament.pair_first_round()
        self.update_pairings_display()
        self.round_label.config(text=f"Round: {self.tournament.current_round}")

    def next_round(self):
        if self.tournament.current_round == 0:
            messagebox.showerror("Error", "First round not paired")
            return
        # Check if all results are entered for current round
        for i, r in enumerate(self.tournament.results):
            if self.tournament.pairings[i][1] is not None and r is None:
                if not messagebox.askyesno("Incomplete", "Some results not entered. Continue anyway?"):
                    return
                break
        self.tournament.current_round += 1
        self.tournament.pair_next_round()
        self.update_pairings_display()
        self.round_label.config(text=f"Round: {self.tournament.current_round}")

    def new_tournament(self):
        if messagebox.askyesno("New Tournament", "Clear all data?"):
            self.tournament.clear()
            self.update_player_table()
            self.update_pairings_display()
            self.round_label.config(text="Round: 0")
            self.current_selection = None

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()