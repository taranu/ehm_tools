import argparse
import contracts as cntr
from datetime import datetime
import players as plyr
import teams

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process EHM files")
    parser.add_argument('--players', default='C:/Games/EHM/saves/EHEC/players.ehm')
    parser.add_argument('--compare_players', default=None, type=str)
    parser.add_argument('--config_teams', default='C:/Games/EHM/config_teams.ehm', type=str)
    parser.add_argument('--date_format', default='%Y/%m/%d', type=str)
    parser.add_argument('--difference', default=None, type=str)
    parser.add_argument('--draft_year_last', default=None, type=int)
    parser.add_argument('--elcs', default=None, type=str)
    parser.add_argument('--extensions', default=None, type=str)
    parser.add_argument('--junior_birthdate', default=None, type=str)
    parser.add_argument('--output', default=None, type=str)
    parser.add_argument('--qualified_rfas', default=None, type=str)
    parser.add_argument('--release_rights_date', default=None, type=str)
    parser.add_argument('--replace_vopatizers', action='store_true')
    parser.add_argument('--reset_invalid_salaries', action='store_true')
    parser.add_argument('--retire_players', action='store_true')
    parser.add_argument('--return_juniors', default=None, type=str)
    parser.add_argument('--salaries_min', default=None, type=str)
    parser.add_argument('--signings', default=None, type=str)
    parser.add_argument('--skip_reset_low_fighting', action='store_true')
    parser.add_argument('--slide_eligible', default=None, type=str)
    parser.add_argument('--slide_ineligible', default=None, type=str)
    parser.add_argument('--unretire', action='store_true')
    group = parser.add_mutually_exclusive_group()
    parser.add_argument('--invite_prospects', action='store_true')
    parser.add_argument('--return_prospects', action='store_true')

    args = parser.parse_args()
    teams.read_teams(args.config_teams)

    date_junior = (datetime.strptime(args.junior_birthdate, args.date_format) if args.junior_birthdate is not None
                   else None)

    players = plyr.Players(args.players)
    tab = players.table
    
    if args.retire_players:
        retirees = players.find_retirees(print_summary=True)
        tab.loc[retirees, ['status']] = 1

    if args.unretire:
        tab.loc[tab.loc[:, 'status'] == 1, ['status']] = 0

    salaries_min = cntr.read_salaries_min(args.salaries_min) if args.salaries_min is not None else None

    errors_all, warnings_all, results_all, resignings_all = [], [], [], {}
    for file_contract, entry_level, extend in (
            (args.elcs, True, False), (args.extensions, False, True), (args.signings, False, False),
    ):
        if file_contract is not None:
            contracts = cntr.read_contracts(
                file_contract,
                entry_level=entry_level,
                salaries_min=salaries_min if not entry_level else None,
                extend=extend,
            )
            errors, warnings, results, resignings = cntr.enter_contracts(
                players,
                contracts=contracts,
                salaries_min=salaries_min,
                year_draft_max=args.draft_year_last if entry_level else None,
            )
            for msgs_all, msgs_new in ((errors_all, errors), (warnings_all, warnings), (results_all, results)):
                msgs_all.extend(msgs_new)
            resignings_all.update(resignings)

    if args.slide_eligible:
        errors, warnings, results, resignings = cntr.slide_contracts(
            players, args.slide_eligible, args.slide_ineligible,
        )
        for msgs_all, msgs_new in ((errors_all, errors), (warnings_all, warnings), (results_all, results)):
            msgs_all.extend(msgs_new)

    if args.draft_year_last:
        for player in [players.get_player(pid) for pid in range(players.n_players)]:
            if player.is_booster and (player.years == 0) and not player.is_just_drafted(args.draft_year_last + 1) \
                    and (player.age(datetime.fromisoformat(f'{args.draft_year_last + 1}-09-16')) < 20):
                warnings_all.append(f'Pot booster {player} still unsigned')

    if warnings_all:
        print("Warnings:")
        for warning in warnings_all:
            print(warning)
    if errors_all:
        print("Errors: ")
        for error in errors_all:
            print(error)
    elif results_all:
        print("Results: ")
        for result in results_all:
            print(result)
        cntr.summarize(resignings_all)

    if args.compare_players is not None:
        players_comp = plyr.Players(args.compare_players)
        for pid in range(players.n_players):
            player = players.get_player(pid)
            player_comp = players_comp.get_player(pid)
            if player.pot > player_comp.pot:
                print(f'{player} ({player.rights.name}, {player.con} CON)'
                      f' boosted from {player_comp.pot} to {player.pot}')
            elif player.pot < player_comp.pot:
                print(f'{player} ({player.rights.name}, {player.con} CON)'
                      f' busted from {player_comp.pot} to {player.pot}')
            elif player_comp.draft_year == args.draft_year_last and player_comp.is_booster:
                print(f'{player} ({player.rights.name}, {player.con} CON) failed to boost')

    if args.invite_prospects or args.return_prospects:
        years_check = args.return_prospects
        years_set = 1 - years_check
        for idx, player in tab.iterrows():
            if player.years == years_check and player.salary == cntr.salary_unsigned:
                tab.loc[idx, 'years'] = years_set
                tab.loc[idx, 'team'] = args.invite_prospects*player.rights

    if args.qualified_rfas is not None:
        cntr.sign_qualifiers(players, args.qualified_rfas)

    if args.return_juniors is not None:
        with open(args.return_juniors, encoding='UTF-8') as f:
            index = tab.index
            for line in f:
                pid = players.find_player_by_fullname(line.strip())
                player = players.get_player(pid)
                if not player.is_junior(date_junior):
                    raise RuntimeError(f'{player} birthdate={player.birthdate} not > date_junior={date_junior}')
                tab.loc[index[pid], 'team'] = teams.Team.none

    if args.reset_invalid_salaries:
        tab.loc[(tab.salary < cntr.salary_min_league) & (tab.salary != cntr.salary_unsigned), 'salary'] = \
            cntr.salary_min_league
    
    if not args.skip_reset_low_fighting:
        tab.loc[tab.fi < 10, 'fi'] = 50

    if args.replace_vopatizers:
        _ = players.replace_vopatizers(print_each=True)

    if args.release_rights_date is not None:
        date_release = datetime.strptime(args.release_rights_date, args.date_format)
        for idx, player in tab.iterrows():
            if (player.team == teams.Team.none.value) and (player.rights <= teams.N_TEAMS) and (
                    player.rights != teams.Team.none.value) and (player.years == 0):
                player_obj = players.get_player(idx)
                if player_obj.birthdate < date_release:
                    print(f"Releasing rights to {player_obj}")
                    player_obj.rights = teams.Team.none

    if args.difference is not None:
        sub = plyr.Players(args.difference)
        players.subtract(sub)

    if args.output is not None:
        print(f"Writing modified file to: {args.output}")
        players.write(args.output)
