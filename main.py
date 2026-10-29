
import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).with_name("sharesphere.db")

st.set_page_config(
    page_title="ShareSphere",
    page_icon="🔗",
    layout="wide",
)


# ---------------- DATABASE FUNCTIONS ----------------

def connect_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    with connect_db() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                location TEXT NOT NULL,
                available_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                owner TEXT NOT NULL,
                training_required INTEGER DEFAULT 0,
                rules TEXT NOT NULL,
                active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                purpose TEXT NOT NULL,
                booking_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                trained INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Pending',
                checked_in TEXT,
                returned_at TEXT,
                before_condition TEXT,
                after_condition TEXT,
                incident TEXT DEFAULT '',
                FOREIGN KEY(resource_id) REFERENCES resources(id)
            );

            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
        """)

        count = con.execute(
            "SELECT COUNT(*) FROM resources"
        ).fetchone()[0]

        if count == 0:
            samples = [
                (
                    "Computer Lab - 20 Seats", "Lab",
                    "Block A, Room 204", date.today().isoformat(),
                    "15:00", "17:00", "Lab Manager", 0,
                    "Keep the lab clean; no unauthorised software."
                ),
                (
                    "DSLR Camera", "Camera",
                    "Media Centre", date.today().isoformat(),
                    "10:00", "16:00", "Media Coordinator", 0,
                    "Handle carefully and return with accessories."
                ),
                (
                    "3D Printer", "Specialised Equipment",
                    "Innovation Lab", date.today().isoformat(),
                    "11:00", "13:00", "Lab Manager", 1,
                    "Verified training and staff supervision required."
                ),
            ]

            con.executemany("""
                INSERT INTO resources
                (name, category, location, available_date,
                 start_time, end_time, owner, training_required, rules)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, samples)


def log_action(booking_id, actor, action):
    with connect_db() as con:
        con.execute("""
            INSERT INTO activity_log
            (booking_id, actor, action, timestamp)
            VALUES (?, ?, ?, ?)
        """, (
            booking_id,
            actor,
            action,
            datetime.now().isoformat(timespec="seconds")
        ))


def get_data(query, params=()):
    with connect_db() as con:
        return pd.read_sql_query(query, con, params=params)


def execute(query, params=()):
    with connect_db() as con:
        con.execute(query, params)


def has_overlap(resource_id, booking_date, start_time, end_time):
    """Check overlap against approved or checked-in bookings."""
    existing = get_data("""
        SELECT start_time, end_time
        FROM bookings
        WHERE resource_id = ?
          AND booking_date = ?
          AND status IN ('Approved', 'Checked In')
    """, (resource_id, booking_date))

    return any(
        start_time < row["end_time"]
        and end_time > row["start_time"]
        for _, row in existing.iterrows()
    )


def promote_waitlisted(resource_id, booking_date, actor):
    """
    Move the oldest compatible waitlisted request to Pending.
    The resource owner must still approve it.
    """
    waiting = get_data("""
        SELECT *
        FROM bookings
        WHERE resource_id = ?
          AND booking_date = ?
          AND status = 'Waitlisted'
        ORDER BY id ASC
    """, (resource_id, booking_date))

    for _, candidate in waiting.iterrows():
        conflict = has_overlap(
            resource_id,
            booking_date,
            candidate["start_time"],
            candidate["end_time"]
        )

        if not conflict:
            execute("""
                UPDATE bookings
                SET status = 'Pending'
                WHERE id = ? AND status = 'Waitlisted'
            """, (int(candidate["id"]),))

            log_action(
                int(candidate["id"]),
                actor,
                "Promoted from waiting list to Pending for owner review"
            )
            return int(candidate["id"])

    return None


# ---------------- INITIALISE APP ----------------

init_db()

st.title("🔗 ShareSphere")
st.caption("Share Resources. Build Opportunities.")

st.write(
    "Discover underused institutional resources and access them "
    "through accountable, fair and transparent bookings."
)

# Demo role selector. This is not real authentication.
role = st.sidebar.selectbox(
    "Choose demo role",
    ["Student", "Resource Owner", "Administrator"]
)

