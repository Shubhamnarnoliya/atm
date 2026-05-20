import mysql.connector
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from tkinter import ttk

# ====== VOICE (pyttsx3) ======
try:
    import pyttsx3
    tts_engine = pyttsx3.init()
    tts_engine.setProperty("rate", 175)  # speed
    tts_engine.setProperty("volume", 1.0)
except Exception:
    tts_engine = None


def speak(text: str):
    """Speak text using pyttsx3 (if available)."""
    if tts_engine is None:
        return
    try:
        tts_engine.say(text)
        tts_engine.runAndWait()
    except Exception:
        # If audio fails, just ignore (do not crash app)
        pass


# ========== DATABASE HELPERS ==========

from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

def get_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


def get_account(account_no, pin):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT account_no, name, balance FROM accounts WHERE account_no=%s AND pin=%s",
        (account_no, pin),
    )
    row = cur.fetchone()
    conn.close()
    return row  # (account_no, name, balance) or None


def get_balance(account_no):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT balance FROM accounts WHERE account_no=%s", (account_no,))
    row = cur.fetchone()
    conn.close()
    return float(row[0]) if row else None


def update_balance(account_no, new_balance):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE accounts SET balance=%s WHERE account_no=%s",
        (new_balance, account_no),
    )
    conn.commit()
    conn.close()


def update_pin(account_no, new_pin):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE accounts SET pin=%s WHERE account_no=%s",
        (new_pin, account_no),
    )
    conn.commit()
    conn.close()


def log_transaction(account_no, txn_type, amount, balance_after):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transactions(account_no,txn_type,amount,balance_after) "
        "VALUES(%s,%s,%s,%s)",
        (account_no, txn_type, amount, balance_after),
    )
    conn.commit()
    conn.close()


def get_last_5(account_no):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT txn_time, txn_type, amount, balance_after "
        "FROM transactions WHERE account_no=%s "
        "ORDER BY txn_time DESC LIMIT 5",
        (account_no,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_transactions(account_no):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT txn_time, txn_type, amount, balance_after "
        "FROM transactions WHERE account_no=%s "
        "ORDER BY txn_time ASC",
        (account_no,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_account_name(account_no):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM accounts WHERE account_no=%s", (account_no,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def create_account_db(account_no, name, pin, balance):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO accounts(account_no,name,pin,balance) "
            "VALUES(%s,%s,%s,%s)",
            (account_no, name, pin, balance),
        )
        conn.commit()
        log_transaction(account_no, "OPENING", balance, balance)
        return True, "Account created successfully!"
    except mysql.connector.IntegrityError:
        return False, "Account number already exists!"
    finally:
        conn.close()


def get_all_accounts():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT account_no, name, balance FROM accounts")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_total_bank_balance():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT SUM(balance) FROM accounts")
    row = cur.fetchone()
    conn.close()
    return float(row[0]) if row[0] is not None else 0.0


# ========== TKINTER APP ==========

class ATMApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ATM System - Voice Enabled")
        self.geometry("560x520")
        self.resizable(False, False)

        # Theme
        self.bg_color = "#0f172a"
        self.card_color = "#1e293b"
        self.accent_color = "#38bdf8"
        self.text_color = "#e5e7eb"
        self.button_color = "#0ea5e9"
        self.configure(bg=self.bg_color)

        self.current_account = None
        self.current_name = None

        # optional logo
        self.logo_img = None
        try:
            self.logo_img = tk.PhotoImage(file="logo.png")
        except Exception:
            self.logo_img = None

        speak("Welcome to voice enabled ATM.")
        self.show_login_screen()

    # ---------- Utility ----------

    def clear_window(self):
        for w in self.winfo_children():
            w.destroy()

    def create_header(self, parent, title):
        header = tk.Frame(parent, bg=self.card_color)
        header.pack(fill="x", pady=10, padx=15)

        if self.logo_img:
            tk.Label(header, image=self.logo_img, bg=self.card_color).pack(
                side="left", padx=10
            )
        else:
            tk.Label(
                header,
                text="🏦",
                font=("Arial", 20, "bold"),
                bg=self.card_color,
                fg=self.accent_color,
            ).pack(side="left", padx=10)

        tk.Label(
            header,
            text=title,
            font=("Arial", 16, "bold"),
            bg=self.card_color,
            fg=self.text_color,
        ).pack(side="left", padx=10)

    def voice_button(self, parent, text, command, **kwargs):
        """Create a button that also speaks when pressed."""
        def wrapped():
            speak(text)
            command()
        return tk.Button(parent, text=text, command=wrapped, **kwargs)

    # ---------- Screens ----------

    def show_login_screen(self):
        self.clear_window()
        frame = tk.Frame(self, bg=self.bg_color)
        frame.pack(expand=True, fill="both")

        self.create_header(frame, "Welcome to My Bank ATM")

        card = tk.Frame(frame, bg=self.card_color)
        card.pack(pady=20, padx=40, fill="x")

        tk.Label(
            card,
            text="User / Admin Login",
            font=("Arial", 14, "bold"),
            bg=self.card_color,
            fg=self.accent_color,
        ).pack(pady=10)

        tk.Label(card, text="Account / Username:", bg=self.card_color, fg=self.text_color).pack()
        acc_entry = tk.Entry(card, width=25)
        acc_entry.pack(pady=5)

        tk.Label(card, text="PIN / Password:", bg=self.card_color, fg=self.text_color).pack()
        pin_entry = tk.Entry(card, width=25, show="*")
        pin_entry.pack(pady=5)

        def do_login():
            acc = acc_entry.get().strip()
            pin = pin_entry.get().strip()

            if not acc or not pin:
                messagebox.showwarning(
                    "Input Error", "Please enter Account/Username and PIN/Password."
                )
                speak("Please enter account and pin.")
                return

            # Admin login
            if acc == "admin" and pin == "admin123":
                messagebox.showinfo("Admin Login", "Welcome, Admin!")
                speak("Admin login successful.")
                self.show_admin_panel()
                return

            # User login
            user = get_account(acc, pin)
            if user:
                self.current_account, self.current_name, bal = user
                messagebox.showinfo("Login", f"Welcome, {self.current_name} 👋")
                speak(f"Welcome {self.current_name}. You are now logged in.")
                self.show_main_menu()
            else:
                messagebox.showerror("Login Failed", "Invalid account or PIN!")
                speak("Login failed. Invalid account or pin.")

        self.voice_button(
            card,
            "Login",
            do_login,
            width=15,
            bg=self.button_color,
            fg=self.bg_color,
        ).pack(pady=10)

        self.voice_button(
            card,
            "Create New Account",
            self.show_create_account_screen,
            width=18,
            bg="#4ade80",
            fg="#022c22",
        ).pack(pady=5)

        self.voice_button(
            card,
            "Exit",
            self.destroy,
            width=10,
            bg="#ef4444",
            fg="white",
        ).pack(pady=5)

    def show_main_menu(self):
        self.clear_window()
        frame = tk.Frame(self, bg=self.bg_color)
        frame.pack(expand=True, fill="both")

        self.create_header(frame, "ATM Dashboard")

        card = tk.Frame(frame, bg=self.card_color)
        card.pack(pady=15, padx=40, fill="x")

        tk.Label(
            card,
            text=f"Welcome, {self.current_name}",
            font=("Arial", 14, "bold"),
            bg=self.card_color,
            fg=self.text_color,
        ).pack(pady=8)

        self.balance_label = tk.Label(
            card,
            text="",
            font=("Consolas", 12),
            bg=self.card_color,
            fg=self.accent_color,
        )
        self.balance_label.pack(pady=8)
        self.refresh_balance_label()

        btn_frame = tk.Frame(frame, bg=self.bg_color)
        btn_frame.pack(pady=10)

        def add_btn(text, cmd, r, c):
            self.voice_button(
                btn_frame,
                text,
                cmd,
                width=20,
                bg=self.button_color,
                fg=self.bg_color,
            ).grid(row=r, column=c, padx=8, pady=6)

        add_btn("Check Balance", self.refresh_balance_label, 0, 0)
        add_btn("Deposit", self.deposit_window, 0, 1)
        add_btn("Withdraw", self.withdraw_window, 1, 0)
        add_btn("Quick Cash", self.quick_cash_window, 1, 1)
        add_btn("Transfer", self.transfer_window, 2, 0)
        add_btn("Mini Statement", self.show_mini_statement, 2, 1)
        add_btn("Change PIN", self.change_pin_window, 3, 0)
        add_btn("Download History", self.download_statement, 3, 1)

        self.voice_button(
            frame,
            "Logout",
            self.logout,
            width=14,
            bg="#f97316",
            fg="black",
        ).pack(pady=10)

        speak("Main menu loaded. You can check balance, deposit, withdraw, quick cash, transfer, view statement, change pin or download history.")

    def show_create_account_screen(self):
        win = tk.Toplevel(self)
        win.title("Create New Account")
        win.geometry("400x320")
        win.resizable(False, False)
        win.configure(bg=self.bg_color)

        tk.Label(
            win,
            text="Create New Account",
            font=("Arial", 14, "bold"),
            bg=self.bg_color,
            fg=self.accent_color,
        ).grid(row=0, column=0, columnspan=2, pady=10)

        def add_row(label, r):
            tk.Label(win, text=label, bg=self.bg_color, fg=self.text_color).grid(
                row=r, column=0, sticky="e", padx=5, pady=5
            )

        add_row("Name:", 1)
        name_entry = tk.Entry(win, width=25)
        name_entry.grid(row=1, column=1, padx=5, pady=5)

        add_row("Account No:", 2)
        acc_entry = tk.Entry(win, width=25)
        acc_entry.grid(row=2, column=1, padx=5, pady=5)

        add_row("PIN (4 digits):", 3)
        pin_entry = tk.Entry(win, width=25, show="*")
        pin_entry.grid(row=3, column=1, padx=5, pady=5)

        add_row("Confirm PIN:", 4)
        pin2_entry = tk.Entry(win, width=25, show="*")
        pin2_entry.grid(row=4, column=1, padx=5, pady=5)

        add_row("Opening Balance:", 5)
        bal_entry = tk.Entry(win, width=25)
        bal_entry.grid(row=5, column=1, padx=5, pady=5)

        def do_create():
            name = name_entry.get().strip()
            acc = acc_entry.get().strip()
            pin = pin_entry.get().strip()
            pin2 = pin2_entry.get().strip()
            bal_str = bal_entry.get().strip()

            if not (name and acc and pin and pin2 and bal_str):
                messagebox.showwarning("Input Error", "All fields are required.")
                speak("All fields are required.")
                return

            if pin != pin2:
                messagebox.showerror("Error", "PIN and Confirm PIN do not match.")
                speak("PIN and confirm PIN do not match.")
                return

            if not (pin.isdigit() and len(pin) == 4):
                messagebox.showerror("Error", "PIN must be 4 digits.")
                speak("PIN must be four digits.")
                return

            try:
                opening_balance = float(bal_str)
                if opening_balance < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Invalid opening balance.")
                speak("Invalid opening balance.")
                return

            ok, msg = create_account_db(acc, name, pin, opening_balance)
            if ok:
                messagebox.showinfo("Success", msg)
                speak("Account created successfully.")
                win.destroy()
            else:
                messagebox.showerror("Error", msg)
                speak("Failed to create account. Account number already exists.")

        self.voice_button(
            win,
            "Create Account",
            do_create,
            bg="#4ade80",
            fg="#022c22",
        ).grid(row=6, column=0, columnspan=2, pady=15)

    # ---------- User Operations ----------

    def refresh_balance_label(self):
        if self.current_account:
            bal = get_balance(self.current_account)
            self.balance_label.config(text=f"Balance: ₹{bal:.2f}")
            speak(f"Your current balance is {bal:.2f} rupees.")

    def deposit_window(self):
        amount = simpledialog.askfloat("Deposit", "Enter amount (₹):", minvalue=1)
        if amount:
            bal = get_balance(self.current_account)
            new_bal = bal + amount
            update_balance(self.current_account, new_bal)
            log_transaction(self.current_account, "DEPOSIT", amount, new_bal)
            messagebox.showinfo("Deposit", f"₹{amount:.2f} deposited.")
            speak(f"{amount:.2f} rupees deposited. New balance is {new_bal:.2f} rupees.")
            self.refresh_balance_label()

    def _process_withdraw(self, amount):
        bal = get_balance(self.current_account)
        if amount > bal:
            messagebox.showerror("Error", "Insufficient balance.")
            speak("Insufficient balance.")
            return False
        new_bal = bal - amount
        update_balance(self.current_account, new_bal)
        log_transaction(self.current_account, "WITHDRAW", amount, new_bal)
        messagebox.showinfo("Withdraw", f"₹{amount:.2f} withdrawn.")
        speak(f"{amount:.2f} rupees withdrawn. New balance is {new_bal:.2f} rupees.")
        self.refresh_balance_label()
        return True

    def withdraw_window(self):
        amount = simpledialog.askfloat("Withdraw", "Enter amount (₹):", minvalue=1)
        if amount:
            self._process_withdraw(amount)

    def quick_cash_window(self):
        win = tk.Toplevel(self)
        win.title("Quick Cash")
        win.geometry("280x240")
        win.resizable(False, False)
        win.configure(bg=self.bg_color)

        tk.Label(
            win,
            text="Quick Cash",
            font=("Arial", 14, "bold"),
            bg=self.bg_color,
            fg=self.accent_color,
        ).pack(pady=10)

        btn_frame = tk.Frame(win, bg=self.bg_color)
        btn_frame.pack(pady=5)

        def qc_btn(text, amount):
            btn = self.voice_button(
                btn_frame,
                text,
                lambda: (self._process_withdraw(amount) and win.destroy()),
                width=10,
                bg=self.button_color,
                fg=self.bg_color,
            )
            btn.pack(pady=4)

        qc_btn("₹500", 500)
        qc_btn("₹1000", 1000)
        qc_btn("₹2000", 2000)
        qc_btn("₹5000", 5000)

        def custom():
            amount = simpledialog.askfloat(
                "Quick Cash", "Enter amount (₹):", minvalue=1, parent=win
            )
            if amount:
                if self._process_withdraw(amount):
                    win.destroy()

        self.voice_button(
            win,
            "Custom",
            custom,
            bg="#4ade80",
            fg="#022c22",
        ).pack(pady=5)

        self.voice_button(
            win,
            "Close",
            win.destroy,
            bg="#ef4444",
            fg="white",
        ).pack(pady=5)

    def transfer_window(self):
        to_acc = simpledialog.askstring("Transfer", "Enter receiver Account No:")
        if not to_acc:
            return
        amt = simpledialog.askfloat("Transfer", "Enter amount (₹):", minvalue=1)
        if not amt:
            return

        receiver_name = get_account_name(to_acc)
        receiver_balance = get_balance(to_acc)

        if receiver_name is None or receiver_balance is None:
            messagebox.showerror("Error", "Receiver account not found.")
            speak("Receiver account not found.")
            return

        sender_balance = get_balance(self.current_account)
        if amt > sender_balance:
            messagebox.showerror("Error", "Insufficient balance.")
            speak("Insufficient balance for transfer.")
            return

        new_sender = sender_balance - amt
        new_receiver = receiver_balance + amt

        update_balance(self.current_account, new_sender)
        update_balance(to_acc, new_receiver)

        log_transaction(self.current_account, "TRANSFER_OUT", amt, new_sender)
        log_transaction(to_acc, "TRANSFER_IN", amt, new_receiver)

        messagebox.showinfo(
            "Transfer",
            f"₹{amt:.2f} transferred to {receiver_name} ({to_acc}).",
        )
        speak(f"{amt:.2f} rupees transferred to {receiver_name}. Your new balance is {new_sender:.2f} rupees.")
        self.refresh_balance_label()

    def show_mini_statement(self):
        txns = get_last_5(self.current_account)
        win = tk.Toplevel(self)
        win.title("Mini Statement")
        win.geometry("600x260")
        win.configure(bg=self.bg_color)

        tk.Label(
            win,
            text="Last 5 Transactions",
            font=("Arial", 13, "bold"),
            bg=self.bg_color,
            fg=self.accent_color,
        ).pack(pady=5)

        text = tk.Text(win, font=("Consolas", 10))
        text.pack(fill="both", expand=True, padx=10, pady=10)

        if not txns:
            text.insert("end", "No transactions found.")
            speak("No recent transactions.")
        else:
            text.insert("end", "Date/Time           | Type         | Amount   | Balance\n")
            text.insert("end", "-" * 65 + "\n")
            for t in txns:
                time, ttype, amt, bal = t
                text.insert(
                    "end",
                    f"{time} | {ttype:<10} | ₹{amt:<7.2f} | ₹{bal:<7.2f}\n",
                )
            speak("Showing your last five transactions.")
        text.config(state="disabled")

    def change_pin_window(self):
        cur = simpledialog.askstring("Change PIN", "Enter current PIN:", show="*")
        if not cur:
            return
        if not get_account(self.current_account, cur):
            messagebox.showerror("Error", "Incorrect current PIN.")
            speak("Incorrect current PIN.")
            return
        new1 = simpledialog.askstring("Change PIN", "Enter new 4-digit PIN:", show="*")
        new2 = simpledialog.askstring("Change PIN", "Confirm new PIN:", show="*")
        if not (new1 and new2):
            return
        if new1 != new2 or not (new1.isdigit() and len(new1) == 4):
            messagebox.showerror("Error", "PINs do not match or invalid.")
            speak("PINs do not match or invalid.")
            return
        update_pin(self.current_account, new1)
        messagebox.showinfo("Success", "PIN changed successfully.")
        speak("PIN changed successfully.")

    def download_statement(self):
        txns = get_all_transactions(self.current_account)
        if not txns:
            messagebox.showinfo("Statement", "No transactions to download.")
            speak("No transactions to download.")
            return

        default_name = f"statement_{self.current_account}.txt"
        path = filedialog.asksaveasfilename(
            title="Save Statement",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"ATM Statement for {self.current_name}\n")
                f.write(f"Account: {self.current_account}\n")
                f.write(f"Generated: {datetime.now()}\n")
                f.write("-" * 60 + "\n")
                f.write("Date/Time | Type | Amount | Balance\n")
                for t in txns:
                    time, typ, amt, bal = t
                    f.write(f"{time} | {typ} | ₹{amt} | ₹{bal}\n")
            messagebox.showinfo("Saved", f"Statement saved to:\n{path}")
            speak("Statement downloaded successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")
            speak("Error saving statement file.")

    def logout(self):
        speak("Logging out.")
        self.current_account = None
        self.current_name = None
        self.show_login_screen()

    # ---------- Admin Panel ----------

    def show_admin_panel(self):
        self.clear_window()
        frame = tk.Frame(self, bg=self.bg_color)
        frame.pack(expand=True, fill="both")

        self.create_header(frame, "Admin Panel")

        total = get_total_bank_balance()
        tk.Label(
            frame,
            text=f"Total Bank Balance: ₹{total:.2f}",
            font=("Arial", 13, "bold"),
            bg=self.bg_color,
            fg="#4ade80",
        ).pack(pady=6)
        speak(f"Total bank balance is {total:.2f} rupees.")

        tree = ttk.Treeview(
            frame, columns=("acc", "name", "bal"), show="headings", height=10
        )
        tree.pack(fill="both", expand=True, padx=15, pady=10)

        tree.heading("acc", text="Account No")
        tree.heading("name", text="Name")
        tree.heading("bal", text="Balance")

        tree.column("acc", width=120)
        tree.column("name", width=200)
        tree.column("bal", width=120)

        for acc_no, name, bal in get_all_accounts():
            tree.insert("", "end", values=(acc_no, name, f"₹{bal:.2f}"))

        def open_history():
            sel = tree.focus()
            if not sel:
                messagebox.showwarning("Select", "Please select an account.")
                speak("Please select an account first.")
                return
            acc_no, name, _ = tree.item(sel, "values")
            txns = get_all_transactions(acc_no)
            win = tk.Toplevel(self)
            win.title(f"History - {acc_no}")
            win.geometry("650x350")
            win.configure(bg=self.bg_color)

            tk.Label(
                win,
                text=f"Transaction History - {name} ({acc_no})",
                font=("Arial", 13, "bold"),
                bg=self.bg_color,
                fg=self.accent_color,
            ).pack(pady=5)

            text = tk.Text(win, font=("Consolas", 10))
            text.pack(fill="both", expand=True, padx=10, pady=10)

            if not txns:
                text.insert("end", "No transactions.")
            else:
                text.insert("end", "Date/Time | Type | Amount | Balance After\n")
                text.insert("end", "-" * 60 + "\n")
                for t in txns:
                    time, typ, amt, bal = t
                    text.insert(
                        "end", f"{time} | {typ} | ₹{amt:.2f} | ₹{bal:.2f}\n"
                    )
            text.config(state="disabled")
            speak(f"Showing transaction history for account {acc_no}.")

        self.voice_button(
            frame,
            "View Selected User History",
            open_history,
            bg=self.button_color,
            fg=self.bg_color,
        ).pack(pady=5)

        self.voice_button(
            frame,
            "Back to Login",
            self.show_login_screen,
            bg="#f97316",
            fg="black",
        ).pack(pady=8)


if __name__ == "__main__":
    app = ATMApp()
    app.mainloop()