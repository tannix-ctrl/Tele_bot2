import re
import binascii
import requests
from datetime import datetime
from telethon import TelegramClient, events

API_ID = 123456
API_HASH = "your_hash"
BOT_TOKEN = "your_token"

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

def luhn_checksum(card_number):
    def digits_of(n):
        return [int(d) for d in str(n)]
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return checksum % 10 == 0

def parse_track_data(track_data):
    # Track1: B<accnum>^name^addr^city^state^zip^ctry^mod^exp^disco^
    # Track2: ;accnum=exp=cvv|disc?
    track1 = re.search(r'B(\d+)\^([^^]+)\^?([^^]*)', track_data)
    track2 = re.search(r';(\d+)\=(\d{2})(\d{2})=(\d{3})?', track_data)
    
    if track2:
        num, exp_yy, exp_mm, cvv = track2.groups()
        exp = f"{exp_mm}/{exp_yy}"
        return {
            'number': num,
            'expiry': exp,
            'cvv': cvv,
            'track': track_data
        }
    return None

def check_bin(bin_num):
    try:
        resp = requests.get(f"https://lookup.binlist.net/{bin_num}", timeout=5).json()
        return {
            'bank': resp.get('bank', {}).get('name', 'Unknown'),
            'type': resp.get('type', 'Unknown'),
            'country': resp.get('country', {}).get('name', 'Unknown'),
            'brand': resp.get('brand', 'Unknown')
        }
    except:
        return {'error': 'BIN lookup failed'}

def validate_dump(track_data):
    dump = parse_track_data(track_data)
    if not dump:
        return {'valid': False, 'error': 'Invalid track format'}
    
    num = dump['number']
    exp = dump['expiry']
    
    results = {
        'number': num,
        'expiry': exp,
        'cvv': dump['cvv'],
        'luhn_valid': luhn_checksum(num),
        'expiry_valid': datetime.strptime(exp, '%m/%y') > datetime.now(),
        'bin_info': check_bin(num[:6]),
        'full_dump': dump['track']
    }
    
    results['overall_valid'] = (
        results['luhn_valid'] and 
        results['expiry_valid'] and 
        results['cvv'] and 
        'error' not in results['bin_info']
    )
    
    return results

# BULK CHECKER
def bulk_check(dumps_file):
    valid = []
    invalid = []
    with open(dumps_file, 'r') as f:
        for line in f:
            track = line.strip()
            res = validate_dump(track)
            if res['overall_valid']:
                valid.append(res)
            else:
                invalid.append(res)
    return(f"Valid: {len(valid)} | Invalid: {len(invalid)}")
    
    
    # Bulk: python dump_checker.py dumps.txt
    # import sys
    # bulk_check(sys.argv[1])
