from scipy import stats
import numpy as np
import io
import pandas as pd
import numpy as np

_norm_cdf = stats.norm(0, 1).cdf
_norm_pdf = stats.norm(0, 1).pdf

def _d1(S, K, T, r, sigma):
    return (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))

def _d2(S, K, T, r, sigma):
    return _d1(S, K, T, r, sigma) - sigma * np.sqrt(T)

def call_value(S, K, T, r, sigma):
    return S * _norm_cdf(_d1(S, K, T, r, sigma)) - K * np.exp(-r * T) * _norm_cdf(_d2(S, K, T, r, sigma))

def put_value(S, K, T, r, sigma):
    return np.exp(-r * T) * K * _norm_cdf(-_d2(S, K, T, r, sigma)) - S * _norm_cdf(-_d1(S, K, T, r, sigma))

def call_delta(S, K, T, r, sigma):
       return _norm_cdf(_d1(S, K, T, r, sigma))

def put_delta(S, K, T, r, sigma):
       return call_delta(S, K, T, r, sigma) - 1

def call_vega(S, K, T, r, sigma):
    return S * _norm_pdf(_d1(S, K, T, r, sigma)) * np.sqrt(T)

def put_vega(S, K, T, r, sigma):
    return call_vega(S, K, T, r, sigma)




def read_data(filename):
    
    df = pd.read_csv(filename, index_col=0)

    time_to_expiry = df.filter(like='TimeToExpiry')

    stock = df.filter(like='Stock')
    
    stock.columns = [stock.columns.str[-5:], stock.columns.str[:-6]]

    options = pd.concat((df.filter(like='-P'), df.filter(like='-C')), axis=1)
    
    options.columns = [options.columns.str[-3:], options.columns.str[:-4]]

    market_data = pd.concat((stock, options), axis=1)
    
    return time_to_expiry, market_data


def get_list_of_all_instruments(market_data):
    # Get the variable option names to return all the names of the options
    instrument_names = list(market_data.columns.get_level_values(0).unique())
    option_names = instrument_names[1:]
    return option_names


def set_tte_to_market_data(market_data, time_to_expiry):
    # Add time_to_expiry to market_data
    market_data['TTE'] = time_to_expiry['TimeToExpiry']
    timestamp = market_data.index
    market_data = market_data.set_index('TTE')
    return market_data


def create_df_to_store_options_values_delta(market_data, option_names):
    short_call_values = {}
    long_call_values = {}
    long_put_values = {}
    short_put_values = {}
    short_call_deltas = {}
    long_call_deltas = {}
    long_put_deltas = {}
    short_put_deltas = {}
    option_values = {}
    option_deltas = {}

    r = 0
    sigma = 0.20

    # Forloop to create new columns with Call/Put names
    for option in option_names:
        # Retrieve K from the Option
        K = int(option[-2:])

        if 'C' in option:
            short_call_values[option] = []
            long_call_values[option] = []
            short_call_deltas[option] = []
            long_call_deltas[option] = []

            # Forloop to calculate short/long call values and deltas
            for time, stock_value in market_data.iterrows():
                short_call_values[option].append(call_value(
                    stock_value['Stock', 'AskPrice'], K, time, r, sigma))
                long_call_values[option].append(call_value(
                    stock_value['Stock', 'BidPrice'], K, time, r, sigma))
                long_call_deltas[option].append(call_delta(
                    stock_value['Stock', 'BidPrice'], K, time, r, sigma))
                short_call_deltas[option].append(-call_delta(
                    stock_value['Stock', 'AskPrice'], K, time, r, sigma))

            option_values['Short Call', option] = short_call_values[option]
            option_values['Long Call', option] = long_call_values[option]
            option_deltas['Short Call', option] = short_call_deltas[option]
            option_deltas['Long Call', option] = long_call_deltas[option]

        if 'P' in option:
            long_put_values[option] = []
            short_put_values[option] = []
            long_put_deltas[option] = []
            short_put_deltas[option] = []

            # Forloop to calculate short/long put values and deltas
            for time, stock_value in market_data.iterrows():
                long_put_values[option].append(
                    put_value(stock_value['Stock', 'AskPrice'], K, time, r, sigma))
                short_put_values[option].append(
                    put_value(stock_value['Stock', 'BidPrice'], K, time, r, sigma))
                long_put_deltas[option].append(
                    put_delta(stock_value['Stock', 'AskPrice'], K, time, r, sigma))
                short_put_deltas[option].append(-put_delta(
                    stock_value['Stock', 'BidPrice'], K, time, r, sigma))
   
            # once you are iterating the loop, you can store the dictionaries
            # into options values for short call, long call for values and deltas
            option_values['Long Put', option] = long_put_values[option]
            option_values['Short Put', option] = short_put_values[option]
            option_deltas['Long Put', option] = long_put_deltas[option]
            option_deltas['Short Put', option] = short_put_deltas[option]

    # Create DataFrames with index market_data
    option_values = pd.DataFrame(option_values, index=market_data.index)
    option_deltas = pd.DataFrame(option_deltas, index=market_data.index)

    # Sort the DataFrames
    option_values = option_values.reindex(sorted(option_values.columns), axis=1)
    option_deltas = option_deltas.reindex(sorted(option_deltas.columns), axis=1)

    # Rounding
    option_values = round(option_values, 2)

    return option_values,option_deltas


