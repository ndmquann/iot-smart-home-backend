# Smart Home IoT Backend

A high-performance, asynchronous REST API and MQTT Bridge designed to control, monitor, and automate a smart home environment. Built with **FastAPI**, **PostgreSQL** (`asyncpg`), and **Adafruit IO**, featuring strict database normalization and real-time bidirectional hardware communication.

# System Architecture

- **Web Framework:** FastAPI (Python 3.11+)
- **Database:** PosgreSQL (Raw SQL via `asyncpg` connection pooling)
- **Authentication:** JWT & bcrypt password hashing
- **IoT Messaging:** Paho MQTT (connect to Adafruit IO)
- **Containerization:** Docker

# Database Design (ERD)

The database used raw SQL to enforce a strictly normalized, high-performance schema:

- **Class Table Inheritance:** `users` (parent) $\rightarrow$ `admins` / `members` (children). `devices` $\rightarrow$ `sensors` / `controllers`. `settings` $\rightarrow$ `schedules` / `thresholds`.
- **Ternary Mapping Tables:** History and configurations are logged without `NULL` columns using strictly defined ternary relationships: `interact`, `config`, and `contain`.
- **Safe Deletions:** "Ghost Data" prevention. Deleting a `zone` or `floor` is strictly blocked if physical `devices` are still attached to it, forcing admins to properly reassign or remove hardware first. Deletions are logged to a standalone Audit Log.

# Core Modules & Feature
## 1. Security & Authentication (`/api/v1/auth`)

- **JWT Login:** Secure endpoint returning encrypted access tokens containing user roles.

- **Centralized Error Handling:** Custom `exceptions` (`NotFoundException`, `UnauthorizedException`, `BadRequestException`) intercepted globally to guarantee consistent, frontend-friendly JSON error responses.

## 2. Physical Layout Management (`/api/v1/zones`)
- **Room & Floor Creation:** Organize the home by floors and specific rooms.

- **Safe Destruction:** Bulk delete entire floors, or specific rooms, with database-level checks preventing the deletion of rooms that still contain active smart devices.

## 3. Device & Hardware Control (`/api/v1/devices`)
- **Hardware Registry:** Registers devices and strictly categorizes them as `sensors` (read-only) or `controllers` (read/write).

- **Bidirectional Toggles:** Toggling a device updates the DB, logs the user action, and publishes an MQTT payload to Adafruit IO.

- **Granular Permissions:** Anyone can toggle a controller (like a fan), but ONLY verified Admins can manually toggle the power state of a sensor node.

- **Advanced Controls:** Controllers support `mode` (auto/manual) and `speed` integer settings.

## 4. Smart Settings (`/api/v1/settings`)
- **Thresholds:** Define numeric limits (e.g., Temp > 30°C) and apply them to specific sensors.

- **Schedules:** Define time-based triggers and apply them to specific controllers.

## 5. The Activity Dashboard (`/api/v1/logs`)
- **Unified History:** A single, complex SQL `LEFT JOIN` query that stitches together the ternary mapping tables to provide the frontend with a beautiful, human-readable history (e.g., *"User A turned on the Living Room Fan"* or *"Admin deleted Floor 2"*).

## 6. The IoT Bridge (MQTT Worker)
- **Background Listener:** Runs asynchronously alongside FastAPI, subscribed to Adafruit IO.

- **Smart Filtering:** Automatically ignores Adafruit metadata feeds (`/json`, `/csv`).

- **State Syncing:** Interprets incoming MQTT payloads, queries the DB to determine if the feed belongs to a sensor or controller, and updates the respective SQL tables in real-time.

# Quick Start & Useful Commands
Ensure Docker is already installed.

## 1. Start the Environment
Build the containers and start the background services (FastAPI, PostgreSQL).

```bash
docker compose up -d --build
```
## 2. Access the Interactive API Dashboard
Once running, open your browser to view the auto-generated Swagger UI. You can log in, create users, and test endpoints directly from here:
[http://localhost:8000/docs](http://localhost:8000/docs)

## 3. Watch the Live Logs
Crucial for debugging MQTT messages coming from Adafruit IO or seeing backend crashes.
```bash
# Watch the FastAPI application logs in real-time
docker compose logs -f api

# Watch the PostgreSQL database logs
docker compose logs -f db
```

## 4. Perform a Hard Database Reset
If you mess up your database schema or want to completely wipe the data and re-run your init.sql script to start fresh:

```bash
# 1. Stop containers and DESTROY the database volume
docker compose down -v

# 2. Rebuild and restart (this triggers init.sql)
docker compose up -d
```

## 5. Stop the Application
Gracefully shut down the server and MQTT background threads.

```bash
docker compose down
```
