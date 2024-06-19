import os
import requests
import telebot
import subprocess
import time
import random
import pendulum
from enum import Enum
import platform
from dotenv import load_dotenv

load_dotenv()

# Check all variables are set
if not os.getenv("HOSTS") or not os.getenv("CHECK_GENERATOR_STATE") or not os.getenv("GENERATOR_PORT") or not os.getenv("CHAT_IDS") or not os.getenv("TELEGRAM_KEY"):
    print("Please set the HOSTS, CHECK_GENERATOR_STATE, GENERATOR_PORT, CHAT_IDS and TELEGRAM_KEY environment "
          "variables.")
    exit(1)

if not os.getenv("DRY_RUN", "False") == "True":
    bot = telebot.TeleBot(os.getenv("TELEGRAM_KEY"))

hosts = os.getenv("HOSTS").split(",")
generator_port = os.getenv("GENERATOR_PORT")
chat_id = os.getenv("CHAT_IDS").split(",")

# 0, 3, 6, 9, 12, 15, 18, 21
shutdown_times = [i for i in range(0, 23) if i % 3 == 0]
# 4, 8, 12, 16, 20
up_times = [i + 1 for i in shutdown_times]


class electricity_states(Enum):
    no_electricity = -1
    unknown_electricity_source = 0
    generator = 1
    city_electricity = 2


# Get the current date in the Europe/Kiev timezone
def get_current_date():
    return pendulum.now("Europe/Kiev")


# Check if any of the hosts is up
def last_state():
    for host in hosts:
        try:
            if platform.system() != "Windows":
                subprocess.check_output(["ping", "-c", "10", host])
            else:
                subprocess.check_output(["ping", "-n", "10", host])
            return True
        except subprocess.CalledProcessError:
            pass

    return False


# Check if the generator is up
# In my case, I have a device that is not connected to the generator (Printer, Raspberry PI, old router).
# Therefore, when we start the generator, it will be OFF.
def check_generator_state():
    for host in hosts:
        try:
            r = requests.head(f"http://{host}:{generator_port}/", timeout=120)
            if r.status_code == 200:
                return False
        except:
            continue

    return last_state()


# Get the time of last power outage from the file
def get_last_power_outage():
    try:
        with open("last_power_outage.txt", "r") as f:
            return pendulum.parse(f.read(), tz="Europe/Kiev")
    except:
        return None


# Save the current time as the time of last power outage
def save_power_outage():
    with open("last_power_outage.txt", "w") as f:
        f.write(get_current_date().to_datetime_string())


# Get the time of last power state from the file
def get_last_power_state():
    try:
        with open("last_power_state.txt", "r") as f:
            state = f.read()
            if state in electricity_states.__members__:
                return electricity_states[state]
            else:
                return electricity_states.no_electricity
    except:
        return electricity_states.unknown_electricity_source


# Save the current state
def save_power_state(state):
    global current_state
    with open("last_power_state.txt", "w") as f:
        f.write(state.name)
        current_state = electricity_states(state)

    if current_state == electricity_states.no_electricity:
        save_power_outage()


# Get a random swear message
def get_swear_messages_en():
    return random.choice([
        "😡 Dammit, no electricity.",
        "😡 Fever to his mother... Electricity... Disappeared...",
        "😡 Let them burn in hell... Bastards stole toilets and electricity!",
        "😡 Cursed russians, the electricity is gone.",
        "😡 Devil! Cursed bastards again left us without electricity!",
        "😡 Damn moscow imperialists! The office is again without electricity!",
        "😡 So that it would be empty for these pests! Power supply is gone!",
        "😡 Very honored people, with regret we inform you that the office is currently without electricity.",
        "😡 This is the end! They give us the opportunity to save on electricity and donate the rest to the Armed Forces of Ukraine! The office lost power.",
        "😡 How much can it be?! Through cursed russians we are without electricity!",
        "😡 Talk to the teacher, you can't take it anymore with these hours without electricity!",
        "😡 The aunt says in the Viber chat that there's no electricity in the office! And her brother-in-law works at SBU!",
        "😡 Half of the head is already bald from nasty russia! The office is without electricity!",
    ])


# Get a random swear message
def get_swear_messages_uk():
    return random.choice([
        "😡 Йобана русня, немає електрики.",
        "😡 Трясця його матері... Електрика... Тойво...",
        "😡 Хай їм грець... Кацапи вкрали унітази та електрику!",
        "😡 Кляті москалі, електрика пропала.",
        "😡 Дідько! Клята кацапня знов лишила нас електрики!",
        "😡 Довбані московські Ымперіалісти! Офіс знову без електрики!",
        "😡 Та щоб їм пусто було цим покидькам! Зникло енергопостачання!",
        "😡 Вельмишановне панство, зі скорботою повідомляю, що офіс наразі лишився без електропостачання.",
        "😡 Ото вже кончені! Дають нам можливість зекономити на електриці та задонатити залишок на ЗСУ! В офісі зникло енергопостачання.",
        "😡 Та кілько-то можна вже?! Через клятих москалів ми без електрики!",
        "😡 Розпові вчительке, що вже нема сечі терпіти ці години без електрохарчування!",
        "😡 Кума у вайбер чаті каже що нема електрики в офісі! А в неї брат свекра в СБУ працює!",
        "😡 Стать голови вже сива від гидкої русні! Офіс без електрики!",
    ])


