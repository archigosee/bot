import telebot
from telebot import types
import mysql.connector
from mysql.connector import Error
import re


# Connect to MySQL database
def create_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='mybot',
            user='root',
            password=''
        )
        print("Connected to MySQL database")
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
    return connection


# Replace 'YOUR_BOT_TOKEN' with your actual bot token
bot = telebot.TeleBot('7048190865:AAFLdlCEBmdR89Jt52f-ntILKt6MgXMGWf8')

# Dictionary to store user registration data
user_data = {}


# Function to validate name
def validate_name(name):
    return bool(re.match("^[a-zA-Z ]+$", name))


# Function to validate additional phone number
# Function to validate additional phone number
def validate_phone_number(phone_number):
    return bool(re.match(r"^(\+\d{1,3})?\d{10,}$", phone_number))


@bot.message_handler(commands=['start'])
def handle_start(message):
    user_name = message.from_user.first_name
    welcome_message = f"Hello, {user_name}! Welcome to the bot. Would you like to continue registering?"

    # Create inline keyboard
    markup = types.InlineKeyboardMarkup()
    yes_btn = types.InlineKeyboardButton('Yes', callback_data='register_yes')
    no_btn = types.InlineKeyboardButton('No', callback_data='register_no')
    markup.row(yes_btn, no_btn)

    bot.send_message(message.chat.id, welcome_message, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('register_'))
def handle_callback_query(call):
    if call.data == 'register_yes':
        # Request contact information
        contact_message = "Please share your contact information."
        contact_request = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        contact_request.add(types.KeyboardButton(text="Share contact", request_contact=True))
        bot.send_message(call.message.chat.id, contact_message, reply_markup=contact_request)
    elif call.data == 'register_no':
        # End the registration process
        bot.send_message(call.message.chat.id, "Registration process terminated.")


