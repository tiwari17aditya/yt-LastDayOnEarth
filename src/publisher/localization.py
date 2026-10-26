"""Multi-language metadata and subtitle localization engine for YouTube.

Enables global audience reach by translating titles, descriptions, and gameplay cues
into primary non-English player demographics for Last Day on Earth: Survival:
- Russian (ru): Kefir! developer home base & top download region (Russia & Eastern Europe)
- Portuguese (pt): Brazil & Latin American mobile gaming audience
- Spanish (es): Latin America & European Spanish-speaking community

Features:
- YouTube Data API v3 'localizations' payload formatting.
- AI-powered localization via Google GenAI / Gemini when configured.
- High-fidelity offline deterministic dictionary & template fallback.
- Character boundary validation (YouTube title <= 100 chars, description <= 5000 chars).
"""

import re
from typing import Dict, List, Optional, Any
from src.logging_config import get_logger

logger = get_logger(component="MetadataLocalizer")


# High-frequency community gaming vocabulary mapping for LDoE
GAME_VOCABULARY = {
    "ru": {
        "Last Day on Earth": "Last Day on Earth",
        "Survival": "Выживание",
        "Episode": "Эпизод",
        "Ep": "Эп.",
        "Bunker Alfa": "Бункер Альфа",
        "Bunker Bravo": "Бункер Браво",
        "Chopper": "Чоппер",
        "ATV": "Вездеход",
        "Woodworking": "Столярный верстак",
        "Smelting": "Плавильная печь",
        "Furnace": "Печь",
        "Base Building": "Строительство базы",
        "Storage Chest": "Сундуки и склад",
        "Farming": "Фарм ресурсов",
        "Resource Gathering": "Сбор ресурсов",
        "Weapon Workshop": "Оружейный верстак",
        "Guns": "Огнестрел",
        "Zombie Horde": "Орда зомби",
        "Fastest Way": "Быстрый способ",
        "Guide": "Гайд",
        "Tips": "Советы",
        "Looting": "Лут",
        "Crafting": "Крафт",
        "Home Base": "Домашняя база",
        "Pine Woods": "Сосновый бор",
        "Limestone Ridge": "Известняковые гряды",
        "Crooked Creek Farm": "Старая ферма",
        "Blackport PD": "Полицейский участок",
    },
    "pt": {
        "Last Day on Earth": "Last Day on Earth",
        "Survival": "Sobrevivência",
        "Episode": "Episódio",
        "Ep": "Ep.",
        "Bunker Alfa": "Bunker Alfa",
        "Bunker Bravo": "Bunker Bravo",
        "Chopper": "Moto Chopper",
        "ATV": "Quadriciclo ATV",
        "Woodworking": "Bancada de Madeira",
        "Smelting": "Fornalha de Fundição",
        "Furnace": "Fornalha",
        "Base Building": "Construção da Base",
        "Storage Chest": "Baús e Organização",
        "Farming": "Farm de Recursos",
        "Resource Gathering": "Coleta de Recursos",
        "Weapon Workshop": "Bancada de Armas",
        "Guns": "Armas de Fogo",
        "Zombie Horde": "Horda de Zumbis",
        "Fastest Way": "Maneira Mais Rápida",
        "Guide": "Guia Completo",
        "Tips": "Dicas",
        "Looting": "Loot",
        "Crafting": "Crafting",
        "Home Base": "Base Principal",
        "Pine Woods": "Floresta de Pinheiros",
        "Limestone Ridge": "Cordilheira de Calcário",
        "Crooked Creek Farm": "Fazenda",
        "Blackport PD": "Delegacia de Polícia",
    },
    "es": {
        "Last Day on Earth": "Last Day on Earth",
        "Survival": "Supervivencia",
        "Episode": "Episodio",
        "Ep": "Ep.",
        "Bunker Alfa": "Búnker Alfa",
        "Bunker Bravo": "Búnker Bravo",
        "Chopper": "Moto Chopper",
        "ATV": "Vehículo ATV",
        "Woodworking": "Mesa de Carpintería",
        "Smelting": "Horno de Fundición",
        "Furnace": "Horno",
        "Base Building": "Construcción de Base",
        "Storage Chest": "Cofres y Organización",
        "Farming": "Farmeo de Recursos",
        "Resource Gathering": "Recolección de Recursos",
        "Weapon Workshop": "Banco de Armamento",
        "Guns": "Armas de Fuego",
        "Zombie Horde": "Horda de Zombis",
        "Fastest Way": "Forma Más Rápida",
        "Guide": "Guía",
        "Tips": "Consejos",
        "Looting": "Saqueo de Botín",
        "Crafting": "Crafteo",
        "Home Base": "Base Principal",
        "Pine Woods": "Bosque de Pinos",
        "Limestone Ridge": "Cresta de Caliza",
        "Crooked Creek Farm": "Granja",
        "Blackport PD": "Comisaría de Policía",
    },
}

