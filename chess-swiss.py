import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import math


# ══════════════════════════════════════════════════════════════
#  DATA MODEL
# ══════════════════════════════════════════════════════════════

class Player:
    def __init__(self, name, rating):
        self.name    = name
        self.rating  = rating
        self.points  = 0.0
        self.opponents = []   # opponent names per round
        self.colors    = []   # 'white'/'black' per round
        self.has_bye   = False

    # color_diff: positive = more whites played, negative = more blacks
    def color_diff(self):
        return self.colors.count('white') - self.colors.count('black')

    # last color played
    def last_color(self):
        return self.colors[-1] if self.colors else None


class Tournament:
    def __init__(self):
        self.players       = []
        self.current_round = 0
        self.pairings      = []   # list of (white|None, black|None)  – bye => (player, None)
        self.results       = []   # '1-0' / '0-1' / '1/2-1/2' / None
        self.history       = []   # list of rounds: each = list of (wName, bName|None, result|None)
        self.pairing_ended = False   # set True when no more valid pairings possible

    # ── basic helpers ────────────────────────────────────────

    def add_player(self, name, rating):
        self.players.append(Player(name, rating))

    def clear(self):
        self.players.clear()
        self.current_round = 0
        self.pairings.clear()
        self.results.clear()
        self.history.clear()
        self.pairing_ended = False

    def standings(self):
        """Sort by points desc, rating desc, name asc."""
        return sorted(self.players,
                      key=lambda p: (-p.points, -p.rating, p.name))

    @staticmethod
    def recommended_rounds(n):
        if n < 2:
            return 0
        return max(3, math.ceil(math.log2(n)))

    # ── color assignment ────────────────────────────────────
    # Rules (priority order):
    #   1. Neither player should reach color_diff ±2  (absolute limit)
    #   2. Player whose last color differs gets their due color
    #   3. Player with lower color_diff (more blacks) gets white
    #   4. Tiebreak: higher score → white; then higher rating → white; then name asc → white
    #
    # "top_player" here means the higher-ranked of the two (score→rating→name).

    @staticmethod
    def _player_rank_key(p):
        return (-p.points, -p.rating, p.name)

    def assign_colors(self, p1, p2):
        """Return (white, black)."""

        def would_reach_limit(p, color):
            """True if giving 'color' to p would make |color_diff| reach 2."""
            diff = p.color_diff()
            if color == 'white':
                return diff + 1 >= 2
            else:
                return diff - 1 <= -2

        # Determine which is the "top" player by standing
        if self._player_rank_key(p1) <= self._player_rank_key(p2):
            top, bot = p1, p2
        else:
            top, bot = p2, p1

        # --- Step 1: absolute limit guard ---
        # If one player MUST NOT get a color (would hit ±2), force the other
        top_must_white = would_reach_limit(top, 'black')   # giving black to top forbidden
        top_must_black = would_reach_limit(top, 'white')   # giving white to top forbidden
        bot_must_white = would_reach_limit(bot, 'black')
        bot_must_black = would_reach_limit(bot, 'white')

        if top_must_white and not bot_must_black:
            return top, bot
        if top_must_black and not bot_must_white:
            return bot, top
        if bot_must_white and not top_must_black:
            return bot, top
        if bot_must_black and not top_must_white:
            return top, bot

        # --- Step 2: due color (alternation) for top player ---
        top_last = top.last_color()
        if top_last == 'white':
            # top is due black → top gets black
            return bot, top
        elif top_last == 'black':
            # top is due white → top gets white
            return top, bot

        # --- Step 3: color_diff balance ---
        td = top.color_diff()
        bd = bot.color_diff()
        if td < bd:    # top has more blacks → top gets white
            return top, bot
        if bd < td:
            return bot, top

        # --- Step 4: tiebreak → top player gets white ---
        return top, bot

    # ── bye selection ────────────────────────────────────────

    def _pick_bye_player(self, pool):
        """Lowest score → lowest rating → name asc; prefer players who haven't had a bye."""
        no_bye = [p for p in pool if not p.has_bye]
        candidates = no_bye if no_bye else pool
        return min(candidates, key=lambda p: (p.points, p.rating, p.name))

    # ── save round to history ───────────────────────────────

    def _save_to_history(self):
        """Call this after all results for the round are finalised (before next round)."""
        snap = []
        for i, (w, b) in enumerate(self.pairings):
            wn = w.name if w else None
            bn = b.name if b else None
            res = self.results[i] if i < len(self.results) else None
            snap.append((wn, bn, res))
        self.history.append(snap)

    # ══ ROUND 1 ══════════════════════════════════════════════
    # Classic top-half vs bottom-half.
    # top_color_white=True  → rank-1 player gets white on board 1,
    #                          rank-3 gets white on board 2, etc. (alternating)

    def pair_first_round(self, top_color_white=True):
        sorted_players = sorted(self.players, key=lambda p: (-p.rating, p.name))
        working = sorted_players[:]
        pairs   = []

        if len(working) % 2 == 1:
            bye_p = self._pick_bye_player(working)
            working.remove(bye_p)
            bye_p.points  += 1.0
            bye_p.has_bye  = True
            pairs.append((bye_p, None))

        mid    = len(working) // 2
        top    = working[:mid]
        bottom = working[mid:]

        for i in range(mid):
            if top_color_white:
                w, b = (top[i], bottom[i]) if i % 2 == 0 else (bottom[i], top[i])
            else:
                w, b = (bottom[i], top[i]) if i % 2 == 0 else (top[i], bottom[i])
            pairs.append((w, b))

        self.pairings      = pairs
        self.results       = [None] * len(pairs)
        self.pairing_ended = False
        return pairs

    # ══ ROUND 2+ ═════════════════════════════════════════════
    # Score-group top/bottom with:
    #   • no rematch
    #   • color balance (±2 limit + alternation)
    #   • float-down for odd groups
    #   • one bye per player max
    #   • "Pairing Ended" when no valid pairing exists

    def pair_next_round(self):
        self.pairing_ended = False

        all_players  = sorted(self.players,
                               key=lambda p: (-p.points, -p.rating, p.name))
        paired_names = set()
        all_pairs    = []

        # ── decide bye ──────────────────────────────────────
        bye_player = None
        if len(all_players) % 2 == 1:
            bye_player = self._pick_bye_player(all_players)

        # ── build score groups ──────────────────────────────
        groups_dict = {}
        for p in all_players:
            groups_dict.setdefault(p.points, []).append(p)
        score_levels = sorted(groups_dict.keys(), reverse=True)

        floater = None   # player dropped from previous group

        for score in score_levels:
            group = [p for p in groups_dict[score] if p.name not in paired_names]

            if floater:
                group = [floater] + group
                floater = None

            # Remove bye candidate from group if group is odd-sized
            if bye_player and bye_player in group and len(group) % 2 == 1:
                group.remove(bye_player)

            if len(group) < 2:
                if len(group) == 1:
                    floater = group[0]
                continue

            new_pairs, leftover = self._pair_group_top_bottom(group, paired_names)
            all_pairs.extend(new_pairs)
            for w, b in new_pairs:
                paired_names.add(w.name)
                paired_names.add(b.name)

            if leftover:
                floater = leftover

        # handle final floater
        if floater and floater.name not in paired_names:
            remaining = [p for p in all_players
                         if p.name not in paired_names and p is not bye_player]
            if remaining:
                opp = self._best_opponent(floater, remaining)
                if opp:
                    w, b = self.assign_colors(floater, opp)
                    all_pairs.append((w, b))
                    paired_names.add(floater.name)
                    paired_names.add(opp.name)

        # ── assign bye ──────────────────────────────────────
        if bye_player:
            if bye_player.name not in paired_names:
                bye_player.points += 1.0
                bye_player.has_bye = True
                all_pairs.append((bye_player, None))
                paired_names.add(bye_player.name)
            else:
                # bye_player got paired; find another unpaired player
                unpaired = [p for p in all_players if p.name not in paired_names]
                if unpaired:
                    alt = self._pick_bye_player(unpaired)
                    alt.points  += 1.0
                    alt.has_bye  = True
                    all_pairs.append((alt, None))
                    paired_names.add(alt.name)

        # ── check for "pairing ended" ────────────────────────
        still_unpaired = [p for p in all_players if p.name not in paired_names]
        if still_unpaired:
            # Cannot pair remaining players (all met each other)
            self.pairing_ended = True

        self.pairings = all_pairs
        self.results  = [None] * len(all_pairs)
        return all_pairs

    # ── group pairing: top/bottom with opponent-history check ─

    def _pair_group_top_bottom(self, group, already_paired):
        """
        Split group into top/bottom halves.
        Match top[i] with bottom[j] (prefer not-yet-played).
        Returns (pairs_list, leftover_player_or_None).
        """
        group = sorted(group, key=lambda p: (-p.points, -p.rating, p.name))
        n   = len(group)
        mid = n // 2
        top    = group[:mid]
        bottom = group[mid:]

        used_b = [False] * len(bottom)
        pairs  = []

        for t in top:
            # First pass: not-yet-played
            chosen = -1
            for j in range(len(bottom)):
                if not used_b[j] and t.name not in bottom[j].opponents:
                    chosen = j
                    break
            # Second pass: allow rematch if necessary
            if chosen == -1:
                for j in range(len(bottom)):
                    if not used_b[j]:
                        chosen = j
                        break
            if chosen != -1:
                w, b = self.assign_colors(t, bottom[chosen])
                pairs.append((w, b))
                used_b[chosen] = True

        leftover_bottom = [bottom[j] for j in range(len(bottom)) if not used_b[j]]
        paired_names_here = {p.name for pair in pairs for p in pair}
        leftover_top    = [t for t in top if t.name not in paired_names_here]
        leftover_all    = leftover_top + leftover_bottom

        leftover = leftover_all[0] if len(leftover_all) == 1 else None
        return pairs, leftover

    def _best_opponent(self, player, candidates):
        valid = [c for c in candidates if player.name not in c.opponents]
        pool  = valid if valid else candidates
        return min(pool, key=lambda c: abs(c.rating - player.rating)) if pool else None

    # ── enter result ────────────────────────────────────────

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


