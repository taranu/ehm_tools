import logging
from collections import defaultdict
from dataclasses import dataclass
from decimal import *
import pandas as pd
from typing import Dict

import players as plyr
import teams

encoding_default = 'UTF-8'
getcontext().prec = 10


@dataclass
class Contract:
    salary: int
    years: int
    team: teams.Team = None


draft_slots_2020 = [0, 3000000, 2750000, 2500000, 2250000, 2000000, 1900000, 1800000, 1700000, 1600000, 1500000,
                    1450000, 1400000, 1350000, 1300000, 1250000]
salary_round = 50000
salary_unsigned = 100000
salary_min_league = 600000
salary_max_league = 9000000
years_max_league = 7


def get_elc(player: plyr.Player, year_draft_max=None, check_contract=True, default_undrafted=False):
    if not player.draft_overall > 0:
        if default_undrafted:
            return Contract(salary=salary_min_league, years=1)
        raise ValueError(f"Can't get ELC for undrafted player: {player} with draft_overall={player.draft_overall}")
    elif check_contract and not (player.years == 0 or (player.years == 1 and player.salary == salary_unsigned)):
        raise ValueError(f"Player: {player} contract: {player.salary} x {player.years}Y not consistent with drafted,"
                         f" unsigned prospect")
    if year_draft_max is not None and (
        player.is_booster
        and player.is_just_drafted(year_draft_max + 1)
    ):
        raise ValueError(f"Player: {player} is_booster and is_just_drafted from draft year={player.draft_year} "
                         f"> year_draft_max={year_draft_max}")
    if player.draft_year >= 2020:
        if player.draft_overall <= 14:
            salary = draft_slots_2020[player.draft_overall]
        elif player.draft_overall >= 61:
            salary = 600000
        elif player.draft_overall >= 56:
            salary = 650000
        elif player.draft_overall >= 51:
            salary = 700000
        elif player.draft_overall >= 47:
            salary = 750000
        elif player.draft_overall >= 43:
            salary = 800000
        elif player.draft_overall >= 39:
            salary = 850000
        elif player.draft_overall >= 35:
            salary = 900000
        elif player.draft_overall >= 31:
            salary = 950000
        elif player.draft_overall >= 27:
            salary = 1000000
        elif player.draft_overall >= 24:
            salary = 1050000
        elif player.draft_overall >= 21:
            salary = 1100000
        elif player.draft_overall >= 19:
            salary = 1150000
        elif player.draft_overall >= 17:
            salary = 1200000
        elif player.draft_overall >= 15:
            salary = 1250000
        else:
            raise RuntimeError(f'Unhandled player={player} 2020+ draft slot for {player.draft_overall} OV'
                               f' ({player.draft_year})')
    else:
        if player.draft_overall >= 106:
            salary = 600000
        elif player.draft_overall >= 91:
            salary = 640000
        elif player.draft_overall >= 76:
            salary = 680000
        elif player.draft_overall >= 61:
            salary = 720000
        elif player.draft_overall >= 51:
            salary = 800000
        elif player.draft_overall >= 41:
            salary = 1000000
        elif player.draft_overall >= 31:
            salary = 1200000
        elif player.draft_overall >= 21:
            salary = 1400000
        elif player.draft_overall >= 11:
            salary = 1600000
        elif player.draft_overall >= 1:
            salary = 2000000
        else:
            raise RuntimeError(f'Unhandled player={player} 2019- draft slot for {player.draft_overall} OV'
                               f' ({player.draft_year})')
    return Contract(salary=salary, years=3)


def get_max_years(salary: int):
    if not salary > salary_min_league:
        raise ValueError(f"No valid contract length for salary={salary} !> salary_min_league={salary_min_league}")
    if salary < 800000:
        return 1
    elif salary < 1200000:
        return 2
    elif salary < 3000000:
        return 3
    elif salary < 5000000:
        return 5
    else:
        return 7


def get_salary_min(years: int):
    if not years > 0:
        raise ValueError(f"No valid salary for contract years={years}")
    if years <= 1:
        return 600000
    elif years <= 2:
        return 800000
    elif years <= 3:
        return 1200000
    elif years <= 5:
        return 3000000
    else:
        return 5000000


