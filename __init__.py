from os.path import dirname
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler, intent_file_handler
from mycroft.util.log import getLogger
from mycroft.skills.context import adds_context, removes_context

from kodipydent import Kodi
import re

_author__ = 'PCWii'

LOGGER = getLogger(__name__)


class KodiSkill(MycroftSkill):
    """
    A Skill to control playback on a Kodi instance via the json-rpc interface.
    """
    def __init__(self):
        super(KodiSkill, self).__init__(name="KodiSkill")
        # self.settings["ipstring"] = ""
        self.kodi_instance = Kodi('192.168.0.32')
        self.notifier_bool = False
        self.movie_list = []
        self.movie_index = 0

    def initialize(self):
        self.load_data_files(dirname(__file__))

        # Check and then monitor for credential changes
        # self.settings.set_changed_callback(self.on_websettings_changed)
        # self.on_websettings_changed()

        self.register_regex("film (?P<Film>.*)")
        self.register_regex("movie (?P<Film>.*)")
        self.register_regex("with (?P<Film>.*)")
        self.register_regex("containing (?P<Film>.*)")
        self.register_regex("matching (?P<Film>.*)")
        self.register_regex("including (?P<Film>.*)")

        self.add_event('recognizer_loop:wakeword', self.handle_listen)
        self.add_event('recognizer_loop:utterance', self.handle_utterance)
        self.add_event('speak', self.handle_speak)

        play_film_intent = IntentBuilder("PlayFilmIntent"). \
            require("PlayKeyword").require("Film").build()
        self.register_intent(play_film_intent, self.handle_play_film_intent)

        search_film_intent = IntentBuilder("SearchFilmIntent"). \
            require("SearchKeyword").require("Film").build()
        self.register_intent(search_film_intent, self.handle_search_film_intent)

        stop_film_intent = IntentBuilder("StopFilmIntent"). \
            require("StopKeyword").require("FilmKeyword").build()
        self.register_intent(stop_film_intent, self.handle_stop_film_intent)

        pause_film_intent = IntentBuilder("PauseFilmIntent"). \
            require("PauseKeyword").require("FilmKeyword").build()
        self.register_intent(pause_film_intent, self.handle_pause_film_intent)

        resume_film_intent = IntentBuilder("ResumeFilmIntent"). \
            require("ResumeKeyword").require("FilmKeyword").build()
        self.register_intent(resume_film_intent, self.handle_resume_film_intent)

        notification_on_intent = IntentBuilder("NotifyOnIntent"). \
            require("NotificationKeyword").require("OnKeyword"). \
            require("KodiKeyword").build()
        self.register_intent(notification_on_intent, self.handle_notification_on_intent)

        notification_off_intent = IntentBuilder("NotifyOffIntent"). \
            require("NotificationKeyword").require("OffKeyword"). \
            require("KodiKeyword").build()
        self.register_intent(notification_off_intent, self.handle_notification_off_intent)

        move_kodi_intent = IntentBuilder("MoveKodiIntent"). \
            require("MoveKeyword").require("CursorKeyword").\
            require("DirectionKeyword").build()
        self.register_intent(move_kodi_intent, self.handle_move_kodi_intent)

    def handle_listen(self, message):
        voice_payload = "Listening"
        if self.notifier_bool:
            self.kodi_instance.GUI.ShowNotification(title="Mycroft.AI", message=voice_payload, displaytime=2500)

    def handle_utterance(self, message):
        utterance = message.data.get('utterances')
        voice_payload = utterance
        if self.notifier_bool:
            self.kodi_instance.GUI.ShowNotification(title="Mycroft.AI utt", message=voice_payload, displaytime=2500)

    def handle_speak(self, message):
        speak = message.data.get('utterance')
        voice_payload = speak
        if self.notifier_bool:
            self.kodi_instance.GUI.ShowNotification(title="Mycroft.AI sp", message=voice_payload, displaytime=2500)

    def handle_play_film_intent(self, message):
        movie_name = message.data.get("Film")
        movie_name = re.sub('\W', ' ', movie_name)
        movie_name = re.sub(' +', ' ', movie_name)
        # self.speak_dialog("play.film", data={"result": movie_name})
        self.play_film_by_search(self.kodi_instance, movie_name)

    def handle_search_film_intent(self, message):
        movie_name = message.data.get("Film")
        movie_name = re.sub('\W', ' ', movie_name)
        movie_name = re.sub(' +', ' ', movie_name)
        self.speak_dialog("find.film", data={"result": movie_name})
        results = self.find_films_matching(self.kodi_instance, movie_name)
        self.speak_multi_film_match(message.data.get['Film'], results)

    def handle_stop_film_intent(self, message):
        self.kodi_instance.Player.Stop(playerid=1)

    def handle_pause_film_intent(self, message):
        self.kodi_instance.Player.PlayPause(playerid=1)

    def handle_resume_film_intent(self, message):
        self.kodi_instance.Player.PlayPause(playerid=1)

    def handle_notification_on_intent(self, message):
        self.notifier_bool = True
        self.speak_dialog("notification", data={"result": "On"})

    def handle_notification_off_intent(self, message):
        self.notifier_bool = False
        self.speak_dialog("notification", data={"result": "Off"})

    def handle_move_kodi_intent(self, message):
        direction = message.data.get("DirectionKeyword")
        if direction == "up":
            self.kodi_instance.Input.Up()
        if direction == "down":
            self.kodi_instance.Input.Down()
        if direction == "left":
            self.kodi_instance.Input.Left()
        if direction == "right":
            self.kodi_instance.Input.Right()
        if direction == "select":
            self.kodi_instance.Input.Select()
        if direction == "enter":
            self.kodi_instance.Input.Select()
        if direction == "back":
            self.kodi_instance.Input.Back()
        move_kw = message.data.get('MoveKeyword')
        cursor_kw = message.data.get('CursorKeyword')
        self.set_context('MoveKeyword', move_kw)
        self.set_context('CursorKeyword', cursor_kw)
        self.speak_dialog("direction", data={"result": direction}, expect_response=True)
        
    # Kodi specific functions for searching and playing movies
    def find_films_matching(self, kodi_id, search):
        """
        Find all Movies Matching the search
        """
        my_movies = kodi_id.VideoLibrary.GetMovies()['result']['movies']
        results = []
        for m in my_movies:
            index_movie = re.sub('\W', ' ', m['label'].lower())
            index_movie = re.sub(' +', ' ', index_movie)
            if search in index_movie:
                results.append(m)
        return results

    def play_film(self, kodi_id, movieid):
        """
        Play a movie by id.
        """
        kodi_id.Playlist.Clear(playlistid=1)
        kodi_id.Playlist.Add(playlistid=1, item={'movieid': movieid})
        kodi_id.Player.Open(item={'playlistid': 1})

    def speak_multi_film_match(self, search, results):
        """
        Tell the user about a list of results.
        """
        output = "I found the following movies matching {}: ".format(search)
        for film in results:
            output += "{}, ".format(film['label'])
        self.speak(output)

    @adds_context('Navigate')
    def play_film_by_search(self, kodi_id, film_search):
        results = self.find_films_matching(kodi_id, film_search)
        if len(results) == 1:
            self.speak_dialog("play.film", data={"result": movie_name})
            self.play_film(kodi_id, results[0]['movieid'])
        elif len(results):
            self.movie_list = results
            self.movie_index = 0
            msg_payload = "I found, " + str(len(results)) + ", results, would you like me to list them?"
            self.speak_dialog('context', data={"result": msg_payload}, expect_response=True)
            if self.notifier_bool:
                self.kodi_instance.GUI.ShowNotification(title="Mycroft.AI", message=msg_payload, displaytime=2500)
        else:
            msg_payload = "I found no results for the search: {}.".format(film_search)
            self.speak_dialog('context', data={"result": msg_payload}, expect_response=True)
            if self.notifier_bool:
                self.kodi_instance.GUI.ShowNotification(title="Mycroft.AI", message=msg_payload, displaytime=2500)

    @intent_handler(IntentBuilder('NavigateYesIntent').require("YesKeyword").require('Navigate').build())
    @adds_context('ParseList')
    def handle_navigate_yes_intent(self, message):
        msg_payload = str(self.movie_list[self.movie_index]['label']) + ", To Skip, say Next, Say Select, to" \
                                                               " play, or Cancel, to stop"
        self.speak_dialog('context', data={"result": msg_payload}, expect_response=True)

    @intent_handler(IntentBuilder('NavigatePlayIntent').require("SelectKeyword").require('ParseList').
                    optionally('Navigate').build())
    @removes_context('ParseList')
    @removes_context('Navigate')
    def handle_navigate_play_intent(self, message):
        self.play_film(self.kodi_instance, self.movie_list[self.movie_index]['movieid'])
        msg_payload = "Attempting to play, " + str(self.movie_list[self.movie_index]['label'])
        self.speak_dialog('context', data={"result": msg_payload}, expect_response=False)

    @intent_handler(IntentBuilder('SkipIntent').require("NextKeyword").require('ParseList').optionally('Navigate').
                    build())
    def handle_navigate_skip_intent(self, message):
        self.movie_index += 1
        if self.movie_index < len(self.movie_list):
            msg_payload = str(self.movie_list[self.movie_index]['label'])
            self.speak_dialog('context', data={"result": msg_payload}, expect_response=True)
        else:
            msg_payload = "there are no more movies in the list"
            self.speak_dialog('context', data={"result": msg_payload}, expect_response=False)

    @intent_handler(IntentBuilder('NavigateCancelIntent').require("CancelKeyword").require('Navigate').
                    optionally('ParseList').build())
    @removes_context('Navigate')
    @removes_context('ParseList')
    def handle_navigate_cancel_intent(self, message):
        msg_payload = 'Canceled'
        self.speak_dialog('context', data={"result": msg_payload}, expect_response=False)

    def stop(self):
        pass


def create_skill():
    return KodiSkill()
