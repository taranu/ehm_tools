from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from dateutil.relativedelta import relativedelta
from enum import IntEnum
import numpy as np
import pandas as pd
from textwrap import wrap
from typing import Any, List, Tuple

import teams

names_columns = (
    ('sh', 'pl', 'st', 'ch', 'po', 'hi', 'sk', 'en', 'pe', 'fa'),
    ('le', 'str', 'pot', 'con', 'gre', 'fi', 'click', 'team', 'position', 'country', 'hand'),
    ('byear', 'bday', 'bmonth', 'salary', 'years', 'draft_year', 'draft_round', 'draft_team', 'rights'),
    ('thisweek_gp', 'thisweek_g', 'thisweek_a', 'thisweek_gwg'),
    ('thismonth_gp', 'thismonth_g', 'thismonth_a', 'thismonth_gwg'),
    ('records_g', 'records_a', 'records_p', 'notrade', 'twoway', 'option'),
    ('status', 'rookie', 'offer_status', 'offer_team', 'offer_time', 'injury_status'),
    ('scout_1', 'scout_2', 'scout_3', 'scout_4', 'scout_5', 'scout_6', 'scout_7', 'scout_8', 'scout_9', 'scout_10'),
    ('scout_11', 'scout_12', 'scout_13', 'scout_14', 'scout_15', 'scout_16', 'scout_17', 'scout_18', 'scout_19',
     'scout_20'),
    ('scout_21', 'scout_22', 'scout_23', 'scout_24', 'scout_25', 'scout_26', 'scout_27', 'scout_28', 'scout_29',
     'scout_30'),
    ('streak_g', 'streak_p', 'gp', 'suspension', 'training', 'weight', 'height', 'status_org'),
    ('streak_best_gp', 'streak_best_gwg', 'streak_best_p', 'streak_best_a', 'streak_best_g'),
    ('unused',),
    ('name_first', 'name_last'),
    ('performance',),
    ('acquired',),
    ('ceil_fi', 'ceil_sh', 'ceil_pl', 'ceil_st', 'ceil_ch', 'ceil_po', 'ceil_hi', 'ceil_sk', 'ceil_en', 'ceil_pe',
     'ceil_fa', 'ceil_le', 'ceil_str'),
    ('version_1',),
    ('version_2',),
    ('attitude', 'position_alt', 'rights_2', 'injury_prone', 'draft_overall'),
)


class Position(IntEnum):
    null = 0
    G = 1
    D = 2
    LW = 3
    C = 4
    RW = 5


class Handedness(IntEnum):
    R = 0
    L = 1


class Country(IntEnum):
    CAN = 0
    USA = 1
    RUS = 2
    CZE = 3
    SWE = 4
    FIN = 5
    BLR = 6
    SVK = 7
    NOR = 8
    GER = 9
    OTH = 10
    ITA = 11
    AUT = 12
    LAT = 13
    UKR = 14
    SLO = 15
    SUI = 16
    POL = 17
    FRA = 18
    JAP = 19


def get_names(name_full: str):
    return name_full.split(" ", 1)


@dataclass(frozen=True)
class PlayerRow:
    idx: int
    tab: pd.DataFrame

    def __repr__(self):
        return f"PlayerRow({self.idx}/{len(self.tab)})"

    def get(self, item: str):
        return self.tab.at[self.idx, item]

    def set(self, item: str, value: Any):
        self.tab.at[self.idx, item] = value


