-- NextStop Database Schema
-- Project: GPS-Based Smart Bus Occupancy Prediction and Seat Availability System
-- Module 1: User Authentication System

-- Create Database if not exists
CREATE DATABASE IF NOT EXISTS nextstop_db;
USE nextstop_db;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL, -- Will store hashed password using pbkdf2:sha256/scrypt
    role ENUM('admin', 'conductor') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Occupancy Table
CREATE TABLE IF NOT EXISTS occupancy (
    bus_number VARCHAR(50) PRIMARY KEY,
    current_occupancy INT DEFAULT 0,
    seat_capacity INT NOT NULL DEFAULT 40,
    seats_available INT NOT NULL DEFAULT 40,
    standing_capacity INT NOT NULL DEFAULT 20,
    standing_available INT NOT NULL DEFAULT 20,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tickets Table
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id INT AUTO_INCREMENT PRIMARY KEY,
    bus_number VARCHAR(50) NOT NULL,
    source_stop VARCHAR(100) NOT NULL,
    destination_stop VARCHAR(100) NOT NULL,
    passenger_count INT NOT NULL,
    fare DECIMAL(10, 2) NOT NULL,
    ticket_date DATE NOT NULL,
    ticket_time TIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bus_number) REFERENCES occupancy(bus_number) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
