import re
from timeout import random_timeout

def place_bet(bet_details, browser, log, max_stake, rebel_tab_index=None, bet365_tab_index=None):
    bet_selection_button_xpath, match_link, maximum_odds_to_accept, minimum_odds_to_accept, rebel_odds, stake, stake_as_float, xpath_expression_to_expand_markets = bet_details.values()
    # print()
    # print('bet_selection_button_xpath:')
    # print(bet_selection_button_xpath)
    # print()

    browser.get(match_link)
    page_loaded = browser.wait_for('div[class*="-MarketGroup"]') # Wait for match page to load
    if not page_loaded: # Check bet365 doesn't need reloading
        log('Reloading bet365')
        log()
        browser.reload()
        random_timeout(3, 4)
        browser.create_isolated_world()
        browser.wait_for('div[class*="-MarketGroup"]')

    browser.login_to_bet365_and_close_popups()
    browser.clear_old_betslips()
    
    bookmaker_balance, currency = browser.get_bet365_balance()
    
    current_odds = rebel_odds
    if not bookmaker_balance or bookmaker_balance > stake_as_float:
        expanded_markets = browser.click_multiple_by_xpath_if_available(xpath_expression_to_expand_markets, scroll=True, click_in_reverse=True) # Expand main and alternative market if needed with xpath

        bet_selection_button = browser.find_by_xpath(bet_selection_button_xpath, silent=True) # Click on bet selection button to open betslip
        if bet_selection_button:
            try:
                current_odds = float(bet_selection_button.text)
            except ValueError:
                current_odds = None

            if current_odds:
                if minimum_odds_to_accept <= current_odds <= maximum_odds_to_accept:
                    if current_odds != rebel_odds and rebel_tab_index is not None: # If on master browser
                        log('Changing rebel odds from', rebel_odds, 'to', current_odds)
                        browser.switch_to_tab(rebel_tab_index)

                        # Update odds in Rebel
                        browser.clear(5, '#Odds')
                        browser.send(current_odds)

                        # Get updated Rebel stake
                        stake_as_float = browser.get_value('#Stake', as_float=True)
                        if stake_as_float > max_stake:
                            stake_as_float = max_stake
                        stake = '{:.2f}'.format(stake_as_float) # Format to string with two decimal places - '0.1' to '0.10'
                        browser.switch_to_tab(bet365_tab_index)

                    bet_selection_button.click(container_css_selector='.ipe-EventViewDetailScroller, .wcl-PageContainer_Colcontainer')
                    if browser.wait_for('.bs-AnimationHelper_ContainerNoScale'): # Wait for betslip to open
                        # Check stake and change if needed
                        current_stake = browser.get_text('.bsf-StakeBox_StakeValue-input')
                        if current_stake != stake:
                            browser.click('.bsf-StakeBox_StakeUnits, .bsf-StakeBox_StakeValue-input.bsf-StakeBox_StakeValue-empty') # If stake is set already, click on the units selector to highlight stake input and overwrite it
                            number_of_characters_in_current_stake = len(current_stake)
                            if current_stake:
                                browser.send_delete(number_of_characters_in_current_stake)
                            browser.send(stake)

                        browser.click('.bsf-PlaceBetButton:not(.Hidden), .bsf-AcceptButton:not(.Hidden)') # Place bet button
                        if browser.wait_for('div[class*="-ReceiptContent_Title"], .bs-OpportunityChangeErrorMessage, .bs-BetslipReferralsMessage_Title, .qd-CardDepositButton, .bsf-AcceptButton:not(.Hidden):not(:has(.bsf-AcceptButton_Message))'): # 'Bet Placed' text, odds changed message, max stake exceeded message, deposit required message or selection expired message
                            if browser.check('div[class*="-ReceiptContent_Title"]'): # 'Bet Placed' text
                                placer_result = 'Bet placed'
                            elif browser.check('.bs-OpportunityChangeErrorMessage, .bs-BetslipReferralsMessage_Title'): # Recheck odds and retry bet placement if odds are within allowed range or adjust bet to max stake allowed
                                if browser.check('.bs-OpportunityChangeErrorMessage'):
                                    log('Odds changed, retrying')
                                elif browser.check('.bsf-AcceptButton:not(.Hidden)'):
                                    log('Max stake exceeded, adjusting to max stake allowed')
                                    browser.click('.bsf-AcceptButton:not(.Hidden)')
                                    random_timeout(1)
                                    stake = browser.get_text('.bsf-StakeBox_StakeValue-input')
                                for retry_attempt in range(9):
                                    current_odds = browser.get_text('.bsc-OddsDropdownLabel > span', as_float=True)
                                    if current_odds:
                                        if minimum_odds_to_accept <= current_odds <= maximum_odds_to_accept:
                                            if current_odds != rebel_odds and rebel_tab_index is not None: # If on master browser
                                                log('Changing rebel odds from', rebel_odds, 'to', current_odds)
                                                browser.switch_to_tab(rebel_tab_index)

                                                # Update odds in Rebel
                                                browser.clear(5, '#Odds')
                                                browser.send(current_odds)

                                                # Get updated Rebel stake
                                                stake_as_float = browser.get_value('#Stake', as_float=True)
                                                if stake_as_float > max_stake:
                                                    stake_as_float = max_stake
                                                stake = '{:.2f}'.format(stake_as_float) # Format to string with two decimal places - '0.1' to '0.10'
                                                browser.switch_to_tab(bet365_tab_index)

                                                # Check stake and change if needed
                                                current_stake = browser.get_text('.bsf-StakeBox_StakeValue-input')
                                                if current_stake != stake:
                                                    browser.click('.bsf-StakeBox_StakeUnits, .bsf-StakeBox_StakeValue-input.bsf-StakeBox_StakeValue-empty') # If stake is set already, click on the units selector to highlight stake input and overwrite it
                                                    number_of_characters_in_current_stake = len(current_stake)
                                                    browser.send_delete(number_of_characters_in_current_stake)
                                                    browser.send(stake)

                                            browser.click('.bsf-PlaceBetButton:not(.Hidden), .bsf-AcceptButton:not(.Hidden)') # Accept changed odds and place bet button
                                            random_timeout(1)
                                            if browser.wait_for('div[class*="-ReceiptContent_Title"], .bs-OpportunityChangeErrorMessage, .bs-BetslipReferralsMessage_Title, .bsf-AcceptButton:not(.Hidden):not(:has(.bsf-AcceptButton_Message))'):
                                                if browser.check('div[class*="-ReceiptContent_Title"]'): # 'Bet Placed' text
                                                    if float(stake) != stake_as_float:
                                                        if currency == '£' or currency == '€':
                                                            placer_result = f'Bet placed for {currency}{stake}'
                                                        else:
                                                            placer_result = f'Bet placed for {stake}{currency}'
                                                    else:
                                                        placer_result = 'Bet placed'
                                                    break
                                                elif browser.check('.bs-OpportunityChangeErrorMessage'):
                                                    if retry_attempt == 8:
                                                        placer_result = "Didn't bet - odds changed more than eight times"
                                                    continue
                                                elif browser.check('.bs-BetslipReferralsMessage_Title'):
                                                    placer_result = "Didn't bet - stake exceeds maximum limit"
                                                elif browser.check('.bsf-AcceptButton:not(.Hidden):not(:has(.bsf-AcceptButton_Message))'):
                                                    placer_result = "Didn't bet - selection not available"
                                                else:
                                                    placer_result =  "Didn't bet - unknown error"
                                                    break
                                            else:
                                                placer_result =  "Didn't bet - unknown error"
                                                break
                                        else:
                                            placer_result = f"Didn't bet - odds changed to {current_odds}"
                                            break
                                    else:
                                        placer_result = "Didn't bet - error checking odds"
                                        break
                            elif browser.check('.qd-CardDepositButton'):
                                placer_result = "Didn't bet - deposit required"
                            elif browser.check('.bsf-AcceptButton:not(.Hidden):not(:has(.bsf-AcceptButton_Message))'):
                                placer_result = "Didn't bet - selection no longer available"
                            else:
                                placer_result = "Didn't bet - unknown error"
                        else:
                            placer_result = "Didn't bet - error clicking on bet button, IP could be blocked"
                    else:
                        placer_result = "Didn't bet - error when opening betslip, could be a problem logging into your bet365 account"
                else:
                    placer_result = f"Didn't bet - odds changed to {current_odds}"
            else:
                placer_result = "Didn't bet - error checking odds"
        else:
            placer_result = "Didn't bet - couldn't find selection button (usually means market or line is no longer available)"
        
        browser.clear_old_betslips()

    else:
        placer_result = 'Deposit required'
    
    return placer_result, current_odds, stake, bookmaker_balance

