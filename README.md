![image](https://github.com/brunoruas2/brick-by-brick/assets/16859514/2225d5cf-f6e0-4de2-9f66-a19990275061)

# Brick by Brick
Python module for obtain data about Brazilian Reits (FIIS)

## Disclaimer
This is an ongoing project. To see the current development state check de [milestones page](https://github.com/brunoruas2/brick-by-brick/milestones?direction=asc&sort=title&state=open).

## Overview
Brick By Brick is a Python module designed to build a solid foundation for real estate investment decisions by efficiently collecting publicly available data on Fundos de Investimento Imobiliário (FIIs) in Brazil (The Brazilian version of Reits). The module offers a seamless way to aggregate crucial information, empowering developers, analysts, and enthusiasts with comprehensive data for analysis and decision-making.

## Features
- **Data Aggregation:** Collects various data points, including fund details, historical performance, and relevant financial metrics.
- **User-Friendly:** Provides an easy-to-use interface for fetching data and allows users to specify criteria for data retrieval.
- **SQLite Integration:** Creates an SQLite database at the specified path to store collected data, ensuring easy accessibility and data integrity.
- **Customization:** Allows users to customize data collection based on specific funds, time periods, or data types.
- **Data Integrity:** Ensures accuracy by pulling information from reputable sources and implementing data validation.

## Getting Started
To get started with Brick By Brick, follow these steps:

### Requirements
- Python 3.11+
- brick-by-brick uses in or core:
    - [Numpy](https://github.com/numpy/numpy)
    - [Pandas](https://github.com/pandas-dev/pandas)
    - [SQLite](https://github.com/sqlite/sqlite)
### Installation

```bash
$ pip install brick_by_brick
```

###### or

```bash
$ pip install git+https://github.com/brunoruas2/brick-by-brick
```

### Examples
```py
import brick_by_brick as bbb
```

## Contribute to the project
If you want helps us in the project, look the directory [contributing](contributing/en.md) or [contribuindo (pt-br)](https://github.com/brunoruas2/brick-by-brick/blob/main/contributing/pt-br.md)

### License
This project is licensed under the therms of the MIT license
