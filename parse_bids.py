import argparse
from datetime import datetime
import teams

managers = {
    'Duckduckdeke': 1,
    'The-Boss-GM': 3,
    'Sharp Stick Bisons': 4,
    None: 6,
    'Calgary Flames GM': 5,
    'Bernyhawks': 7,
    'AvalancheGM': 8,
    'Leon / Blue Jackets': 2,
    'Dallas Stars GM': 10,
    'DetroitGM': 11,
    None: 12,
    'PanthersGM': 13,
    'Kings GM': 14,
    'Wiild': 15,
    None: 16,
    'NashvillePredatorsGM': 19,
    'DevilsGM (Interim)': 20,
    'IslandersGM': 17,
    'NYRNYRNYR': 18,
    'SensGM': 21,
    'Gritty': 22,
    'ArizonaGM': 23,
    'PittsburghGM': 24,
    'SharksGM': 25,
    'St.Louis Blues GM': 26,
    'TBGM - Geoff': 27,
    'TorontoGM': 28,
    'VancouverCanucksGM': 29,
    'zach washington': 30,
    'Jets MKB GM': 9,
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process phpBB UFA bids")
    parser.add_argument('--bids', default='C:/Games/EHM/ufabids.txt', type=str)
    parser.add_argument('--config_teams', default='C:/Games/EHM/config_teams.ehm', type=str)
    parser.add_argument('--rfas', default='C:/Games/EHM/rfa.txt', type=str)
    parser.add_argument('--time_format', default='%a %b %d, %Y %I:%M %p', type=str)
    args = parser.parse_args()

    teams.read_teams(args.config_teams)
    rfas = []
    if args.rfas:
        with open(args.rfas) as file:
            for line in file:
                rfas.append(line.strip().split(' - ')[1])

    now = datetime.now()
    print(now.strftime(args.time_format))

    with open(args.bids, encoding='UTF-8') as bids:
        player, manager = None, None
        complete = True
        idx_offset = 0
        for idx, line in enumerate(bids):
            idx_mod = 1 + ((idx_offset + idx) % 10)
            if idx_mod == 1:
                player = line.strip()
            elif idx_mod == 2:
                timestamp = datetime.strptime(line.strip().split(' » ')[1], args.time_format)
                complete &= (now - timestamp).days >= 2
            elif idx_mod == 3 and line.strip() == "":
                idx_offset -= 1
            elif idx_mod == 8:
                manager = line.strip().split('by ')[1]
            elif idx_mod == 9:
                timestamp = datetime.strptime(line.strip(), args.time_format)
                complete &= (now - timestamp).days >= 1
            elif idx_mod == 10:
                if complete:
                    print(f'{player} 1y 600k {teams.Team(managers[manager])}')
                complete = True