@dataclass
class Player:
    row: PlayerRow

    def age(self, date_as_of: datetime = None) -> float:
        return (pd.Timestamp(date_as_of if date_as_of is not None else datetime.now()) - self.birthdate).days / 365.25

    @property
    def birthdate(self) -> datetime:
        return datetime(year=self.byear, month=self.bmonth, day=self.bday)

    @property
    def country(self) -> Country:
        return Country(self.row.get('country'))

    @property
    def hand(self) -> Handedness:
        return Handedness(self.row.get('hand'))

    @property
    def is_booster(self) -> bool:
        return self.pot < 70 and self.con >= 75

    def is_junior(self, junior_date: datetime) -> bool:
        return self.birthdate > junior_date

    @property
    def position(self) -> Position:
        return Position(self.row.get('position'))

    @position.setter
    def position(self, position: Position):
        if position == self.position_alt:
            raise ValueError(f"Can't set position to same position={position} as self.position_alt")
        self.__setattr__('position', Position.value)

    @property
    def position_alt(self) -> Position:
        return Position(self.row.get('position_alt'))

    @position_alt.setter
    def position_alt(self, position: Position):
        if self.position == Position.G:
            raise ValueError(f"Can't set position_alt for a goalie")
        if position == self.position:
            raise ValueError(f"Can't set position_alt to same position={position} as self.position")
        self.__setattr__('position_alt', Position.value)

    @property
    def rights(self) -> teams.Team:
        return teams.Team(self.row.get('rights'))

    @rights.setter
    def rights(self, team: teams.Team):
        self.__setattr__('rights', team.value)

    @property
    def team(self) -> teams.Team:
        team = self.row.get('team')
        try:
            return teams.Team(team)
        except:
            # TODO: Fix this farm hack
            return teams.Team(team - teams.N_TEAMS)

    @team.setter
    def team(self, team: teams.Team):
        self.__setattr__('team', team.value)

    def __getattr__(self, item):
        try:
            return self.row.get(item)
        except KeyError:
            raise AttributeError(item)

    def __repr__(self):
        return f"Player({self.row})"

    def __setattr__(self, item, value):
        if item == 'row':
            super().__setattr__('row', value)
        else:
            try:
                self.row.set(item, value)
            except KeyError:
                raise AttributeError(item)

    def __str__(self):
        return f"Player {self.name_last}, {self.name_first} [team:{self.team.name}, rights:{self.rights.name}]," \
               f" {self.age():.2f}yrs, {self.salary}x{self.years}"

    def __init__(self, idx: int, tab: pd.DataFrame, **kwargs):
        self.row = PlayerRow(idx=idx, tab=tab)
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
            raise ValueError(f'Player {self} failed setting attrs with args: {invalid}')


