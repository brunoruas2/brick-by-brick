# Contributing to Development

## Setting Up
After cloning the repository, here are some guidelines to set up your environment.

1. Have a text editor of your choice.
2. A terminal of your choosing.
3. Install Python version 3.11:
   - You can download it from the [official website](https://www.python.org/downloads/)
   - Or via [pyenv](https://github.com/pyenv/pyenv).
4. Use [Poetry](https://python-poetry.org/) to manage packages and your virtual environment, avoiding conflicts with other projects on your machine.
5. Install [Git](https://git-scm.com/) for version control.

### Virtual Environment with `venv`
To install Python 3.11 in your virtual environment, it is **recommended**
to use [pyenv](https://github.com/pyenv/pyenv).

If you encounter difficulties during installation, pyenv provides two simplified assistants for configuration. For Windows, use [pyenv-windows](https://pyenv-win.github.io/pyenv-win/). For GNU/Linux and MacOS, use [pyenv-installer](https://github.com/pyenv/pyenv-installer).

Navigate to the directory where you will do the exercises and run example codes in your terminal. Then, type the following commands in your terminal:

```bash
$ pyenv update
$ pyenv install 3.11.8
```
###### Ensure Version 3.11 is Installed

```bash
$ pyenv versions
* system (set by /home/azevedo/.pyenv/version)
  3.11.8
```
The expected response is to have Python 3.11 in this list.

### Dependency Management with Poetry
After installing Python, the next step is to install [Poetry](https://python-poetry.org/), a package and dependency manager for Python. Poetry simplifies the creation, management, and distribution of Python packages.

I recommend a video if you want to learn more about the tool: [Python Live](https://www.youtube.com/watch?v=ZOSWdktsKf0&t=1s).

To install Poetry, you should follow these instructions

Para instalar o Poetry você deve seguir a seguinte instrução.
```bash
pip install poetry
```

### Installing Dependencies
Now we'll initialize our virtual environment with Poetry and install the necessary dependencies.

```bash
$ poetry install
```

To activate our virtual environment so that Python can see our installed dependencies, Poetry has a specific command for this:

```bash 
$ poetry shell
```
This way, the environment synchronizes the Python version through the .python-version file and uses the library versions according to the versioning of the pyproject.toml file.

### Development Tools

#### Ruff
[Ruff](https://docs.astral.sh/ruff/) is a static code analyzer. Its function is to check if we are programming according to Python's best practices.

#### Isort
[Isort](https://pycqa.github.io/isort/) is a tool for organizing imports. In PEP-8, there is a rule regarding [import precedence](https://peps.python.org/pep-0008/#imports). Isort's function is to group imports and also sort them alphabetically to help locate and identify imports.

#### Pytest
[Pytest](https://docs.pytest.org/en/8.0.x/) is a testing framework that we will use to write and execute our tests.

#### Black
[Black](https://black.readthedocs.io/en/stable/) is a code formatter. The idea behind using a formatter is simply to standardize the entire code writing process. For example, how do we define strings, using single quotes ' or double quotes "? When the line exceeds 79 characters, how do we break the line? If we break the line, do we use a comma on the last value or not? The focus is to standardize the code.

#### Taskipy
[Taskipy](https://github.com/taskipy/taskipy) is a task runner helper in our application. Instead of remembering commands, we can replace them with something simpler like `task test`, which will execute our test routine.

This task is responsible for running our tests present in the `test` directory

##### Main Available Commands
```bash
$ task lint
```
This task is responsible for showing us if our formatting is consistent with PEP-8, indicating what should be done differently if it is not in the proper format.

---

```bash
$ task format
```
This task is responsible for automatically formatting in case you don't want to understand what went wrong with your code and why it doesn't comply with one of the best practice rules.

---

```bash
$ task test
```
It also in the docstrings it shows a table that gives us very valuable data such as the number of lines in our code (Stmts), we have a column of Miss that represents how many lines were not executed and finally the column Coverage that represents the ratio between the other two columns.

We can better observe our coverage through the file htmlcov/index.html.
by opening this file in the browser of your choice, such as:

```bash
firefox htmlcov/index.html
```
### Test Structure

To write tests, I prefer the [AAA](https://xp123.com/articles/3a-arrange-act-assert/) approach, which divides the test into three stages: Arrange, Act, Assert.

#### Phase 1 - Arrange
In this stage, we prepare the environment for the test by declaring variables that will be used in our function for testing.

#### Phase 2 - Act
This is where the main action occurs, where our function to be tested will be used with the variables we predefined earlier, and we will save the response.

#### Phase 3 - Assert
In this final stage, it is responsible for verifying if everything happened as expected, where our variable that came out of the function returns the expected value.

