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
        self.pairings = []
        self.results = []

    def add_player(self, name, rating):
        self.players.append(Player(name, rating))

    def clear(self):
        self.players.clear()
        self.current_round = 0
        self.pairings.clear()
        self.results.clear()

    def standings(self):
        return sorted(self.players, key=lambda p: (-p.points, -p.rating))

    # ---------- ROUND 1 ----------
    def pair_first_round(self, top_color_white=True):
        sorted_players = sorted(self.players, key=lambda p: (-p.rating, p.name))
        n = len(sorted_players)
        mid = n // 2
        top = sorted_players[:mid]
        bottom_temp = sorted_players[mid:]
        pairs = []
        if n % 2 == 1:
            bye = bottom_temp.pop()
            bye.points += 1.0
            bye.has_bye = True
            pairs.append((bye, None))
        bottom = bottom_temp
        for i in range(len(bottom)):
            if top_color_white:
                if i % 2 == 0:
                    w, b = top[i], bottom[i]
                else:
                    w, b = bottom[i], top[i]
            else:
                if i % 2 == 0:
                    w, b = bottom[i], top[i]
                else:
                    w, b = top[i], bottom[i]
            pairs.append((w, b))
        self.pairings = pairs
        self.results = [None] * len(pairs)
        return pairs

    # ---------- ROUND 2, 3... (Top/Bottom + HOLD) ----------
    def pair_next_round(self):
        if len(self.players) < 2:
            return []

        # Group by points
        groups = {}
        for p in self.players:
            pts = p.points
            groups.setdefault(pts, []).append(p)

        sorted_points = sorted(groups.keys(), reverse=True)
        all_pairs = []
        already_paired = set()

        # Global bye (only one per round)
        total_players = len(self.players)
        need_bye = (total_players % 2 == 1)
        global_bye_player = None
        if need_bye:
            candidates = [p for p in self.players if not p.has_bye]
            if not candidates:
                candidates = self.players[:]
            global_bye_player = min(candidates, key=lambda p: (p.rating, p.name))

        # Process each point group
        for pts in sorted_points:
            group = groups[pts][:]
            # Remove already paired players
            group = [p for p in group if p.name not in already_paired]
            if len(group) < 2:
                # If only one left, it will be handled later (bye or float)
                if len(group) == 1 and global_bye_player is None:
                    # This could happen if total players even? We'll handle.
                    pass
                continue

            # We'll use a while loop to re-group unpaired players
            remaining = group[:]
            while len(remaining) >= 2:
                # Sort by rating descending for Top/Bottom
                remaining.sort(key=lambda p: (-p.rating, p.name))
                n = len(remaining)
                mid = n // 2
                top = remaining[:mid]
                bottom = remaining[mid:]

                paired_this_iter = []
                used_bottom = [False] * len(bottom)

                # For each top player, try to find a bottom that hasn't played him
                for i in range(len(top)):
                    white_candidate = top[i]
                    chosen = -1
                    # First, try to find a bottom not used and not played before
                    for j in range(len(bottom)):
                        if not used_bottom[j] and white_candidate.name not in bottom[j].opponents:
                            chosen = j
                            break
                    if chosen != -1:
                        black_candidate = bottom[chosen]
                        used_bottom[chosen] = True
                        # Assign colors: higher rated gets desired color
                        higher = white_candidate if white_candidate.rating >= black_candidate.rating else black_candidate
                        def desired(p):
                            if not p.colors:
                                return 'white'
                            return 'black' if p.colors[-1] == 'white' else 'white'
                        if desired(higher) == 'white':
                            white, black = higher, (black_candidate if higher == white_candidate else white_candidate)
                        else:
                            white, black = (black_candidate if higher == white_candidate else white_candidate), higher
                        paired_this_iter.append((white, black))
                        already_paired.add(white.name)
                        already_paired.add(black.name)
                    else:
                        # No suitable opponent for this top player; we will hold him for next iteration
                        # Just continue with next top
                        pass

                # Add pairs from this iteration
                all_pairs.extend(paired_this_iter)

                # Re-group remaining (those not paired yet)
                remaining = [p for p in remaining if p.name not in already_paired]

                # If no progress (i.e., remaining size didn't change), break to avoid infinite loop
                if not paired_this_iter and len(remaining) == len(group):
                    # This means no pairs could be made in this group; break
                    break

            # After loop, if one player remains in this group, it will float down to next group or get bye
            if remaining and len(remaining) == 1:
                # We'll add this player to the next lower group if exists
                # For simplicity, we'll just leave it; bye will be assigned globally if needed
                pass

        # Assign global bye if needed
        if global_bye_player and global_bye_player.name not in already_paired:
            global_bye_player.points += 1.0
            global_bye_player.has_bye = True
            all_pairs.append((global_bye_player, None))
            already_paired.add(global_bye_player.name)
        elif global_bye_player and global_bye_player.name in already_paired:
            # Find another unpaired player
            unpaired = [p for p in self.players if p.name not in already_paired]
            if unpaired:
                bye_player = min(unpaired, key=lambda p: (p.rating, p.name))
                bye_player.points += 1.0
                bye_player.has_bye = True
                all_pairs.append((bye_player, None))
                already_paired.add(bye_player.name)

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


