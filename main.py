#!/usr/bin/python3
import requests
import re
import datetime
import html
import json
from epg_sources.teleboy import teleboy
from epg_sources.init7 import init7
import validators


# Erste Tagesschau-Sendung auf SRF 1: 3. Februar 1953
TAGESSCHAU_FIRST_BROADCAST = datetime.date(1953, 2, 3)
# Erste «10 vor 10»-Sendung auf SRF 1: 20. August 1990
TEN_VOR_TEN_FIRST_BROADCAST = datetime.date(1990, 8, 20)
# Channel-ID nach gen_channel_id_from_name("SRF 1") → "srf1"
SRF1_CHANNEL_ID = "srf1"


class channel_item:
    id: str
    lang: str
    display_name: str
    icon: str


class programm_item:
    start: datetime
    stop: datetime
    channel: str
    icon: str
    title: str
    country: str
    desc: str
    sub_title: str
    credits: dict
    category: str
    episode_num: str
    date: int
    length: int


def add_srf1_news_episode_numbers(programms):
    """
    Fügt sequenzielle Episodennummern zu SRF-1-Nachrichtensendungen hinzu:

    - Tagesschau Hauptausgabe (19:30 Uhr, täglich):
        Episodennummer = Tage seit der ersten Sendung am 03.02.1953 (Folge 1).
        Andere Tagesschau-Ausgaben (Mittag, Flash, 22:00 etc.) werden ignoriert.

    - «10 vor 10» (21:50 Uhr, Mo-Fr):
        Episodennummer = Tage seit der ersten Sendung am 20.08.1990 (Folge 1).

    Mehrere Ausstrahlungen derselben Ausgabe innerhalb des Erkennungs-Zeitfensters
    erhalten dieselbe Nummer. Bestehende episode_num-Felder werden nicht überschrieben.
    Andere Kanäle (z.B. SRF info Wiederholungen) werden nicht angefasst.
    """
    tagesschau_count = 0
    ten_vor_ten_count = 0

    for programm in programms:
        if gen_channel_id_from_name(programm.get("channel", "")) != SRF1_CHANNEL_ID:
            continue
        if programm.get("episode_num"):
            continue  # nicht überschreiben

        title = (programm.get("title") or "").lower().strip()
        start = programm["start"]
        hour, minute = start.hour, start.minute

        # Tagesschau Hauptausgabe: exakter Titel "tagesschau" + 19:30 (±5 min)
        is_tagesschau_main = (
            title == "tagesschau"
            and hour == 19
            and 25 <= minute <= 35
        )

        # «10 vor 10»: Titel enthält "10 vor 10" oder "10vor10" + 21:50 (±10 min)
        is_ten_vor_ten = (
            ("10 vor 10" in title or "10vor10" in title)
            and hour == 21
            and 40 <= minute <= 59
        )

        if is_tagesschau_main:
            episode = (start.date() - TAGESSCHAU_FIRST_BROADCAST).days + 1
            programm["episode_num"] = f"E{episode}"
            tagesschau_count += 1
        elif is_ten_vor_ten:
            episode = (start.date() - TEN_VOR_TEN_FIRST_BROADCAST).days + 1
            programm["episode_num"] = f"E{episode}"
            ten_vor_ten_count += 1

    print(f"[✓] Tagesschau Hauptausgabe: {tagesschau_count} Episodennummern gesetzt")
    print(f"[✓] «10 vor 10»: {ten_vor_ten_count} Episodennummern gesetzt")
    return programms