def enter_contracts(players: plyr.Players, contracts: Dict[str, Contract], salaries_min: Dict[str, int],
                    year_draft_max: int = None):
    errors = []
    warnings = []
    results = []
    resignings = {}
    if salaries_min is None:
        logging.warning("salaries_min not provided; will default to league minimum")
        salaries_min = {}
    for name_full, contract in contracts.items():
        try:
            pid = players.find_player_by_fullname(name_full)
            player = players.get_player(pid)
            if contract is not None:
                salary, years = player.salary, player.years
                player.salary, player.years = salary_unsigned, 0
            is_free = contract is not None and contract.team is not None
            elc = get_elc(player, year_draft_max=year_draft_max, default_undrafted=True) if not is_free else None
            if contract is None:
                contract = elc
                player.team = player.rights
                msg = "signing ELC"
            else:
                player.salary, player.years = salary, years
                if is_free:
                    if not (years == 0):
                        raise ValueError(f"Player {player.name_last}, {player.name_first} can't be signed as"
                                         f" free agent with years={player.years} > 0")
                    player.team = contract.team
                else:
                    if not player.years == 1:
                        raise ValueError(f"Player {player.name_last}, {player.name_first} invalid extension"
                                         f" years={player.years}")
                player.salary, player.years = salary, years
                salary_min = min(
                    max(int(salaries_min.get(name_full, salary_min_league)), get_salary_min(contract.years)),
                    salary_max_league,
                ) if not is_free else salary_min_league
                if (not is_free) and (player.salary == elc.salary) and (contract.years >= 5):
                    warnings.append(f"Player {name_full} salary={player.salary} == elc.salary={elc.salary}"
                                    f" and contract.years={contract.years}>=5; applying 20% post-ELC bonus")
                    salary_min = min(round_salary((1 + 0.1*(contract.years - 4))*salary_min), salary_max_league)
                if salary_min is None:
                    raise KeyError(f"Player {name_full} has no defined minimum salary")
                errmsgs = []
                if not (contract.salary >= salary_min):
                    errmsgs.append(f"Player {name_full} salary={contract.salary} !>= salary_min={salary_min}"
                                   f" for {contract.years}y")
                elif (contract.team is None) and (contract.salary > salary_min):
                    warnings.append(f"Player {name_full} salary={contract.salary} > salary_min={salary_min}"
                                    f" for {contract.years}y")
                if errmsgs:
                    raise ValueError(f"Player {name_full} {' and '.join(errmsgs)}")
                msg = f"{'re-' if contract.team is None else ''}signing"
                # Contract extensions only happen in offseason before rollover
                # Need to add an extra year since all contracts will lose one in July
                contract.years += not is_free
            player.salary = int(contract.salary)
            player.years = contract.years
            if is_free:
                player.rights = contract.team.value
                player.team = contract.team.value
                player.acquired = "signed as a free agent"
            results.append(f"Player {name_full} ({player.rights.name}) {msg}:"
                           f" {contract.years}y {player.salary:d}")
            resignings[name_full] = player
        except NameError:
            errors.append(f"Couldn't find player: {name_full} ({plyr.get_names(name_full)})")
        except Exception as error:
            errors.append(f"Player {name_full} got error: {error}")

    return errors, warnings, results, resignings


def parse_length(string: str) -> int:
    string = string.lower()
    if string[-1] != 'y':
        raise RuntimeError(f"Can't parse string={string} as contract length")
    return int(string[:-1])


# not parsley_celery
def parse_salary(salary: str) -> int:
    salary_orig = salary
    salary = salary.lower()
    last = salary[-1]
    is_letter = last.isalpha()
    salary = Decimal(salary[:-1] if is_letter else salary)
    if is_letter:
        if last == 'm':
            salary *= 1000000
        elif last == 'k':
            salary *= 1000
        else:
            raise RuntimeError(f"Unrecognized suffix char={last} in salary={salary_orig}")
    return salary


