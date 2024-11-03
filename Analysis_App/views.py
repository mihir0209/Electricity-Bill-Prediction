from django.shortcuts import render, HttpResponseRedirect
from django.contrib.auth.hashers import make_password, check_password
from mlxtend.frequent_patterns import apriori, association_rules
from pymongo import MongoClient, errors
from django.utils.timezone import now
import pandas as pd
import json

import base64
from io import BytesIO
from django.http import JsonResponse

client = MongoClient("mongodb+srv://DMWUser:Mihir0209@clustermeow.pucav.mongodb.net/User_DATA?retryWrites=true&w=majority")
db = client['User_DATA']
username=""

def get_db():
    try:
        client.server_info()
        return db
    except Exception as e:
        print("Database connection error:", e)
        return None
def setup_view(request):
    global username
    if username is None:
        return HttpResponseRedirect('/login/')
    db = get_db()
    if db is None:
        return render(request, 'setup.html', {'error': 'Database connection failed'})
    users_collection = db['users']
    user = users_collection.find_one({'username': username})
     # Load appliance data and filter columns
    try:
        appliance_df = pd.read_csv('DATAAA/ApplianceUsageData.csv', usecols=["Appliance", "Model", "Wattage"])
        appliance_types = appliance_df["Appliance"].unique().tolist()
    except Exception as e:
        print("Error loading appliance data:", e)
        appliance_types = []
        appliance_df = pd.DataFrame()
    if request.method == 'POST':
        try:
            appliance_data = []
            appliance_names = request.POST.getlist('appliance_name')
            wattages = request.POST.getlist('wattage')
            types = request.POST.getlist('appliance_type')
            for name, wattage, app_type in zip(appliance_names, wattages, types):
                if name and wattage:
                    try:
                        wattage_val = float(wattage)
                        appliance_data.append({
                            'name': name,
                            'wattage': wattage_val,
                            'type': app_type
                        })
                    except ValueError:
                        print("Ulalal")
            users_collection.update_one(
                {'username': username},
                    {
                        '$push': {
                            'appliances': {'$each': appliance_data},
                        },
                        '$set': {
                            'first_time_login': False
                        }
                    }
                )
            return HttpResponseRedirect('/home/')
        except Exception as e:
            print("Setup error:", e)
            return render(request, 'setup.html', {
                'error': 'An error occurred during setup',
                'username': username,
                'appliances': user.get('appliances', [])
            })
    return render(request, 'setup.html', {
        'username': username,
        'appliances': user.get('appliances', []),
        'appliance_types': appliance_types,
        'appliance_data': appliance_df.to_dict(orient="records")
    })
def calculate_indian_bill(total_kwh):
    try:
        total_bill = 0
        if total_kwh <= 100:
            total_bill = total_kwh * (200.25 / 100)
        elif total_kwh <= 300:
            total_bill = (100 * (200.25 / 100)) + (total_kwh - 100) * (370.45 / 100)
        elif total_kwh <= 500:
            total_bill = (100 * (200.25 / 100)) + (200 * (370.45 / 100)) + (total_kwh - 300) * (500.60 / 100)
        else:
            total_bill = (100 * (200.25 / 100)) + (200 * (370.45 / 100)) + (200 * (500.60 / 100)) + (total_kwh - 500) * (575.65 / 100)
        return total_bill
    except Exception as e:
        print("Billing error:", e)
        return None
def preprocess_data():
    try:
        data_df = pd.read_csv('DATAAA/ApplianceUsageData.csv')
        main_data_df = pd.read_csv('DATAAA/MainDataAVG.csv')
        appliance_matrix = pd.get_dummies(data_df['Appliance'])
        frequent_itemsets = apriori(appliance_matrix, min_support=0.3, use_colnames=True)
        rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1)
        return rules, main_data_df
    except Exception as e:
        print("Data preprocessing error:", e)
        return None, None

