import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import csv
import json
import os

class Player:
    def __init__(self, name, rating):
        self.name = name
        self.rating = rating
        self.points = 0.0
        self.opponents = []
        self.colors = []
        self.has_bye = False

    def to_dict(self):
        return {
            "name": self.name,
            "rating": self.rating,
            "points": self.points,
            "opponents": self.opponents,
            "colors": self.colors,
            "has_bye": self.has_bye
        }

    @classmethod
    def from_dict(cls, data):
        p = cls(data["name"], data["rating"])
        p.points = data["points"]
        p.opponents = data["opponents"]
        p.colors = data["colors"]
        p.has_bye = data["has_bye"]
        return p

class Tournament:
    def __init__(self):
        self.players = []
        self.current_round = 0
        self.pairings = []
        self.results = []
        self.history = []          # Round history
        self.pairing_possible = True

    def add_player(self, name, rating):
        self.players.append(Player(name, rating))

    def clear(self):
        self.players.clear()
        self.current_round = 0
        self.pairings.clear()
        self.results.clear()
        self.history.clear()
        self.pairing_possible = True

    def standings(self):
        return sorted(self.players, key=lambda p: (-p.points, -p.rating))

    # ---------- BACKTRACKING PAIRING ENGINE ----------
    def _find_pairing(self, players):
        """Recursive backtracking to find a valid pairing for EVEN number of players."""
        if not players:
            return []
        if len(players) % 2 == 1:
            return None  # Should not happen if handled correctly

        first = players[0]
        # Try to pair first with every other player
        for i in range(1, len(players)):
            opponent = players[i]
            # Skip if they have already played
            if opponent.name in first.opponents:
                continue
            # Remaining players after removing first and opponent
            remaining = players[1:i] + players[i+1:]
            # Recursively find pairing for the rest
            result = self._find_pairing(remaining)
            if result is not None:
                return [(first, opponent)] + result
        return None  # No valid pairing found

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
        self._save_history()
        return pairs

    # ---------- ROUND 2, 3... (BACKTRACKING) ----------
    def pair_next_round(self):
        if not self.pairing_possible:
            return []

        # Group by points (for Swiss, we pair within same points group if possible)
        groups = {}
        for p in self.players:
            pts = p.points
            groups.setdefault(pts, []).append(p)

        sorted_points = sorted(groups.keys(), reverse=True)
        all_pairs = []
        already_paired = set()
        bye_assigned = False
        global_bye_player = None

        # We need to process groups in order, but if a group is odd, we float a player down.
        # Instead of complex floating, we use backtracking globally or per group.
        # For simplicity and robustness, we'll pair each group independently with backtracking.
        # If a group is odd, we try to give bye or float to next group.
        # But since we want best results, we'll just use global backtracking with bye assignment.
        # However, standard Swiss floats players down. We'll do simple: if group has odd players,
        # the lowest rated floats to the next group, or gets bye if it's the last group.

        # We'll use a recursive approach to handle floating.
        # But for now, let's implement the exact Backtracking + Bye assignment as per PDF.
        # Approach: For each point group, if even, call _find_pairing. If odd, try to assign bye.

        # Actually, the best way is to collect all players, and run a global backtracking
        # that respects point groups (prefer same points).
        # We'll keep it simple: process groups sequentially.

        for pts in sorted_points:
            group = groups[pts][:]
            # Remove already paired players
            group = [p for p in group if p.name not in already_paired]
            if not group:
                continue

            # If odd number, we need to decide bye or float
            if len(group) % 2 == 1:
                # Try to give bye to someone in this group (only if no bye assigned yet)
                # Check if we can assign bye
                if not bye_assigned:
                    # Find eligible players for bye in this group (no previous bye)
                    eligible = [p for p in group if not p.has_bye]
                    if eligible:
                        # Sort by rating descending (higher rating gets priority to NOT get bye? Actually lowest rating gets bye usually)
                        eligible.sort(key=lambda p: p.rating)
                        # We need to find a bye that allows valid pairing for the rest
                        for candidate in eligible:
                            rest = [p for p in group if p != candidate]
                            # Check if rest can be paired validly
                            result = self._find_pairing(rest)
                            if result is not None:
                                # Found valid pairing with bye
                                candidate.points += 1.0
                                candidate.has_bye = True
                                all_pairs.append((candidate, None))
                                already_paired.add(candidate.name)
                                all_pairs.extend(result)
                                for w, b in result:
                                    already_paired.add(w.name)
                                    already_paired.add(b.name)
                                bye_assigned = True
                                break
                        if bye_assigned:
                            continue
                        else:
                            # No valid bye candidate in this group, try to float the lowest rated down
                            # We'll just move the lowest rated to the next group (if exists)
                            # For simplicity, if no bye works, we will just let the algorithm try to pair
                            # the odd group normally (which might fail, and we catch later).
                            # We'll just take the lowest rated and try to pair with it later.
                            # Actually, we just fall through to normal pairing, which will fail and trigger end.
                            pass

                # If bye didn't work, we try to pair the group anyway (will fail if odd)
                # But we want to find a solution. Let's try to float the lowest rated down.
                # For simplicity, we just remove the lowest rated and add to next group.
                # This is a simplification. But since we want to ensure pairing possible,
                # we use the global backtracking approach.

            # Try normal pairing (even count)
            if len(group) % 2 == 0:
                result = self._find_pairing(group)
                if result is not None:
                    all_pairs.extend(result)
                    for w, b in result:
                        already_paired.add(w.name)
                        already_paired.add(b.name)
                else:
                    # If even group fails, we need to do something (should not happen with backtracking)
                    pass
            else:
                # Odd group handling - try to pair without bye first (will likely fail)
                # Instead, we attempt to pair the odd group by floating the lowest player to next group
                # Since we don't have a simple way to "float" with groups, we'll just use a global approach.
                pass

        # After processing all groups, check if all players are paired.
        unpaired = [p for p in self.players if p.name not in already_paired]
        if unpaired:
            # Try to assign global bye if not done yet
            if not bye_assigned:
                # Give bye to the lowest rated unpaired player
                eligible = [p for p in unpaired if not p.has_bye]
                if eligible:
                    candidate = min(eligible, key=lambda p: p.rating)
                    candidate.points += 1.0
                    candidate.has_bye = True
                    all_pairs.append((candidate, None))
                    already_paired.add(candidate.name)
                    bye_assigned = True
                    unpaired.remove(candidate)
            # If still unpaired, try to pair them using backtracking
            if unpaired:
                # If even, try to pair
                if len(unpaired) % 2 == 0:
                    result = self._find_pairing(unpaired)
                    if result is not None:
                        all_pairs.extend(result)
                        for w, b in result:
                            already_paired.add(w.name)
                            already_paired.add(b.name)
                    else:
                        self.pairing_possible = False
                        return []
                else:
                    # Odd unpaired, cannot proceed
                    self.pairing_possible = False
                    return []

        # Check if all players are paired (or one bye)
        if len(already_paired) != len(self.players) - (1 if bye_assigned else 0):
            # Try to find a solution using full backtracking including bye selection
            # This is a fallback: brute force over all players to find ANY valid pairing + bye
            fallback_result = self._pair_with_global_backtracking()
            if fallback_result is not None:
                all_pairs = fallback_result
            else:
                self.pairing_possible = False
                return []

        # If we get here, pairing is successful
        self.pairings = all_pairs
        self.results = [None] * len(all_pairs)
        self._save_history()
        return all_pairs

    def _pair_with_global_backtracking(self):
        """Global backtracking to pair all players, allowing one bye."""
        players = self.players[:]
        total = len(players)
        # Try with bye if odd
        if total % 2 == 1:
            # Try each eligible player for bye
            eligible = [p for p in players if not p.has_bye]
            eligible.sort(key=lambda p: p.rating)
            for bye_player in eligible:
                rest = [p for p in players if p != bye_player]
                result = self._find_pairing(rest)
                if result is not None:
                    bye_player.points += 1.0
                    bye_player.has_bye = True
                    return [(bye_player, None)] + result
            return None
        else:
            # Even number, just pair
            result = self._find_pairing(players)
            if result is not None:
                return result
            return None

    def _save_history(self):
        """Save current round to history."""
        self.history.append({
            "round": self.current_round,
            "pairings": [(w.name, b.name if b else None) for w, b in self.pairings],
            "results": self.results.copy()
        })

    # ---------- SAVE / LOAD ----------
    def save_to_file(self, filename):
        data = {
            "current_round": self.current_round,
            "players": [p.to_dict() for p in self.players],
            "history": self.history,
            "pairing_possible": self.pairing_possible
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def load_from_file(self, filename):
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.clear()
        self.current_round = data["current_round"]
        self.players = [Player.from_dict(p) for p in data["players"]]
        self.history = data["history"]
        self.pairing_possible = data["pairing_possible"]

    # ---------- ENTER RESULT ----------
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


# ---------- GUI APP ----------
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Chess Swiss V2 - Backtracking Engine")
        self.root.geometry("1000x750")
        self.tournament = Tournament()
        self.top_color_white = True
        self.build_ui()
        self.update_player_table()
        self.update_pairings_display()

    def build_ui(self):
        # Top Frame: Add Player, Import, Save, Load, New
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
        ttk.Button(top_frame, text="Save", command=self.save_tournament).grid(row=0, column=6, padx=5)
        ttk.Button(top_frame, text="Load", command=self.load_tournament).grid(row=0, column=7, padx=5)
        ttk.Button(top_frame, text="New", command=self.new_tournament).grid(row=0, column=8, padx=5)

        # Players Tree
        f2 = ttk.LabelFrame(self.root, text="Players")
        f2.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree = ttk.Treeview(f2, columns=("Name","Rating","Points"), show="headings")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Rating", text="Rating")
        self.tree.heading("Points", text="Points")
        self.tree.pack(fill="both", expand=True)

        # Round Control Buttons
        f3 = ttk.Frame(self.root)
        f3.pack(fill="x", padx=10, pady=5)
        ttk.Button(f3, text="Round 1", command=self.round1).pack(side="left", padx=5)
        self.next_btn = ttk.Button(f3, text="Next Round", command=self.next_round)
        self.next_btn.pack(side="left", padx=5)
        ttk.Button(f3, text="Previous Rounds", command=self.show_history).pack(side="left", padx=5)
        self.round_label = ttk.Label(f3, text="Round: 0", font=("Arial", 10, "bold"))
        self.round_label.pack(side="left", padx=20)

        # Pairings Display
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

        # Result Buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="White Wins (1-0)", command=self.white_wins, width=15).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Black Wins (0-1)", command=self.black_wins, width=15).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Draw (½-½)", command=self.draw, width=15).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear Results", command=self.clear_results, width=15).pack(side="left", padx=20)

    # ---------- Handlers ----------
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
        self.update_pairings_display()

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

    def save_tournament(self):
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not filename:
            return
        try:
            self.tournament.save_to_file(filename)
            messagebox.showinfo("Success", "Tournament saved!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_tournament(self):
        filename = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not filename:
            return
        try:
            self.tournament.load_from_file(filename)
            self.update_player_table()
            self.update_pairings_display()
            self.round_label.config(text=f"Round: {self.tournament.current_round}")
            self.next_btn.config(state="normal" if self.tournament.pairing_possible else "disabled")
            messagebox.showinfo("Success", "Tournament loaded!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def new_tournament(self):
        if messagebox.askyesno("New", "Clear all data?"):
            self.tournament.clear()
            self.update_player_table()
            self.update_pairings_display()
            self.round_label.config(text="Round: 0")
            self.next_btn.config(state="normal")

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
        if not self.tournament.pairing_possible:
            messagebox.showinfo("Info", "Pairing ended. Cannot enter results.")
            return
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
        self.next_btn.config(state="normal")

    def next_round(self):
        if self.tournament.current_round == 0:
            messagebox.showerror("Error", "Round 1 first")
            return
        # Check if all results are entered (except byes)
        for i, r in enumerate(self.tournament.results):
            if self.tournament.pairings[i][1] is not None and r is None:
                if not messagebox.askyesno("Warning", "Some results missing. Continue?"):
                    return
                break
        self.tournament.current_round += 1
        pairs = self.tournament.pair_next_round()
        if not self.tournament.pairing_possible:
            messagebox.showinfo("Tournament Ended", 
                "Pairing Ended.\n\nNo valid pairing can be generated under current tournament rules.\n\n"
                "Reasons:\n- All possible opponents already played.\n- Bye already used for all players.\n"
                "Maximum possible rounds reached.")
            self.next_btn.config(state="disabled")
            self.pairings = []
            self.update_pairings_display()
            self.round_label.config(text=f"Round: {self.tournament.current_round} (Ended)")
            return
        self.update_pairings_display()
        self.round_label.config(text=f"Round: {self.tournament.current_round}")

    def show_history(self):
        if not self.tournament.history:
            messagebox.showinfo("Info", "No history yet.")
            return
        win = tk.Toplevel(self.root)
        win.title("Round History")
        win.geometry("600x400")
        tree = ttk.Treeview(win, columns=("Round", "Board", "White", "Black", "Result"), show="headings")
        tree.heading("Round", text="Round")
        tree.heading("Board", text="Board")
        tree.heading("White", text="White")
        tree.heading("Black", text="Black")
        tree.heading("Result", text="Result")
        tree.pack(fill="both", expand=True)
        for rec in self.tournament.history:
            rnd = rec["round"]
            for i, (w_name, b_name) in enumerate(rec["pairings"], 1):
                res = rec["results"][i-1] if rec["results"][i-1] else "Not played"
                tree.insert("", tk.END, values=(rnd, i, w_name, b_name if b_name else "Bye", res))

# ---------- MAIN ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()