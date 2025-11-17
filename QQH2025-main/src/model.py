import numpy as np
import pandas as pd


class Model:
    def __init__(self):
        # {team_id: [Elo, Matches, Wins, Losses, Draws, AvgGoalsFor, AvgGoalsAgainst, AvgSOG, AvgPIM, AvgPPG, AvgSHG, AvgSV%, AvgFO%, Recent5Form]}
        self.teams_rankings = {}
        self.last_update_date = {}
        self.team_stats_history = {}  # Uchovává poslední N zápasů pro form

    def place_bets(self, summary: pd.DataFrame, opps: pd.DataFrame, inc: pd.DataFrame):
        self.define_rankings(inc)
        bankroll = summary.iloc[0]["Bankroll"]
        max_bet = summary.iloc[0]["Max_bet"]
        min_bet = summary.iloc[0]["Min_bet"]
        
        total_staked = 0.0
        N = len(opps)
        bets = np.zeros((N, 3))
        
        for i in range(N):
            home_id = int(opps.iloc[i]["HID"])
            away_id = int(opps.iloc[i]["AID"])

            if home_id not in self.teams_rankings or away_id not in self.teams_rankings:
                continue

            rate_home = opps.iloc[i]["OddsH"]
            rate_away = opps.iloc[i]["OddsA"]
            rate_draw = opps.iloc[i]["OddsD"]

            # Vypočti pravděpodobnosti pomocí rozšířeného modelu
            probs = self.calculate_match_probabilities(home_id, away_id)
            expected_home = probs['home']
            expected_away = probs['away']
            expected_draw = probs['draw']

            # Breakeven pravděpodobnosti (bez marže)
            be_home = 1 / rate_home if rate_home > 0 else 1
            be_away = 1 / rate_away if rate_away > 0 else 1
            be_draw = 1 / rate_draw if rate_draw > 0 else 1

            # Spočti edge (rozdíl oproti breakevenu)
            edge_home = expected_home - be_home
            edge_away = expected_away - be_away
            edge_draw = expected_draw - be_draw

            MIN_EDGE = 0.03  # Minimální edge 3% pro vsazení (vyšší = konzervativnější)

            # Sázej JEN na nejvyšší pozitivní edge
            best_edge = max(edge_home, edge_away, edge_draw)
            
            if best_edge > MIN_EDGE:
                available = bankroll - total_staked
                if available < min_bet:
                    break  # Už nelze sázet
                
                # Kelly criterium: f = edge / (kurz - 1)
                if best_edge == edge_home and rate_home > 0:
                    kelly_frac = edge_home / (rate_home - 1)
                    stake = min(kelly_frac * bankroll * 0.2, max_bet, available)  # konzervativní 20% Kelly
                    if stake >= min_bet:
                        bets[i, 0] = stake
                        total_staked += stake
                
                elif best_edge == edge_away and rate_away > 0:
                    kelly_frac = edge_away / (rate_away - 1)
                    stake = min(kelly_frac * bankroll * 0.2, max_bet, available)
                    if stake >= min_bet:
                        bets[i, 1] = stake
                        total_staked += stake
                
                elif best_edge == edge_draw and rate_draw > 0:
                    kelly_frac = edge_draw / (rate_draw - 1)
                    stake = min(kelly_frac * bankroll * 0.2, max_bet, available)
                    if stake >= min_bet:
                        bets[i, 2] = stake
                        total_staked += stake

        bets = pd.DataFrame(
            data=bets, columns=["BetH", "BetA", "BetD"], index=opps.index
        )
        return bets
    
    def calculate_match_probabilities(self, home_id, away_id):
        """
        Vypočítá pravděpodobnosti výsledku zápasu pomocí VŠECH dostupných statistik.
        """
        home_stats = self.teams_rankings[home_id]
        away_stats = self.teams_rankings[away_id]
        
        # 1) ELO komponenta (40% váha)
        elo_home = home_stats[0]
        elo_away = away_stats[0]
        HOME_ADVANTAGE = 50
        
        elo_prob_home = 1 / (1 + 10 ** ((elo_away - (elo_home + HOME_ADVANTAGE)) / 400))
        elo_prob_away = 1 - elo_prob_home
        
        # 2) Ofenzivní síla (15% váha) - průměr gólů
        goals_home = home_stats[5]  # AvgGoalsFor
        goals_away = away_stats[5]
        off_total = goals_home + goals_away
        off_prob_home = goals_home / off_total if off_total > 0 else 0.5
        
        # 3) Defenzivní síla (15% váha) - průměr gólů proti
        def_home = away_stats[6]  # AvgGoalsAgainst away = obrana home
        def_away = home_stats[6]
        def_total = def_home + def_away
        def_prob_home = def_away / def_total if def_total > 0 else 0.5  # větší def_away = lepší home
        
        # 4) Střely (10% váha) - dominance ve hře
        sog_home = home_stats[7]  # AvgSOG
        sog_away = away_stats[7]
        sog_total = sog_home + sog_away
        sog_prob_home = sog_home / sog_total if sog_total > 0 else 0.5
        
        # 5) Power play efektivita (5% váha)
        ppg_home = home_stats[9]  # AvgPPG
        ppg_away = away_stats[9]
        ppg_total = ppg_home + ppg_away
        ppg_prob_home = ppg_home / ppg_total if ppg_total > 0 else 0.5
        
        # 6) Short-handed góly (3% váha) - disciplína
        shg_home = home_stats[10]  # AvgSHG
        shg_away = away_stats[10]
        shg_total = shg_home + shg_away
        shg_prob_home = shg_home / shg_total if shg_total > 0 else 0.5
        
        # 7) Save percentage brankářů (7% váha)
        sv_pct_home = home_stats[11]  # AvgSV%
        sv_pct_away = away_stats[11]
        sv_total = sv_pct_home + sv_pct_away
        sv_prob_home = sv_pct_home / sv_total if sv_total > 0 else 0.5
        
        # 8) Face-off % (3% váha) - kontrola puku
        fo_pct_home = home_stats[12]  # AvgFO%
        fo_pct_away = away_stats[12]
        fo_total = fo_pct_home + fo_pct_away
        fo_prob_home = fo_pct_home / fo_total if fo_total > 0 else 0.5
        
        # 9) Recent form - poslední 5 zápasů (12% váha)
        form_home = home_stats[13]  # Recent5Form (0-5 body)
        form_away = away_stats[13]
        form_total = form_home + form_away
        form_prob_home = form_home / form_total if form_total > 0 else 0.5
        
        # Vážený průměr všech komponent
        prob_home = (
            0.40 * elo_prob_home +
            0.15 * off_prob_home +
            0.15 * def_prob_home +
            0.10 * sog_prob_home +
            0.05 * ppg_prob_home +
            0.03 * shg_prob_home +
            0.07 * sv_prob_home +
            0.03 * fo_prob_home +
            0.12 * form_prob_home
        )
        
        prob_away = 1 - prob_home
        
        # Remíza - závisí na vyrovnanosti týmů
        elo_diff = abs(elo_home - elo_away)
        draw_prob_base = 0.12  # základní pravděpodobnost remízy v NHL
        
        if elo_diff < 30:
            prob_draw = draw_prob_base * 1.8  # velmi vyrovnaný zápas
        elif elo_diff < 60:
            prob_draw = draw_prob_base * 1.3
        elif elo_diff < 100:
            prob_draw = draw_prob_base
        else:
            prob_draw = draw_prob_base * 0.5  # jasný favorit
        
        # Normalizace do součtu 1.0
        total = prob_home + prob_away + prob_draw
        prob_home /= total
        prob_away /= total
        prob_draw /= total
        
        return {'home': prob_home, 'away': prob_away, 'draw': prob_draw}

    def define_rankings(self, inc: pd.DataFrame):
        for _, row in inc.iterrows():
            home_id = int(row["HID"])
            away_id = int(row["AID"])

            # Inicializuj oba týmy nezávisle
            if home_id not in self.teams_rankings:
                self.teams_rankings[home_id] = [1500.0, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                self.team_stats_history[home_id] = []
            if away_id not in self.teams_rankings:
                self.teams_rankings[away_id] = [1500.0, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                self.team_stats_history[away_id] = []
            
            # Teď aktualizuj podle výsledku
            self.update_rankings_between_2_teams_in_match(row)

    def calculate_dynamic_k(self, inc_row):
        """
        Vypočítá dynamické K podle dominance výhry - VŠECHNY statistiky.
        """
        K_BASE = 30
        K_MAX = 65 # zvýšeno pro větší citlivost
        K_MIN = 20
        
        # 1) Rozdíl gólů (35% váha)
        goal_diff = abs(inc_row.get("HS", 0) - inc_row.get("AS", 0))
        goal_factor = min(goal_diff / 4.0, 1.0)
        
        # 2) Střely na branku (20% váha)
        h_sog = inc_row.get("H_SOG", 0)
        a_sog = inc_row.get("A_SOG", 0)
        if h_sog + a_sog > 0:
            shot_diff = abs(h_sog - a_sog) / (h_sog + a_sog)
        else:
            shot_diff = 0
        shot_factor = min(shot_diff * 2.5, 1.0)
        
        # 3) Power play (10% váha)
        h_ppg = inc_row.get("H_PPG", 0)
        a_ppg = inc_row.get("A_PPG", 0)
        ppg_factor = min(abs(h_ppg - a_ppg) / 2.5, 0.5)
        
        # 4) Short-handed góly (5% váha) - ukazuje převahu
        h_shg = inc_row.get("H_SHG", 0)
        a_shg = inc_row.get("A_SHG", 0)
        shg_factor = min(abs(h_shg - a_shg) / 2.0, 0.3)
        
        # 5) Save percentage (12% váha)
        h_sv = inc_row.get("H_SV", 0)
        a_sv = inc_row.get("A_SV", 0)
        if a_sog > 0 and h_sog > 0:
            h_sv_pct = h_sv / a_sog
            a_sv_pct = a_sv / h_sog
            sv_factor = abs(h_sv_pct - a_sv_pct) * 1.2
        else:
            sv_factor = 0
        
        # 6) Face-off dominance (5% váha)
        h_fo = inc_row.get("H_FO", 0)
        a_fo = inc_row.get("A_FO", 0)
        if h_fo + a_fo > 0:
            fo_diff = abs(h_fo - a_fo) / (h_fo + a_fo)
        else:
            fo_diff = 0
        fo_factor = min(fo_diff * 1.5, 0.3)
        
        # 7) Bloky (3% váha) - defenzivní práce
        h_blk = inc_row.get("H_BLK", 0)
        a_blk = inc_row.get("A_BLK", 0)
        if h_blk + a_blk > 0:
            blk_diff = abs(h_blk - a_blk) / (h_blk + a_blk)
        else:
            blk_diff = 0
        blk_factor = min(blk_diff * 0.8, 0.2)
        
        # 8) Hity (3% váha) - fyzická hra
        h_hit = inc_row.get("H_HIT", 0)
        a_hit = inc_row.get("A_HIT", 0)
        if h_hit + a_hit > 0:
            hit_diff = abs(h_hit - a_hit) / (h_hit + a_hit)
        else:
            hit_diff = 0
        hit_factor = min(hit_diff * 0.6, 0.2)
        
        # 9) Penalty minutes (2% váha) - disciplína
        h_pim = inc_row.get("H_PIM", 0)
        a_pim = inc_row.get("A_PIM", 0)
        if h_pim + a_pim > 0:
            pim_diff = abs(h_pim - a_pim) / (h_pim + a_pim)
        else:
            pim_diff = 0
        pim_factor = min(pim_diff * 0.5, 0.2)
        
        # 10) Prodloužení/nájezdy (penalizace -35%)
        special = inc_row.get("Special", "")
        if "OT" in str(special) or "SO" in str(special):
            overtime_penalty = -0.35
        else:
            overtime_penalty = 0
        
        # Kombinovaný faktor
        dominance = (
            0.35 * goal_factor +
            0.20 * shot_factor +
            0.12 * sv_factor +
            0.10 * ppg_factor +
            0.05 * shg_factor +
            0.05 * fo_factor +
            0.03 * blk_factor +
            0.03 * hit_factor +
            0.02 * pim_factor
        ) + overtime_penalty
        
        # Vypočti finální K
        K = K_BASE + (K_MAX - K_BASE) * max(0, min(dominance, 1.0))
        K = max(K_MIN, min(K, K_MAX))
        
        return K

    def update_rankings_between_2_teams_in_match(self, inc_row):
        """
        Aktualizuje Elo a VŠECHNY statistiky týmů.
        """
        K = self.calculate_dynamic_k(inc_row)
        HOME_ADVANTAGE = 50
        DECAY_PER_DAY = 0.997  # mírnější decay

        home_id = int(inc_row["HID"])
        away_id = int(inc_row["AID"])
        current_date = pd.to_datetime(inc_row["Date"])

        # Aplikuj decay
        for tid in [home_id, away_id]:
            if tid in self.last_update_date:
                days_idle = (current_date - self.last_update_date[tid]).days
                decay_factor = DECAY_PER_DAY ** days_idle
                self.teams_rankings[tid][0] = 1500 + (self.teams_rankings[tid][0] - 1500) * decay_factor
            self.last_update_date[tid] = current_date

        # Získání aktuálních hodnot
        R_home = self.teams_rankings[home_id][0]
        R_away = self.teams_rankings[away_id][0]

        # Očekávaná pravděpodobnost výhry
        expected_home = 1 / (1 + 10 ** ((R_away - (R_home + HOME_ADVANTAGE)) / 400))
        expected_away = 1 - expected_home

        # Skutečný výsledek zápasu
        if inc_row["H"]:
            score_home, score_away = 1, 0
            self.teams_rankings[home_id][2] += 1
            self.teams_rankings[away_id][3] += 1
            form_home, form_away = 1.0, 0.0
        elif inc_row["A"]:
            score_home, score_away = 0, 1
            self.teams_rankings[home_id][3] += 1
            self.teams_rankings[away_id][2] += 1
            form_home, form_away = 0.0, 1.0
        elif inc_row["D"]:
            score_home, score_away = 0.5, 0.5
            self.teams_rankings[home_id][4] += 1
            self.teams_rankings[away_id][4] += 1
            form_home, form_away = 0.5, 0.5
        else:
            score_home, score_away = 0, 0
            form_home, form_away = 0, 0

        # Aktualizace Elo
        new_R_home = R_home + K * (score_home - expected_home)
        new_R_away = R_away + K * (score_away - expected_away)
        self.teams_rankings[home_id][0] = new_R_home
        self.teams_rankings[away_id][0] = new_R_away

        # Aktualizace zápasů
        self.teams_rankings[home_id][1] += 1
        self.teams_rankings[away_id][1] += 1
        
        matches_home = self.teams_rankings[home_id][1]
        matches_away = self.teams_rankings[away_id][1]
        
        # Aktualizace průměrných statistik (klouzavý průměr)
        alpha = 0.15  # váha nového zápasu (15%)
        
        # 5) AvgGoalsFor
        self.teams_rankings[home_id][5] = (1-alpha) * self.teams_rankings[home_id][5] + alpha * inc_row.get("HS", 0)
        self.teams_rankings[away_id][5] = (1-alpha) * self.teams_rankings[away_id][5] + alpha * inc_row.get("AS", 0)
        
        # 6) AvgGoalsAgainst
        self.teams_rankings[home_id][6] = (1-alpha) * self.teams_rankings[home_id][6] + alpha * inc_row.get("AS", 0)
        self.teams_rankings[away_id][6] = (1-alpha) * self.teams_rankings[away_id][6] + alpha * inc_row.get("HS", 0)
        
        # 7) AvgSOG
        self.teams_rankings[home_id][7] = (1-alpha) * self.teams_rankings[home_id][7] + alpha * inc_row.get("H_SOG", 0)
        self.teams_rankings[away_id][7] = (1-alpha) * self.teams_rankings[away_id][7] + alpha * inc_row.get("A_SOG", 0)
        
        # 8) AvgPIM
        self.teams_rankings[home_id][8] = (1-alpha) * self.teams_rankings[home_id][8] + alpha * inc_row.get("H_PIM", 0)
        self.teams_rankings[away_id][8] = (1-alpha) * self.teams_rankings[away_id][8] + alpha * inc_row.get("A_PIM", 0)
        
        # 9) AvgPPG
        self.teams_rankings[home_id][9] = (1-alpha) * self.teams_rankings[home_id][9] + alpha * inc_row.get("H_PPG", 0)
        self.teams_rankings[away_id][9] = (1-alpha) * self.teams_rankings[away_id][9] + alpha * inc_row.get("A_PPG", 0)
        
        # 10) AvgSHG
        self.teams_rankings[home_id][10] = (1-alpha) * self.teams_rankings[home_id][10] + alpha * inc_row.get("H_SHG", 0)
        self.teams_rankings[away_id][10] = (1-alpha) * self.teams_rankings[away_id][10] + alpha * inc_row.get("A_SHG", 0)
        
        # 11) AvgSV% (save percentage)
        h_sog_against = inc_row.get("A_SOG", 0)
        a_sog_against = inc_row.get("H_SOG", 0)
        h_sv = inc_row.get("H_SV", 0)
        a_sv = inc_row.get("A_SV", 0)
        
        h_sv_pct = h_sv / h_sog_against if h_sog_against > 0 else 0
        a_sv_pct = a_sv / a_sog_against if a_sog_against > 0 else 0
        
        self.teams_rankings[home_id][11] = (1-alpha) * self.teams_rankings[home_id][11] + alpha * h_sv_pct
        self.teams_rankings[away_id][11] = (1-alpha) * self.teams_rankings[away_id][11] + alpha * a_sv_pct
        
        # 12) AvgFO% (face-off percentage)
        h_fo = inc_row.get("H_FO", 0)
        a_fo = inc_row.get("A_FO", 0)
        total_fo = h_fo + a_fo
        
        h_fo_pct = h_fo / total_fo if total_fo > 0 else 0.5
        a_fo_pct = a_fo / total_fo if total_fo > 0 else 0.5
        
        self.teams_rankings[home_id][12] = (1-alpha) * self.teams_rankings[home_id][12] + alpha * h_fo_pct
        self.teams_rankings[away_id][12] = (1-alpha) * self.teams_rankings[away_id][12] + alpha * a_fo_pct
        
        # 13) Recent5Form (poslední 5 zápasů)
        self.team_stats_history[home_id].append(form_home)
        self.team_stats_history[away_id].append(form_away)
        
        # Omez na posledních 5 zápasů
        if len(self.team_stats_history[home_id]) > 5:
            self.team_stats_history[home_id] = self.team_stats_history[home_id][-5:]
        if len(self.team_stats_history[away_id]) > 5:
            self.team_stats_history[away_id] = self.team_stats_history[away_id][-5:]
        
        self.teams_rankings[home_id][13] = sum(self.team_stats_history[home_id])
        self.teams_rankings[away_id][13] = sum(self.team_stats_history[away_id])