def add_blacksholes_data_to_market_data(market_data, option_names,\
                                        option_values,option_deltas):

    for option in option_names:
        if "C" in option:
            market_data[option,
                        'Expected AskPrice'] = option_values['Short Call', option]
            market_data[option,
                        'Expected BidPrice'] = option_values['Long Call', option]
            market_data[option,
                        'Delta Short'] = option_deltas['Short Call', option].values
            market_data[option,
                        'Delta Long'] = option_deltas['Long Call', option].values
    
        elif "P" in option:
            market_data[option,
                        'Expected AskPrice'] = option_values['Short Put', option]
            market_data[option,
                        'Expected BidPrice'] = option_values['Long Put', option]
            market_data[option,
                        'Delta Short'] = option_deltas['Short Put', option].values
            market_data[option,
                        'Delta Long'] = option_deltas['Long Put', option].values
        # elif you will do the same for Put

    # Sort Columns
    market_data = market_data.reindex(sorted(market_data.columns), axis=1)

    return market_data

def option_opportunities(option,market_data):

    if "C" in option:
        expected1 = market_data[option][(market_data[option, 'BidPrice'] - market_data[option,
                                                                                       'Expected AskPrice']) >= 0.10].drop('Expected BidPrice', axis=1)
        expected2 = market_data[option][(market_data[option, 'Expected BidPrice'] -
                                         market_data[option, 'AskPrice']) >= 0.10].drop('Expected AskPrice', axis=1)

    elif "P" in option:
        expected1 = market_data[option][(market_data[option, 'BidPrice'] - market_data[option,
                                                                                       'Expected AskPrice']) >= 0.10].drop('Expected BidPrice', axis=1)
        expected2 = market_data[option][(market_data[option, 'Expected BidPrice'] -
                                         market_data[option, 'AskPrice']) >= 0.10].drop('Expected AskPrice', axis=1)

    return expected1,expected2