# ---------- GUI App ----------
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Chess Swiss - Top/Bottom with HOLD (Fixed)")
        self.root.geometry("950x700")
        self.tournament = Tournament()
        self.top_color_white = True
        self.build_ui()

    def build_ui(self):
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
        self.round_label = ttk.Label(f3, text="Round: 0", font=("Arial",10,"bold"))
        self.round_label.pack(side="left", padx=20)

        f4 = ttk.LabelFrame(self.root, text="Current Pairings (Select board)")
        f4.pack(fill="both", expand=True, padx=10, pady=5)
        self.pair_tree = ttk.Treeview(f4, columns=("Board","White","Black","Result"), show="headings")
        self.pair_tree.heading("Board", text="Board")
        self.pair_tree.heading("White", text="White")
        self.pair_tree.heading("Black", text="Black")
        self.pair_tree.heading("Result", text="Result")
        self.pair_tree.pack(fill="both", expand=True)
        self.pair_tree.bind("<<TreeviewSelect>>", self.on_pair_select)
        self.current_selection = None

        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="White Wins (1-0)", command=self.white_wins, width=15).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Black Wins (0-1)", command=self.black_wins, width=15).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Draw (½-½)", command=self.draw, width=15).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Results", command=self.clear_results, width=15).pack(side="left", padx=20)

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
            messagebox.showerror("Error", "Rating integer")
            return
        self.tournament.add_player(name, rat)
        self.name_entry.delete(0, tk.END)
        self.rating_entry.delete(0, tk.END)
        self.update_player_table()

    def import_csv(self):
        filename = filedialog.askopenfilename(title="Select CSV", filetypes=[("CSV files", "*.csv")])
        if not filename:
            return
        try:
            with open(filename, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                rows = list(reader)
            if not rows:
                return
            if len(rows[0]) >= 2 and (('name' in rows[0][0].lower()) or ('rating' in rows[0][1].lower())):
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
                self.pair_tree.insert("", tk.END, values=(i, w.name, "---", "Bye"))
            else:
                res_str = self.tournament.results[i-1] if self.tournament.results[i-1] else "Not played"
                self.pair_tree.insert("", tk.END, values=(i, w.name, b.name, res_str))
        if self.pair_tree.get_children():
            self.pair_tree.selection_set(self.pair_tree.get_children()[0])

    def on_pair_select(self, event):
        sel = self.pair_tree.selection()
        self.current_selection = sel[0] if sel else None

    def get_selected_index(self):
        if not self.current_selection:
            messagebox.showinfo("Info", "Select a board")
            return -1
        values = self.pair_tree.item(self.current_selection, "values")
        if not values:
            return -1
        return int(values[0]) - 1

    def record_result(self, result_code):
        idx = self.get_selected_index()
        if idx < 0 or idx >= len(self.tournament.pairings):
            return
        w, b = self.tournament.pairings[idx]
        if b is None:
            messagebox.showinfo("Info", "Bye already given")
            return
        if self.tournament.results[idx] is not None:
            if not messagebox.askyesno("Overwrite", f"Overwrite {self.tournament.results[idx]}?"):
                return
        self.tournament.enter_result(w, b, result_code)
        self.tournament.results[idx] = result_code
        self.update_pairings_display()
        self.update_player_table()

    def white_wins(self):
        self.record_result('1-0')
    def black_wins(self):
        self.record_result('0-1')
    def draw(self):
        self.record_result('1/2-1/2')

    def clear_results(self):
        if not self.tournament.pairings:
            return
        if not messagebox.askyesno("Clear", "Clear all results?"):
            return
        for idx, (w, b) in enumerate(self.tournament.pairings):
            if b is None:
                continue
            old = self.tournament.results[idx]
            if old:
                if old == '1-0':
                    w.points -= 1.0
                elif old == '0-1':
                    b.points -= 1.0
                elif old == '1/2-1/2':
                    w.points -= 0.5
                    b.points -= 0.5
                w.opponents.pop()
                b.opponents.pop()
                w.colors.pop()
                b.colors.pop()
                self.tournament.results[idx] = None
        self.update_player_table()
        self.update_pairings_display()

    def round1(self):
        if len(self.tournament.players) < 2:
            messagebox.showerror("Error", "Need >=2 players")
            return
        ans = messagebox.askyesno("Round 1 Color",
            f"Top Player '{self.tournament.standings()[0].name}' ට White ලබා දෙන්නද?\n(Yes = White, No = Black)")
        self.top_color_white = ans
        self.tournament.current_round = 1
        self.tournament.pair_first_round(self.top_color_white)
        self.update_pairings_display()
        self.round_label.config(text=f"Round: {self.tournament.current_round}")

    def next_round(self):
        if self.tournament.current_round == 0:
            messagebox.showerror("Error", "Round 1 first")
            return
        for i, r in enumerate(self.tournament.results):
            if self.tournament.pairings[i][1] is not None and r is None:
                if not messagebox.askyesno("Warning", "Some results missing. Continue?"):
                    return
                break
        self.tournament.current_round += 1
        self.tournament.pair_next_round()
        self.update_pairings_display()
        self.round_label.config(text=f"Round: {self.tournament.current_round}")

    def new_tournament(self):
        if messagebox.askyesno("New", "Clear all?"):
            self.tournament.clear()
            self.update_player_table()
            self.update_pairings_display()
            self.round_label.config(text="Round: 0")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()