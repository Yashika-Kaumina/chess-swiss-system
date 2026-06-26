import tkinter as tk
from tkinter import messagebox, ttk

class ChessPlayer:
    def __init__(self, name):
        self.name = name
        self.score = 0.0
        self.played_with = set()
        self.buchholz_score = 0.0

class CaissaSwissApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Caissa-Swiss Tournament Manager")
        self.root.geometry("600x550")
        self.root.configure(bg="#f0f2f5")

        self.players = []
        self.round_number = 0
        self.current_pairings = []

        # --- UI Design ---
        # Title
        title_label = tk.Label(root, text="🏆 Caissa-Swiss Chess System", font=("Arial", 18, "bold"), bg="#f0f2f5", fg="#1a252f")
        title_label.pack(pady=10)

        # Input Frame
        input_frame = tk.Frame(root, bg="#f0f2f5")
        input_frame.pack(pady=5)

        tk.Label(input_frame, text="Player Name:", font=("Arial", 11), bg="#f0f2f5").grid(row=0, column=0, padx=5)
        self.player_entry = tk.Entry(input_frame, font=("Arial", 11), width=20)
        self.player_entry.grid(row=0, column=1, padx=5)
        
        add_btn = tk.Button(input_frame, text="Add Player", command=self.add_player, bg="#2ecc71", fg="white", font=("Arial", 10, "bold"))
        add_btn.grid(row=0, column=2, padx=5)

        # Content Frame (Lists)
        content_frame = tk.Frame(root, bg="#f0f2f5")
        content_frame.pack(pady=10, fill="both", expand=True, padx=20)

        # Active Players List
        p_frame = tk.LabelFrame(content_frame, text=" Registered Players ", font=("Arial", 10, "bold"), bg="#f0f2f5")
        p_frame.pack(side="left", fill="both", expand=True, padx=5)
        self.player_box = tk.Listbox(p_frame, font=("Arial", 10), height=10)
        self.player_box.pack(fill="both", expand=True, padx=5, pady=5)

        # Pairings List
        pair_frame = tk.LabelFrame(content_frame, text=" Current Round Pairings ", font=("Arial", 10, "bold"), bg="#f0f2f5")
        pair_frame.pack(side="right", fill="both", expand=True, padx=5)
        self.pair_box = tk.Listbox(pair_frame, font=("Arial", 10), height=10)
        self.pair_box.pack(fill="both", expand=True, padx=5, pady=5)

        # Action Buttons
        btn_frame = tk.Frame(root, bg="#f0f2f5")
        btn_frame.pack(pady=15)

        self.pair_btn = tk.Button(btn_frame, text="🎲 Generate Next Round", command=self.generate_round, bg="#3498db", fg="white", font=("Arial", 11, "bold"), state="disabled")
        self.pair_btn.pack(side="left", padx=10)

        self.result_btn = tk.Button(btn_frame, text="⚖️ Enter Dummy Results", command=self.enter_dummy_results, bg="#e67e22", fg="white", font=("Arial", 11, "bold"), state="disabled")
        self.result_btn.pack(side="left", padx=10)

    def add_player(self):
        name = self.player_entry.get().strip()
        if name:
            if any(p.name.lower() == name.lower() for p in self.players):
                messagebox.showwarning("Warning", "Player already exists!")
                return
            self.players.append(ChessPlayer(name))
            self.player_box.insert(tk.END, f"{name} (Score: 0.0)")
            self.player_entry.delete(0, tk.END)
            if len(self.players) >= 2:
                self.pair_btn.config(state="normal")
        else:
            messagebox.showwarning("Warning", "Please enter a name!")

    def calculate_buchholz(self):
        for player in self.players:
            current_buchholz = 0.0
            for opponent_name in player.played_with:
                if opponent_name != "BYE":
                    opponent = next(p for p in self.players if p.name == opponent_name)
                    current_buchholz += opponent.score
            player.buchholz_score = current_buchholz

    def generate_round(self):
        self.round_number += 1
        self.calculate_buchholz()
        
        # Sort by Score, then Buchholz
        sorted_players = sorted(self.players, key=lambda x: (x.score, x.buchholz_score), reverse=True)
        
        self.current_pairings = []
        has_paired = set()
        self.pair_box.delete(0, tk.END)

        # Handle BYE for Odd numbers
        if len(sorted_players) % 2 != 0:
            for player in reversed(sorted_players):
                if "BYE" not in player.played_with:
                    self.current_pairings.append((player.name, "BYE"))
                    player.score += 1.0
                    player.played_with.add("BYE")
                    has_paired.add(player.name)
                    break

        # Main Pairing Logic
        for i in range(len(sorted_players)):
            player = sorted_players[i]
            if player.name in has_paired:
                continue

            paired = False
            for j in range(i + 1, len(sorted_players)):
                opponent = sorted_players[j]
                if opponent.name not in has_paired and opponent.name not in player.played_with:
                    self.current_pairings.append((player.name, opponent.name))
                    has_paired.add(player.name)
                    has_paired.add(opponent.name)
                    paired = True
                    break

            if not paired: # Relax constraints if impossible
                for j in range(i + 1, len(sorted_players)):
                    opponent = sorted_players[j]
                    if opponent.name not in has_paired:
                        self.current_pairings.append((player.name, opponent.name))
                        has_paired.add(player.name)
                        has_paired.add(opponent.name)
                        break

        # Display Pairings
        for p in self.current_pairings:
            self.pair_box.insert(tk.END, f"{p[0]} vs {p[1]}")
        
        self.pair_btn.config(state="disabled")
        self.result_btn.config(state="normal")
        messagebox.showinfo("Success", f"Round {self.round_number} Pairings Generated!")

    def enter_dummy_results(self):
        """ පද්ධතිය පරීක්ෂා කිරීමට Player 1 ට ජයග්‍රහණය ලබා දෙන Dummy ක්‍රමයක් """
        for p1_name, p2_name in self.current_pairings:
            if p2_name == "BYE":
                continue
            
            p1 = next(p for p in self.players if p.name == p1_name)
            p2 = next(p for p in self.players if p.name == p2_name)
            
            p1.played_with.add(p2.name)
            p2.played_with.add(p1.name)
            
            # Dummy result: Player 1 wins for testing
            p1.score += 1.0

        # Update Player Listbox
        self.player_box.delete(0, tk.END)
        for p in sorted(self.players, key=lambda x: x.score, reverse=True):
            self.player_box.insert(tk.END, f"{p.name} (Score: {p.score})")

        self.result_btn.config(state="disabled")
        self.pair_btn.config(state="normal")
        messagebox.showinfo("Results Updated", "Scores updated! Ready for next round.")

if __name__ == "__main__":
    root = tk.Tk()
    app = CaissaSwissApp(root)
    root.mainloop()