def __main__():
    print("[*] Getting/parsing Init7 tvchannels.m3u playlist")
    channels = get_channel_list()

    print("[*] Getting EPG data from Init7")
    init7Obj = init7()
    init7_epg = []
    try:
        init7_epg_raw = init7Obj.get_epg(7 * 24 * 60 * 60, 7 * 24 * 60 * 60)
        init7_epg = match_init7_epg(channels, init7_epg_raw)
        init7_epg = deduplicate_programms(init7_epg)
    except:
        print("[*] Failed. Continue processing other sources.")

    print("[*] Getting past EPG data from teleboy.ch")
    teleboyObj = teleboy()
    teleboy_raw = ""
    try:
        teleboy_raw = teleboyObj.get_epg_from_past_by_duration(7 * 24 * 60)
    except:
        print("[*] Failed. Continue processing other sources.")
    teleboy_epg_past = match_teleboy_epg(channels, teleboy_raw)
    teleboy_epg_past = deduplicate_programms(teleboy_epg_past)

    print("[*] Getting EPG data from teleboy.ch")
    teleboy_raw = ""
    try:
        teleboy_raw = teleboyObj.get_epg_by_duration(7 * 24 * 60)
    except:
        print("[*] Failed. Continue processing other sources.")
    teleboy_epg = match_teleboy_epg(channels, teleboy_raw)
    teleboy_epg = deduplicate_programms(teleboy_epg)

    # generate the xml for the channels
    channels_xmltv = channels_to_xmltv(channels)

    # generate tv7_teleboy_epg.xml
    if len(teleboy_epg) > 0:
        teleboy_epg = add_srf1_news_episode_numbers(teleboy_epg)
        with open("tv7_teleboy_epg.xml", "w+") as w:
            w.write(
                '<?xml version="1.0" encoding="UTF-8" ?><tv>'
                f"{channels_xmltv}{programms_to_xmltv(teleboy_epg)}</tv>"
            )

    if len(teleboy_epg_past) > 0:
        teleboy_epg_past = add_srf1_news_episode_numbers(teleboy_epg_past)
        with open("tv7_teleboy_epg_past.xml", "w+") as w:
            w.write(
                '<?xml version="1.0" encoding="UTF-8" ?><tv>'
                f"{channels_xmltv}{programms_to_xmltv(teleboy_epg_past)}</tv>"
            )

    if len(init7_epg) > 0:
        init7_epg = add_srf1_news_episode_numbers(init7_epg)
        with open("tv7_init7_epg.xml", "w+") as w:
            w.write(
                '<?xml version="1.0" encoding="UTF-8" ?><tv>'
                f"{channels_xmltv}{programms_to_xmltv(init7_epg)}</tv>"
            )

    # generate tv7_epg.xml
    full_epg = []
    full_epg.extend(teleboy_epg)
    full_epg.extend(teleboy_epg_past)
    full_epg.extend(init7_epg)
    full_epg = deduplicate_programms(full_epg)
    full_epg = add_srf1_news_episode_numbers(full_epg)

    programms_xmltv = programms_to_xmltv(full_epg)
    if len(full_epg) > 0:
        with open("tv7_epg.xml", "w+") as w:
            w.write(
                '<?xml version="1.0" encoding="UTF-8" ?><tv>'
                f"{channels_xmltv}{programms_xmltv}</tv>"
            )


def get_channel_list():
    tv7channel_list = requests.get("https://api.init7.net/tvchannels.m3u").text
    tv7channel_list = re.sub(r"udp:\/\/.+", "", tv7channel_list)
    tv7channel_list = tv7channel_list.replace("\n", "")
    tv7channel_list = tv7channel_list.replace("#EXTM3U", "")
    tv7channel_list = tv7channel_list.split("#EXTINF:0 ")

    channel_list = []
    for channel in tv7channel_list:
        channel_obj = {}
        if not channel == "":
            for attribute in channel.split(" "):
                if "=" in attribute:
                    name = attribute.split("=")[0]
                    value = attribute.split("=")[1].replace('"', "")
                else:
                    value = attribute

                if name == "group-title":
                    channel_obj["lang"] = value
                elif name == "tvg-logo":
                    channel_obj["icon"] = value

            # not all channels have tvg-name so do own stuff....
            if "display_name" not in channel_obj:
                channel_obj["display_name"] = channel.split(", ")[1]
                channel_obj["id"] = gen_channel_id_from_name(
                    channel_obj["display_name"]
                )

            if any(x["id"] == channel_obj["id"] for x in channel_list):
                print(f"[!] Duplicate channel: {channel_obj['id']}")
            else:
                channel_list.append(channel_obj)

    return channel_list


def gen_channel_id_from_name(channel_name):
    return (
        channel_name.lower()
        .replace("hd", "")
        .replace("schweiz", "")
        .replace("(", "")
        .replace(")", "")
        .replace(" ", "")
    )


def find_channel_by_id(id, channel_list):
    for channel in channel_list:
        if id == channel["id"]:
            return True

    return False


def match_init7_epg(channel_list, init7_epg):
    print(
        f"[*] Matching init7.ch EPG data ({str(len(init7_epg))}"
        f" programms to {str(len(channel_list))} channels)"
    )
    programms = []
    for programm in init7_epg:
        channel_id = gen_channel_id_from_name(programm["channel"])

        if find_channel_by_id(channel_id, channel_list):
            programms.append(programm)

    return programms


def match_teleboy_epg(channel_list, teleboy_epg):
    print(
        f"[*] Matching teleboy.ch EPG data ({str(len(teleboy_epg))}"
        f" programms to {str(len(channel_list))} channels)"
    )
    mapping = json.loads(open("./mappings/teleboy.json", "r").read())
    programms = []
    matched_channels = set()
    for programm in teleboy_epg:
        channel_id = gen_channel_id_from_name(programm["station"])

        if channel_id in mapping:
            channel_id = mapping[channel_id]

        if find_channel_by_id(channel_id, channel_list):
            matched_channels.add(channel_id)

            programm_matched = {
                "start": programm["begin"],
                "stop": programm["end"],
                "channel": channel_id,
                "icon": programm["image"],
                "title": programm["title"],
            }

            if "subtitle" in programm and programm["subtitle"]:
                programm_matched["sub_title"] = programm["subtitle"]

            if "country" in programm and programm["country"]:
                programm_matched["country"] = programm["country"]

            if "desc" in programm and programm["desc"]:
                programm_matched["desc"] = programm["desc"]

            if (
                "episode_num" in programm
                and "season_num" in programm
                and programm["episode_num"]
                and programm["season_num"]
            ):
                programm_matched["episode_num"] = (
                    f"S{str(programm['season_num'])} E{str(programm['episode_num'])}"
                )
            elif "episode_num" in programm and programm["episode_num"]:
                programm_matched["episode_num"] = str(programm["episode_num"])

            if "year" in programm and programm["year"]:
                programm_matched["date"] = programm["year"]

            programms.append(programm_matched)

    print(f"[✓] Matched {str(len(matched_channels))} teleboy.ch channels")
    return programms


