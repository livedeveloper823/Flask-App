from cc import Chrome
import os, json, random
from textwrap import dedent
from threading import Thread
from datetime import time, datetime, timedelta
from configparser import ConfigParser
from threading import Thread
from flask import Flask
from waitress import serve
from timeout import sleep_timer, random_timeout
from printr import logger
from error_alerts import telegram
from dateutil.parser import parse
# py -m pip install -U flask waitress requests websocket-client python-timeout python-printr python_ghost_cursor price_parser error-alerts python-dateutil pip
from modules import place_bet, market_converter

app = Flask('Rebel server')

# bet_details = {}
# @app.route('/')
# def get_bet():
#     return bet_details


@app.route("/dashboard")
def dashboard():
    html_table = """
    <html>
        <head>
            <title>Dashboard</title>
        </head>
        <body>
            <h1>Dashboard</h1>
            <table border="1">
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>1</td>
                    <td>Item 1</td>
                    <td>100</td>
                </tr>
                <tr>
                    <td>2</td>
                    <td>Item 2</td>
                    <td>200</td>
                </tr>
            </table>
        </body>
    </html>
    """
    return html_table


Thread(target=serve, kwargs={'app': app, 'host': '0.0.0.0', 'port': 9876}, daemon=True).start()

quit()

logger = logger()
log, current_time = logger.log, logger.current_time

settings = ConfigParser()
settings.read('rebel_placer.ini')
settings = settings['Settings']
bet365_username = settings['bet365_username']
bet365_password = settings['bet365_password']
bet365_url = settings['bet365_url']
bet365_country = settings['bet365_country']
hour_to_start_placing_bets_at = settings['hour_to_start_placing_bets_at']
hour_to_stop_placing_bets_at = settings['hour_to_stop_placing_bets_at']
rebel_email = settings['rebel_email']
rebel_password = settings['rebel_password']
minimum_value_percentage = float(settings['minimum_value_percentage'])
minimum_value = 1.0 + minimum_value_percentage / 100 # 3 to 1.03
maximum_value_percentage = float(settings['maximum_value_percentage'])
maximum_value = 1.0 + maximum_value_percentage / 100 # 20 to 1.2
max_stake = float(settings['max_stake'])
channel_id = settings['telegram_channel_id']
dolphin_profile_id = settings['dolphin_profile_id']
incogniton_profile_id = settings['incogniton_profile_id']
multilogin_profile_id = settings['multilogin_profile_id']

during_active_time = sleep_timer(hour_to_start_placing_bets_at, hour_to_stop_placing_bets_at).during_active_time

alerts = telegram(token='1715192479:AAGNBRU7rlCuFJlQ7FoUmrxG0eqeV0Jd2Ek', channel=channel_id, logger=logger, full_error=True, resend_repeat_errors=False) # @bet365alertsbot

if os.path.isfile(f'{bet365_username}.json'):
    with open(f'{bet365_username}.json') as bets_file:
        bets = json.load(bets_file)
else:
    bets = []

browser = Chrome(username=bet365_username, password=bet365_password, port=9223, logger=logger, dolphin_profile_id=dolphin_profile_id,incogniton_profile_id=incogniton_profile_id, multilogin_profile_id=multilogin_profile_id, location_to_spoof=bet365_country)
rebel_tab_index = 0
bet365_tab_index = 1
for index, tab in enumerate(browser.tabs):
    if 'rebel' in tab.url and index == 1:
        rebel_tab_index = 1
        bet365_tab_index = 0
        browser.switch_to_tab(rebel_tab_index)

browser.get('https://vb.rebelbetting.com')
def login_to_rebel():
    if browser.check_by_text('Log in'):
        log('Logging in to Rebel Betting for', rebel_email)
        if browser.check_by_text('Log in again'):
            browser.click_by_text('Log in again')
            browser.create_isolated_world()
        browser.send(rebel_email, css_selector='#inputEmail')
        browser.send(rebel_password, css_selector='#inputPassword')
        browser.click('button.mt-3')
        browser.create_isolated_world()
        if browser.get_text('#validation', silent=True):
            input('Error logging in to Rebel')
login_to_rebel()

