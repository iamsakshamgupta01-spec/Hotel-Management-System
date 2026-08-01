"""
HOTEL MANAGEMENT SYSTEM
------------------------
A mini project demonstrating core hotel operations:
- Room management (add/view/search rooms)
- Customer management
- Room booking & check-in
- Check-out & automatic billing
- Reports (occupancy, revenue, booking history)

Storage: SQLite (file: hotel.db), created automatically on first run.
Run with:  python hotel_management.py
"""

import sqlite3
import datetime
import os

DB_NAME = "hotel.db"


# ---------------------------------------------------------------------------
# DATABASE SETUP
# ---------------------------------------------------------------------------
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            room_no INTEGER PRIMARY KEY,
            room_type TEXT NOT NULL,        -- Single / Double / Deluxe / Suite
            price_per_night REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Available'  -- Available / Occupied
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            room_no INTEGER NOT NULL,
            check_in_date TEXT NOT NULL,
            check_out_date TEXT,
            status TEXT NOT NULL DEFAULT 'Active',   -- Active / Completed
            total_bill REAL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY (room_no) REFERENCES rooms(room_no)
        )
    """)

    conn.commit()

    # Seed a few rooms if the table is empty (nice default for first run)
    cur.execute("SELECT COUNT(*) FROM rooms")
    if cur.fetchone()[0] == 0:
        sample_rooms = [
            (101, "Single", 1500.0, "Available"),
            (102, "Single", 1500.0, "Available"),
            (201, "Double", 2500.0, "Available"),
            (202, "Double", 2500.0, "Available"),
            (301, "Deluxe", 4000.0, "Available"),
            (401, "Suite", 7000.0, "Available"),
        ]
        cur.executemany(
            "INSERT INTO rooms (room_no, room_type, price_per_night, status) VALUES (?, ?, ?, ?)",
            sample_rooms,
        )
        conn.commit()

    conn.close()


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def today_str():
    return datetime.date.today().isoformat()


def parse_date(prompt_text):
    while True:
        raw = input(prompt_text + " (YYYY-MM-DD, blank = today): ").strip()
        if raw == "":
            return today_str()
        try:
            datetime.date.fromisoformat(raw)
            return raw
        except ValueError:
            print("  Invalid date format. Try again.")


def pause():
    input("\nPress Enter to continue...")


# ---------------------------------------------------------------------------
# ROOM MANAGEMENT
# ---------------------------------------------------------------------------
def add_room():
    print("\n--- Add New Room ---")
    try:
        room_no = int(input("Room number: ").strip())
        room_type = input("Room type (Single/Double/Deluxe/Suite): ").strip().title()
        price = float(input("Price per night: ").strip())
    except ValueError:
        print("Invalid input. Room number must be an integer, price must be a number.")
        return

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO rooms (room_no, room_type, price_per_night, status) VALUES (?, ?, ?, 'Available')",
            (room_no, room_type, price),
        )
        conn.commit()
        print(f"Room {room_no} added successfully.")
    except sqlite3.IntegrityError:
        print(f"Room {room_no} already exists.")
    finally:
        conn.close()


def view_rooms(filter_status=None):
    conn = get_connection()
    cur = conn.cursor()
    if filter_status:
        cur.execute("SELECT * FROM rooms WHERE status = ? ORDER BY room_no", (filter_status,))
    else:
        cur.execute("SELECT * FROM rooms ORDER BY room_no")
    rooms = cur.fetchall()
    conn.close()

    print("\n{:<10}{:<12}{:<18}{:<12}".format("Room No", "Type", "Price/Night", "Status"))
    print("-" * 52)
    for r in rooms:
        print("{:<10}{:<12}{:<18}{:<12}".format(r[0], r[1], r[2], r[3]))
    if not rooms:
        print("No rooms found.")


# ---------------------------------------------------------------------------
# CUSTOMER MANAGEMENT
# ---------------------------------------------------------------------------
def add_customer(name=None, phone=None, email=None):
    if name is None:
        print("\n--- Add New Customer ---")
        name = input("Customer name: ").strip()
        phone = input("Phone number: ").strip()
        email = input("Email (optional): ").strip()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO customers (name, phone, email) VALUES (?, ?, ?)",
        (name, phone, email),
    )
    conn.commit()
    customer_id = cur.lastrowid
    conn.close()
    print(f"Customer '{name}' registered with ID {customer_id}.")
    return customer_id


def view_customers():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers ORDER BY customer_id")
    customers = cur.fetchall()
    conn.close()

    print("\n{:<6}{:<20}{:<15}{:<25}".format("ID", "Name", "Phone", "Email"))
    print("-" * 66)
    for c in customers:
        print("{:<6}{:<20}{:<15}{:<25}".format(c[0], c[1], c[2], c[3] or "-"))
    if not customers:
        print("No customers found.")


# ---------------------------------------------------------------------------
# BOOKING / CHECK-IN
# ---------------------------------------------------------------------------
def book_room():
    print("\n--- Book a Room ---")
    view_rooms(filter_status="Available")

    try:
        room_no = int(input("\nEnter room number to book: ").strip())
    except ValueError:
        print("Invalid room number.")
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM rooms WHERE room_no = ?", (room_no,))
    row = cur.fetchone()
    if row is None:
        print("Room does not exist.")
        conn.close()
        return
    if row[0] != "Available":
        print("Room is not available.")
        conn.close()
        return

    print("\nIs this an existing customer?")
    choice = input("Enter existing customer ID, or leave blank to register new: ").strip()
    if choice:
        try:
            customer_id = int(choice)
        except ValueError:
            print("Invalid customer ID.")
            conn.close()
            return
        cur.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
        if cur.fetchone() is None:
            print("No such customer.")
            conn.close()
            return
    else:
        conn.close()
        customer_id = add_customer()
        conn = get_connection()
        cur = conn.cursor()

    check_in_date = parse_date("Check-in date")

    cur.execute(
        "INSERT INTO bookings (customer_id, room_no, check_in_date, status) VALUES (?, ?, ?, 'Active')",
        (customer_id, room_no, check_in_date),
    )
    cur.execute("UPDATE rooms SET status = 'Occupied' WHERE room_no = ?", (room_no,))
    conn.commit()
    booking_id = cur.lastrowid
    conn.close()

    print(f"\nBooking confirmed! Booking ID: {booking_id}, Room: {room_no}, Check-in: {check_in_date}")


# ---------------------------------------------------------------------------
# CHECK-OUT / BILLING
# ---------------------------------------------------------------------------
def view_active_bookings():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.booking_id, c.name, b.room_no, r.room_type, r.price_per_night, b.check_in_date
        FROM bookings b
        JOIN customers c ON b.customer_id = c.customer_id
        JOIN rooms r ON b.room_no = r.room_no
        WHERE b.status = 'Active'
        ORDER BY b.booking_id
    """)
    rows = cur.fetchall()
    conn.close()

    print("\n{:<6}{:<18}{:<8}{:<10}{:<14}{:<12}".format(
        "BkgID", "Customer", "Room", "Type", "Price/Night", "Check-in"))
    print("-" * 68)
    for r in rows:
        print("{:<6}{:<18}{:<8}{:<10}{:<14}{:<12}".format(r[0], r[1], r[2], r[3], r[4], r[5]))
    if not rows:
        print("No active bookings.")
    return rows


