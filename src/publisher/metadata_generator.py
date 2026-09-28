"""Dynamic YouTube metadata and trending tags generator.

Generates:
- Around 50 dynamic, high-engagement trending hashtags for YouTube video descriptions.
- Dynamic video keyword tags for YouTube's tags metadata (under 500 chars).
- Context-aware video descriptions and chapter timestamps based on gameplay events.

Supports:
- Google Gemini API integration (when GEMINI_API_KEY is configured).
- Intelligent, deterministic dynamic algorithmic fallback with multi-cluster contextual matching
  and seeded rotation (when offline or without API key).
"""

import hashlib
import random
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.logging_config import get_logger

logger = get_logger(component="MetadataGenerator")


class DynamicTagGenerator:
    """Generates ~50 trending tags dynamically for YouTube descriptions and metadata."""

    # Core high-authority LDoE pillar hashtags (always included at start)
    CORE_PILLAR_HASHTAGS = [
        "#LastDayOnEarth",
        "#LDoE",
        "#LastDayOnEarthSurvival",
        "#LDoEGameplay",
        "#LDoESurvival",
        "#LDoEGuide",
        "#KefirGames",
    ]

    # Contextual gameplay clusters matched dynamically against video events & title
    EVENT_CLUSTERS: Dict[str, List[str]] = {
        "crafting_woodworking": [
            "#LDoECrafting",
            "#WoodworkingBench",
            "#PlankCrafting",
            "#BaseBuilding",
            "#LDoEWorkshop",
            "#WorkbenchUpgrade",
            "#CraftingEssentials",
            "#CarpentrySurvival",
            "#BaseConstruction",
            "#Woodworking",
        ],
        "smelting_furnace": [
            "#SmeltingFurnace",
            "#IronSmelting",
            "#FurnaceFuel",
            "#MetalSmelting",
            "#ResourceSmelting",
            "#RefiningOres",
            "#CharcoalMaking",
            "#IronOreLDoE",
        ],
        "weapons_combat": [
            "#WeaponBench",
            "#Gunsmith",
            "#LDoEWeapons",
            "#WeaponModding",
            "#ZombieHunter",
            "#ZombieCombat",
            "#MeleeWeapons",
            "#Glock17",
            "#Gunsmithing",
            "#WeaponCrafting",
            "#AK47Mod",
            "#M16Gameplay",
        ],
        "storage_organization": [
            "#LDoEStorage",
            "#StorageChests",
            "#BaseOrganization",
            "#ResourceHoarding",
            "#BaseDesign",
            "#HomeBaseSetup",
            "#OrganizingChests",
            "#BaseExpansion",
            "#ChestSorting",
            "#LDoEBase",
        ],
        "blueprints_tech": [
            "#CheckingBlueprints",
            "#LDoEBlueprints",
            "#SurvivalTech",
            "#CraftingBlueprints",
            "#LDoEProgression",
            "#RecipeUnlock",
            "#TechTreeLDoE",
        ],
        "bunker_raids": [
            "#BunkerAlfa",
            "#BunkerBravo",
            "#LDoERaid",
            "#LDoEBunker",
            "#Floor2Run",
            "#Floor3Run",
            "#TerminalCode",
            "#BlindOneRun",
            "#C4Breach",
            "#AlfaFloor3",
            "#TicketExchange",
        ],
        "map_exploration": [
            "#GlobalMap",
            "#ResourceFarming",
            "#PineWoods",
            "#LimestoneRidge",
            "#WastelandScavenger",
            "#ChopperRide",
            "#EnergyRefill",
            "#LDoEFarming",
            "#OakGladeRun",
            "#RedZoneFarming",
        ],
        "settlement": [
            "#LDoESettlement",
            "#SettlementDefense",
            "#Substation",
            "#Barricades",
            "#ExpeditionRun",
            "#VanUpgrade",
            "#MercenaryLDoE",
            "#SettlementExpansion",
        ],
        "zombie_survival": [
            "#ZombieSurvival",
            "#SurvivalGame",
            "#ZombieApocalypse",
            "#SurvivalGaming",
            "#PostApocalyptic",
            "#SurvivalCraft",
            "#ZombieGame",
            "#SurviveTheApocalypse",
            "#ZombieHorde",
            "#ZombieAttack",
            "#BaseDefense",
            "#ZombieSurvivalGame",
            "#SurvivalRun",
            "#WastelandSurvival",
            "#ApocalypseSurvival",
            "#ZombieDefense",
            "#UndeadSurvival",
            "#LastDayOnEarthTips",
        ],
    }

    # Dynamic pool of high-velocity trending YouTube gaming tags for algorithmic reach
    TRENDING_GAMING_POOL = [
        "#MobileGaming",
        "#Gaming",
        "#Gamer",
        "#GamingCommunity",
        "#GameWalkthrough",
        "#AndroidGaming",
        "#iOSGaming",
        "#GamingClips",
        "#Gameplay",
        "#LetsPlay",
        "#YouTubeGaming",
        "#GamingVideos",
        "#Trending",
        "#ViralGaming",
        "#ExplorePage",
        "#GamingLife",
        "#ProGamer",
        "#SurvivalCrafting",
        "#MobileGames",
        "#ZombieSurvivalRun",
        "#GamingTips",
        "#Walkthrough",
        "#GameGuide",
        "#IndieGaming",
        "#TrendingGame",
        "#TopMobileGames",
        "#SurvivalChallenge",
        "#ActionGame",
        "#GamingReels",
        "#GamingStrategy",
        "#WalkthroughGameplay",
        "#GameStreamer",
        "#EpicGaming",
        "#MobileGame2026",
        "#SurvivalGuide",
        "#HardcoreSurvival",
        "#NoDamageRun",
        "#ProGameplay",
        "#GameMoments",
        "#GameAddict",
        "#GamerVibes",
        "#VideoGame",
        "#BestMobileGames",
        "#GamingShorts",
        "#GamingCreator",
        "#SurvivalHorror",
        "#PlaythroughGuide",
        "#OpenWorldSurvival",
        "#SandboxGaming",
        "#ApocalypseGame",
        "#CasualGaming",
        "#GamingContent",
        "#GamerNation",
    ]

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-2.5-flash",
        target_hashtag_count: int = 50,
    ) -> None:
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self.target_hashtag_count = target_hashtag_count

    def generate_dynamic_hashtags(
        self,
        video_title: str,
        events: List[Any],
        date_str: Optional[str] = None,
    ) -> List[str]:
        """Generates around 50 dynamic hashtags tailored to the video's gameplay content.
        
        Attempts Gemini AI generation first if configured, falling back to dynamic
        multi-cluster contextual algorithmic selection.
        """
        date_str = date_str or datetime.now().strftime("%d %b, %Y")

        # 1. Attempt Gemini AI Generation if configured
        if self._is_gemini_configured():
            try:
                ai_tags = self._generate_gemini_hashtags(video_title, events, date_str)
                if ai_tags and len(ai_tags) >= 40:
                    logger.info(
                        f"Generated {len(ai_tags)} dynamic trending hashtags via Gemini AI",
                        extra_data={"model": self.gemini_model},
                    )
                    return self._finalize_hashtag_list(ai_tags)
                else:
                    logger.warning("Gemini AI returned insufficient hashtags; falling back to dynamic algorithmic generator.")
            except Exception as e:
                logger.warning(f"Gemini AI tag generation failed ({e}); falling back to dynamic algorithmic generator.")

        # 2. Dynamic Algorithmic Engine (offline, deterministic, content-aware)
        return self._generate_algorithmic_hashtags(video_title, events, date_str)

    def _is_gemini_configured(self) -> bool:
        """Checks if a valid, non-placeholder Gemini API key is available."""
        if not self.gemini_api_key:
            return False
        cleaned = self.gemini_api_key.strip()
        return bool(cleaned and cleaned != "your-gemini-api-key-here" and len(cleaned) > 10)

    def _generate_gemini_hashtags(
        self,
        video_title: str,
        events: List[Any],
        date_str: str,
    ) -> List[str]:
        """Calls Google GenAI API to generate ~50 trending hashtags."""
        from google import genai

        event_descriptions = [getattr(ev, "description", str(ev)) for ev in events]
        chapters_text = ", ".join(event_descriptions) if event_descriptions else "Home Base, Crafting, Survival"

        prompt = (
            f"You are a YouTube Gaming SEO and algorithm optimization expert specializing in 'Last Day on Earth: Survival'.\n\n"
            f"Video Title: {video_title}\n"
            f"Episode Date: {date_str}\n"
            f"Key Gameplay Events & Chapters: {chapters_text}\n\n"
            f"Generate exactly 50 trending, high-engagement YouTube hashtags (prefixed with #) for the description.\n"
            f"Guidelines:\n"
            f"1. Include core LDoE hashtags (#LastDayOnEarth, #LDoE, etc.).\n"
            f"2. Include specific gameplay hashtags matching the exact actions above (e.g. woodworking, smelting, weapon bench, chests).\n"
            f"3. Include high-velocity trending mobile gaming and zombie survival hashtags to maximize reach.\n"
            f"4. Format: space-separated hashtags only (e.g. #LastDayOnEarth #LDoE #ZombieSurvival ...).\n"
            f"5. Return ONLY the hashtags, no other text or explanation."
        )

        client = genai.Client(api_key=self.gemini_api_key)
        response = client.models.generate_content(
            model=self.gemini_model,
            contents=prompt,
        )
        text = response.text if hasattr(response, "text") else ""

        # Extract all hashtags
        raw_hashtags = re.findall(r"#\w+", text)
        return raw_hashtags

    def _generate_algorithmic_hashtags(
        self,
        video_title: str,
        events: List[Any],
        date_str: str,
    ) -> List[str]:
        """Generates dynamic hashtags by analyzing video content, events, and dynamic rotation."""
        combined_text = f"{video_title.lower()} " + " ".join(
            getattr(ev, "description", "").lower() for ev in events
        )

        # 1. Start with core pillar hashtags
        selected: List[str] = list(self.CORE_PILLAR_HASHTAGS)

        # 2. Identify relevant clusters based on event & title keywords
        contextual_cluster_tags: List[str] = []
        cluster_weights: Dict[str, int] = {}

        keyword_mappings = {
            "crafting_woodworking": ["craft", "wood", "plank", "workbench", "workshop"],
            "smelting_furnace": ["smelt", "furnace", "iron", "ore", "fuel", "charcoal"],
            "weapons_combat": ["weapon", "gun", "bench", "combat", "fight", "hunter", "glock", "rifle"],
            "storage_organization": ["storage", "chest", "organize", "base", "hoard", "item"],
            "blueprints_tech": ["blueprint", "tech", "recipe", "progress"],
            "bunker_raids": ["bunker", "alfa", "bravo", "raid", "c4", "blind one"],
            "map_exploration": ["map", "farm", "woods", "ridge", "chopper", "scaveng"],
            "settlement": ["settlement", "substation", "barricade", "expedition"],
            "zombie_survival": ["zombie", "survival", "apocalypse", "horde", "defense", "undead"],
        }

        for cluster_name, keywords in keyword_mappings.items():
            matches = sum(1 for kw in keywords if kw in combined_text)
            if matches > 0:
                cluster_weights[cluster_name] = matches

        # Deterministic seed based on title, date, and events for dynamic yet reproducible rotation
        seed_str = f"{video_title}_{date_str}_{len(events)}_{combined_text[:50]}"
        seed_val = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
        rng = random.Random(seed_val)

        # Prioritize matching clusters
        sorted_clusters = sorted(cluster_weights.keys(), key=lambda c: cluster_weights[c], reverse=True)

        for cluster_name in sorted_clusters:
            tags = list(self.EVENT_CLUSTERS[cluster_name])
            rng.shuffle(tags)
            contextual_cluster_tags.extend(tags)

        # Also pull some tags from other clusters for variety
        for cluster_name, tags in self.EVENT_CLUSTERS.items():
            if cluster_name not in sorted_clusters:
                shuffled_tags = list(tags)
                rng.shuffle(shuffled_tags)
                contextual_cluster_tags.extend(shuffled_tags[:3])

        # 3. Pull from trending gaming pool with seeded rotation
        shuffled_trending = list(self.TRENDING_GAMING_POOL)
        rng.shuffle(shuffled_trending)

        # Combine: Core pillars -> High-priority contextual tags -> Rotated trending tags
        candidate_tags = selected + contextual_cluster_tags + shuffled_trending

        return self._finalize_hashtag_list(candidate_tags)

    def _finalize_hashtag_list(self, raw_tags: List[str]) -> List[str]:
        """Cleans, formats, deduplicates (case-insensitively), and trims/pads to target count."""
        seen_lower = set()
        deduped: List[str] = []

        for tag in raw_tags:
            tag = tag.strip()
            if not tag:
                continue
            if not tag.startswith("#"):
                tag = f"#{tag}"

            # Remove invalid characters
            tag = re.sub(r"[^#\w]", "", tag)
            if len(tag) <= 1:
                continue

            tag_lower = tag.lower()
            if tag_lower not in seen_lower:
                seen_lower.add(tag_lower)
                deduped.append(tag)

            if len(deduped) >= self.target_hashtag_count:
                break

        # If still short of target_hashtag_count, pad from backup pool
        if len(deduped) < self.target_hashtag_count:
            for tag in self.TRENDING_GAMING_POOL + self.CORE_PILLAR_HASHTAGS:
                tag_lower = tag.lower()
                if tag_lower not in seen_lower:
                    seen_lower.add(tag_lower)
                    deduped.append(tag)
                if len(deduped) >= self.target_hashtag_count:
                    break

        return deduped[: self.target_hashtag_count]

    def calculate_youtube_tags_length(self, tags: List[str]) -> int:
        """Calculates exact serialized length as evaluated by YouTube API v3.
        
        YouTube wraps keywords containing spaces in double quotes, and separates tags with commas.
        Example: ['LDoE', 'Last Day on Earth'] -> 'LDoE,"Last Day on Earth"' (length: 4 + 1 + 21 = 26).
        """
        if not tags:
            return 0
        return sum((len(t) + 2 if " " in t else len(t)) for t in tags) + (len(tags) - 1)

    def generate_video_tags(
        self,
        video_title: str,
        events: List[Any],
        hashtags: List[str],
        max_chars: int = 400,
    ) -> List[str]:
        """Generates dynamic keyword tags for YouTube's metadata.tags field (no #, <= 500 chars).
        
        YouTube API v3 constraints:
        - Total serialized tags string (including commas and quotation marks around multi-word tags)
          MUST not exceed 500 characters.
        - Angle brackets '<' and '>', commas, and quotes are forbidden in individual tag keywords.
        """
        base_tags = [
            "Last Day on Earth",
            "Last Day on Earth Survival",
            "LDoE",
            "LDoE Gameplay",
            "Zombie Survival Mobile",
            "Kefir Games",
            "Mobile Gaming",
        ]

        # Extract words from events and hashtags
        extracted: List[str] = []
        for ev in events:
            desc = getattr(ev, "description", "")
            if desc:
                # Replace ampersands and sanitize
                clean_desc = desc.replace("&", "and")
                clean_desc = re.sub(r"[^\w\s-]", "", clean_desc).strip()
                clean_desc = re.sub(r"\s+", " ", clean_desc)
                if clean_desc and clean_desc not in extracted:
                    extracted.append(f"LDoE {clean_desc}")
                    extracted.append(clean_desc)

        for ht in hashtags:
            clean = ht.lstrip("#")
            # Separate camelcase words if needed, preserving 'LDoE'
            if clean.lower().startswith("ldoe"):
                remainder = clean[4:]
                if remainder:
                    spaced_remainder = re.sub(r"([a-z])([A-Z])", r"\1 \2", remainder)
                    spaced = f"LDoE {spaced_remainder}".strip()
                else:
                    spaced = "LDoE"
            else:
                spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", clean)

            spaced = re.sub(r"[^\w\s-]", "", spaced).strip()
            spaced = re.sub(r"\s+", " ", spaced)
            if spaced and len(spaced) > 2 and spaced not in extracted:
                extracted.append(spaced)

        all_candidate_tags = base_tags + extracted
        final_tags: List[str] = []
        total_len = 0
        seen = set()

        for t in all_candidate_tags:
            # Clean forbidden characters: commas, angle brackets, quotes, newlines
            t = re.sub(r'[<>,"]', "", t).strip()
            if not t or len(t) < 2 or len(t) > 60:
                continue

            t_lower = t.lower()
            if t_lower in seen:
                continue
            seen.add(t_lower)

            # Compute serialized YouTube cost: quotes for spaced tags + comma separator
            tag_cost = (len(t) + 2 if " " in t else len(t)) + (1 if final_tags else 0)
            if total_len + tag_cost > max_chars:
                break

            final_tags.append(t)
            total_len += tag_cost

        return final_tags

