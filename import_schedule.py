import argparse
from datetime import datetime, timedelta

import numpy as np

import teams
from teams import read_teams, N_TEAMS
import schedule as sched

format_date = ""
names_columns_import = ("day", "month", "year", "team_home_name", "team_away_name",)
now = datetime.now()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Import a hockeyreference season schedule in CSV format")
    parser.add_argument('--schedule_in', type=str,
                        help=f"Path to a csv file containing a season schedule."
                             f"Example: A hockeyreference CSV-exported schedule with dashes in dates replaced by commas"
                             f", and these column names: {names_columns_import}"
                        )
    parser.add_argument('--schedule_out', default='C:/Games/EHM/schedule.ehm', type=str, help='Output file path')
    parser.add_argument('--config_teams', default='C:/Games/EHM/config_teams.ehm', type=str,
                        help='League config_teams.ehm file path')
    parser.add_argument('--date_begin', default=None, type=str)
    parser.add_argument('--dates_unavail', default=f'{now.year}-12-24,{now.year}-12-24', type=str,
                        help='Comma-separated list of dates games should not be scheduled for (e.g. Dec. 25)')
    parser.add_argument('--format_date', default='%Y-%m-%d', type=str)
    parser.add_argument('--team_mapping', default=None, type=str)
    args = parser.parse_args()

    date_begin = datetime.strptime(args.date_begin, args.format_date) if args.date_begin is not None else None
    team_mapping = {}
    if args.team_mapping is not None:
        for mapping in args.team_mapping.split(','):
            team1, team2 = mapping.split(':')
            team_mapping[team1] = team2

    read_teams(args.config_teams)

    schedule = sched.Schedule(args.schedule_in)
    tab = schedule.table

    n_expected = (sched.N_GAMES_REG*N_TEAMS)//2
    n_games = len(tab)
    if n_games != n_expected:
        raise RuntimeError(f'Imported schedule_in={args.schedule_in} has n_games={n_games} != n_expected={n_expected}')

    missing = [column for column in names_columns_import if column not in tab.columns]
    if missing:
        raise RuntimeError(
            f'Imported schedule_in={args.schedule_in} missing required columns: {missing}')

    tab['goals_home'] = 0
    tab['goals_away'] = 0
    tab['status'] = np.full(n_games, sched.GameStatus.unplayed)
    tab['type'] = np.full(n_games, sched.GameType.regpre)

    team_ids = {teaminfo.name: id_team for id_team, teaminfo in teams.teaminfos_all.items()}
    for side in ('home', 'away'):
        name_in, name_out = f'team_{side}_name', f'team_{side}'
        tab[name_out] = [team_ids[team_mapping.get(name_team, name_team)] for name_team in tab[name_in]]

    dates = schedule.dates
    if date_begin is not None:
        diff = date_begin - dates[0]
        dates += diff

    for date in sorted((datetime.strptime(date, args.format_date) for date in args.dates_unavail.split(','))):
        dates[dates >= date] += timedelta(days=1)

    counts = {i: 0 for i in range(7)}
    for date in dates:
        counts[date.weekday()] += 1
    print(counts)

    schedule.dates = dates

    schedule.write(args.schedule_out)