def checkout():
    print("\n--- Check-out & Billing ---")
    rows = view_active_bookings()
    if not rows:
        return

    try:
        booking_id = int(input("\nEnter booking ID to check out: ").strip())
    except ValueError:
        print("Invalid booking ID.")
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.room_no, b.check_in_date, r.price_per_night
        FROM bookings b JOIN rooms r ON b.room_no = r.room_no
        WHERE b.booking_id = ? AND b.status = 'Active'
    """, (booking_id,))
    row = cur.fetchone()
    if row is None:
        print("No active booking with that ID.")
        conn.close()
        return

    room_no, check_in_date, price_per_night = row
    check_out_date = today_str()

    nights = (datetime.date.fromisoformat(check_out_date) -
              datetime.date.fromisoformat(check_in_date)).days
    nights = max(nights, 1)  # minimum 1 night charge

    total_bill = nights * price_per_night

    cur.execute("""
        UPDATE bookings SET check_out_date = ?, status = 'Completed', total_bill = ?
        WHERE booking_id = ?
    """, (check_out_date, total_bill, booking_id))
    cur.execute("UPDATE rooms SET status = 'Available' WHERE room_no = ?", (room_no,))
    conn.commit()
    conn.close()

    print("\n----- INVOICE -----")
    print(f"Booking ID    : {booking_id}")
    print(f"Room No       : {room_no}")
    print(f"Check-in Date : {check_in_date}")
    print(f"Check-out Date: {check_out_date}")
    print(f"Nights Stayed : {nights}")
    print(f"Rate/Night    : {price_per_night}")
    print(f"TOTAL BILL    : {total_bill}")
    print("--------------------")


# ---------------------------------------------------------------------------
# REPORTS
# ---------------------------------------------------------------------------
def booking_history():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.booking_id, c.name, b.room_no, b.check_in_date,
               b.check_out_date, b.status, b.total_bill
        FROM bookings b JOIN customers c ON b.customer_id = c.customer_id
        ORDER BY b.booking_id
    """)
    rows = cur.fetchall()
    conn.close()

    print("\n{:<6}{:<15}{:<6}{:<12}{:<12}{:<10}{:<10}".format(
        "BkgID", "Customer", "Room", "Check-in", "Check-out", "Status", "Bill"))
    print("-" * 75)
    for r in rows:
        print("{:<6}{:<15}{:<6}{:<12}{:<12}{:<10}{:<10}".format(
            r[0], r[1], r[2], r[3], r[4] or "-", r[5], r[6] if r[6] else "-"))
    if not rows:
        print("No bookings yet.")