if role == "Student":
    person = st.sidebar.text_input("Your name", "Aarav")
else:
    person = st.sidebar.text_input("Your name", "Lab Manager")

if not person.strip():
    st.warning("Please enter a name in the sidebar.")
    st.stop()

resources = get_data("""
    SELECT * FROM resources
    WHERE active = 1
""")

pending_count = get_data("""
    SELECT COUNT(*) AS n
    FROM bookings
    WHERE status = 'Pending'
""").iloc[0]["n"]

active_count = get_data("""
    SELECT COUNT(*) AS n
    FROM bookings
    WHERE status IN ('Approved', 'Checked In')
""").iloc[0]["n"]

waitlist_count = get_data("""
    SELECT COUNT(*) AS n
    FROM bookings
    WHERE status = 'Waitlisted'
""").iloc[0]["n"]

c1, c2, c3 = st.columns(3)
c1.metric("Listed Resources", len(resources))
c2.metric("Pending Requests", int(pending_count))
c3.metric("Active Bookings", int(active_count))

st.caption(f"Waiting-list requests: {int(waitlist_count)}")

pages = [
    "Discover Resources",
    "Request a Booking",
    "Manage Bookings",
    "Check-in & Return",
    "Report an Incident",
    "Activity History",
    "My Bookings & Cancellation",
    "Add a Resource",
]

page = st.sidebar.radio("Navigation", pages)


# ---------------- DISCOVER RESOURCES ----------------

if page == "Discover Resources":
    st.header("Discover Resources")

    search = st.text_input("Search by name, category or location")

    categories = ["All"] + sorted(
        resources["category"].unique().tolist()
    )

    category = st.selectbox("Category", categories)
    filtered = resources.copy()

    if search:
        mask = filtered[
            ["name", "category", "location"]
        ].apply(
            lambda col: col.str.contains(
                search, case=False, na=False
            )
        ).any(axis=1)

        filtered = filtered[mask]

    if category != "All":
        filtered = filtered[
            filtered["category"] == category
        ]

    if filtered.empty:
        st.info("No matching resources found.")
    else:
        for _, r in filtered.iterrows():
            with st.container(border=True):
                st.subheader(r["name"])
                st.write(f"**Category:** {r['category']}")
                st.write(f"**Location:** {r['location']}")
                st.write(
                    f"**Available:** {r['available_date']} | "
                    f"{r['start_time']}–{r['end_time']}"
                )
                st.write(f"**Owner:** {r['owner']}")
                st.write(f"**Rules:** {r['rules']}")

                if r["training_required"]:
                    st.warning("Training verification required.")
                else:
                    st.success(
                        "No special training requirement listed."
                    )


# ---------------- REQUEST A BOOKING ----------------

