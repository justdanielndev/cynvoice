"""Support for CynVoice TTS."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.components.tts import (
    CONF_LANG,
    PLATFORM_SCHEMA,
    TextToSpeechEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_VOICE,
    CONF_SPEED,
    CONF_TEMPERATURE,
    CONF_REPETITION_PENALTY,
    CONF_STREAMING,
    DEFAULT_URL,
    DEFAULT_VOICE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = ["en"]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_URL, default=DEFAULT_URL): cv.string,
        vol.Optional(CONF_VOICE, default=DEFAULT_VOICE): cv.string,
    }
)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CynVoice TTS setup."""
    async_add_entities([CynVoiceEntity(hass, config_entry)])


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict[str, Any],
    async_add_entities: AddEntitiesCallback,
    discovery_info: dict[str, Any] | None = None,
) -> None:
    """Set up the CynVoice TTS platform."""
    async_add_entities([CynVoiceEntity(hass, config)])


class CynVoiceEntity(TextToSpeechEntity):
    """The CynVoice TTS Entity."""

    _attr_has_entity_name = True
    _attr_name = "CynVoice"

    def __init__(self, hass: HomeAssistant, config: ConfigEntry | dict[str, Any]) -> None:
        """Init CynVoice TTS service."""
        self.hass = hass
        if isinstance(config, ConfigEntry):
             self._config_entry = config
             data = config.data
             self._attr_unique_id = config.entry_id
        else:
             self._config_entry = None
             data = config
             self._attr_unique_id = "cynvoice_yaml"

        self._url = data.get(CONF_URL, DEFAULT_URL)
        self._voice = data.get(CONF_VOICE, DEFAULT_VOICE)

    @property
    def default_language(self) -> str:
        """Return the default language."""
        return "en"

    @property
    def supported_languages(self) -> list[str]:
        """Return list of supported languages."""
        return SUPPORTED_LANGUAGES

    @property
    def supported_options(self) -> list[str]:
        """Return list of supported options like voice."""
        return [
            CONF_VOICE,
            CONF_SPEED,
            CONF_TEMPERATURE,
            CONF_REPETITION_PENALTY,
            CONF_STREAMING,
        ]

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any] | None = None
    ) -> tuple[str, bytes] | None:
        """Load TTS from CynVoice."""
        session = async_get_clientsession(self.hass)
        options = options or {}

        # Parse options
        voice_id = options.get(CONF_VOICE, self._voice)
        temperature = options.get(CONF_TEMPERATURE, 0.95)
        repetition_penalty = options.get(CONF_REPETITION_PENALTY, 1.1)
        streaming = options.get(CONF_STREAMING, False)

        payload = {
            "text": message,
            "chunk_length": 200,
            "format": "wav",
            "references": [],
            "reference_id": voice_id,
            "seed": None,
            "use_memory_cache": "off",
            "normalize": True,
            "streaming": streaming,
            "max_new_tokens": 1024,
            "top_p": 0.8,
            "repetition_penalty": repetition_penalty,
            "temperature": temperature,
        }

        try:
            async with session.post(
                self._url,
                json=payload,
                headers={"Content-Type": "application/json", "accept": "*/*"},
                timeout=30
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Error %d on load url %s", response.status, self._url)
                    return None
                
                data = await response.read()

        except aiohttp.ClientError as e:
            _LOGGER.error("Can't connect to CynVoice server: %s", e)
            return None

        return "wav", data
