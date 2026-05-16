# school-result-management-system-SRMS-
School Result Management System (SRMS) is a Python-based desktop application designed to manage student records, courses, subject-wise marks, results, and student login access. It provides separate access for teachers and students, making result management easier, faster, and more organized.

## Features

- Teacher and student login system
- Add, update, delete, and search student records
- Manage courses and student enrollments
- Add subject-wise marks and full marks
- Calculate overall percentage automatically
- Pass/Fail determination with 35% minimum passing threshold
- View student results in a clear table format
- Export student marksheet as PDF
- Create and manage student login IDs
- Search student login details by name

## Technology Used

- Python
- Tkinter
- SQLite
- FPDF
- Pillow

## Purpose

The purpose of SRMS is to reduce manual paperwork and help schools manage student results digitally. Teachers can manage academic data from one dashboard, while students can log in separately to view their results and download their marksheet.

## Result Rule

A student is marked as **PASS** if the overall percentage is **35% or above**.  
A student is marked as **FAIL** if the overall percentage is below **35%**.
```
