from pathlib import Path
from typing import cast, Literal

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Center, VerticalScroll
from textual.events import Click
from textual.widgets import Button, Select, Static, Collapsible, Input
from textual.screen import ModalScreen

from focusseeds.sound_mixer import SoundMixer
from focusseeds.db import DatabaseManager
from focusseeds.config import AppConfig
from focusseeds.widgets.accordion import Accordion


def return_sounds_list(*paths: Path):
    """Return list of audio files supported by Pygame from paths"""
    return [sound.name for path in paths for sound in path.glob('*')
            if sound.suffix in {'.wav', '.mp3', '.ogg', '.flac', '.opus'}]


def remove_id_suffix(string: str) -> str:
    """Remove _something from the end of the string"""
    return string[:string.rindex('_')]


def rename_file(old_path: Path, old_name: str, new_name: str) -> None:
    """Rename a file located at `old_path` with the given `old_name` to `new_name`."""
    old_file_path = old_path / old_name
    new_file_path = old_path / new_name
    old_file_path.rename(new_file_path)


class SoundSettings(Container):
    DEFAULT_CSS = """
    SoundSettings {
        height: auto;
        & > * {
            height: auto;
        }
    }
    .sound-settings-horizontal-padding {
        padding-bottom: 1;
    }
    """

    # External classes
    db = DatabaseManager()
    app_config = AppConfig()
    # App paths
    sounds: Path = app_config.sounds
    ambiences: Path = app_config.ambiences
    # User paths
    user_sounds: Path = app_config.user_sounds
    user_ambiences: Path = app_config.user_ambiences

    def __init__(self):
        super().__init__()
        self.set_alarm = self.app_config.get_used_sound('alarm')['name']
        self.set_signal = self.app_config.get_used_sound('signal')['name']
        self.set_ambient = self.app_config.get_used_sound('ambient')['name']

        sound_list = return_sounds_list(self.sounds, self.user_sounds)
        # Set alarm Select
        self.select_alarm = Select.from_values(sound_list)
        self.select_alarm.prompt = f'Alarm: {self.set_alarm}'
        self.select_alarm.id = 'alarm'
        # Set signal Select
        self.select_signal = Select.from_values(sound_list)
        self.select_signal.prompt = f'Signal: {self.set_signal}'
        self.select_signal.id = 'signal'
        # Set ambient Select
        ambiences_list = return_sounds_list(self.ambiences, self.user_ambiences)
        self.select_ambient = Select.from_values(ambiences_list)
        self.select_ambient.prompt = f'Ambient: {self.set_ambient}'
        self.select_ambient.id = 'ambient'

    @on(Select.Changed)
    def select_changed(self, event: Select.Changed) -> None:
        """Change sound connected to type and update config"""
        # If press blank or already chosen return
        if (event.value == Select.BLANK or
                event.control.id in [self.set_alarm, self.set_signal, self.set_ambient]):
            return None

        if event.control.id == 'ambient':
            songs_list = [path.name for path in self.ambiences.glob('*')]
            file_path = self.ambiences if event.value in songs_list else self.user_sounds
        else:
            songs_list = [path.name for path in self.sounds.glob('*')]
            file_path = self.sounds if event.value in songs_list else self.user_sounds

        self.app_config.update_used_sound(
            sound_type=cast(Literal['alarm', 'signal', 'ambient'], event.control.id),
            name=event.value,
            path=str(file_path)
        )

        if event.control.id == 'alarm':
            self.set_alarm = event.value
            self.select_alarm.prompt = f'Alarm: {self.set_alarm}'
        elif event.control.id == 'signal':
            self.set_signal = event.value
            self.select_signal.prompt = f'Signal: {self.set_signal}'
        else:
            self.set_ambient = event.value
            self.select_ambient.prompt = f'Ambient: {self.set_ambient}'

    def compose(self) -> ComposeResult:
        with Horizontal(classes='sound-settings-horizontal-padding'):
            yield self.select_alarm
            yield Button('Edit Alarms', id='edit-alarm')
        with Horizontal(classes='sound-settings-horizontal-padding'):
            yield self.select_signal
            yield Button('Edit Signals', id='edit-signal')
        with Horizontal():
            yield self.select_ambient
            yield Button('Edit Ambiences', id='edit-ambient')

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed):
        """Open Sounds Edit menu and refresh page if changes
        where applied"""
        async def reinit_and_recompose_self(arg):
            """Restart initialization and recompose"""
            self.set_alarm = self.app_config.get_used_sound('alarm')['name']
            self.set_signal = self.app_config.get_used_sound('signal')['name']
            self.set_ambient = self.app_config.get_used_sound('ambient')['name']

            sound_list = return_sounds_list(self.sounds, self.user_sounds)
            # Set alarm Select
            self.select_alarm = Select.from_values(sound_list)
            self.select_alarm.prompt = f'Alarm: {self.set_alarm}'
            self.select_alarm.id = 'alarm'
            # Set signal Select
            self.select_signal = Select.from_values(sound_list)
            self.select_signal.prompt = f'Signal: {self.set_signal}'
            self.select_signal.id = 'signal'
            # Set ambient Select
            ambiences_list = return_sounds_list(self.ambiences, self.user_ambiences)
            self.select_ambient = Select.from_values(ambiences_list)
            self.select_ambient.prompt = f'Ambient: {self.set_ambient}'
            self.select_ambient.id = 'ambient'
            await self.recompose()

        if event.button.id == 'edit-ambient':
            sound_type: Literal['ambient'] = 'ambient'
            path_to_sounds: Path = self.user_ambiences
        else:
            sound_type: Literal['alarm'] = 'alarm'
            path_to_sounds: Path = self.user_sounds

        await self.app.push_screen(
            EditSound(sound_type, path_to_sounds),
            reinit_and_recompose_self
        )


