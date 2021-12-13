from dataclasses import dataclass
import datetime as dt
#from dateutil.relativedelta import relativedelta
from enum import IntEnum
import numpy as np
import pandas as pd

from teams import Team

N_GAMES_REG = 82

names_columns = (
    ("day", "month", "year", "team_home", "team_away", "status", "type",),
    ("goals_home", "goals_away",),
)


class GameStatus(IntEnum):
    unplayed = 0
    regulation = 1
    overtime = 2


class GameType(IntEnum):
    null = 0
    regpre = 1
    playoff = 4
    special = 5


@dataclass
class Game:
    row: pd.Series = None

    @property
    def team_away(self) -> Team:
        return Team(self.row.team_away)

    @property
    def team_home(self) -> Team:
        return Team(self.row.team_home)

    @property
    def date(self) -> dt.date:
        return dt.date(self.row.year, self.row.month, self.row.day)

    def __getattr__(self, item):
        try:
            return getattr(self.row, item)
        except KeyError:
            raise AttributeError(item)

    def __repr__(self):
        return f"Player({self.row})"

    def __setattr__(self, item, value):
        if item == 'row':
            super().__setattr__('row', value)
        else:
            try:
                setattr(self.row, item, value)
            except KeyError:
                raise AttributeError(item)

    def __str__(self):
        return (f"Game('{self.team_home}' vs '{self.team_away}: {self.goals_home}-{self.goals_away} ({self.date}"
                f", {self.type.name})")

    def __init__(self, row, **kwargs):
        self.row = row
        invalid = []
        for arg in kwargs:
            if not hasattr(self, arg):
                invalid.append(arg)
        if invalid:
            raise ValueError(f'Passed invalid init args: {",".join(invalid)}')
        invalid = []
        for arg, val in kwargs:
            try:
                setattr(self, arg, val)
            except AttributeError as e:
                invalid.append(arg, e)
        if invalid:
            raise ValueError(f'Game {self} failed setting attrs with args: {invalid}')


class Schedule:
    table: pd.DataFrame = None

    @staticmethod
    def lines_per_game():
        return 2

    @staticmethod
    def lines_expected(n_games: int):
        return 1 + Schedule.lines_per_game()*n_games

    @staticmethod
    def columns_per_line():
        return tuple(len(x) for x in names_columns)

    @property
    def dates(self):
        dates = pd.to_datetime(self.table[['year', 'month', 'day']])
        bad = np.where(~np.isfinite(dates))[0]
        if len(bad) > 0:
            print(f'Warning; games {bad} have invalid birthdates: ')
            print(self.table.iloc[bad])
        return dates

    @dates.setter
    def dates(self, dates):
        self.table['year'] = [date.year for date in dates]
        self.table['month'] = [date.month for date in dates]
        self.table['day'] = [date.day for date in dates]

    @property
    def n_games_max(self) -> int:
        return len(self.table)

    def set_game(self, pid: int, game: Game):
        self.table.iloc[pid] = game.row

    def write(self, filename):
        if filename[-3:] == 'csv':
            self.write_csv(filename, index=False, encoding='cp1252')
        elif filename[-3:] == 'ehm':
            self.write_ehm(filename)
        else:
            ValueError(f'Unknown extension for output filename={filename}')

    def write_csv(self, filename, **kwargs):
        self.table.to_csv(filename, **kwargs)

    def write_ehm(self, filename):
        with open(filename, 'w', encoding='cp1252') as file:
            tab = self.table
            for idx, row in enumerate(tab.itertuples()):
                for idx_col, cols in enumerate(names_columns):
                    try:
                        string = ''.join(f"{getattr(row, col): d} " for col in cols)
                        file.write(f'{string}\n')
                    except Exception as err:
                        print(f'{err} from game:')
                        print(Game(tab.iloc[idx]))

    def __init__(self, filename):
        with open(filename, 'r') as file:
            if filename[-3:] == 'ehm':
                lines = file.readlines()
                n_lines = len(lines)
                lines_per_player = Schedule.lines_per_game()
                n_dates = n_lines//lines_per_player
                columns_per_line = Schedule.columns_per_line()
                n_columns = sum(columns_per_line)

                rows = [None]*n_dates
                for idx_game in range(n_dates):
                    line_start = 1 + idx_game*lines_per_player
                    row = [None]*(n_columns + 1)
                    row[-1] = idx_game
                    idx_begin = 0

                    for idx_row, n_columns_row in enumerate(columns_per_line):
                        line = lines[line_start + idx_row]
                        columns = [int(x) for x in line.split()]
                        if len(columns) != n_columns_row:
                            raise RuntimeError(f"len(columns)={len(columns)} != n_columns_row={n_columns_row}"
                                               f" on line number {line_start + idx_row + 1}")
                        row[idx_begin:idx_begin + n_columns_row] = columns
                        idx_begin += n_columns_row
                    rows[idx_game] = row
                table = pd.DataFrame(rows)
                self.table = table
            elif filename[-3:] == 'csv':
                tab = pd.read_csv(filename, encoding='cp1252')
                # fixups
                tab.fillna('', inplace=True)
                self.table = tab
            else:
                raise ValueError(f'Unknown extension for filename={filename}')