def home(request):
    global username
    if username is None:
        return HttpResponseRedirect('/login/')
    
    db = get_db()
    if db is None:
        return render(request, 'home.html', {'error': 'Database connection failed'})
    
    users_collection = db['users']
    user = users_collection.find_one({'username': username})

    try:
        current_month = now().month
        season = get_season(current_month)
        appliances = user.get('appliances', [])
        if not appliances:
            return render(request, 'home.html', {
                'username': username,
                'email': user.get('email', ''),
                'message': 'Please add your appliances in the setup page.',
                'season': season
            })
        
        # Preprocess the data
        rules, main_data_df = preprocess_data()
        if rules is None or main_data_df is None:
            return render(request, 'home.html', {'error': 'Data processing failed'})
        
        usage_suggestion = calculate_usage_suggestions(appliances, main_data_df, season)
        total_bill, price_distribution = calculate_total_bill(appliances, main_data_df, season)
        print(price_distribution)
        import matplotlib.pyplot as plt
        import matplotlib 
        matplotlib.use('Agg')
        # Generate a dynamic plot
        fig, ax = plt.subplots()
        appliance_names = [appliance['name'] for appliance in appliances]
        appliance_wattages = [appliance['wattage'] for appliance in appliances]
        
        ax.barh(appliance_names, appliance_wattages, color='skyblue')
        ax.set_xlabel('Wattage (Watts)')
        ax.set_title('Appliance Usage Visualization')
        ax.tick_params(axis='y', labelsize=10)
        plt.subplots_adjust(left=0.25)  # Adds padding on the left for long labels

        # Save the plot to a BytesIO object and convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png',bbox_inches='tight')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        
        image_base64 = base64.b64encode(image_png).decode('utf-8')
        plt.close()  # Close the plot after use to free memory
        
        fig, ax = plt.subplots()
        appliance_names = [appliance['name'] for appliance in appliances]
        prices = [calculate_indian_bill(kwh) for kwh in price_distribution]
        
        ax.barh(appliance_names, prices, color='skyblue')
        ax.set_xlabel('Individual Price (INR)')
        ax.set_title('Appliance price distribution visualisation')
        ax.tick_params(axis='y', labelsize=10)
        plt.subplots_adjust(left=0.25)  # Adds padding on the left for long labels

        # Save the plot to a BytesIO object and convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png',bbox_inches='tight')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        
        image_base64_1 = base64.b64encode(image_png).decode('utf-8')
        plt.close()  # Close the plot after use to free memory
        
        return render(request, 'home.html', {
            'username': username,
            'email': user.get('email', ''),
            'usage_suggestion': usage_suggestion,
            'season': season,
            'total_bill': total_bill,
            'plot_image': image_base64,
            'plot_image1':image_base64_1    # Pass the image to the template
        })
    
    except Exception as e:
        print("Home page error:", e)
        return render(request, 'home.html', {
            'username': username,
            'email': user.get('email', ''),
            'error': 'An error occurred while processing your data'
        })
def calculate_usage_suggestions(appliances, main_data_df, season):
    usage_suggestion = {}
    for appliance in appliances:
        try:
            appliance_data = main_data_df[main_data_df['Appliance'] == appliance['type']]
            if not appliance_data.empty:
                seasonal_usage = appliance_data.iloc[0][season]
                usage_suggestion[appliance['name']] = round(seasonal_usage, 2)
        except Exception as e:
            print(f"Error calculating usage for {appliance['name']}: {e}")
    return usage_suggestion
def calculate_total_bill(appliances, main_data_df, season):
    total_kwh = 0
    price_distribution=[]
    for appliance in appliances:
        try:
            appliance_data = main_data_df[main_data_df['Appliance'] == appliance['type']]
            if not appliance_data.empty:
                seasonal_usage = appliance_data.iloc[0][season]
                wattage = float(appliance['wattage'])
                monthly_usage_kwh = (wattage * seasonal_usage) / 1000
                total_kwh += monthly_usage_kwh
                price_distribution.append(monthly_usage_kwh)
        except Exception as e:
            print(f"Error calculating bill for {appliance['name']}: {e}")
    total_bill = calculate_indian_bill(total_kwh)
    return round(total_bill, 2), price_distribution


def get_season(month):
    if month in [11, 12, 1]:
        return 'Winter'
    elif month in [5, 6, 7]:
        return 'Summer'
    elif month in [8, 9, 10]:
        return 'Monsoon'
    else:
        return 'Year-round'
def signup(request):
    if request.method == 'POST':
        global username
        username = request.POST.get('username').strip()
        email = request.POST.get('email').strip()
        password = request.POST.get('password').strip()
        db = get_db()
        if db is None:
            return render(request, 'signup.html', {'error': 'Database connection failed'})
        users_collection = db['users']
        existing_user = users_collection.find_one({'username': username})
        if existing_user is not None:
            return render(request, 'signup.html', {'error': 'Username already taken'})
        hashed_password = make_password(password)
        users_collection.insert_one({
            'username': username,
            'email': email,
            'password': hashed_password,
            'first_time_login': True
        })
        return HttpResponseRedirect('/login/')
    return render(request, 'signup.html')
def login_view(request):
    if request.method == 'POST':
        global username 
        username = request.POST.get('username')
        password = request.POST.get('password')
        db = get_db()
        if db is None:
            return render(request, 'login.html', {'error': 'Database connection failed'})
        users_collection = db['users']
        user = users_collection.find_one({'username': username})
        if username is not None and check_password(password, user['password']):
            username = user['username']
            if user.get('first_time_login', False):
                return HttpResponseRedirect('/setup/')
            return HttpResponseRedirect('/home/')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')
def logout_view(request):
    global username
    username=""
    return HttpResponseRedirect('/login/')
