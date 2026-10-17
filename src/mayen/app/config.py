"""Config'in okunması (§14): tek YAML, gizli bilgiler ortamda, prompt ayrı dosyada.

Göreli yollar config dosyasının yanına göredir: çalışma dizinine göre olsaydı, servisi başka
yerden başlatmak boş bir veritabanı ya da başka bir prompt açardı.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from mayen.core.context import LANGUAGE_SLOT
from mayen.core.models import ModelConfigError, ModelRegistry
from mayen.core.turns import TurnConfigError, Turns
from mayen.ports.models import ModelRecord
from mayen.ports.tools import Effect, Sensitivity
from mayen.ports.triggers import Fate, Priority, TriggerSource

ACTIVE_MODEL_ENV = "MAYEN_MODEL"

_records = TypeAdapter(dict[str, ModelRecord])


class ConfigError(Exception):
    """Kalıcı yapılandırma hatası: yeniden başlatmak düzeltmez (§14)."""


class _Strict(BaseModel):
    # Yanlış yazılmış bir anahtar sessizce yok sayılırsa varsayılanla çalışılır.
    model_config = ConfigDict(extra="forbid", frozen=True)


class StorageConfig(_Strict):
    path: Path


class PromptConfig(_Strict):
    system: Path
    language: Path  # bağlam bloğunun sonundaki dil kuralı, `{language}` yer tutucusuyla (§8.6)


class TriggerConfig(_Strict):
    voice_priority: Priority
    text_priority: Priority
    max_running: int = Field(ge=1)
    settle_s: float = Field(gt=0)
    response_timeout_s: float = Field(gt=0)
    fates: dict[TriggerSource, Fate]


class ConfirmationConfig(_Strict):
    timeout_s: float = Field(gt=0)


class LoopConfig(_Strict):
    """Ajan döngüsünün dış sınırı (§8.8, §9.1)."""

    max_steps: int = Field(ge=1)  # geçerli çağrı taşıyan cevap sayısı
    max_corrections: int = Field(ge=0)  # bütün çağrıları bozuk cevap sayısı; adım harcamaz


class ChannelConfig(_Strict):
    host: str
    port: int = Field(ge=1, le=65535)


class PanelConfig(_Strict):
    """Panel (§14). Tarayıcıda açık her sayfa sahibin cihazından bağlanabilir; bu yüzden
    yalnızca burada adı geçen adreslerden açılan panel bağlanır."""

    origins: list[str] = []  # tarayıcının Origin başlığıyla birebir karşılaştırılır
    dist: Path | None = None  # derlenmiş panel; verilirse çekirdek onu `/panel/` altında sunar


class WakeConfig(_Strict):
    """Wake word (§6); model STT servisinde, sözü de odur."""

    threshold: float = Field(gt=0, lt=1)  # modelin puanı bunu geçince uyanır
    follow_up_s: float = Field(ge=0)  # asistan sustuktan sonra wake word'süz söz başlama süresi


class SttConfig(_Strict):
    """STT model servisi (§3); model ve boyutu servisin kendi config'inde."""

    url: str
    language: str | None = None  # dinleme dili; verilmezse model kendisi bulur
    # Yoksa her söz tur açar; varsa yalnızca wake word, süren tur ve takip penceresi (§5.1).
    wake: WakeConfig | None = None
    # Varsa yazıya dökülen her sözün sesi (WAV) ve metni buraya yazılır; config'e göre yol.
    # Sahibin açık isteğiyle, izi yeniden çıkarmak için (§10.4: hangi sözün kimin olduğunu sahip
    # seçer). Silinmez, saklama süresi yok (§16.15 açık).
    record_dir: Path | None = None


class SpeakerConfig(_Strict):
    """Konuşmacı tanıma (§6): izi çıkaran model servisi ve izi kişiye çeviren eşik.

    Eşiğin varsayılanı yoktur: yanlış kabulün (başkası sahip sayılır) ve yanlış reddin (sahip
    tanınmaz, onay yeniden sorulur) bedeli eşit değildir; seçim config'i yazanındır.
    """

    url: str
    threshold: float = Field(gt=0, lt=1)  # kosinüs puanı; en yüksek puan bunu geçerse tanınır


class TtsConfig(_Strict):
    """TTS model servisi (§3). Her çıkış dilinin sesi (§16.3): anahtar, profildeki dil."""

    url: str
    voices: dict[str, str]


class _File(_Strict):
    storage: StorageConfig
    prompts: PromptConfig
    default_language: str  # tanınmayan kişiye konuşulan dil; tanınanınki profilinde (§8.6)
    triggers: TriggerConfig
    confirmation: ConfirmationConfig
    loop: LoopConfig
    channel: ChannelConfig
    panel: PanelConfig = PanelConfig()
    # Ses birimleri; yalnızca yazılı kanalla çalışan kurulumda yoktur (§7, kısmi çalışma).
    stt: SttConfig | None = None
    tts: TtsConfig | None = None
    # Yoksa söz cihazın kişisinindir (kişisel değilse tanımsız); varsa sesten tanınır (§6).
    speaker: SpeakerConfig | None = None
    # Kimse konuşmadan açılan turun yetkisi, turu açan kaynağa göre (§10.2).
    system_role: dict[TriggerSource, dict[Effect, list[Sensitivity]]]
    # Skill varsayılanlarının üzerine yazılanlar (§9.1); doğrulaması skill'ler bulununca.
    skills: dict[str, dict[str, Any]] = {}
    # Açılabilecek uygulamalar (§9.4): ad → `.desktop` kimliği; ad katalogda seçenek olur.
    apps: dict[str, str] = {}
    models: dict[str, ModelRecord]


