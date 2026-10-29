# 🔗 ShareSphere – A Smart & Trusted Resource-Sharing Platform

### Share Resources. Build Opportunities.

**Hackathon Problem Statement:** Unlock Underused Equipment and Spaces

ShareSphere is a resource-sharing platform designed to help institutions make better use of underutilized spaces and equipment. It provides a centralized interface where users can discover resources, request bookings, and track their status, while resource owners can manage approvals and monitor usage.

## 🎯 Problem Statement

Educational institutions and organizations often have equipment, laboratories, rooms, and other facilities that remain underused. At the same time, students and other authorized users may need access to these resources but lack a simple and transparent way to discover availability and request permission.

ShareSphere aims to bridge this gap through a structured resource discovery and booking workflow.

## 💡 Proposed Solution

ShareSphere provides a centralized platform for discovering and managing shared institutional resources. It supports booking requests, owner approvals, waiting-list handling, cancellation, check-in and return tracking, incident reporting, and activity history.

The goal is to encourage efficient resource utilization while promoting fairness, transparency, and accountability.

## ✨ Key Features

- **Resource Discovery:** Browse available equipment and spaces, with search and category filtering.
- **Booking Requests:** Submit resource requests with a purpose and preferred time slot.
- **Booking Management:** Resource owners can approve or reject pending requests.
- **Fair Waiting List:** Conflicting booking requests can be placed on a waiting list.
- **Automatic Waiting-List Promotion:** When an approved booking is cancelled, a compatible waiting-list request can move to Pending for owner review.
- **Booking Cancellation:** Users can cancel eligible bookings through the cancellation interface.
- **Check-in and Return:** Track resource handover and return.
- **Incident Reporting:** Submit reports related to resource use.
- **Activity History:** View recorded actions, actors, and timestamps.
- **Add Resource:** Add new equipment or spaces to the resource listings.
- **Persistent Storage:** SQLite retains application records across local Streamlit restarts.

## 🔄 Product Workflow

1. **Discover:** Browse resources and review their details, availability, location, and usage rules.
2. **Request:** Select a resource, enter the purpose, and submit a booking request.
3. **Review:** The resource owner approves or rejects the request.
4. **Waitlist:** If a requested slot conflicts with an active booking, the user can request waiting-list placement.
5. **Cancel and Promote:** When an approved booking is cancelled, a compatible waiting-list request can be promoted to Pending.
6. **Check-in and Return:** Track the resource's usage and return.
7. **Report and Monitor:** Submit incidents and review the activity history.
8. **Expand Resources:** Add more resources to the platform.

## 🛠️ Technology Stack

- **Programming Language:** Python
- **Web Application Framework:** Streamlit
- **Database:** SQLite
- **Development Environment:** Visual Studio Code
- **Version Control:** Git and GitHub

## 🏗️ Implementation Overview

ShareSphere uses Python to implement its application logic, Streamlit to provide the interactive user interface, and SQLite to store resources, bookings, and activity records.

The application organizes the resource-sharing process into separate navigation sections for