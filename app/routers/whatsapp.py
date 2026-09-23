import requests
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from app.config import get_settings
from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.whatsapp import WhatsAppLinkRead, WhatsAppLinkStatus
from app.services import whatsapp_service
from app.services.rate_limit import check_rate_limit

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _require_twilio_configured() -> None:
    settings = get_settings()
    if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_whatsapp_number):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp integration is not configured",
        )


@router.post("/link", response_model=WhatsAppLinkRead)
def create_link(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> WhatsAppLinkRead:
    _require_twilio_configured()
    token = whatsapp_service.generate_link_token(session, current_user)
    number = get_settings().twilio_whatsapp_number.removeprefix("whatsapp:")
    wa_link = f"https://wa.me/{number.lstrip('+')}?text={token}"
    return WhatsAppLinkRead(token=token, wa_link=wa_link)


@router.get("/link", response_model=WhatsAppLinkStatus)
def get_link_status(current_user: User = Depends(get_current_user)) -> WhatsAppLinkStatus:
    return WhatsAppLinkStatus(
        linked=current_user.whatsapp_phone is not None, phone_number=current_user.whatsapp_phone
    )


@router.delete("/link", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    whatsapp_service.unlink(session, current_user)


@router.post("/webhook")
async def webhook(request: Request, session: Session = Depends(get_session)) -> Response:
    _require_twilio_configured()
    settings = get_settings()

    form = await request.form()
    params = {key: str(value) for key, value in form.multi_items()}
    signature = request.headers.get("X-Twilio-Signature", "")

    # Railway (and most PaaS reverse proxies) terminate TLS before this
    # process ever sees the request, so request.url often reports http://
    # even though Twilio actually called https://. Twilio's signature is
    # computed against the URL it really called, so the scheme must be
    # corrected from X-Forwarded-Proto before validating, or every request
    # fails validation behind such a proxy.
    forwarded_proto = request.headers.get("x-forwarded-proto")
    url = str(request.url.replace(scheme=forwarded_proto)) if forwarded_proto else str(request.url)

    validator = RequestValidator(settings.twilio_auth_token)
    if not validator.validate(url, params, signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")

    phone_number = params.get("From", "").removeprefix("whatsapp:")
    check_rate_limit(request, "whatsapp_webhook", limit=20, window_seconds=300, identifier=phone_number)

    body = params.get("Body")
    num_media = int(params.get("NumMedia") or "0")

    audio: tuple[bytes, str] | None = None
    if num_media > 0:
        media_url = params.get("MediaUrl0")
        content_type = params.get("MediaContentType0", "")
        if media_url and content_type.startswith("audio/"):
            media_response = requests.get(
                media_url,
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                timeout=15,
            )
            media_response.raise_for_status()
            audio = (media_response.content, content_type)

    reply_text = whatsapp_service.handle_incoming(session, phone_number, body, audio)

    twiml = MessagingResponse()
    twiml.message(reply_text)
    return Response(content=str(twiml), media_type="application/xml")