@dataclass(frozen=True)
class Config:
    models: ModelRegistry
    storage_path: Path
    system_prompt: str
    language_rule: str
    default_language: str
    triggers: TriggerConfig
    confirmation: ConfirmationConfig
    loop: LoopConfig
    channel: ChannelConfig
    panel: PanelConfig
    stt: SttConfig | None
    tts: TtsConfig | None
    speaker: SpeakerConfig | None
    system_role: dict[TriggerSource, dict[Effect, list[Sensitivity]]]
    skills: dict[str, dict[str, Any]]
    apps: dict[str, str]

    def turns(self) -> Turns:
        return Turns(self.triggers.fates, self.triggers.max_running)


def _read(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: top level must be a mapping")
    return raw


def _relative(config: Path, path: Path) -> Path:
    return config.parent / path.expanduser()


def _language_rule(path: Path) -> str:
    rule = path.read_text(encoding="utf-8")
    if LANGUAGE_SLOT not in rule:
        # Yer tutucusuz kural her kişiye aynı dili söyler; profildeki tercih sessizce düşer.
        raise ConfigError(f"{path}: the language rule has no {LANGUAGE_SLOT}")
    return rule


def _panel(config: Path, panel: PanelConfig) -> PanelConfig:
    if panel.dist is None:
        return panel
    return panel.model_copy(update={"dist": _relative(config, panel.dist)})


def _stt(config: Path, stt: SttConfig | None) -> SttConfig | None:
    if stt is None or stt.record_dir is None:
        return stt
    return stt.model_copy(update={"record_dir": _relative(config, stt.record_dir)})


def _tts(tts: TtsConfig | None, default_language: str) -> TtsConfig | None:
    if tts is not None and default_language not in tts.voices:
        # Tanınmayan kişiye konuşulan dilin sesi yoksa ilk yabancıya asistan susar.
        raise ConfigError(f"tts.voices has no voice for default_language {default_language!r}")
    return tts


def _apps(apps: dict[str, str]) -> dict[str, str]:
    for name, entry in apps.items():
        if not entry or entry.startswith("-"):
            # Kimlik başlatıcının argv'sinde durur; tireyle başlayan değer bir seçenek olurdu.
            raise ConfigError(f"apps.{name}: {entry!r} is not a desktop entry id")
    return apps


def load(path: Path, env: Mapping[str, str]) -> Config:
    """Bütün config; her hata `ConfigError` olarak, açılışta yükselir."""
    try:
        file = _File.model_validate(_read(path))
        if ACTIVE_MODEL_ENV not in env:
            raise ModelConfigError(f"{ACTIVE_MODEL_ENV} is not set")
        config = Config(
            models=ModelRegistry(file.models, env[ACTIVE_MODEL_ENV], env),
            storage_path=_relative(path, file.storage.path),
            system_prompt=_relative(path, file.prompts.system).read_text(encoding="utf-8"),
            language_rule=_language_rule(_relative(path, file.prompts.language)),
            default_language=file.default_language,
            triggers=file.triggers,
            confirmation=file.confirmation,
            loop=file.loop,
            channel=file.channel,
            panel=_panel(path, file.panel),
            stt=_stt(path, file.stt),
            tts=_tts(file.tts, file.default_language),
            speaker=file.speaker,
            system_role=file.system_role,
            skills=file.skills,
            apps=_apps(file.apps),
        )
        config.turns()  # eksik ya da hatta karşılığı olmayan akıbet açılışta görünsün (§5.3)
    except (OSError, yaml.YAMLError, ValidationError, ModelConfigError, TurnConfigError) as e:
        raise ConfigError(str(e)) from e
    return config


def load_models(path: Path, env: Mapping[str, str]) -> ModelRegistry:
    """YAML'ın `models` bölümünden depo; etkin model ortamdan seçilir (§8.9)."""
    if ACTIVE_MODEL_ENV not in env:
        raise ModelConfigError(f"{ACTIVE_MODEL_ENV} is not set")
    raw = _read(path)
    return ModelRegistry(
        _records.validate_python(raw.get("models", {})), env[ACTIVE_MODEL_ENV], env
    )


def storage_path(path: Path) -> Path:
    """YAML'ın `storage` bölümünden veritabanı dosyası (§11.6); model gerekmez."""
    try:
        return _relative(path, StorageConfig.model_validate(_read(path).get("storage")).path)
    except (OSError, yaml.YAMLError, ValidationError) as e:
        raise ConfigError(str(e)) from e


def speaker_url(path: Path) -> str:
    """YAML'ın `speaker` bölümünden konuşmacı servisinin adresi; kurulum komutu için, model
    gerekmez."""
    try:
        section = _read(path).get("speaker")
        if section is None:
            raise ConfigError(f"{path}: no speaker section")
        return SpeakerConfig.model_validate(section).url
    except (OSError, yaml.YAMLError, ValidationError) as e:
        raise ConfigError(str(e)) from e