def create_positions(market_data, option_names, timestamp):
    # Create a Dictionary with Timestamp and Time to Expiry
    # Index of market_data was changed earlier to time to expiry
    trades = {('Timestamp', ''): timestamp,
              ('Time to Expiry', ''): market_data.index}

    # Forloop that adds columns for the Call/Put Positions and Deltas
    # Global function is a changing variable name based on the option
    # For option C60 it will create a variable named positions_call_C60
    # Forloop over the rows of market_data
    for option in option_names:

        if 'C' in option:
            trades['Call Position', option] = []
            trades['Call Delta', option] = []
            globals()['positions_call_' + option] = 0
    
        if 'P' in option:
            trades['Put Position', option] = []
            trades['Put Delta', option] = []
            globals()['positions_put_' + option] = 0

    for time, data in market_data.iterrows():

        max_delta = min(data['Stock', 'AskVolume'], data['Stock', 'BidVolume'])
    
        # Forloop over the option_names with conditions
        # if-statements if Call or Put + if Short/Long in Call or Put
        for option in option_names:
    
            if 'C' in option:
    
                # Short Call
                if (data[option, 'BidPrice'] - data[option, 'Expected AskPrice']) >= 0.10:
                    short_call_volume = data[option, 'BidVolume']
                    long_call_volume = 0
    
                # Long Call
                elif (data[option, 'Expected BidPrice'] - data[option, 'AskPrice']) >= 0.10:
                    long_call_volume = data[option, 'AskVolume']
                    short_call_volume = 0
    
                else:
                    long_call_volume = short_call_volume = 0
    
                call_trade = long_call_volume - short_call_volume
    
                # Define variable, as set earlier. Note the first position is set to zero otherwise
                # One would get an error here since the variable is then not yet defined.
                globals()['positions_call_' + option] = call_trade + \
                    globals()['positions_call_' + option]
    
                # Add Positions (cumulative)
                trades['Call Position', option].append(
                    globals()['positions_call_' + option])
    
                if globals()['positions_call_' + option] >= 0:
                    long_call_delta = data[option, 'Delta Long']
                    short_call_delta = 0
    
                elif globals()['positions_call_' + option] < 0:
                    short_call_delta = data[option, 'Delta Short']
                    long_call_delta = 0
    
                # Add Deltas (cumulative)
                trades['Call Delta', option].append(
                    abs(globals()['positions_call_' + option]) * (long_call_delta + short_call_delta))
    
            if 'P' in option:
    
                # Short Put
                if (data[option, 'BidPrice'] - data[option, 'Expected AskPrice']) >= 0.10:
                    short_put_volume = data[option, 'BidVolume']
                    long_put_volume = 0
    
                # Long Put
                elif (data[option, 'Expected BidPrice'] - data[option, 'AskPrice']) >= 0.10:
                    long_put_volume = data[option, 'AskVolume']
                    short_put_volume = 0
    
                else:
                    long_put_volume = short_put_volume = 0
    
                put_trade = long_put_volume - short_put_volume
    
                globals()['positions_put_' + option] = put_trade + \
                    globals()['positions_put_' + option]
    
                trades['Put Position', option].append(
                    globals()['positions_put_' + option])
    
                if globals()['positions_put_' + option] >= 0:
                    long_put_delta = data[option, 'Delta Long']
                    short_put_delta = 0
    
                elif globals()['positions_put_' + option] < 0:
                    short_put_delta = data[option, 'Delta Short']
                    long_put_delta = 0
    
                trades['Put Delta', option].append(
                    abs(globals()['positions_put_' + option]) * (long_put_delta + short_put_delta))     
    
    trades = pd.DataFrame(trades).set_index('Timestamp')

    # Sort Columns
    trades = trades.reindex(sorted(trades.columns), axis=1)

    # Calculate Total Option Delta (based on sorted columns)
    trades['Total Option Delta', ''] = np.sum(
        trades['Call Delta'], axis=1) + np.sum(trades['Put Delta'], axis=1)

    # Calculate Cumulative Stock Position (floored if positive, ceiled if negative)
    trades['Stock Position', 'Stock'] = -np.where(trades['Total Option Delta', ''] >= 0, np.floor(
        trades['Total Option Delta', '']), np.ceil(trades['Total Option Delta', '']))


    trades['Remaining Option Delta', ''] = trades['Total Option Delta',
                                                ''] + trades['Stock Position', 'Stock']
    trades.tail()
    return trades


def create_orders(positions):
    
    # Create trades_diff dataframe that gives all actual trades (not positions)
    trades_diff = positions.diff()[1:].drop(
    ['Call Delta', 'Put Delta', 'Time to Expiry', 'Total Option Delta', 'Remaining Option Delta'], axis=1)

    # Drop the 'Call Position','Put Position' and 'Stock Position' top level
    # Makes forlooping easier
    trades_diff.columns = trades_diff.columns.droplevel(level=0)

    # Since positions are not neccesarily zero at the last timestamp, final positions are calculated to be able to valuate these
    final_positions = positions[-1:].drop(['Call Delta', 'Put Delta', 'Time to Expiry',
                                        'Total Option Delta', 'Remaining Option Delta'], axis=1)

    final_positions.columns = final_positions.columns.droplevel(level=0)
    return trades_diff,final_positions