checked_value_bets = []
if len(browser.tabs) == 1:
    browser.new_tab()
else:
    browser.switch_to_tab(bet365_tab_index)
browser.setup_bet365_on_startup(url=bet365_url)
bookmaker_balance, currency = browser.get_bet365_balance() # 52.49, '£'

deposits_log = []
amount_deposited_in_last_24_hours = 0
deposit_required_alert_sent = False

browser.switch_to_tab(rebel_tab_index)
current_time('Scanning for new bets')
while True:
    try:
        value_bets = browser.find_multiple('.bet-card-details.text-nowrap') # Bet details container
        for bet_element in value_bets:
            bet_identifier = bet_element.text
            bookmaker = bet_element.get_text('.text-muted > span:nth-of-type(2)') # 'Bet365
            if bet_identifier not in checked_value_bets and bookmaker == 'Bet365':
                checked_value_bets.append(bet_identifier)
                log('Opening bet details for', bet_identifier)
                browser.switch_to_tab(rebel_tab_index)
                bet_element.click(scroll=True, recheck_coordinates=True)
                random_timeout(1)
                if browser.wait_for('.show > .valuebet'):
                    rebel_odds, stake_as_float, expected_value, selection, match, market, sport, match_link, match_start = browser.js('''\
                        odds = parseFloat(document.querySelector('#Odds').value)
                        stake_as_float = parseFloat(document.querySelector('#Stake').value)
                        expected_value = parseFloat(document.querySelector('#Value').innerText)
                        selection = document.querySelector('#display > strong').innerText
                        match = document.querySelector('#participants').innerText.trim().normalize()
                        market = document.querySelector('#oddstype').innerText.trim().normalize() // Remove whitespace and newline
                        sport = document.querySelector('#sport').innerText
                        match_link = document.querySelector('#BetOnBookmaker').href.slice(18) // Remove 'http://zoot.link/@' redirect from match link
                        match_start = document.querySelector('#start').getAttribute('data-original-title')
                        return [odds, stake_as_float, expected_value, selection, match, market, sport, match_link, match_start]
                        ''')

                    current_time('match_start', match_start)
                    # market = 'Asian handicap'
                    # selection = 'AH(+2.25) Ukraine'
                    # sport = 'Soccer'
                    # match_link = 'https://www.bet365.com/#/AC/B1/C1/D8/E134593013/F3/'
                    # rebel_odds = 1.45
                    # expected_value = 8
                    
                    if stake_as_float > max_stake:
                        log('Overriding stake from', stake_as_float, 'to', max_stake)
                        stake_as_float = max_stake

                    if match_start:
                        match_start_date_and_time = parse(match_start).strftime('%Y-%m-%d %H:%M:%S') # '6 Feb 22:00' to '2023-02-06 22:00:00'
                    else:
                        match_start_date_and_time = None
                    stake = '{:.2f}'.format(stake_as_float) # Format to string with two decimal places - '0.1' to '0.10'
                    
                    current_time('Found new bet:')
                    logger.set_indent()
                    log('Match:', match)
                    log('Match link:', match_link)
                    log('Match start date:', match_start_date_and_time)
                    log('Market:', market)
                    log('Selection:', selection)
                    log('Odds:', rebel_odds)
                    if currency == '£' or currency == '$':
                        log(f'Stake: {currency}{stake}')
                    elif not currency:
                        log(f'Stake: {stake}')
                    else:
                        log(f'Stake: {stake}{currency}')
                    log(f'Expected value: {expected_value}%')
                    log('Sport:', sport)
                    log()
                    
                    value_as_float = 1.0 + expected_value / 100 # 2.3 to 1.023
                    minimum_odds_to_accept = round(rebel_odds / value_as_float * minimum_value, 2)
                    log('Minimum odds to accept', minimum_odds_to_accept)
                    maximum_odds_to_accept = round(rebel_odds / value_as_float * maximum_value, 2)
                    log('Maximum odds to accept', maximum_odds_to_accept)
                    log()

                    if channel_id == '-1001739336908':
                        message = dedent(f'''\
                            Match: {match}
                            Market: {market}
                            Selection: {selection}
                            Odds: {rebel_odds}
                            Match link: {match_link}
                            ''')

                        if sport == 'Basketball' and expected_value >= 9:
                            current_time('Sending bet to BETNINJA - Basketball channel')
                            alerts.send_message(message, channel=-1001835108706)
                        elif 5.8 <= expected_value <= 8.9:
                            current_time('Sending bet to BETNINJA - ALGO channel')
                            alerts.send_message(message, channel=-1001646946316)

                    market, alternative_market, selection, column, section_url = market_converter(match, market, selection, sport)

                    # Modify match_link and set xpath to expand markets after setting markets for Over/under overtime included
                    if section_url:
                        if sport == 'Soccer':
                            match_link = match_link.replace('I0/', section_url) # 'https://www.bet365.com/#/AC/B1/C1/D8/E134461800/F3/I0/' to 'https://www.bet365.com/#/AC/B1/C1/D8/E134461800/F3/I3/'
                        else:
                            match_link += section_url # 'https://www.bet365.com/#/AC/B18/C20604387/D19/E16577680/F19/' to 'https://www.bet365.com/#/AC/B18/C20604387/D19/E16577680/F19/I1/'
                        log('Updated match link:', match_link)

                    xpath_expression_to_expand_markets = f'//div[not(contains(@class, "MarketGroup_Open")) and div[text()="{market}" or text()="{alternative_market}"]]'
                    
                    log('Converted market:', market)
                    if alternative_market:
                        log('Converted alternative market:', alternative_market)
                    log('Converted selection:', selection)
                    if column:
                        log('Column:', column)
                    log()

                    if market == 'Alternative Game Total': # Alternative Game Total is a double table market, xpath checks line is in first or second table before counting index
                        bet_selection_button_xpath = f'//div[div/div[text()="Alternative Game Total" or text()="Alternative Game Total 2"]]//div[@class="gl-MarketGroupContainer "]/div[div/div[contains(@class, "srb-ParticipantLabel") and contains(@class, "Name") and normalize-space()="{selection}"]]/following-sibling::div[{column}]//div[count(//div[div/div[text()="Alternative Game Total" or text()="Alternative Game Total 2"]]//div[div[contains(@class, "srb-ParticipantLabel") and contains(@class, "Name") and normalize-space()="{selection}"]]/preceding-sibling::*)+1][not(@class="gl-MarketColumnHeader ")]'

                    else:
                        # XPath expression:
                            # Select market
                                # Check if bet button is in a table market
                            # Select market
                                # Check if bet button is in a column market
                            # Select market
                                # Check if bet button is in a default market
                        bet_selection_button_xpath = dedent(f'\
                            //div[contains(@class, "-MarketGroup ") and div/div[contains(@class, "MarketGroupButton_Text") and text()="{market}" or text()="{alternative_market}"]] \
                                //div[contains(@class, "gl-Market_General-columnheader")][{column}]//div[count(//div[contains(@class, "-MarketGroup ") and div/div[contains(@class, "MarketGroupButton_Text") and text()="{market}" or text()="{alternative_market}"]]//div[div[contains(@class, "srb-ParticipantLabel") and normalize-space()="{selection}"]]/preceding-sibling::*)+1][not(@class="gl-MarketColumnHeader ")] | \
                            //div[contains(@class, "-MarketGroup ") and div/div[contains(@class, "MarketGroupButton_Text") and text()="{market}" or text()="{alternative_market}"]] \
                                //div[contains(@class, "gl-Market_General-columnheader")][{column}]//div[span[contains(@class, "gl-ParticipantCentered") and normalize-space()="{selection}"]]/span[contains(@class, "Odds")] | \
                            //div[contains(@class, "-MarketGroup ") and div/div[contains(@class, "MarketGroupButton_Text") and text()="{market}" or text()="{alternative_market}"]] \
                                //div[span[normalize-space()="{selection}"]]/span[contains(@class, "Odds")]')

                    bet_details = {
                        'bet_selection_button_xpath': bet_selection_button_xpath,
                        'match_link': match_link,
                        'maximum_odds_to_accept': maximum_odds_to_accept,
                        'minimum_odds_to_accept': minimum_odds_to_accept,
                        'rebel_odds': rebel_odds,
                        'stake': stake,
                        'stake_as_float': stake_as_float,
                        'xpath_expression_to_expand_markets': xpath_expression_to_expand_markets
                        }
                    
                    placer_result = None
                    if during_active_time(): # If during active time place bet
                        browser.switch_to_tab(bet365_tab_index)

                        # if channel_id == '-1001739336908':
                        #     bookmaker_balance, currency = browser.get_bet365_balance()

                        #     if bookmaker_balance and bookmaker_balance < stake_as_float:
                        #         date_24_hours_ago = datetime.now() - timedelta(hours=24)
                        #         for deposit in deposits_log:
                        #             deposit_amount, deposit_date = deposit
                        #             if date_24_hours_ago > deposit_date:
                        #                 amount_deposited_in_last_24_hours -= deposit_amount
                        #                 deposits_log.remove(deposit)

                        #         if amount_deposited_in_last_24_hours - stake_as_float < 1000:
                        #             current_time('Depositing')
                        #             amount_deposited_in_last_24_hours += stake_as_float
                        #             deposit = [stake_as_float, datetime.now()]
                        #             deposits_log.append(deposit)

                        placer_result, current_odds, stake, bookmaker_balance = place_bet(bet_details, browser, log, max_stake, rebel_tab_index, bet365_tab_index)
                        
                        if placer_result == 'Deposit required':
                            if not deposit_required_alert_sent:
                                alerts.send_message(f'Rebel placer for {bet365_username}: deposit required')
                                deposit_required_alert_sent = True
                        elif channel_id == '-1001739336908':
                            placer_date_and_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            bet = {
                                'odds': current_odds,
                                'stake': stake_as_float,
                                'expected_value': expected_value,
                                'selection': selection,
                                'match': match,
                                'market': market,
                                'sport': sport,
                                'match_link': match_link,
                                'match_start_date_and_time': match_start_date_and_time,
                                'placer_result': placer_result,
                                'placer_date_and_time': placer_date_and_time,
                                'bookmaker': 'bet365',
                                'bookmaker_balance': bookmaker_balance
                                }
                            bets.append(bet)
                            with open(f'{bet365_username}.json', 'w') as bets_file:
                                json.dump(bets, bets_file, indent=4)
                else:
                    placer_result = 'Error opening bet details on Rebel'

                if placer_result:
                    current_time('Place bet result:', placer_result)
                    browser.switch_to_tab(rebel_tab_index)

                if placer_result and 'Bet placed' in placer_result:
                    if float(stake) != browser.get_value('#Stake', as_float=True): # Update stake on Rebel if changed to max stake bet365 allows
                        log('Updating stake on rebel from', browser.get_value('#Stake'), 'to', stake)
                        browser.clear(6, '#Stake')
                        browser.send(stake)

                    log('Saving bet to Rebel tracker')
                    browser.click_by_text('LOG')
                    # browser.send_key('l')
                    random_timeout(1)
                    if deposit_required_alert_sent and bookmaker_balance > stake_as_float * 10: # Reset deposit message flag
                        deposit_required_alert_sent = False
                else:
                    log('Snoozing bet on Rebel')
                    browser.click_by_text('SNOOZE')
                    # browser.send_key('z')
                    random_timeout(1)

                logger.remove_indent()
                log()
                    
                if len(checked_value_bets) == 1000:
                    checked_value_bets.pop(0)
                
                bet_details = {}
                
                break # Recheck bets on rebel

        browser.click_multiple_if_available('#SelectedBetModal.show #CloseSelectedCard, .text-bg-danger.clickable, .alert-tutorialbox > div > .btn:nth-child(2)') # Close bet details button backup, reconnect to Rebel servers button, tutorial prompt

        browser.get_current_url()
        if 'error' in browser.url:
            browser.reload()
            browser.create_isolated_world()
        if 'log' in browser.url:
            browser.create_isolated_world()
            login_to_rebel()

    except Exception:
        log()
        alerts.send(f'Error on Rebel placer for {bet365_username}')
        log('Continuing')
        log()
        browser.switch_to_tab(rebel_tab_index)

    random_timeout(1)