@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    # Check if the phone number is already registered
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        phone_number = message.contact.phone_number
        select_query = "SELECT * FROM user_registration WHERE phone_number = %s"
        cursor.execute(select_query, (phone_number,))
        existing_user = cursor.fetchone()
        cursor.close()
        connection.close()

        if existing_user:
            # Phone number is already registered
            bot.send_message(message.chat.id, "This phone number is already registered",
                             reply_markup=types.ReplyKeyboardRemove())
        else:
            # Save contact information and proceed with registration
            user_data['contact'] = phone_number
            first_name_message = "Please enter your first name."
            bot.send_message(message.chat.id, first_name_message, reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(message.chat.id, "Error connecting to database.")


@bot.message_handler(func=lambda message: 'contact' in user_data and 'first_name' not in user_data)
def handle_first_name(message):
    # Validate first name
    if not validate_name(message.text):
        bot.send_message(message.chat.id, "Please enter a valid first name containing only letters and spaces.")
        return

    # Save first name
    user_data['first_name'] = message.text

    # Ask for last name
    last_name_message = "Please enter your last name."
    bot.send_message(message.chat.id, last_name_message)


@bot.message_handler(func=lambda message: 'first_name' in user_data and 'last_name' not in user_data)
def handle_last_name(message):
    # Validate last name
    if not validate_name(message.text):
        bot.send_message(message.chat.id, "Please enter a valid last name containing only letters and spaces.")
        return

    # Save last name
    user_data['last_name'] = message.text

    # Ask for gender
    gender_message = "Please select your gender."
    markup = types.InlineKeyboardMarkup()
    male_btn = types.InlineKeyboardButton('Male', callback_data='gender_male')
    female_btn = types.InlineKeyboardButton('Female', callback_data='gender_female')
    markup.row(male_btn, female_btn)
    bot.send_message(message.chat.id, gender_message, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('gender_'))
def handle_gender(call):
    # Save gender
    user_data['gender'] = 'Male' if call.data == 'gender_male' else 'Female'

    # Ask for additional phone number or skip
    additional_phone_message = ("Please enter your additional phone number (optional). If you don't have one, "
                                "just type /skip.")
    bot.send_message(call.message.chat.id, additional_phone_message)


@bot.message_handler(func=lambda message: 'gender' in user_data and 'phone_2' not in user_data)
def handle_additional_phone(message):
    # Check if user wants to skip
    if message.text.lower() == '/skip':
        user_data['phone_2'] = None
        # Ask for city
        city_message = "Please enter your city."
        bot.send_message(message.chat.id, city_message)
    else:
        # Validate additional phone number
        if not validate_phone_number(message.text):
            bot.send_message(message.chat.id, "Please enter a valid additional phone number.")
            return

        # Save additional phone number
        user_data['phone_2'] = message.text
        # Ask for city
        city_message = "Please enter your city."
        bot.send_message(message.chat.id, city_message)


@bot.message_handler(func=lambda message: 'gender' in user_data and 'city' not in user_data)
def handle_city(message):
    # Save city
    user_data['city'] = message.text

    # Show the filled information and ask for confirmation
    confirmation_message = f"Please confirm the following information:\n\n" \
                           f"User ID: {message.chat.id}\n" \
                           f"Phone Number: {user_data.get('contact', 'Not provided')}\n" \
                           f"Additional Phone Number: {user_data.get('phone_2', 'Not provided')}\n" \
                           f"First Name: {user_data['first_name']}\n" \
                           f"Last Name: {user_data['last_name']}\n" \
                           f"Gender: {user_data['gender']}\n" \
                           f"City: {user_data['city']}\n\n" \
                           "Is this information correct?"
    markup = types.InlineKeyboardMarkup()
    confirm_btn = types.InlineKeyboardButton('Yes', callback_data='confirm_registration')
    cancel_btn = types.InlineKeyboardButton('No', callback_data='cancel_registration')
    markup.add(confirm_btn, cancel_btn)
    bot.send_message(message.chat.id, confirmation_message, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'confirm_registration')
def handle_confirm_registration(call):
    if call.data == 'confirm_registration':
        message = call.message

        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            insert_query = ("INSERT INTO user_registration (user_id, phone_number, phone_2, first_name, last_name, "
                            "gender, city) VALUES (%s, %s, %s, %s, %s, %s, %s)")
            user_data_values = (
                message.chat.id,
                user_data.get('contact', 'Not provided'),
                user_data.get('phone_2', None),
                user_data['first_name'],
                user_data['last_name'],
                user_data['gender'],
                user_data['city']
            )
            try:
                cursor.execute(insert_query, user_data_values)
                connection.commit()
                print("User data inserted into database")
            except Error as e:
                print(f"Error inserting user data into database: {e}")
            finally:
                cursor.close()
                connection.close()
                print("MySQL connection closed")
        # Registration confirmed, you can save the user data to a database or perform any other necessary actions
        bot.send_message(call.message.chat.id, "Registration confirmed! Thank you.")

        # Ask if the user wants to open the web app
        open_webapp_message = "Do you want to open the web app?"
        markup = types.InlineKeyboardMarkup()
        open_webapp_btn = types.InlineKeyboardButton('Open Web App', url='https://t.me/waga_lancerbot/waga_bot')
        markup.add(open_webapp_btn)
        bot.send_message(call.message.chat.id, open_webapp_message, reply_markup=markup)

        # Clear user data for the next registration
        user_data.clear()


@bot.callback_query_handler(func=lambda call: call.data == 'cancel_registration')
def handle_cancel_registration(call):
    # Set a flag to indicate the user wants to re-enter their data
    user_data['confirm'] = False

    # End the registration process
    bot.send_message(call.message.chat.id,
                     "Registration process terminated. If you want to register, please type /start.")


@bot.message_handler(commands=['profile'])
def handle_profile(message):
    user_id = message.chat.id

    # Connect to MySQL database
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        # Retrieve user profile from the database
        select_query = "SELECT * FROM user_registration WHERE user_id = %s"
        cursor.execute(select_query, (user_id,))
        profile_data = cursor.fetchone()
        cursor.close()
        connection.close()

        if profile_data:
            # Format the profile information
            profile_message = f"User ID: {profile_data[1]}\n" \
                              f"Phone Number: {profile_data[2]}\n" \
                              f"First Name: {profile_data[3]}\n" \
                              f"Last Name: {profile_data[4]}\n" \
                              f"Gender: {profile_data[5]}\n" \
                              f"City: {profile_data[6]}\n"
            bot.send_message(message.chat.id, profile_message)
        else:
            bot.send_message(message.chat.id, "Profile not found.")
    else:
        bot.send_message(message.chat.id, "Error connecting to database.")


@bot.message_handler(commands=['quit'])
def handle_quit(message):
    # End the conversation and clear user data
    user_data.clear()
    bot.send_message(message.chat.id, "Goodbye!")


@bot.message_handler(commands=['edit'])
def handle_edit(message):
    # Create inline keyboard for editing options
    markup = types.InlineKeyboardMarkup()
    first_name_btn = types.InlineKeyboardButton('First Name', callback_data='edit_first_name')
    last_name_btn = types.InlineKeyboardButton('Last Name', callback_data='edit_last_name')
    city_btn = types.InlineKeyboardButton('City', callback_data='edit_city')
    phone_2_btn = types.InlineKeyboardButton('Additional Phone Number', callback_data='edit_phone_2')

    markup.row(first_name_btn)
    markup.row(last_name_btn)
    markup.row(city_btn)
    markup.row(phone_2_btn)

    edit_message = "What would you like to edit?"
    bot.send_message(message.chat.id, edit_message, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_'))
def handle_edit_callback(call):
    if call.data == 'edit_first_name':
        # Ask for the new first name
        message = "Please enter your new first name."
        bot.send_message(call.message.chat.id, message, reply_markup=types.ReplyKeyboardRemove())
        user_data['edit'] = 'first_name'  # Store the field to be edited
    elif call.data == 'edit_last_name':
        # Ask for the new last name
        message = "Please enter your new last name."
        bot.send_message(call.message.chat.id, message, reply_markup=types.ReplyKeyboardRemove())
        user_data['edit'] = 'last_name'  # Store the field to be edited
    elif call.data == 'edit_city':
        # Ask for the new city
        message = "Please enter your new city."
        bot.send_message(call.message.chat.id, message, reply_markup=types.ReplyKeyboardRemove())
        user_data['edit'] = 'city'  # Store the field to be edited
    elif call.data == 'edit_phone_2':
        # Ask for the new additional phone number
        message = "Please enter your new additional phone number."
        bot.send_message(call.message.chat.id, message, reply_markup=types.ReplyKeyboardRemove())
        user_data['edit'] = 'phone_2'  # Store the field to be edited


@bot.message_handler(func=lambda message: 'edit' in user_data and user_data['edit'] == 'phone_2')
def handle_new_phone_2(message):
    # Update the additional phone number in the database
    if message.text.lower() == '/skip':
        bot.send_message(message.chat.id, "Phone number update skipped.")
    else:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            update_query = "UPDATE user_registration SET phone_2 = %s WHERE user_id = %s"
            try:
                cursor.execute(update_query, (message.text, message.chat.id))
                connection.commit()
                bot.send_message(message.chat.id, "Additional phone number updated successfully.")
            except Error as e:
                print(f"Error updating additional phone number: {e}")
            finally:
                cursor.close()
                connection.close()
    user_data.pop('edit', None)  # Remove the edit flag


@bot.message_handler(func=lambda message: 'edit' in user_data and user_data['edit'] == 'first_name')
def handle_new_first_name(message):
    # Update the first name in the database
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        update_query = "UPDATE user_registration SET first_name = %s WHERE user_id = %s"
        try:
            cursor.execute(update_query, (message.text, message.chat.id))
            connection.commit()
            bot.send_message(message.chat.id, "First name updated successfully.")
        except Error as e:
            print(f"Error updating first name: {e}")
        finally:
            cursor.close()
            connection.close()
    user_data.pop('edit', None)  # Remove the edit flag


@bot.message_handler(func=lambda message: 'edit' in user_data and user_data['edit'] == 'last_name')
def handle_new_last_name(message):
    # Update the last name in the database
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        update_query = "UPDATE user_registration SET last_name = %s WHERE user_id = %s"
        try:
            cursor.execute(update_query, (message.text, message.chat.id))
            connection.commit()
            bot.send_message(message.chat.id, "Last name updated successfully.")
        except Error as e:
            print(f"Error updating last name: {e}")
        finally:
            cursor.close()
            connection.close()
    user_data.pop('edit', None)  # Remove the edit flag


@bot.message_handler(func=lambda message: 'edit' in user_data and user_data['edit'] == 'city')
def handle_new_city(message):
    # Update the city in the database
    connection = create_connection()
    if connection:
        cursor = connection.cursor()
        update_query = "UPDATE user_registration SET city = %s WHERE user_id = %s"
        try:
            cursor.execute(update_query, (message.text, message.chat.id))
            connection.commit()
            bot.send_message(message.chat.id, "City updated successfully.")
        except Error as e:
            print(f"Error updating city: {e}")
        finally:
            cursor.close()
            connection.close()
    user_data.pop('edit', None)  # Remove the edit flag


# Start the bot
bot.polling()