# Get a message about the schedule
def schedule_message(locale):
    if int(time.strftime("%H").lstrip("0")) in shutdown_times:
        u = int(time.strftime("%H").lstrip("0")) + 4
        if u > 23:
            u = up_times[0]

        if locale == "uk":
            return "Ймовірне включення за графіком, о " + str(u).zfill(2) + ":00"
        else:
            return "It's likely to switch on according to schedule " + str(u).zfill(2) + ":00"
    else:
        if locale == "uk":
            return "Відключення не за графіком, мабудь аварійне..."
        else:
            return "Outage not according to schedule, probably an emergency..."


# Get a message about the duration of the last power outage
def power_outage_lasted_message(locale):
    last_power_outage = get_last_power_outage()

    if last_power_outage:
        current_time = get_current_date()

        if last_power_outage > current_time:
            raise ValueError("Last power outage is in the future.")

        delta = current_time - last_power_outage

        if locale == "uk":
            mydict = {
                "день": "день",
                "дня": "дні",
                "дней": "днів",
                "часов": "годин",
                "часа": "години",
                "час": "годину",
                "минуту": "хвилину",
                "минуты": "хвилини",
                "минут": "хвилин",
                "секунда": "секунда",
                "секунды": "секунди",
                "секунд": "секунд"
            }
            mystr = f"Відключення електроенергії тривало {delta.in_words(locale='ru')}."
            for k, v in mydict.items():
                mystr = mystr.replace(k, v)

            return mystr
        else:
            return f"Power outage lasted {delta.in_words(locale=locale)}."

    return ""


# Messages for each state
class electricity_status_messages_en(Enum):
    no_electricity = get_swear_messages_en() + "\n" + schedule_message('en')
    unknown_electricity_source = "⚡ There is no information about the electricity source, but it is there!"
    generator = "⚡ We are working from a generator, please turn off the heaters and air conditioning."
    city_electricity = "⚡ We are working from the city's electrical supply." + "\n" + power_outage_lasted_message('en')


# Messages for each state
class electricity_status_messages_uk(Enum):
    no_electricity = get_swear_messages_uk() + "\n" + schedule_message('uk')
    unknown_electricity_source = "⚡ Немає інформації про джерело електрохарчування, але воно є!"
    generator = "⚡ Працюємо від генератора, вимкніть будь ласка обігрівачі та кондиціонери."
    city_electricity = "⚡ Працюємо від міського електропостачання." + "\n" + power_outage_lasted_message('uk')


# Send a message about the current state
def send_electricity_status_message():
    if get_current_date().day == 4 and os.getenv("ENGLISH_FRIDAY", "False") == "True":
        send_message(electricity_status_messages_en[current_state.name].value)
    else:
        send_message(electricity_status_messages_uk[current_state.name].value)


# Send a message to the telegram chat
def send_message(message):
    if os.getenv("DO_NOT_DISTURB_AT_NIGHT", "False") == "True":
        if int(time.strftime("%H").lstrip("0")) in range(0, 6):
            print(get_current_date().to_datetime_string() + " - " + message)
            print("DO_NOT_DISTURB_AT_NIGHT is set to True, not sending a message at night.")
            return

    if not os.getenv("DRY_RUN", "False") == "True":
        for chat in chat_id:
            bot.send_message(chat, message)
    else:
        print(get_current_date().to_datetime_string() + " - " + message)


# Get the current state
current_state = get_last_power_state()

# Check the current state
# If the state is unknown, check the generator
# If the generator is True, then the state is generator
# If the generator is False, then the state is city electricity
if last_state():
    if current_state.value < electricity_states.unknown_electricity_source.value:
        save_power_state(electricity_states.unknown_electricity_source)
        send_electricity_status_message()

    if current_state.value >= electricity_states.unknown_electricity_source.value:
        if os.getenv("CHECK_GENERATOR_STATE") == "True":
            if check_generator_state():
                if current_state != electricity_states.generator:
                    save_power_state(electricity_states.generator)
                    send_electricity_status_message()
            elif current_state != electricity_states.city_electricity:
                save_power_state(electricity_states.city_electricity)
                send_electricity_status_message()
                os.remove("last_power_outage.txt")
        else:
            if current_state != electricity_states.unknown_electricity_source:
                save_power_state(electricity_states.unknown_electricity_source)
                send_electricity_status_message()
                os.remove("last_power_outage.txt")
else:
    if current_state != electricity_states.no_electricity:
        save_power_state(electricity_states.no_electricity)
        send_electricity_status_message()
