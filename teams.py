from dataclasses import dataclass
from enum import IntEnum
from typing import Dict

N_TEAMS = 30
sentinel = "---------------- End of NHL teams ----------------"


class Team(IntEnum):
    none = 0
    UFA = 98
    Undrafted = 99


@dataclass(frozen=True)
class TeamInfo:
    name: str
    acronym: str
    name_arena: str
    capacity_arena: int
    division: int
    id: int
    name_farm: str
    acronym_farm: str
    id_farm: int


teaminfos_all: Dict[int, TeamInfo] = {}


def read_teams(filename: str):
    global Team
    global teaminfos_all

    with open(filename, 'r') as file:
        teams = {}
        rows = ('name', 'acronym', 'name_arena', 'capacity_arena', 'division')
        for idx_team in range(1, N_TEAMS + 1):
            teaminfo = {name: file.readline().strip() for name in rows}
            teaminfo['capacity_arena'] = int(teaminfo['capacity_arena'])
            teaminfo['division'] = int(teaminfo['division'])
            teaminfo['id'] = idx_team
            teaminfo['id_farm'] = idx_team + N_TEAMS
            teams[idx_team] = teaminfo
        line = file.readline().strip()
        if line != sentinel:
            raise RuntimeError(f'Filename={filename} line={line} != sentinel={sentinel}')
        for name, team in teams.items():
            team['name_farm'] = file.readline().strip()
            team['acronym_farm'] = file.readline().strip()
            teams[name] = TeamInfo(**team)

    team_enum = {teaminfo.acronym: teaminfo.id for teaminfo in teams.values()}
    team_enum['none'] = 0
    team_enum['UFA'] = 98
    team_enum['Undrafted'] = 99

    Team = IntEnum('Team', team_enum)
    teaminfos_all = teams