prelive_line_map = {
    '0.25': '0.0, 0.5',
    '0.75': '0.5, 1.0',
    '1.25': '1.0, 1.5',
    '1.75': '1.5, 2.0',
    '2.25': '2.0, 2.5',
    '2.75': '2.5, 3.0',
    '3.25': '3.0, 3.5',
    '3.75': '3.5, 4.0',
    '4.25': '4.0, 4.5',
    '4.75': '4.5, 5.0',
    '5.25': '5.0, 5.5',
    '5.75': '5.5, 6.0',
    '6.25': '6.0, 6.5',
    '6.75': '6.5, 7.0',
    '7.25': '7.0, 7.5',
    '7.75': '7.5, 8.5',
    '8.25': '8.0, 8.5',
    '8.75': '8.5, 9.0',
    '9.25': '9.0, 9.5'
    }

def market_converter(match, market, selection, sport):
    home_team, away_team = match.split(' vs ') # 'CSKA Sofia vs Academic Plovdiv' to ['CSKA Sofia', 'Academic Plovdiv']
    column = 0
    section_url = None
    alternative_market = None

    if '1X2' in market: # 'Full Time Result'
        if sport == 'Soccer':
            if market == '1X2':
                market = 'Full Time Result'
                if 'Draw' in selection:
                    selection = 'Draw'
            else: # '1X2 first half'
                section_url = 'I7/' # 'Half'
                market = 'Half Time Result'
                if home_team in selection:
                    selection = home_team
                elif 'Draw' in selection:
                    selection = 'Draw'
                else: # Away team
                    selection = away_team
        elif sport == 'Hockey':
            if market == '1X2':
                market = '3-Way'
            else: # 1st period
                market = '1st Period 3-Way'
            selection = 'Money Line'
            if home_team in selection:
                column = 2
            elif 'Draw' in selection:
                column = 3
            else: # Away team
                column = 4
        elif sport == 'Basketball' or sport == 'AMFootball':
            market = 'Game Lines 3-Way'
            if home_team in selection:
                column = 2
            elif 'Draw' in selection:
                column = 3
            else: # Away team
                column = 4
    elif market == 'Double chance':
        market = 'Double Chance'
        if home_team in selection and 'draw' in selection:
            selection = f'{home_team} or draw'
        elif home_team in selection and away_team in selection:
            selection = f'{home_team} or {away_team}'
        elif away_team in selection and 'draw' in selection:
            selection = f'{away_team} or draw'
    elif market == 'Win':
        if sport == 'Soccer':
            market = 'Draw No Bet'
        elif sport == 'Tennis':
            market = 'To Win Match'
        elif sport == 'ESport' or sport == 'Baseball':
            market = 'Match Lines' # Match Lines > To Win
            selection = 'To Win'
            if home_team in selection:
                column = 2
            else: # Away team
                column = 3
    elif market == 'Win overtime included':
        if sport == 'Hockey' or sport == 'Basketball' or sport == 'AMFootball':
            market = 'Game Lines'
            selection = 'Money Line'
            if home_team in selection:
                column = 2
            else: # Away team
                column = 3
    elif market == 'Win first set': # Tennis market
        market = 'First Set Winner'
        if home_team in selection:
            selection = home_team
        else: # Away team
            selection = away_team
    elif market == 'Asian handicap overtime included':
        if sport == 'Basketball':
            section_url = 'I1/' # 'Main Props'
            market = 'Alternative Point Spread'
            alternative_market = 'Alternative Point Spread 2'
            selection = re.search(r'\((.+)\)', selection).group(1) # 'AH(+2.5) Anhelina Kalinina' to '+2.5'
            if '.' not in selection: # Basketball AH selections end with .0 on bet365
                selection += '.0' # '+1' to '+1.0'
        elif sport == 'AMFootball':
            section_url = 'I1/' # 'Main Props'
            market = 'Alternative Point Spread 2-Way'
            selection = re.search(r'\((.+)\)', selection).group(1) # 'AH(+2.5) Anhelina Kalinina' to '+2.5' - NFL AH selections dont end with .0 on bet365
        elif sport == 'Hockey':
            market = 'Game Lines' # Game Lines > Line
            selection = 'Line'
            if home_team in selection:
                column = 2
            else: # Away team
                column = 3
    elif market == 'Asian handicap games': # Tennis market
        section_url = 'I2/' # 'Games'
        market = 'Match Handicap (Games)'
        if away_team in selection: # Only need to set column for away team
            column = 2
        selection = re.search(r'\((.+)\)', selection).group(1) # 'AH(+2.5) Anhelina Kalinina' to '+2.5' - selections always end with .5
    elif 'Asian handicap' in market:
        if sport == 'Soccer':
            section_url = 'I3/' # 'Asian Lines'
            if market == 'Asian handicap':
                market = 'Asian Handicap'
                alternative_market = 'Alternative Asian Handicap'
            else: # 'Asian handicap first half'
                market = '1st Half Asian Handicap'
                alternative_market = 'Alternative 1st Half Asian Handicap'
            if away_team in selection: # Only need to set column for away team
                column = 2
            selection = re.search(r'\((.+)\)', selection).group(1) # 'AH(+0.5) Etimesgut Belediyespor' to '+0.5'
            if selection == '+0' or selection == '-0': # '-0' and '+0' converts to '0.0' on bet365
                selection = '0.0' # '+0' or '-0' to '0.0'
            elif '.' not in selection: # Football AH selections end with .0 on bet365
                selection += '.0' # '+1' to '+1.0'
            elif selection.endswith('.25') or selection.endswith('.75'): # Convert '+2.25' to '+2.0, +2.5'
                mapped_line = prelive_line_map[selection[1:]] # '2.25' (without '-') to '2.0, 2.5'
                if '-' in selection:
                    if not mapped_line.startswith('0.0'): # Not '+0.25' to '0.0, +0.5'
                        mapped_line = '-' + mapped_line # '2.0, 2.5' to '-2.0, 2.5'
                    selection = mapped_line.replace(', ', ', -') # '-2.0, 2.5' to '-2.0, -2.5'
                else: # '+2.25'
                    if not mapped_line.startswith('0.0'): # Not '-0.25' to '0.0, -0.5'
                        mapped_line = '+' + mapped_line # '2.0, 2.5' to '+2.0, 2.5'
                    selection = mapped_line.replace(', ', ', +') # '+2.0, 2.5' to '+2.0, +2.5'
        elif sport == 'Hockey':
            section_url = 'I1/' # 'Main'
            line = re.search(r'\((.+)\)', selection).group(1) # 'AH(+0.5) Etimesgut Belediyespor' to '+0.5'
            if line == '0.0':
                market = 'Draw No Bet'
                if home_team in selection: # Only need to set column for away team
                    selection = home_team
                else: # Away team
                    selection = away_team
            else:
                market = 'Asian Handicap'
                if away_team in selection: # Only need to set column for away team
                    column = 2
                selection = line # Ice hockey uses +0.25 rather than 0.0, +0.5 and -1 rather than -1.0
    elif market == 'Draw no bet':
        market = 'Draw No Bet' # Selection is already the team name
    elif 'Euro' in market and 'handicap' in market: # 'European handicap', 'Euro handicap first half'
        if sport == 'Soccer' or sport == 'AMFootball' or sport == 'Hockey':
            if sport == 'Soccer':
                if market == 'European handicap':
                    market = 'Handicap Result'
                    alternative_market = 'Alternative Handicap Result'
                else: # 'Euro handicap first half'
                    section_url = 'I7/' # 'Half'
                    market = '1st Half Handicap'
                    alternative_market = 'Alternative 1st Half Handicap Result'
            elif sport == 'AMFootball':
                section_url = 'I1/' # 'Main Props'
                market = 'Alternative Handicap 3-Way'
            else: # Ice hockey
                section_url = 'I1/' # 'Main'
                market = 'Alternative Puck Line 3-Way'
            if home_team in selection:
                column = 1
            elif 'Draw' in selection: # 'EH(-1) Draw'
                column = 2
            else: # Away team
                column = 3
            selection = re.search(r'\((.+)\)', selection).group(1) # 'EH(+1) Al Ittihad Al Sakandary' to '+1'
        elif sport == 'Basketball':
            market = 'Game Lines 3-Way' # Game Lines 3-Way > Spread
            selection = 'Spread'
            if home_team in selection:
                column = 2
            elif 'Draw' in selection: # 'EH(-1) Draw'
                column = 3
            else: # Away team
                column = 4
    elif 'Over/under' in market:
        if sport == 'Soccer':
            section_url = 'I3/' # 'Asian Lines'
            if selection.startswith('O'): # Over column
                column = 2
            else: # Under column
                column = 3
            selection = re.search(r'\((.+)\)', selection).group(1) # 'U(1.5) ES Setif vs JS Saoura' to '1.5'
            if market == 'Over/under': # 'Goal Line' market
                market = 'Goal Line'
                alternative_market = 'Alternative Goal Line'
            else: # 'Over/under first half'
                market = '1st Half Goal Line'
                alternative_market = '1st Half Alternative Goal Line'
            if selection in prelive_line_map: # '2.25' to '2.0, 2.5'
                selection = prelive_line_map[selection]
            elif '.5' not in selection:
                selection += '.0' # '1' to '1.0'
        else:
            if sport == 'Basketball':
                section_url = 'I1/' # 'Main Props'
                market = 'Alternative Game Total'
                alternative_market = 'Alternative Game Total 2'
            elif sport == 'Baseball':
                section_url = 'I1/' # 'Main Props'
                market = 'Alternative Game Total'
            elif sport == 'AMFootball':
                section_url = 'I1/' # 'Main Props'
                market = 'Alternative Total 2-Way' # Alternative Total 2-Way
            elif sport == 'Hockey':
                section_url = 'I1/' # 'Main'
                market = 'Alternative Total 2-Way' # Alternative Total 2-Way - Single table market
            if selection.startswith('O'): # Over column
                column = 1
            else: # Under column
                column = 2
            selection = re.search(r'\((.+)\)', selection).group(1) # 'U(154) ES Setif vs JS Saoura' to '154'
            if '.' not in selection:
                selection += '.0' # '154' to '154.0'

    return market, alternative_market, selection, column, section_url