def programms_to_xmltv(programms):
    print(f"[*] Generating XML for {str(len(programms))} programms")
    programms_xml = ""
    for programm in programms:
        programm_xml = ""
        programm_xml = (
            f'{programm_xml}<programme start="'
            f"{programm['start'].strftime('%Y%m%d%H%M%S %z')}\" "
            f"stop=\"{programm['stop'].strftime('%Y%m%d%H%M%S %z')}\" channel=\"{gen_channel_id_from_name(programm['channel'])}\">"
        )

        if "title" in programm:
            programm_xml = (
                f"{programm_xml}<title>{html.escape(programm['title'] or '')}</title>"
            )

        if "sub_title" in programm:
            programm_xml = f"{programm_xml}<sub-title>{html.escape(programm['sub_title'] or '')}</sub-title>"

        if "desc" in programm:
            programm_xml = f"{programm_xml}<desc lang=\"de\">{html.escape(programm['desc'] or '')}</desc>"

        if "persons" in programm:
            programm_xml = f"{programm_xml}<credits>"
            for attrib in programm["persons"]:
                if attrib == "actors":
                    for actor in programm["persons"]["actors"]:
                        programm_xml = f"{programm_xml}<actor>{actor}</actor>"
                else:
                    programm_xml = f"{programm_xml}<{attrib}>{programm['persons'][attrib]}</{attrib}>"
            programm_xml = f"{programm_xml}</credits>"

        if "date" in programm:
            programm_xml = f"{programm_xml}<date>{str(programm['date'])}</date>"

        if "category" in programm:
            programm_xml = f"{programm_xml}<category lang=\"de\">{html.escape(programm['category'] or '')}</category>"

        if "categories" in programm:
            for category in programm["categories"]:
                programm_xml = f"{programm_xml}<category lang=\"de\">{html.escape(category or '')}</category>"

        if "duration" in programm:
            programm_xml = f"{programm_xml}<length units=\"seconds\">{str(int(programm['duration']))}</length>"

        if (
            "icon" in programm
            and programm["icon"] != ""
            and validators.url(programm["icon"])
        ):
            programm_xml = f"{programm_xml}<icon src=\"{re.sub(r'&(?!amp;)', '&amp;', programm['icon'])}\" />"

        if "country" in programm:
            programm_xml = f"{programm_xml}<country>{html.escape(programm['country'] or '')}</country>"

        if "episode_num" in programm:
            if "episode_num_system" in programm:
                programm_xml = f"{programm_xml}<episode-num system=\"{programm['episode_num_system']}\">{programm['episode_num']}</episode-num>"
            else:
                programm_xml = f"{programm_xml}<episode-num system=\"onscreen\">{programm['episode_num']}</episode-num>"

        programm_xml = f"{programm_xml}</programme>"
        programms_xml = programms_xml + programm_xml

    return programms_xml


def channels_to_xmltv(channel_list):
    print(f"[*] Generating XML for {str(len(channel_list))} channels")
    channels_xml = ""
    for channel in channel_list:
        channel_xml = (
            f"<channel id=\"{channel['id']}\">"
            f"<display-name lang=\"de\">{channel['display_name']}</display-name>"
            f"<display-name lang=\"fr\">{channel['display_name']}</display-name>"
            f"<display-name lang=\"it\">{channel['display_name']}</display-name>"
        )

        if "icon" in channel:
            channel_xml = f"{channel_xml}<icon src=\"{re.sub(r'&(?!amp;)', '&amp;', channel['icon'])}\" />"

        channel_xml = f"{channel_xml}</channel>"
        channels_xml = channels_xml + channel_xml

    return channels_xml


def deduplicate_programms(programms):
    seen = set()
    unique_programms = []
    for programm in programms:
        identifier = (programm["start"].timestamp(), programm["stop"].timestamp(), gen_channel_id_from_name(programm['channel']))
        if identifier not in seen:
            seen.add(identifier)
            unique_programms.append(programm)
    print("Deduplicated from ", len(programms), "to", len(unique_programms))
    return unique_programms

__main__()