class Players:
    table: pd.DataFrame = None

    @staticmethod
    def lines_per_player():
        return 20

    @staticmethod
    def lines_expected(n_players: int):
        return 1 + Players.lines_per_player()*n_players

    @staticmethod
    def columns_per_line():
        return tuple(len(x) for x in names_columns)

    @staticmethod
    def column_is_numeric(idx: int):
        return (idx <= 11) or (idx == 19)

    def find_player_by_fullname(self, name_full: str) -> int:
        return self.find_player_by_names(*get_names(name_full))

    def find_player_by_names(self, name_first: str, name_last: str) -> int:
        pids = np.where((name_first == self.table['name_first']) & (name_last == self.table['name_last']))[0]
        if len(pids) != 1:
            raise NameError(f'No player named {name_last}, {name_first}')
        return pids[0]

    def find_retirees(self, date: datetime = None, num: int = None, print_summary: bool = True,
                      age_any: int = None, age_expired: int = None, age_expiring: int = None):
        if date is None:
            date = datetime(year=datetime.today().year, month=9, day=16)
        if num is None:
            num = 175
        if age_any is None:
            age_any = 42
        if age_expired is None:
            age_expired = 37
        if age_expiring is None:
            age_expiring = 30
        ages = np.array([relativedelta(date, bday).years for bday in self.get_birthdates()])
        overalls = self.get_overall()
        years = self.table['years']
        retiring = np.zeros_like(years, dtype=bool)

        stages = (
            (age_any, np.Inf, 'age_any'),
            (age_expired, 0, 'age_expired'),
            (age_expiring, 1, 'age_expiring'),
        )
        stage_final = len(stages) - 1

        for idx, (age_min, years_max, name) in enumerate(stages):
            limit = idx == stage_final
            too_old = (ages >= age_min) & (years <= years_max) & ~retiring
            n_too_old = np.sum(too_old)
            if limit and (num > 0):
                if n_too_old < num:
                    raise RuntimeError(f'Only {n_too_old} players to retire in final stage; decrease {name}={age_min}')
                expiring = np.sort(np.where(too_old)[0][np.argpartition(overalls[too_old], num)[:num]])
                too_old[:] = False
                too_old[expiring] = True
                n_too_old = np.sum(too_old)
            retiring[too_old] = True
            num -= n_too_old

            desc = f'players over {age_min} and years <= {years_max}'
            if print_summary:
                if n_too_old > 0:
                    print(f'Retiring {n_too_old} {desc}')
                    for row, overall in zip(
                        self.table.loc[too_old][["name_first", "name_last"]].itertuples(),
                        overalls[too_old],
                    ):
                        print(f'{row.name_first} {row.name_last} OV={int(round(overall)):d}')
                else:
                    print(f'No retiring ')
            if not (limit or (num >= 0)):
                raise RuntimeError(f'Retiring too many {desc}; increase {name} or increase num by at least {-num}')

        return retiring

    def get_birthdates(self):
        bdates = pd.to_datetime(
            self.table[['byear', 'bmonth', 'bday']].rename(columns={f'b{x}': x for x in ('year', 'month', 'day')}),
            errors='coerce'
        )
        bad = np.where(~np.isfinite(bdates))[0]
        if len(bad) > 0:
            print(f'Warning; players {bad} have invalid birthdates: ')
            print(self.table[['name_first', 'name_last', 'byear', 'bmonth', 'bday']].iloc[bad])
        return bdates

    def get_overall(self, simple: bool = True):
        if simple:
            return self.table.loc[:, ['sh', 'pl', 'st', 'ch', 'po', 'hi']].aggregate('mean', axis=1)
        else:
            return self.table.loc[:, ['sh', 'pl', 'st', 'ch', 'po', 'hi', 'sk']].aggregate('mean', axis=1)

    def get_player(self, pid: int) -> Player:
        player = Player(pid, self.table)
        return player

    @property
    def n_players(self) -> int:
        return len(self.table)

    def release_rights(self, age: float = 25, date_as_of: datetime = None) -> List[Player]:
        if date_as_of is None:
            date_as_of = datetime.now()
        bdates = self.get_birthdates()
        tab = self.table
        ages = (pd.Timestamp(date_as_of) - bdates).days / 365.25
        releases = np.where((ages > age) & (tab.rights < teams.N_TEAMS))[0]
        tab.loc[releases, 'rights'] = teams.Team.UFA
        return [Player(tab.iloc[x]) for x in releases]

    def replace_vopatizers(
            self, age_min: float = 30, ov_max: float = 60, years_max: int = 1, date_as_of: datetime = None,
            potential_min: int = 50, print_each: bool = False
    ) -> List[Tuple[Player, Player]]:
        if date_as_of is None:
            date_as_of = datetime.now()
        bdates = self.get_birthdates()
        ages = np.array([x.days/365.25 for x in pd.Timestamp(date_as_of) - bdates])
        ov = self.get_overall()
        tab = self.table
        vopats = (ages > age_min) & (ov < ov_max) & (tab.team > teams.N_TEAMS) & (tab.years > 0) & (
                tab.years <= years_max)
        replacements = (ages < (age_min - 1)) & (ov < ov_max) & (tab.rights == teams.Team.UFA.value) & (
                tab.pot > potential_min)

        replaced = []
        for idx in np.where(vopats)[0]:
            vopat = Player(idx, tab)
            position = vopat.position
            replacer = np.where(replacements & ((tab.position == position) | (tab.position_alt == position)))[0]
            if len(replacer) > 0:
                replacements[replacer[0]] = False
                replacer = Player(replacer[0], tab)
            else:
                raise RuntimeError(f"Couldn't find vopatizer replacement for {Player(vopat)}")
            if print_each:
                print(f"Replacing vopatizer {vopat} with {replacer}")
            replacer.salary = vopat.salary
            replacer.years = vopat.years
            replacer.rights = vopat.rights
            replacer.team = vopat.team
            # TODO: Set farm teams properly instead
            replacer.row.tab.loc[replacer.row.idx, 'team'] += 30
            vopat.rights = teams.Team.UFA
            vopat.team = teams.Team.none
            vopat.years = 0
            replaced.append((vopat, replacer))
        return replaced

    def subtract(self, players: Players, columns=None):
        if columns is None:
            columns = ['sh', 'pl', 'st', 'ch', 'po', 'hi', 'sk', 'en', 'pe', 'fa',
                       'le', 'str', 'pot', 'con', 'gre', 'fi']
            self.table[columns] -= players.table[columns]

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
            file.write(f' {self.n_players} \n')
            tab = self.table
            for idx, row in enumerate(tab.itertuples()):
                for idx_col, cols in enumerate(names_columns):
                    try:
                        if Players.column_is_numeric(idx_col):
                            string = ''.join(f"{getattr(row, col): d} " for col in cols)
                        elif idx_col == 16:
                            string = ''.join(f"{getattr(row, col):03d}" for col in cols)
                        else:
                            string = ' '.join(getattr(row, col) for col in cols)
                        file.write(f'{string}\n')
                    except Exception as err:
                        print(f'{err} from player:')
                        print(Player(tab.iloc[idx]))

    def __init__(self, filename):
        with open(filename, 'r') as file:
            if filename[-3:] == 'ehm':
                lines = file.readlines()
                n_players = int(lines[0])
                n_lines = len(lines)
                lines_per_player = Players.lines_per_player()
                n_expected = Players.lines_expected(n_players)
                if n_lines != n_expected:
                    raise RuntimeError(f'Player file {filename} has n_lines={n_lines} != expected={n_expected} from'
                                       f' n_players={n_players}*rows_per_player={lines_per_player}')

                columns_per_line = Players.columns_per_line()
                n_columns = sum(columns_per_line)

                rows = [None]*n_players
                for idx_player in range(n_players):
                    line_start = 1 + idx_player*lines_per_player
                    row = [None]*(n_columns + 1)
                    row[-1] = idx_player
                    idx_begin = 0

                    for idx_row, n_columns_row in enumerate(columns_per_line):
                        line = lines[line_start + idx_row]
                        # Space-padded integer ratings
                        if Players.column_is_numeric(idx_row):
                            columns = [int(x) for x in line.split()]
                        # Name
                        elif idx_row == 13:
                            columns = get_names(line.strip())
                        # Ceilings
                        elif idx_row == 16:
                            columns = [int(x) for x in wrap(line.strip(), 3)]
                        # 12 - ??, 14 - performance, 15-acquired, 18-19 versions
                        else:
                            columns = [line.rstrip('\n')]
                        if len(columns) != n_columns_row:
                            raise RuntimeError(f"len(columns)={len(columns)} != n_columns_row={n_columns_row}"
                                               f" on line number {line_start + idx_row + 1}")
                        row[idx_begin:idx_begin + n_columns_row] = columns
                        idx_begin += n_columns_row
                    rows[idx_player] = row
                table = pd.DataFrame(rows)
                table.columns = [y for x in names_columns for y in x] + ['index']
                self.table = table
            elif filename[-3:] == 'csv':
                tab = pd.read_csv(filename, encoding='cp1252')
                # fixups
                tab.fillna('', inplace=True)
                self.table = tab
            else:
                raise ValueError(f'Unknown extension for filename={filename}')
