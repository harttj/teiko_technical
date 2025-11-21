# Teiko Technical Interview Project

This repository contains the code, data, and documentation for the **Teiko Technical Interview** assignment. Here is the related dashboard ([Link](https://teiko-technical.onrender.com/)).

---

## Table of Contents

1. [Overview](#overview)  
2. [Getting Started / Installation](#getting-started--installation)  
3. [Database Schema](#database-schema)  
4. [Running the Code](#running-the-code)  
5. [Project Structure](#project-structure)  
6. [Scaling & Design Rationale](#scaling--design-rationale)  
7. [Testing](#testing)  
8. [License](#license)  

---

## Overview

This project contains a dashboard that relies on an internally created sql database. It includes:

- A schema definition & setup script  
- Python script to compute analytics (e.g., relative frequency tables)  
- A simple dashboard (via `dashboard.py`) for visualizing results  
- Utilities to maintain and load data  

---

## Getting Started / Installation

### Prerequisites

- Python ≥ 11.4
- SQLite (or another relational database if you adapt the code)  
- `uv` for dependencies  

### Installation steps
0. Install UV
```curl -LsSf https://astral.sh/uv/install.sh | sh```


1. Sync dependencies:

    ```bash
    uv sync
    ```

2. Initialize the database:

    ```bash
    python database.py
    ```

   This will create the relational schema (e.g., tables) in a local SQLite database.

---

## Database Schema

Here is a summary of the relational design (contained in `database.py`).

**Tables:**

`metadata` Table
| Column                   | Type                | Description            |
| ------------------------ | ------------------- | ---------------------- |
| id                       | INTEGER PRIMARY KEY | Unique row identifier  |
| project                  | TEXT NOT NULL       | Project name           |
| subject                  | TEXT NOT NULL       | Subject identifier     |
| condition                | TEXT                | Experimental condition |
| age                      | INTEGER             | Age of subject         |
| sex                      | TEXT                | Sex of subject         |
| treatment                | TEXT                | Treatment group        |
| response                 | TEXT                | Biological response    |
| UNIQUE(project, subject) |                     | Ensures no duplicates  |

`samples` Table
| Column                    | Type                 | Description                |
| ------------------------- | -------------------- | -------------------------- |
| id                        | INTEGER PRIMARY KEY  | Unique row identifier      |
| sample_code               | TEXT NOT NULL UNIQUE | Sample identifier          |
| metadata_id               | INTEGER NOT NULL     | Foreign key to metadata.id |
| sample_type               | TEXT                 | Sample type                |
| time_from_treatment_start | INTEGER              | Timepoint                  |
| b_cell                    | INTEGER              | B cell count               |
| cd8_t_cell                | INTEGER              | CD8 T cell count           |
| cd4_t_cell                | INTEGER              | CD4 T cell count           |
| nk_cell                   | INTEGER              | NK cell count              |
| monocyte                  | INTEGER              | Monocyte count             |



**Rationale & Scaling:**
It separates subject-level metadata from sample-level measurements

1. Clean separation of subjects and samples
    - Subjects belong to projects.
    - Samples belong to subjects.
    - This creates a clear 1-to-many relationship.

- **Scalability:** The current method should scale nicely. If you scale to *hundreds of projects* and *millions of samples*, I would have a "metadata" table for each project potentially.

---

## Code Structure

First, we have the `data/` folder containing the original data and the sql database. Then to keep things simple we have a `utils/` folder that consists of utils for setuping the database and the dashboard. Then we have the main app. I also included `tests/` that contain unit tests for the database and main data loader, because these where the most important pieces. Note: *With more time I would add more unit tests for the rest of the important utils*

```
teiko_technical/
│
├── tests/
│   ├── test_database.py     # Unit tests the creation of the database
│   └── test_load_data.py    # Unit tests for the main data loading function
│
├── utils/
│   ├── database.py          # Database connection + schema creation
│   ├── load_data.py         # Main helper functions for retrieving data
│   ├── path_constants.py    # Contains pathway constants
│   ├── plotting.py          # Main Plotting Object for box plots in the dashboard
│   └── stats.py             # Main helper functions for calculating stats in the box plots
│
├── db/
│   └── cell_counts.sqlite       
│
├── data/
│   ├── cell_counts.db         
│   └── cell-count.csv         # Data that leads to the cell_counts sqllite database
│
├── dashboard.py             # Main Dash application with requested results
│
├── pyproject.toml           # Dependencies file #1
├── uv.lock                  # Dependencies file #2
└── README.md
```
---

## Running the Code

Here are the main pieces of functionality and how to run them:

1. **Database setup:**  
   Run `uv run python utils/database.py` — this script defines your schema, connects to your database, and runs any necessary migrations or table-creation logic.

2. **Compute analytics:**  
   Use scripts like `rel_freq_table.py` to compute relative frequency tables. For example:

   ```bash
   uv run python rel_freq_table.py
   ```
   **Note**: Most the analytics and results are computed directly in the dashboard.

## Dashboard ([Link](https://teiko-technical.onrender.com/))
The dashboard answers the questions for parts 2-4. 

**Note:** For the statistical analysis (part 3), I’ve worked with enough clinicians and data scientists to know that everyone uses slightly different thresholds for what counts as a “statistically significant” difference. Instead of labeling results as significant, I report the full statistics for each comparison so that end users (whether clinicians or bioinformaticians) can apply their own internal criteria.

## Last Note
I acknowledge that this repo is not a prefect and has areas for improvments