elif page == "Request a Booking":
    st.header("Request a Resource")

    if resources.empty:
        st.info("No resources are listed yet.")
    else:
        options = {
            f"{r['name']} — {r['location']} (ID {r['id']})":
            int(r["id"])
            for _, r in resources.iterrows()
        }

        with st.form("booking_form"):
            selected = st.selectbox(
                "Choose resource", list(options)
            )

            purpose = st.text_area("Purpose of use")

            booking_date = st.date_input(
                "Booking date",
                min_value=date.today()
            )

            start = st.time_input("Start time")
            end = st.time_input("End time")

            trained = st.checkbox(
                "I have completed the required training, if applicable"
            )

            join_waitlist = st.checkbox(
                "If my requested time conflicts, join the fair waiting list",
                value=True
            )

            submitted = st.form_submit_button("Submit Request")

        if submitted:
            resource_id = options[selected]

            r = resources[
                resources["id"] == resource_id
            ].iloc[0]

            start_text = start.strftime("%H:%M")
            end_text = end.strftime("%H:%M")
            date_text = booking_date.isoformat()

            if not purpose.strip():
                st.error("Please describe the purpose of your booking.")

            elif start >= end:
                st.error("End time must be after start time.")

            elif date_text != r["available_date"]:
                st.error(
                    "This demo resource is listed for "
                    f"{r['available_date']}. Choose a matching date."
                )

            elif (
                start_text < r["start_time"]
                or end_text > r["end_time"]
            ):
                st.error(
                    f"Choose a time between {r['start_time']} "
                    f"and {r['end_time']}."
                )

            elif r["training_required"] and not trained:
                st.error(
                    "Training is required before you can request this resource."
                )

            else:
                usage = get_data("""
                    SELECT COUNT(*) AS n
                    FROM bookings
                    WHERE user_name = ?
                      AND status IN (
                          'Pending',
                          'Approved',
                          'Checked In',
                          'Waitlisted'
                      )
                """, (person,)).iloc[0]["n"]

                conflict = has_overlap(
                    resource_id,
                    date_text,
                    start_text,
                    end_text
                )

                if usage >= 2:
                    st.warning(
                        "Fair-use limit reached: you may have at most "
                        "two pending, waitlisted, or active bookings."
                    )

                elif conflict and not join_waitlist:
                    st.error(
                        "That time overlaps with an existing booking. "
                        "Select the waiting-list option to queue fairly."
                    )

                else:
                    initial_status = (
                        "Waitlisted" if conflict else "Pending"
                    )

                    with connect_db() as con:
                        cur = con.execute("""
                            INSERT INTO bookings
                            (
                                resource_id, user_name, purpose,
                                booking_date, start_time, end_time,
                                trained, status
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            resource_id,
                            person,
                            purpose.strip(),
                            date_text,
                            start_text,
                            end_text,
                            int(trained),
                            initial_status
                        ))

                        booking_id = cur.lastrowid

                    if conflict:
                        log_action(
                            booking_id,
                            person,
                            "Added to waiting list"
                        )

                        st.info(
                            f"Request #{booking_id} added to the waiting list. "
                            "When a slot is freed, the oldest compatible "
                            "request can move to Pending for owner review."
                        )
                    else:
                        log_action(
                            booking_id,
                            person,
                            "Booking requested"
                        )

                        st.success(
                            f"Request #{booking_id} submitted! "
                            "The owner must review it."
                        )


# ---------------- MANAGE BOOKINGS ----------------

elif page == "Manage Bookings":
    st.header("Booking Approval Desk")

    if role == "Student":
        st.info("Switch to Resource Owner to review requests.")

    else:
        query = """
            SELECT b.*, r.name AS resource_name, r.owner
            FROM bookings b
            JOIN resources r ON r.id = b.resource_id
        """

        params = ()

        if role == "Resource Owner":
            query += " WHERE r.owner = ?"
            params = (person,)

        query += " ORDER BY b.id DESC"

        bookings = get_data(query, params)

        if bookings.empty:
            st.info("No booking requests yet.")

        else:
            for _, b in bookings.iterrows():
                with st.container(border=True):
                    st.subheader(
                        f"Request #{b['id']} — {b['resource_name']}"
                    )

                    st.write(f"**User:** {b['user_name']}")
                    st.write(f"**Purpose:** {b['purpose']}")
                    st.write(
                        f"**Slot:** {b['booking_date']}, "
                        f"{b['start_time']}–{b['end_time']}"
                    )
                    st.write(f"**Status:** {b['status']}")

                    if b["status"] == "Pending":
                        a, d = st.columns(2)

                        if a.button(
                            "Approve",
                            key=f"approve_{b['id']}"
                        ):
                            conflict = has_overlap(
                                int(b["resource_id"]),
                                b["booking_date"],
                                b["start_time"],
                                b["end_time"]
                            )

                            if conflict:
                                st.error(
                                    "Slot was taken by another booking."
                                )
                            else:
                                execute("""
                                    UPDATE bookings
                                    SET status = 'Approved'
                                    WHERE id = ?
                                      AND status = 'Pending'
                                """, (int(b["id"]),))

                                log_action(
                                    int(b["id"]),
                                    person,
                                    "Booking approved"
                                )
                                st.rerun()

                        if d.button(
                            "Reject",
                            key=f"reject_{b['id']}"
                        ):
                            execute("""
                                UPDATE bookings
                                SET status = 'Rejected'
                                WHERE id = ?
                                  AND status = 'Pending'
                            """, (int(b["id"]),))

                            log_action(
                                int(b["id"]),
                                person,
                                "Booking rejected"
                            )
                            st.rerun()


# ---------------- CHECK-IN AND RETURN ----------------

elif page == "Check-in & Return":
    st.header("Check-in & Check-out")

    my_bookings = get_data("""
        SELECT b.*, r.name AS resource_name
        FROM bookings b
        JOIN resources r ON r.id = b.resource_id
        WHERE b.user_name = ?
        ORDER BY b.id DESC
    """, (person,))

    if my_bookings.empty:
        st.info("No bookings found for this name.")

    else:
        for _, b in my_bookings.iterrows():
            with st.container(border=True):
                st.subheader(
                    f"#{b['id']} — {b['resource_name']}"
                )
                st.write(f"Status: **{b['status']}**")

                if b["status"] == "Approved":
                    condition = st.selectbox(
                        "Initial condition",
                        ["Good", "Minor wear", "Needs attention"],
                        key=f"before_{b['id']}"
                    )

                    if st.button(
                        "Check in",
                        key=f"in_{b['id']}"
                    ):
                        execute("""
                            UPDATE bookings
                            SET status = 'Checked In',
                                checked_in = ?,
                                before_condition = ?
                            WHERE id = ?
                              AND status = 'Approved'
                        """, (
                            datetime.now().isoformat(timespec="seconds"),
                            condition,
                            int(b["id"])
                        ))

                        log_action(
                            int(b["id"]), person, "Checked in"
                        )
                        st.rerun()

                elif b["status"] == "Checked In":
                    final_condition = st.selectbox(
                        "Return condition",
                        ["Good", "Minor wear", "Damaged"],
                        key=f"after_{b['id']}"
                    )

                    if st.button(
                        "Confirm return",
                        key=f"out_{b['id']}"
                    ):
                        execute("""
                            UPDATE bookings
                            SET status = 'Returned',
                                returned_at = ?,
                                after_condition = ?
                            WHERE id = ?
                              AND status = 'Checked In'
                        """, (
                            datetime.now().isoformat(timespec="seconds"),
                            final_condition,
                            int(b["id"])
                        ))

                        log_action(
                            int(b["id"]),
                            person,
                            "Resource returned"
                        )

                        if final_condition == "Damaged":
                            log_action(
                                int(b["id"]),
                                person,
                                "Return flagged for damage review"
                            )

                        st.rerun()


# ---------------- REPORT AN INCIDENT ----------------

elif page == "Report an Incident":
    st.header("Incident & Damage Report")

    my_bookings = get_data("""
        SELECT b.id, r.name
        FROM bookings b
        JOIN resources r ON r.id = b.resource_id
        WHERE b.user_name = ?
          AND b.status IN ('Approved', 'Checked In', 'Returned')
    """, (person,))

    if my_bookings.empty:
        st.info("No eligible bookings found.")

    else:
        options = {
            f"#{r['id']} — {r['name']}": int(r["id"])
            for _, r in my_bookings.iterrows()
        }

        with st.form("incident_form"):
            chosen = st.selectbox("Booking", list(options))
            description = st.text_area("Describe the issue")
            submitted = st.form_submit_button("Submit Report")

        if submitted:
            if not description.strip():
                st.error("Please describe the incident.")

            else:
                execute("""
                    UPDATE bookings
                    SET incident = ?
                    WHERE id = ?
                """, (description.strip(), options[chosen]))

                log_action(
                    options[chosen],
                    person,
                    "Incident report submitted"
                )

                st.success("Incident recorded for review.")


# ---------------- ACTIVITY HISTORY ----------------

elif page == "Activity History":
    st.header("Auditable Activity History")

    history = get_data("""
        SELECT id, booking_id, actor, action, timestamp
        FROM activity_log
        ORDER BY id DESC
    """)

    if history.empty:
        st.info("Activity will appear here as actions are performed.")

    else:
        st.dataframe(
            history,
            use_container_width=True,
            hide_index=True
        )


# ---------------- MY BOOKINGS AND CANCELLATION ----------------

elif page == "My Bookings & Cancellation":
    st.header("My Bookings & Cancellation")

    st.caption(
        "Cancel a pending, approved or waitlisted booking. "
        "Checked-in bookings must be returned first."
    )

    my_bookings = get_data("""
        SELECT b.*, r.name AS resource_name, r.location
        FROM bookings b
        JOIN resources r ON r.id = b.resource_id
        WHERE b.user_name = ?
        ORDER BY b.id DESC
    """, (person,))

    if my_bookings.empty:
        st.info("No bookings found for this name.")

    else:
        for _, b in my_bookings.iterrows():
            with st.container(border=True):
                st.subheader(
                    f"Request #{b['id']} — {b['resource_name']}"
                )

                st.write(
                    f"**Date/time:** {b['booking_date']} | "
                    f"{b['start_time']}–{b['end_time']}"
                )

                st.write(f"**Status:** {b['status']}")

                if b["status"] in (
                    "Pending", "Approved", "Waitlisted"
                ):
                    if st.button(
                        "Cancel booking",
                        key=f"cancel_{int(b['id'])}"
                    ):
                        previous_status = b["status"]

                        execute("""
                            UPDATE bookings
                            SET status = 'Cancelled'
                            WHERE id = ?
                              AND status IN (
                                  'Pending', 'Approved', 'Waitlisted'
                              )
                        """, (int(b["id"]),))

                        log_action(
                            int(b["id"]),
                            person,
                            f"Booking cancelled (previous status: "
                            f"{previous_status})"
                        )

                        promoted_id = None

                        # A released approved slot may free up a waiting request.
                        if previous_status == "Approved":
                            promoted_id = promote_waitlisted(
                                int(b["resource_id"]),
                                b["booking_date"],
                                person
                            )

                        if promoted_id is not None:
                            st.success(
                                f"Booking cancelled. Waiting-list request "
                                f"#{promoted_id} has moved to Pending for "
                                "owner approval."
                            )
                        else:
                            st.success(
                                "Booking cancelled and activity logged."
                            )

                        st.rerun()


# ---------------- ADD A RESOURCE ----------------

elif page == "Add a Resource":
    st.header("List a Resource")

    if role == "Student":
        st.info("Switch to Resource Owner to list a resource.")

    else:
        with st.form("resource_form"):
            name = st.text_input("Resource name")

            category = st.selectbox(
                "Category",
                [
                    "Lab", "Computer", "Camera", "Classroom",
                    "Projector", "Specialised Equipment", "Other"
                ]
            )

            location = st.text_input("Location")

            available_date = st.date_input(
                "Available date",
                min_value=date.today()
            )

            start_time = st.time_input("Available from")
            end_time = st.time_input("Available until")

            owner = st.text_input("Owner / manager", person)
            training_required = st.checkbox("Training required")
            rules = st.text_area("Usage rules")

            submitted = st.form_submit_button("Publish Resource")

        if submitted:
            if not all([
                name.strip(),
                location.strip(),
                owner.strip(),
                rules.strip()
            ]):
                st.error("Please complete all required fields.")

            elif start_time >= end_time:
                st.error("End time must be after start time.")

            else:
                with connect_db() as con:
                    con.execute("""
                        INSERT INTO resources
                        (
                            name, category, location, available_date,
                            start_time, end_time, owner,
                            training_required, rules
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        name.strip(),
                        category,
                        location.strip(),
                        available_date.isoformat(),
                        start_time.strftime("%H:%M"),
                        end_time.strftime("%H:%M"),
                        owner.strip(),
                        int(training_required),
                        rules.strip()
                    ))

                st.success("Resource published successfully!")
                st.rerun()


# ---------------- FOOTER ----------------

st.divider()

st.caption(
    "ShareSphere Hackathon Prototype | Demo data only | "
    "Institutional access requires authorised human approval."
)