LOCALIZED_DESCRIPTIONS = {
    "ru": {
        "greeting": "Добро пожаловать в Last Day on Earth: Survival! В выпуске #{episode} мы продолжаем выживание в зомби-апокалипсисе.",
        "body": "В этом видео: оптимизация базы, сбор ресурсов, эффективный крафт и подготовка к опасным вылазкам.",
        "cta": "Понравилось видео? Обязательно поставьте лайк 👍 и подпишитесь на канал 🔔, чтобы не пропустить новые серии и рейды!",
        "playlist": "📺 Плейлист всех серий выживания:",
    },
    "pt": {
        "greeting": "Bem-vindos ao Last Day on Earth: Survival! No episódio #{episode}, continuamos nossa jornada de sobrevivência no apocalipse zumbi.",
        "body": "Neste episódio: otimização da base, farm de recursos essenciais, crafting avançado e preparação para os desafios do wasteland.",
        "cta": "Gostou do vídeo? Deixe seu like 👍 e inscreva-se no canal 🔔 para acompanhar novos episódios e dicas de sobrevivência!",
        "playlist": "📺 Playlist oficial completa da série:",
    },
    "es": {
        "greeting": "¡Bienvenidos a Last Day on Earth: Survival! En el episodio #{episode}, continuamos sobreviviendo en el páramo zombi.",
        "body": "En este video: organización de base, farmeo eficiente de recursos, crafteo y preparación para los peligros del apocalipsis.",
        "cta": "¿Te gustó el video? ¡Deja tu like 👍 y suscríbete al canal 🔔 para no perderte nuevos episodios y guías de supervivencia!",
        "playlist": "📺 Lista de reproducción oficial de la serie:",
    },
}


