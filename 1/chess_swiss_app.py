import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

class Player:
    def __init__(self, name, rating):
        self.name = name
        self.rating = rating
        self.points = 0.0
        self.opponents = []

class Tournament:
    def __init__(self):
        self.players = []
        self.current_round = 0
        self.pairings = []

    def add_player(self, name, rating):
        self.players.append(Player(name, rating))

    def get_standings(self):
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
            bye.points += 1
            pairs.append((bye, None))
        for i in range(len(bottom)):
            if i % 2 == 0:
                white, black = top[i], bottom[i]
            else:
                white, black = bottom[i], top[i]
            pairs.append((white, black))
        self.pairings = pairs
        return pairs

    def enter_result(self, white, black, result):
        if result == '1-0':
            white.points += 1
        elif result == '0-1':
            black.points += 1
        elif result == '1/2-1/2':
            white.points += 0.5
            black.points += 0.5
        white.opponents.append(black.name)
        black.opponents.append(white.name)

class ChessApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chess Swiss System")
        self.root.geometry("800x600")
        self.tournament = Tournament()
        self.create_widgets()

    def create_widgets(self):
        # Input Frame
        frame = ttk.LabelFrame(self.root, text="Add Player")
        frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(frame, text="Name:").grid(row=0, column=0)
        self.name_entry = ttk.Entry(frame)
        self.name_entry.grid(row=0, column=1)
        ttk.Label(frame, text="Rating:").grid(row=0, column=2)
        self.rating_entry = ttk.Entry(frame)
        self.rating_entry.grid(row=0, column=3)
        ttk.Button(frame, text="Add", command=self.add_player).grid(row=0, column=4)

        # Players List
        self.tree = ttk.Treeview(self.root, columns=("Name", "Rating", "Points"), show="headings")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Rating", text="Rating")
        self.tree.heading("Points", text="Points")
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        # Round Control
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="Pair Round 1", command=self.pair_round1).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Enter Results", command=self.enter_results).pack(side="left", padx=5)
        self.round_label = ttk.Label(btn_frame, text="Round: 0")
        self.round_label.pack(side="left", padx=20)

        # Pairings Display
        self.pair_text = tk.Text(self.root, height=10)
        self.pair_text.pack(fill="both", expand=True, padx=10, pady=5)

    def add_player(self):
        name = self.name_entry.get().strip()
        try:
            rating = int(self.rating_entry.get().strip())
        except:
            rating = 1200
        if name:
            self.tournament.add_player(name, rating)
            self.update_player_list()
            self.name_entry.delete(0, tk.END)
            self.rating_entry.delete(0, tk.END)

    def update_player_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for p in self.tournament.get_standings():
            self.tree.insert("", tk.END, values=(p.name, p.rating, p.points))

    def pair_round1(self):
        if len(self.tournament.players) < 2:
            messagebox.showerror("Error", "Need at least 2 players")
            return
        self.tournament.current_round = 1
        pairs = self.tournament.pair_first_round()
        self.display_pairings(pairs)
        self.round_label.config(text="Round: 1")

    def display_pairings(self, pairs):
        self.pair_text.delete(1.0, tk.END)
        for i, (w, b) in enumerate(pairs, 1):
            if b is None:
                self.pair_text.insert(tk.END, f"Board {i}: {w.name} (bye)\n")
            else:
                self.pair_text.insert(tk.END, f"Board {i}: {w.name} (white) vs {b.name} (black)\n")

    def enter_results(self):
        if not self.tournament.pairings:
            messagebox.showinfo("Info", "No pairings yet")
            return
        for white, black in self.tournament.pairings:
            if black is None:
                continue
            res = simpledialog.askstring("Result", f"{white.name} vs {black.name}\n1-0, 0-1, 1/2-1/2")
            if res in ['1-0', '0-1', '1/2-1/2']:
                self.tournament.enter_result(white, black, res)
        self.update_player_list()
        self.tournament.pairings = []
        self.pair_text.delete(1.0, tk.END)
        self.pair_text.insert(tk.END, "Results saved. Click 'Pair Round 1' for new tournament or close.")
        messagebox.showinfo("Done", "Results recorded")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChessApp(root)
    root.mainloop()