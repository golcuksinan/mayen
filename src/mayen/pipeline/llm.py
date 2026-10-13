"""Bir rolün Pipecat model servisi, model deposundaki ayarlarla (§8.9, §8.10)."""

from pipecat.services.openai.llm import OpenAILLMService

from mayen.ports.models import NO_KEY, Endpoint


def llm_service(endpoint: Endpoint, system_instruction: str) -> OpenAILLMService:
    """Ayarlar gövdeyle her istekte gider; sunucunun varsayılanı rol farkını bilmez."""
    service = OpenAILLMService(
        base_url=endpoint.base_url,
        api_key=endpoint.api_key.get_secret_value() if endpoint.api_key else NO_KEY,
        settings=OpenAILLMService.Settings(
            model=endpoint.model,
            system_instruction=system_instruction,
            extra={"extra_body": dict(endpoint.body)},
        ),
    )
    # Şablon ortadaki geliştirici mesajını reddediyorsa Pipecat onu kullanıcı mesajına çevirir.
    service.supports_developer_role = endpoint.developer_role
    return service
