from cc import Chrome
import sys, requests
from configparser import ConfigParser
from timeout import sleep_timer, random_timeout
from printr import logger
from error_alerts import telegram
# py -m pip install -U flask waitress requests websocket-client python-timeout python-printr python_ghost_cursor price_parser error-alerts python-dateutil pip
from modules import place_bet

launch_arguments = sys.argv # Provides a list of command line arguments ['secondary_placer.py', '2']
if len(launch_arguments) == 1:
    placer_number = 2
else:
    placer_number = int(launch_arguments[1]) # Convert to integer for browser port calculation

logger = logger(f'{placer_number}.txt', name=f'secondary_placer.py {placer_number}')
log, current_time = logger.log, logger.current_time

settings = ConfigParser()
settings.read(f'{placer_number}.ini')
settings = settings['Settings']
bet365_username = settings['bet365_username']
bet365_password = settings['bet365_password']
bet365_url = settings['bet365_url']
bet365_country = settings['bet365_country']
hour_to_start_placing_bets_at = settings['hour_to_start_placing_bets_at']
hour_to_stop_placing_bets_at = settings['hour_to_stop_placing_bets_at']
stake_multiplier = float(settings['stake_multiplier'])
max_stake = float(settings['max_stake'])
server_url = settings['server_url']
channel_id = settings['telegram_channel_id']
dolphin_profile_id = settings['dolphin_profile_id']
incogniton_profile_id = settings['incogniton_profile_id']
multilogin_profile_id = settings['multilogin_profile_id']

during_active_time = sleep_timer(hour_to_start_placing_bets_at, hour_to_stop_placing_bets_at).during_active_time

alerts = telegram(token='1715192479:AAGNBRU7rlCuFJlQ7FoUmrxG0eqeV0Jd2Ek', channel=channel_id, logger=logger, full_error=True, resend_repeat_errors=False) # @bet365alertsbot

additional_options = ['--window-size=532,1050']
browser = Chrome(username=bet365_username, password=bet365_password, port=9223 + placer_number, logger=logger, additional_options=additional_options, dolphin_profile_id=dolphin_profile_id,incogniton_profile_id=incogniton_profile_id, multilogin_profile_id=multilogin_profile_id, location_to_spoof=bet365_country)
browser.setup_bet365_on_startup(url=bet365_url)

deposit_required_alert_sent = False

previous_bet_details = {}

current_time('Scanning for new bets')
while True:
    try:
        if during_active_time():
            try:
                bet_details = requests.get(server_url).json()
            except Exception:
                # current_time('Server not running')
                bet_details = previous_bet_details

            if bet_details and bet_details != previous_bet_details:
                previous_bet_details = bet_details
                current_time('Found new bet')
                logger.set_indent()

                multiplied_stake = bet_details['stake_as_float'] * stake_multiplier
                if multiplied_stake > 1:
                    multiplied_stake = round(multiplied_stake) # 25.5 * 1.2 rounded to 30 instead of it being 30.6
                bet_details['stake'] = '{:.2f}'.format(multiplied_stake) # Format to string with two decimal places - '0.1' to '0.10'
                bet_details['stake_as_float'] = multiplied_stake

                placer_result, current_odds, stake, bookmaker_balance = place_bet(bet_details, browser, log, max_stake)
                
                if placer_result == 'Deposit required':
                    if not deposit_required_alert_sent:
                        alerts.send_message(f'Rebel placer for {bet365_username}: deposit required')
                        deposit_required_alert_sent = True
                elif deposit_required_alert_sent and bookmaker_balance > bet_details['stake_as_float'] * 10: # Reset deposit message flag
                    deposit_required_alert_sent = False

                current_time('Place bet result:', placer_result)

                logger.remove_indent()
                log()

            else:
                browser.login_to_bet365_and_close_popups()
                browser.clear_old_betslips()
                random_timeout(1)

    except Exception:
        log()
        alerts.send(f'Error on Rebel placer {placer_number} ({bet365_username})')
        log('Continuing')
        log()

    random_timeout(1)