def read_contracts(filename: str, entry_level: bool = False, encoding=encoding_default,
                   salaries_min: Dict[str, int] = None, extend=False):
    contracts = {}
    with open(filename, 'r', encoding=encoding) as file:
        has_min = salaries_min is not None
        for line in file:
            if entry_level:
                contracts[line.strip()] = None
            else:
                data = line.strip()
                team = None
                if data:
                    data = data.rsplit(' ', 1)
                    try:
                        if not extend:
                            team = teams.Team(int(data[1]))
                            data = data[0].rsplit(' ', 1)
                        years = parse_length(data[1])
                        try:
                            data = data[0].rsplit(' ', 1)
                            salary = parse_salary(data[1])
                            check_min = False
                        except RuntimeError:
                            salary = get_salary_min(years)
                            check_min = has_min
                    except RuntimeError:
                        salary = parse_salary(data[1])
                        data = data[0].rsplit(' ', 1)
                        years = parse_length(data[1])
                        check_min = False

                    name_full = data[0]
                    if check_min:
                        salary_min = salaries_min[name_full]
                        salary = min(max(salary_min, salary), salary_max_league)
                    contracts[name_full] = Contract(salary=salary, years=years, team=team)
    return contracts


def read_salaries_min(filename: str, encoding=encoding_default):
    tab = pd.read_csv(filename, encoding=encoding)
    salaries = [1000000*Decimal(x) for x in tab['UFA']*tab['UFA?'] + tab['RFA']*~tab['UFA?']]
    names = tab['NAME']
    return {name: salary for name, salary in zip(names, salaries)}


def round_salary(salary: float, round_num: int = None) -> int:
    if round_num is None:
        round_num = salary_round
    return round_num * int(round(salary/round_num))


def sign_qualifiers(players: plyr.Players, filename: str, encoding=encoding_default):
    found = set()
    to_sign = defaultdict(list)
    with open(filename, encoding=encoding) as f:
        for line in f:
            team, name = line.strip().split(' - ')
            if name in found:
                raise RuntimeError(f'Duplicate qualified RFA fonud: {name}')
            pid = players.find_player_by_fullname(name)
            player = players.get_player(pid)
            if player.years != 0 or player.rights != Team.UFA:
                raise RuntimeError(f'Player {player} is not listed UFA and cannot sign qualifying offer')
            to_sign[team].append((pid, player))
    for name_team, players_team in to_sign.items():
        team = Team[name_team]
        for (pid, player) in players_team:
            player.rights = team
            player.team = team
            player.years = 1
            player.salary = round_salary(1.2*player.salary)
            print(f"Signing {player} ({team.name}) qualifying offer at player.salary={player.salary}")


def slide_contracts(players: plyr.Players, filename: str, filename_ineligible: str = None, year_draft_max=None,
                    encoding="UTF-8"):
    with open(filename, encoding=encoding) as f:
        sliders = set(f.read().splitlines())
    if filename_ineligible:
        with open(filename_ineligible, encoding=encoding) as f:
            sliders_no = set(f.read().splitlines())
    else:
        sliders_no = {}
    errors = []
    warnings = []
    results = []
    resignings = {}
    for name_full in (name for name in sliders if name and (name not in sliders_no)):
        try:
            pid = players.find_player_by_fullname(name_full)
            player = players.get_player(pid)
            errmsgs = []
            if not 2 <= player.years <= 3:
                errmsgs.append(f"Player {name_full} can't slide contract unless 2 <= players.years={players.years} <= 3"
                               f"(either unsigned or not first two years of ELC)")
            elc = get_elc(player, year_draft_max=year_draft_max, check_contract=False)
            if elc.salary != player.salary:
                errmsgs.append(f"Player {name_full} slide contract salary={player.salary} != elc.salary={elc.salary}"
                               f"; player appears not to be on ELC")
            if errmsgs:
                raise ValueError(f"Player {name_full} {' and '.join(errmsgs)}")
            player.years += 1
            results.append(f"Player {name_full} ({player.rights.name}) contract sliding to:"
                           f" {player.years}y {player.salary}")
            resignings[name_full] = player
        except NameError:
            errors.append(f"Couldn't find player: {name_full} ({plyr.get_names(name_full)})")
        except Exception as error:
            errors.append(f"Player {name_full} got error: {error}")

    return errors, warnings, results, resignings


def summarize(players: Dict[str, plyr.Player]):
    players_teams = defaultdict(list)
    for player in players.values():
        players_teams[player.rights.name].append(player)
    for team in teams.Team:
        players_team = players_teams.get(team.name, [])
        salaries_total, salaries_next = 0, 0
        for player in players_team:
            salaries_next += player.salary
            salaries_total += (player.years - 1) * player.salary
        msg = (
            f"{team.name} signing {len(players_team)} players to contracts totalling {salaries_total/1000000:.3f}M"
            f" ({salaries_next/1000000:.3f}M next season)"
        )
        print(msg)