# ══════════════════════════════════════════════════════════════
#  GUI  (original tkinter style – no color themes)
# ══════════════════════════════════════════════════════════════

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Chess Swiss Manager")
        self.root.geometry("950x700")
        self.root.minsize(800, 560)
        self.tournament = Tournament()
        self.top_color_white = True
        self._build_ui()

    # ── UI construction ──────────────────────────────────────

    def _build_ui(self):
        # ── top input bar ──
        top = ttk.Frame(self.root, padding=4)
        top.pack(fill="x")

        ttk.Label(top, text="Name:").grid(row=0, column=0, padx=2)
        self.name_entry = ttk.Entry(top, width=20)
        self.name_entry.grid(row=0, column=1, padx=2)
        self.name_entry.bind("<Return>", lambda e: self.rating_entry.focus())

        ttk.Label(top, text="Rating:").grid(row=0, column=2, padx=2)
        self.rating_entry = ttk.Entry(top, width=8)
        self.rating_entry.grid(row=0, column=3, padx=2)
        self.rating_entry.bind("<Return>", lambda e: self.add_player())

        ttk.Button(top, text="Add Player",     command=self.add_player).grid(row=0, column=4, padx=4)
        ttk.Button(top, text="Import CSV",     command=self.import_csv).grid(row=0, column=5, padx=4)
        ttk.Button(top, text="New Tournament", command=self.new_tournament).grid(row=0, column=6, padx=4)

        # ── player list ──
        pf = ttk.LabelFrame(self.root, text="Players & Standings", padding=4)
        pf.pack(fill="both", expand=False, padx=6, pady=4)

        cols = ("Rank", "Name", "Rating", "Points", "Colors")
        self.tree = ttk.Treeview(pf, columns=cols, show="headings", height=6)
        self.tree.heading("Rank",   text="#")
        self.tree.heading("Name",   text="Name")
        self.tree.heading("Rating", text="Rating")
        self.tree.heading("Points", text="Pts")
        self.tree.heading("Colors", text="W/B  (diff)")
        self.tree.column("Rank",   width=30,  anchor="center", stretch=False)
        self.tree.column("Name",   width=160, stretch=True)
        self.tree.column("Rating", width=60,  anchor="center", stretch=False)
        self.tree.column("Points", width=50,  anchor="center", stretch=False)
        self.tree.column("Colors", width=110, anchor="center", stretch=False)
        sb = ttk.Scrollbar(pf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # ── round control ──
        ctrl = ttk.Frame(self.root, padding=4)
        ctrl.pack(fill="x", padx=6)
        ttk.Button(ctrl, text="Round 1",       command=self.round1).pack(side="left", padx=4)
        ttk.Button(ctrl, text="Next Round",    command=self.next_round).pack(side="left", padx=4)
        ttk.Button(ctrl, text="Round Info",    command=self.show_round_info).pack(side="left", padx=4)
        ttk.Button(ctrl, text="Round History", command=self.show_history).pack(side="left", padx=4)
        self.round_lbl = ttk.Label(ctrl, text="Round: 0", font=("Arial", 10, "bold"))
        self.round_lbl.pack(side="left", padx=16)
        self.rec_lbl = ttk.Label(ctrl, text="", font=("Arial", 9))
        self.rec_lbl.pack(side="left")

        # ── pairings table ──
        pf2 = ttk.LabelFrame(self.root, text="Current Pairings  (select a board, then enter result)",
                              padding=4)
        pf2.pack(fill="both", expand=True, padx=6, pady=4)

        cols2 = ("Board", "White", "Black", "Result")
        self.pair_tree = ttk.Treeview(pf2, columns=cols2, show="headings")
        self.pair_tree.heading("Board",  text="Brd")
        self.pair_tree.heading("White",  text="White")
        self.pair_tree.heading("Black",  text="Black")
        self.pair_tree.heading("Result", text="Result")
        self.pair_tree.column("Board",  width=36,  anchor="center", stretch=False)
        self.pair_tree.column("White",  width=200, stretch=True)
        self.pair_tree.column("Black",  width=200, stretch=True)
        self.pair_tree.column("Result", width=110, anchor="center", stretch=False)
        sb2 = ttk.Scrollbar(pf2, orient="vertical", command=self.pair_tree.yview)
        self.pair_tree.configure(yscrollcommand=sb2.set)
        self.pair_tree.pack(side="left", fill="both", expand=True)
        sb2.pack(side="right", fill="y")
        self.pair_tree.bind("<<TreeviewSelect>>", self._on_select)
        self.current_selection = None

        # ── result buttons ──
        bf = ttk.Frame(self.root, padding=4)
        bf.pack(fill="x", padx=6)
        ttk.Button(bf, text="White Wins (1-0)",  command=self.white_wins,   width=18).pack(side="left", padx=4)
        ttk.Button(bf, text="Black Wins (0-1)",  command=self.black_wins,   width=18).pack(side="left", padx=4)
        ttk.Button(bf, text="Draw (1/2-1/2)",    command=self.draw,         width=18).pack(side="left", padx=4)
        ttk.Button(bf, text="Clear Results",     command=self.clear_results, width=14).pack(side="left", padx=16)

        # ── status bar ──
        self.status_var = tk.StringVar(value="Welcome!  Add players and start the tournament.")
        ttk.Label(self.root, textvariable=self.status_var, relief="sunken",
                  anchor="w").pack(fill="x", side="bottom", padx=0, pady=0)

    # ── player table helpers ──────────────────────────────────

    def _update_player_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for rank, p in enumerate(self.tournament.standings(), 1):
            w = p.colors.count('white')
            b = p.colors.count('black')
            diff = p.color_diff()
            sign = "+" if diff > 0 else ""
            color_str = f"W{w} B{b}  ({sign}{diff})"
            pts = f"{p.points:.1f}" if p.points % 1 else str(int(p.points))
            self.tree.insert("", tk.END, values=(rank, p.name, p.rating, pts, color_str))

    def _update_recommended(self):
        n = len(self.tournament.players)
        if n >= 2:
            r = Tournament.recommended_rounds(n)
            self.rec_lbl.config(text=f"[Suggested: {r} rounds for {n} players]")
        else:
            self.rec_lbl.config(text="")

    def _update_pairings_display(self):
        for row in self.pair_tree.get_children():
            self.pair_tree.delete(row)
        for i, (w, b) in enumerate(self.tournament.pairings, 1):
            if b is None:
                self.pair_tree.insert("", tk.END, values=(i, w.name, "---", "BYE"))
            else:
                res = self.tournament.results[i - 1]
                self.pair_tree.insert("", tk.END,
                                      values=(i, w.name, b.name,
                                              res if res else "Not played"))
        kids = self.pair_tree.get_children()
        if kids:
            self.pair_tree.selection_set(kids[0])

    # ── selection & result entry ──────────────────────────────

    def _on_select(self, event):
        sel = self.pair_tree.selection()
        self.current_selection = sel[0] if sel else None

    def _get_idx(self):
        if not self.current_selection:
            self.status_var.set("Select a board first.")
            return -1
        vals = self.pair_tree.item(self.current_selection, "values")
        return int(vals[0]) - 1 if vals else -1

    def _record(self, code):
        idx = self._get_idx()
        if idx < 0 or idx >= len(self.tournament.pairings):
            return
        w, b = self.tournament.pairings[idx]
        if b is None:
            self.status_var.set("Bye board – no result to enter.")
            return

        existing = self.tournament.results[idx]
        if existing is not None:
            if not messagebox.askyesno("Overwrite", f"Board {idx+1} already has '{existing}'. Overwrite?"):
                return
            # Undo old result
            if existing == '1-0':   w.points -= 1.0
            elif existing == '0-1': b.points -= 1.0
            else:                   w.points -= 0.5; b.points -= 0.5
            self._remove_last_encounter(w, b)

        self.tournament.enter_result(w, b, code)
        self.tournament.results[idx] = code
        self._update_pairings_display()
        self._update_player_table()
        self.status_var.set(f"Board {idx+1}: {w.name} vs {b.name}  →  {code}")

    def _remove_last_encounter(self, w, b):
        """Remove the most recent mutual opponent/color record."""
        if b.name in w.opponents:
            i2 = len(w.opponents) - 1 - w.opponents[::-1].index(b.name)
            w.opponents.pop(i2); w.colors.pop(i2)
        if w.name in b.opponents:
            i2 = len(b.opponents) - 1 - b.opponents[::-1].index(w.name)
            b.opponents.pop(i2); b.colors.pop(i2)

    def white_wins(self): self._record('1-0')
    def black_wins(self): self._record('0-1')
    def draw(self):       self._record('1/2-1/2')

    def clear_results(self):
        if not self.tournament.pairings:
            return
        if not messagebox.askyesno("Clear Results", "Clear ALL results for this round?"):
            return
        for idx, (w, b) in enumerate(self.tournament.pairings):
            if b is None:
                continue
            old = self.tournament.results[idx]
            if old:
                if old == '1-0':   w.points -= 1.0
                elif old == '0-1': b.points -= 1.0
                else:              w.points -= 0.5; b.points -= 0.5
                self._remove_last_encounter(w, b)
                self.tournament.results[idx] = None
        self._update_player_table()
        self._update_pairings_display()
        self.status_var.set("All results cleared for this round.")

    # ── player management ────────────────────────────────────

    def add_player(self):
        name    = self.name_entry.get().strip()
        rat_str = self.rating_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Player name required.")
            return
        if any(p.name.lower() == name.lower() for p in self.tournament.players):
            messagebox.showerror("Error", f"'{name}' already exists.")
            return
        try:
            rat = int(rat_str) if rat_str else 1200
            if not (0 <= rat <= 4000):
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Rating must be an integer 0–4000.")
            return
        self.tournament.add_player(name, rat)
        self.name_entry.delete(0, tk.END)
        self.rating_entry.delete(0, tk.END)
        self.name_entry.focus()
        self._update_player_table()
        self._update_recommended()
        self.status_var.set(f"Added {name} ({rat})")

    def import_csv(self):
        fn = filedialog.askopenfilename(title="Select CSV",
                                        filetypes=[("CSV files", "*.csv"), ("All", "*.*")])
        if not fn:
            return
        try:
            with open(fn, 'r', encoding='utf-8-sig') as f:
                rows = list(csv.reader(f))
            if rows and rows[0] and rows[0][0].strip().lower() in ('name', 'player'):
                rows = rows[1:]
            count = 0
            for row in rows:
                if not row:
                    continue
                name = row[0].strip()
                try:
                    rating = int(float(row[1].strip())) if len(row) > 1 and row[1].strip() else 1200
                except:
                    rating = 1200
                if name and not any(p.name.lower() == name.lower() for p in self.tournament.players):
                    self.tournament.add_player(name, rating)
                    count += 1
            self._update_player_table()
            self._update_recommended()
            messagebox.showinfo("Imported", f"{count} players imported.")
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    # ── round management ─────────────────────────────────────

    def show_round_info(self):
        n = len(self.tournament.players)
        if n < 2:
            messagebox.showinfo("Round Info", "Add at least 2 players first.")
            return
        rec  = Tournament.recommended_rounds(n)
        maxr = n - 1
        msg  = (
            f"Total players      : {n}\n\n"
            f"Recommended rounds : {rec}   (ceil of log\u2082({n}))\n"
            f"Maximum rounds     : {maxr}   (everyone meets everyone once)\n\n"
            f"Current round      : {self.tournament.current_round}\n\n"
            f"After {rec} rounds a clear winner usually emerges.\n"
            f"You can continue up to {maxr} rounds for full resolution."
        )
        messagebox.showinfo("Round Information", msg)

    def show_history(self):
        if not self.tournament.history:
            messagebox.showinfo("History", "No completed rounds yet.")
            return
        win = tk.Toplevel(self.root)
        win.title("Round History")
        win.geometry("620x480")

        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True, padx=6, pady=6)

        for rnum, snap in enumerate(self.tournament.history, 1):
            frame = ttk.Frame(nb)
            nb.add(frame, text=f"Round {rnum}")

            cols = ("Board", "White", "Black", "Result")
            tv   = ttk.Treeview(frame, columns=cols, show="headings")
            tv.heading("Board",  text="Brd")
            tv.heading("White",  text="White")
            tv.heading("Black",  text="Black")
            tv.heading("Result", text="Result")
            tv.column("Board",  width=40,  anchor="center", stretch=False)
            tv.column("White",  width=170, stretch=True)
            tv.column("Black",  width=170, stretch=True)
            tv.column("Result", width=100, anchor="center", stretch=False)
            sb = ttk.Scrollbar(frame, orient="vertical", command=tv.yview)
            tv.configure(yscrollcommand=sb.set)
            tv.pack(side="left", fill="both", expand=True)
            sb.pack(side="right", fill="y")

            for i, (wn, bn, res) in enumerate(snap, 1):
                black_str  = bn if bn else "---"
                result_str = res if res else ("BYE" if bn is None else "Not entered")
                tv.insert("", tk.END, values=(i, wn, black_str, result_str))

        ttk.Button(win, text="Close", command=win.destroy).pack(pady=6)

    def round1(self):
        if len(self.tournament.players) < 2:
            messagebox.showerror("Error", "Need at least 2 players.")
            return
        if self.tournament.current_round > 0:
            if not messagebox.askyesno("Restart?",
                                       "Round 1 already started.\n"
                                       "Restart from scratch? (All data will be lost.)"):
                return
            for p in self.tournament.players:
                p.points = 0.0; p.opponents.clear()
                p.colors.clear(); p.has_bye = False
            self.tournament.current_round = 0
            self.tournament.pairings.clear()
            self.tournament.results.clear()
            self.tournament.history.clear()
            self.tournament.pairing_ended = False

        top_player = self.tournament.standings()[0]
        ans = messagebox.askyesno(
            "Round 1 – Color",
            f"Top rated player:  {top_player.name}  ({top_player.rating})\n\n"
            "Give WHITE to the top rated player?\n\n"
            "Yes → Top player gets White on board 1\n"
            "No  → Top player gets Black on board 1"
        )
        self.top_color_white = ans
        self.tournament.current_round = 1
        self.tournament.pair_first_round(self.top_color_white)
        self._update_pairings_display()
        self._update_player_table()
        self.round_lbl.config(text=f"Round: {self.tournament.current_round}")
        self.status_var.set(f"Round 1 pairings done.  {len(self.tournament.pairings)} boards.")

    def next_round(self):
        if self.tournament.current_round == 0:
            messagebox.showerror("Error", "Start with Round 1 first.")
            return
        if self.tournament.pairing_ended:
            messagebox.showinfo("Pairing Ended",
                                "Pairing Ended.\n\n"
                                "All possible pairings have been exhausted.\n"
                                "Every player has already played every other player.\n"
                                "The tournament cannot continue further.")
            return

        # Warn missing results
        missing = [i + 1 for i, r in enumerate(self.tournament.results)
                   if self.tournament.pairings[i][1] is not None and r is None]
        if missing:
            boards = ", ".join(str(x) for x in missing)
            if not messagebox.askyesno("Missing Results",
                                       f"Boards {boards} have no result.\nContinue anyway?"):
                return

        # Warn max rounds
        n = len(self.tournament.players)
        if self.tournament.current_round >= n - 1:
            if not messagebox.askyesno("Max Rounds Reached",
                                       f"Round {self.tournament.current_round} is the maximum useful round "
                                       f"for {n} players (max = {n-1}).\nContinue anyway?"):
                return

        # Save current round to history before moving on
        self.tournament._save_to_history()

        self.tournament.current_round += 1
        self.tournament.pair_next_round()

        # Check if pairing ended after generating
        if self.tournament.pairing_ended:
            self._update_pairings_display()
            self._update_player_table()
            self.round_lbl.config(text=f"Round: {self.tournament.current_round}")
            messagebox.showinfo("Pairing Ended",
                                "Pairing Ended.\n\n"
                                "No valid pairings could be generated.\n"
                                "All players have already played each other.\n"
                                "This is the last round of the tournament.")
            self.status_var.set("Pairing Ended – tournament complete.")
            return

        self._update_pairings_display()
        self._update_player_table()
        self.round_lbl.config(text=f"Round: {self.tournament.current_round}")
        self.status_var.set(f"Round {self.tournament.current_round} pairings done.")

    def new_tournament(self):
        if messagebox.askyesno("New Tournament", "Clear everything and start fresh?"):
            self.tournament.clear()
            self._update_player_table()
            self._update_pairings_display()
            self.round_lbl.config(text="Round: 0")
            self.rec_lbl.config(text="")
            self.status_var.set("New tournament started.  Add players.")


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    app  = App(root)
    root.mainloop()