class MetadataLocalizer:
    """Generates localized titles and descriptions for YouTube Data API v3."""

    SUPPORTED_LANGUAGES = ["ru", "pt", "es"]

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-2.5-flash",
    ) -> None:
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model

    def _is_gemini_configured(self) -> bool:
        """Checks if a valid, non-placeholder Gemini API key is available."""
        if not self.gemini_api_key:
            return False
        cleaned = self.gemini_api_key.strip()
        return bool(cleaned and cleaned != "your-gemini-api-key-here" and len(cleaned) > 10)

    def generate_localizations(
        self,
        primary_title: str,
        primary_description: str,
        episode_number: Optional[int] = None,
        playlist_url: Optional[str] = None,
        events: Optional[List[Any]] = None,
    ) -> Dict[str, Dict[str, str]]:
        """Generates localized metadata dictionaries for supported languages.
        
        Format compliant with YouTube Data API v3 'localizations':
        {
            "ru": {"title": "...", "description": "..."},
            "pt": {"title": "...", "description": "..."},
            "es": {"title": "...", "description": "..."}
        }
        """
        localizations: Dict[str, Dict[str, str]] = {}

        # Attempt AI generation if configured
        if self._is_gemini_configured():
            try:
                ai_localizations = self._generate_gemini_localizations(
                    primary_title=primary_title,
                    episode_number=episode_number,
                    playlist_url=playlist_url,
                )
                if ai_localizations:
                    logger.info(
                        "Generated YouTube localizations via Gemini AI",
                        extra_data={"languages": list(ai_localizations.keys())},
                    )
                    return ai_localizations
            except Exception as e:
                logger.warning(
                    f"Gemini AI localization failed ({e}); falling back to deterministic community engine."
                )

        # Deterministic community dictionary fallback
        for lang in self.SUPPORTED_LANGUAGES:
            loc_title = self._translate_title_rule_based(primary_title, lang, episode_number)
            loc_desc = self._generate_description_rule_based(
                primary_description=primary_description,
                lang=lang,
                episode_number=episode_number,
                playlist_url=playlist_url,
            )
            localizations[lang] = {
                "title": loc_title[:100],
                "description": loc_desc[:5000],
            }

        logger.info(
            "Synthesized deterministic YouTube metadata localizations",
            extra_data={"languages": list(localizations.keys())},
        )
        return localizations

    def _translate_title_rule_based(
        self,
        title: str,
        lang: str,
        episode_number: Optional[int] = None,
    ) -> str:
        """Translates an English YouTube title using domain vocabulary and regex substitution."""
        translated = title
        vocab = GAME_VOCABULARY.get(lang, {})

        # Replace episode prefix if present
        if episode_number:
            ep_patterns = [
                (r"#\s*(\d+)", f"#{episode_number}"),
                (r"Episode\s*#?\s*(\d+)", f"{vocab.get('Episode', 'Episode')} #{episode_number}"),
                (r"Ep\.\s*(\d+)", f"{vocab.get('Ep', 'Ep.')} {episode_number}"),
            ]
            for pat, repl in ep_patterns:
                translated = re.sub(pat, repl, translated, flags=re.IGNORECASE)

        # Replace known game phrases
        for en_term, target_term in vocab.items():
            pattern = re.compile(rf"\b{re.escape(en_term)}\b", re.IGNORECASE)
            translated = pattern.sub(target_term, translated)

        # Enforce max title length of 100 characters
        if len(translated) > 100:
            translated = translated[:97] + "..."

        return translated

    def _generate_description_rule_based(
        self,
        primary_description: str,
        lang: str,
        episode_number: Optional[int] = None,
        playlist_url: Optional[str] = None,
    ) -> str:
        """Constructs an engaging localized video description."""
        templates = LOCALIZED_DESCRIPTIONS.get(lang, LOCALIZED_DESCRIPTIONS["ru"])
        ep_val = episode_number or 1

        greeting = templates["greeting"].format(episode=ep_val)
        body = templates["body"]
        cta = templates["cta"]

        lines = [
            greeting,
            "",
            body,
            "",
            cta,
        ]

        if playlist_url:
            lines.extend([
                "",
                f"{templates['playlist']} {playlist_url}",
            ])

        # Extract and append timestamps/chapters from original description if present
        timestamps = self._extract_timestamps(primary_description)
        if timestamps:
            header_map = {
                "ru": "⏱️ ТАЙМКОДЫ И ГЛАВЫ:",
                "pt": "⏱️ CAPÍTULOS E TIMESTAMPS:",
                "es": "⏱️ CAPÍTULOS Y MARCAS DE TIEMPO:",
            }
            lines.extend([
                "",
                "────────────────────────────────────────",
                header_map.get(lang, "⏱️ CHAPTERS & TIMESTAMPS:"),
                *timestamps,
            ])

        return "\n".join(lines)

    def _extract_timestamps(self, text: str) -> List[str]:
        """Extracts valid YouTube timestamp lines (e.g., '00:00 - ...') from text."""
        timestamp_lines = []
        for line in text.splitlines():
            stripped = line.strip()
            # Match 00:00 or 0:00 patterns at line start
            if re.match(r"^\d{1,2}:\d{2}\s*[-–—]", stripped):
                timestamp_lines.append(stripped)
        return timestamp_lines

    def _generate_gemini_localizations(
        self,
        primary_title: str,
        episode_number: Optional[int] = None,
        playlist_url: Optional[str] = None,
    ) -> Optional[Dict[str, Dict[str, str]]]:
        """Uses Google GenAI / Gemini to produce natural localizations."""
        try:
            from google import genai
            import json

            client = genai.Client(api_key=self.gemini_api_key)
            prompt = (
                f"You are a YouTube Gaming localization expert for 'Last Day on Earth: Survival'.\n"
                f"Primary English Title: {primary_title}\n"
                f"Episode Number: {episode_number}\n\n"
                f"Translate and localize the video title and description into 3 languages:\n"
                f"1. Russian ('ru') - Kefir's home player base (use active Russian gamer terminology: Чоппер, Бункер Альфа, фарм, крафт)\n"
                f"2. Portuguese ('pt') - Brazilian mobile gaming community (use natural Brazilian Portuguese gamer slang)\n"
                f"3. Spanish ('es') - Latin American mobile gaming audience\n\n"
                f"Rules:\n"
                f"- Title MUST be <= 100 characters in each language.\n"
                f"- Description should be 2-3 engaging paragraphs with a Call-To-Action (Like & Subscribe).\n"
                f"- Return strict JSON with format:\n"
                f"{{\n"
                f'  "ru": {{"title": "...", "description": "..."}},\n'
                f'  "pt": {{"title": "...", "description": "..."}},\n'
                f'  "es": {{"title": "...", "description": "..."}}\n'
                f"}}\n"
                f"Return ONLY JSON."
            )

            response = client.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
            )
            raw_text = response.text.strip()
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)

            parsed = json.loads(raw_text)
            validated = {}
            for lang in ["ru", "pt", "es"]:
                if lang in parsed and "title" in parsed[lang] and "description" in parsed[lang]:
                    validated[lang] = {
                        "title": parsed[lang]["title"][:100],
                        "description": parsed[lang]["description"][:5000],
                    }
            return validated if len(validated) == 3 else None
        except Exception as e:
            logger.warning(f"Error calling Gemini for localization: {e}")
            return None
