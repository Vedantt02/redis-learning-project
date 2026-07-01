# Redis Learning Project

This project is a simple Hospital Analytics System built while learning Redis with FastAPI. The primary goal was to understand how Redis improves API performance by caching frequently accessed data.

Rather than building a production-level application, I focused on learning the core Redis concepts and integrating them into an existing FastAPI CRUD project.

---

## Features

- Create a patient
- View all patients
- View a single patient
- Update patient details
- Delete a patient
- Sort patients by Height, Weight, or BMI
- Hospital Analytics endpoint
- Redis caching
- Logging

---

## Technologies Used

- Python
- FastAPI
- Redis
- Pydantic
- Uvicorn

---

## Redis Concepts Covered

During this project, I learned and implemented:

- Connecting FastAPI with Redis
- Cache-Aside Pattern
- Caching individual patient records
- Caching all patient records
- Caching analytics data
- Updating cache after Create, Update, and Delete operations
- Logging cache hits and cache misses