class EditSound(ModalScreen):
    DEFAULT_CSS = """
    EditSound {
        align: center middle;
        width: auto;
        height: auto;
    }

    #edit-sound-body {
        min-width: 50;
        max-width: 70;
        height: 30;
        padding: 1 2;
        background: $panel;
    }

    #sounds-accordion {
        min-width: 50;
        max-width: 70;
        height: auto;
    }

    .sound-buttons-wrapper {
        height: auto;
        padding: 1 1 0 1;
        width: 100%;
    }
    
    #add-sound-wrapper {
        height: auto;
    }

    .sound-buttons-divider {
        width: 1fr;
    }
    
    #add-sound-divider {
        height: 1fr
    }
    """
    BINDINGS = [
        ('ctrl+q', 'quit_app', 'Quit App'),
        ('escape', 'close_popup', 'Close Popup')
    ]

    def action_quit_app(self):
        self.app.exit()

    def __init__(
            self,
            sound_type: Literal['alarm', 'ambient'],
            path_to_sounds: Path,
            name: str | None = None,
            id: str | None = None,
            classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.config = AppConfig()
        self.sound_type = sound_type
        self.path_to_sounds = path_to_sounds
        self.sounds_names: dict[str, str] = {sound.split('.')[0]: f'.{sound.split('.')[1]}'
                                             for sound in return_sounds_list(path_to_sounds)}

    def action_close_popup(self):
        self.dismiss(True)

    def on_click(self, event: Click):
        """Close popup when clicked on the background
        and user is not editing
        Return [self.edited] to give information to call back
        """
        is_background = self.get_widget_at(event.screen_x, event.screen_y)[0] is self
        if is_background:
            self.dismiss(True)

    def compose(self) -> ComposeResult:
        with VerticalScroll(id='edit-sound-body'):
            with Accordion(id='sounds-accordion'):
                for name in self.sounds_names.keys():
                    with Collapsible(title=name, classes='sound-collapsible', id=f'{name}_coll'):
                        yield Input(value=name, id=f"{name}_input", restrict=r'^[a-zA-Z0-9_-]+$')
                        with Horizontal(classes='sound-buttons-wrapper'):
                            yield Button('Rename', variant='success',
                                         disabled=True, id=f"{name}_rename")
                            yield Static(classes='sound-buttons-divider')
                            yield Button('Remove', variant='error',
                                         id=f"{name}_remove")

            yield Static(id='add-sound-divider')
            with Center(id='add-sound-wrapper'):
                yield Button(
                    f"Add {'Sound' if self.sound_type != 'ambient' else 'Ambient'}",
                    variant='primary'
                )

    @on(Input.Changed)
    def check_sound_name(self, event: Input.Changed):
        """Check is new sound name correct"""
        query = f"#{remove_id_suffix(event.input.id)}_rename"
        self.query_one(query).disabled = event.input.value in self.sounds_names

    @on(Button.Pressed)
    async def change_sound_name(self, event: Button.Pressed):
        """Change name of a sound and update DOM and dist"""
        # Change name
        sound_name = remove_id_suffix(event.button.id)
        extension = self.sounds_names[sound_name]
        old_name = sound_name + extension
        new_name = self.query_one(f'#{sound_name}_input', Input).value
        new_name_with_extension = new_name + extension
        rename_file(self.path_to_sounds, old_name, new_name_with_extension)
        # Update DOM and dict
        del self.sounds_names[sound_name]
        self.sounds_names[new_name] = extension
        self.config.change_sound_name_if_in_config(self.sound_type, new_name_with_extension)
        await self.recompose()
        self.query_one(f'#{new_name}_coll', Collapsible).collapsed = False

    @on(Button.Pressed)
    def remove_sound(self):
        """Display confirmation screen
        if users accepts sound is removed from library
        """
