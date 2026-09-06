-- NextStop Database Schema
-- Project: GPS-Based Smart Bus Occupancy Prediction and Seat Availability System

-- Create Database if not exists
CREATE DATABASE IF NOT EXISTS nextstop_db;
USE nextstop_db;

-- Buses Table
CREATE TABLE IF NOT EXISTS buses (
    bus_id INT AUTO_INCREMENT PRIMARY KEY,
    bus_number VARCHAR(50) UNIQUE NOT NULL,
    bus_type VARCHAR(100),
    route_name VARCHAR(100),
    seat_capacity INT NOT NULL DEFAULT 60,
    standing_capacity INT NOT NULL DEFAULT 20,
    status ENUM('active','inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL, -- Hashed password
    role ENUM('admin', 'conductor') NOT NULL,
    employee_id VARCHAR(50) NULL UNIQUE,
    phone_number VARCHAR(20) NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Occupancy Table (Updated with Seating = 60, Standing = 20)
CREATE TABLE IF NOT EXISTS occupancy (
    bus_number VARCHAR(50) PRIMARY KEY,
    current_occupancy INT DEFAULT 0,
    seat_capacity INT NOT NULL DEFAULT 60,
    seats_available INT NOT NULL DEFAULT 60,
    standing_capacity INT NOT NULL DEFAULT 20,
    standing_available INT NOT NULL DEFAULT 20,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tickets Table (Extended for Passenger Exit Management)
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id INT AUTO_INCREMENT PRIMARY KEY,
    bus_number VARCHAR(50) NOT NULL,
    source_stop VARCHAR(100) NOT NULL,
    destination_stop VARCHAR(100) NOT NULL,
    passenger_count INT NOT NULL,
    fare DECIMAL(10, 2) NOT NULL,
    ticket_date DATE NOT NULL,
    ticket_time TIME NOT NULL,
    assigned_seat VARCHAR(500) NULL,
    ticket_status ENUM('Active', 'Completed') NOT NULL DEFAULT 'Active',
    boarding_time TIME NULL,
    exit_time TIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bus_number) REFERENCES occupancy(bus_number) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Seat Status Table
CREATE TABLE IF NOT EXISTS seat_status (
    seat_id INT AUTO_INCREMENT PRIMARY KEY,
    bus_number VARCHAR(50) NOT NULL,
    seat_number INT NOT NULL,
    status ENUM('Available', 'Occupied', 'Reserved') DEFAULT 'Available',
    ticket_id INT NULL,
    boarding_stop VARCHAR(100) NULL,
    destination_stop VARCHAR(100) NULL,
    passenger_name VARCHAR(100) NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY bus_seat_unique (bus_number, seat_number),
    FOREIGN KEY (bus_number) REFERENCES occupancy(bus_number) ON DELETE CASCADE,
    FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Bus Location Table (Module 3 GPS Tracking)
CREATE TABLE IF NOT EXISTS bus_location (
    bus_number VARCHAR(50) PRIMARY KEY,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    current_stop VARCHAR(100) NOT NULL,
    is_demo BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (bus_number) REFERENCES occupancy(bus_number) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Predictions Table (Module 5 ML Predictions)
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id INT AUTO_INCREMENT PRIMARY KEY,
    bus_number VARCHAR(50) NOT NULL,
    prediction_time DATETIME NOT NULL,
    predicted_occupancy INT NOT NULL,
    predicted_available_seats INT NOT NULL,
    predicted_standing_available INT NOT NULL,
    crowd_level VARCHAR(50) NOT NULL,
    model_accuracy DECIMAL(5, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bus_number) REFERENCES occupancy(bus_number) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