def revenue_report():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(total_bill), 0) FROM bookings WHERE status = 'Completed'")
    total_revenue = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM bookings WHERE status = 'Completed'")
    completed_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM rooms WHERE status = 'Occupied'")
    occupied = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM rooms")
    total_rooms = cur.fetchone()[0]
    conn.close()

    print("\n--- Revenue & Occupancy Report ---")
    print(f"Total completed stays : {completed_count}")
    print(f"Total revenue earned  : {total_revenue}")
    print(f"Rooms occupied now    : {occupied} / {total_rooms}")
    occ_rate = (occupied / total_rooms * 100) if total_rooms else 0
    print(f"Current occupancy rate: {occ_rate:.1f}%")


# ---------------------------------------------------------------------------
# MAIN MENU
# ---------------------------------------------------------------------------
def main_menu():
    menu = """
==========================================
        HOTEL MANAGEMENT SYSTEM
==========================================
 1. Add Room
 2. View All Rooms
 3. View Available Rooms
 4. Register Customer
 5. View Customers
 6. Book a Room (Check-in)
 7. View Active Bookings
 8. Check-out & Generate Bill
 9. Booking History
10. Revenue & Occupancy Report
 0. Exit
==========================================
"""
    while True:
        print(menu)
        choice = input("Enter your choice: ").strip()

        if choice == "1":
            add_room()
        elif choice == "2":
            view_rooms()
        elif choice == "3":
            view_rooms(filter_status="Available")
        elif choice == "4":
            add_customer()
        elif choice == "5":
            view_customers()
        elif choice == "6":
            book_room()
        elif choice == "7":
            view_active_bookings()
        elif choice == "8":
            checkout()
        elif choice == "9":
            booking_history()
        elif choice == "10":
            revenue_report()
        elif choice == "0":
            print("Thank you for using the Hotel Management System. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

        pause()


if __name__ == "__main__":
    init_db()
    main_menu()
