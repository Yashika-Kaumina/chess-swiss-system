import tkinter as tk
from tkinter import ttk, messagebox


class FoamPiece:
    def __init__(self, id, thickness, density, hardness):
        self.id = id
        self.thickness = thickness
        self.density = density
        self.hardness = hardness
    
    def calculate_score(self):
        return (self.thickness * 0.5) + (self.density * 0.3) + (self.hardness * 0.2)


def swiss_pair(pieces):
    scored = [(p, p.calculate_score()) for p in pieces]
    scored.sort(key=lambda x: x[1])
    
    used = set()
    pairs = []
    leftovers = []
    
    i = 0
    while i < len(scored):
        if scored[i][0].id in used:
            i += 1
            continue
        
        current = scored[i][0]
        best_match = None
        best_diff = float('inf')
        best_j = -1
        
        for j in range(i+1, len(scored)):
            if scored[j][0].id in used:
                continue
            diff = abs(scored[i][1] - scored[j][1])
            if diff < best_diff:
                best_diff = diff
                best_match = scored[j][0]
                best_j = j
        
        if best_match:
            pairs.append((current, best_match))
            used.add(current.id)
            used.add(best_match.id)
        else:
            leftovers.append(current)
            used.add(current.id)
        i += 1
    
    return pairs, leftovers



if __name__ == "__main__":
    # Sample foam pieces
    samples = [
        FoamPiece("F1", 10, 30, 2),
        FoamPiece("F2", 12, 28, 3),
        FoamPiece("F3", 10, 31, 2),
        FoamPiece("F4", 15, 35, 4),
        FoamPiece("F5", 11, 29, 2),
        FoamPiece("F6", 12, 30, 3)
    ]
    
    pairs, leftovers = swiss_pair(samples)
    
    print("Pairs:")
    for a, b in pairs:
        print(f"{a.id} -- {b.id}  (scores: {a.calculate_score():.2f}, {b.calculate_score():.2f})")
    if leftovers:
        print("Leftover:", [p.id for p in leftovers])



        import tkinter as tk
        from tkinter import ttk, messagebox

class FoamPairingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Foam Swiss Pairing System")
        self.pieces = []
        
        self.create_widgets()
    
    def create_widgets(self):
        # Input frame
        input_frame = ttk.LabelFrame(self.root, text="Add New Foam Piece")
        input_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(input_frame, text="ID:").grid(row=0, column=0)
        self.id_entry = ttk.Entry(input_frame, width=10)
        self.id_entry.grid(row=0, column=1)
        
        ttk.Label(input_frame, text="Thickness (mm):").grid(row=0, column=2)
        self.thick_entry = ttk.Entry(input_frame, width=10)
        self.thick_entry.grid(row=0, column=3)
        
        ttk.Label(input_frame, text="Density (kg/m³):").grid(row=1, column=0)
        self.dens_entry = ttk.Entry(input_frame, width=10)
        self.dens_entry.grid(row=1, column=1)
        
        ttk.Label(input_frame, text="Hardness (1-5):").grid(row=1, column=2)
        self.hard_entry = ttk.Entry(input_frame, width=10)
        self.hard_entry.grid(row=1, column=3)
        
        ttk.Button(input_frame, text="Add Piece", command=self.add_piece).grid(row=2, column=0, columnspan=4, pady=5)
        
        # Table frame
        table_frame = ttk.LabelFrame(self.root, text="Foam List")
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.tree = ttk.Treeview(table_frame, columns=("ID", "Thick", "Dens", "Hard", "Score"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Thick", text="Thick (mm)")
        self.tree.heading("Dens", text="Density")
        self.tree.heading("Hard", text="Hardness")
        self.tree.heading("Score", text="Score")
        self.tree.pack(fill="both", expand=True)
        
        ttk.Button(table_frame, text="Delete Selected", command=self.delete_selected).pack(pady=5)
        
        # Result frame
        result_frame = ttk.LabelFrame(self.root, text="Pairing Results")
        result_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.result_text = tk.Text(result_frame, height=8)
        self.result_text.pack(fill="both", expand=True)
        
        # Buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="Pair (Swiss)", command=self.run_pairing).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear All", command=self.clear_all).pack(side="left", padx=5)
    
    def add_piece(self):
        id_val = self.id_entry.get().strip()
        try:
            thick = float(self.thick_entry.get())
            dens = float(self.dens_entry.get())
            hard = int(self.hard_entry.get())
            if not (1 <= hard <= 5):
                raise ValueError
        except:
            messagebox.showerror("Error", "Please enter valid numbers")
            return
        if not id_val:
            messagebox.showerror("Error", "ID cannot be empty")
            return
        
        piece = FoamPiece(id_val, thick, dens, hard)
        self.pieces.append(piece)
        self.update_table()
        # Clear entries
        self.id_entry.delete(0, tk.END)
        self.thick_entry.delete(0, tk.END)
        self.dens_entry.delete(0, tk.END)
        self.hard_entry.delete(0, tk.END)
    
    def update_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for p in self.pieces:
            self.tree.insert("", tk.END, values=(p.id, p.thickness, p.density, p.hardness, f"{p.calculate_score():.2f}"))
    
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        for item in selected:
            values = self.tree.item(item, "values")
            if values:
                pid = values[0]
                self.pieces = [p for p in self.pieces if p.id != pid]
        self.update_table()
    
    def clear_all(self):
        self.pieces.clear()
        self.update_table()
        self.result_text.delete(1.0, tk.END)
    
    def run_pairing(self):
        if len(self.pieces) < 2:
            messagebox.showinfo("Info", "Need at least 2 pieces to pair")
            return
        pairs, leftovers = swiss_pair(self.pieces.copy())
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "====== Swiss Pairing Results ======\n\n")
        for a, b in pairs:
            self.result_text.insert(tk.END, f"{a.id}  <-->  {b.id}\n")
            self.result_text.insert(tk.END, f"   Scores: {a.calculate_score():.2f} , {b.calculate_score():.2f}\n\n")
        if leftovers:
            self.result_text.insert(tk.END, "Leftover pieces: " + ", ".join([p.id for p in leftovers]) + "\n")

# Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = FoamPairingApp(root)
    root.geometry("750x600")
    root.mainloop()